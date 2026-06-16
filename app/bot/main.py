"""Bot do Telegram (aiogram v3).

Reaproveita o MESMO core e a MESMA fila da web: o handler só coleta as
escolhas do usuário, monta um ProcessRequest e chama process_video_task.

Fluxo:
  1. usuário envia um vídeo  -> bot baixa e pergunta a proporção;
  2. usuário escolhe proporção -> bot pergunta o canto do logo;
  3. usuário escolhe o canto   -> bot enfileira o job e, ao terminar,
     devolve o vídeo processado.

Rodar:  python -m app.bot.main   (precisa de TELEGRAM_BOT_TOKEN no ambiente)
"""

import asyncio
import logging
import uuid
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, FSInputFile, Message
from celery.result import AsyncResult

from app import settings
from app.bot.keyboards import (
    CORNER_CB,
    CROP_CB,
    DONE_CB,
    FIT_CB,
    PRESET_CB,
    TOGGLE_CB,
    borders_keyboard,
    corners_keyboard,
    crop_keyboard,
    fit_keyboard,
    presets_keyboard,
)
from app.core.overlays import Corner
from app.core.schemas import ProcessRequest
from app.worker.celery_app import celery_app
from app.worker.tasks import process_video_task

logging.basicConfig(level=logging.INFO)


class Flow(StatesGroup):
    """Estados da conversa, guardados pelo FSM do aiogram."""

    choosing_preset = State()
    choosing_corner = State()
    choosing_fit = State()
    choosing_crop = State()
    choosing_borders = State()


dp = Dispatcher(storage=MemoryStorage())


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Olá! Me envie um vídeo e eu corto na proporção da rede e aplico os "
        "overlays da sua marca. 🎬\n\nÉ só mandar o vídeo para começar."
    )


@dp.message(F.video | F.document)
async def on_video(message: Message, state: FSMContext, bot: Bot):
    # Aceita vídeo nativo ou enviado como documento.
    media = message.video or message.document

    # Valida tamanho antes de baixar (Telegram informa file_size).
    if media.file_size and media.file_size > settings.MAX_UPLOAD_BYTES:
        await message.answer(f"❌ Arquivo maior que {settings.MAX_UPLOAD_MB} MB.")
        return

    file = await bot.get_file(media.file_id)
    suffix = (Path(file.file_path).suffix or ".mp4").lower()
    if suffix not in settings.ALLOWED_VIDEO_EXTENSIONS:
        await message.answer(
            f"❌ Formato {suffix} não suportado. Aceitos: "
            f"{', '.join(sorted(settings.ALLOWED_VIDEO_EXTENSIONS))}"
        )
        return

    input_path = settings.UPLOADS_DIR / f"{uuid.uuid4().hex}{suffix}"
    await bot.download_file(file.file_path, destination=input_path)

    await state.update_data(input_path=str(input_path))
    await state.set_state(Flow.choosing_preset)
    await message.answer("Recebido! Qual a proporção?", reply_markup=presets_keyboard())


@dp.callback_query(Flow.choosing_preset, F.data.startswith(f"{PRESET_CB}:"))
async def on_preset(callback: CallbackQuery, state: FSMContext):
    preset_key = callback.data.split(":", 1)[1]
    await state.update_data(preset_key=preset_key)
    await state.set_state(Flow.choosing_corner)
    await callback.message.edit_text("Em qual canto fica o logo?", reply_markup=corners_keyboard())
    await callback.answer()


@dp.callback_query(Flow.choosing_corner, F.data.startswith(f"{CORNER_CB}:"))
async def on_corner(callback: CallbackQuery, state: FSMContext):
    logo_corner = callback.data.split(":", 1)[1]
    await state.update_data(logo_corner=logo_corner)
    await state.set_state(Flow.choosing_fit)
    await callback.message.edit_text(
        "Como encaixar na proporção quando o vídeo não bate certinho?",
        reply_markup=fit_keyboard(),
    )
    await callback.answer()


async def _ask_borders(callback: CallbackQuery, state: FSMContext):
    """Avança para o passo de ocultar bordas (reutilizado por crop e blur)."""
    await state.set_state(Flow.choosing_borders)
    data = await state.get_data()
    await callback.message.edit_text(
        "Toque para ocultar/mostrar bordas. Depois, gere o vídeo:",
        reply_markup=borders_keyboard(Corner(data["logo_corner"]), []),
    )


@dp.callback_query(Flow.choosing_fit, F.data.startswith(f"{FIT_CB}:"))
async def on_fit(callback: CallbackQuery, state: FSMContext):
    fit_mode = callback.data.split(":", 1)[1]
    await state.update_data(fit_mode=fit_mode, crop_gravity="center", hidden_borders=[])
    if fit_mode == "crop":
        # Só no modo "cortar" faz sentido escolher a posição do corte.
        await state.set_state(Flow.choosing_crop)
        await callback.message.edit_text("Onde cortar o vídeo?", reply_markup=crop_keyboard())
    else:
        await _ask_borders(callback, state)
    await callback.answer()


@dp.callback_query(Flow.choosing_crop, F.data.startswith(f"{CROP_CB}:"))
async def on_crop(callback: CallbackQuery, state: FSMContext):
    crop_gravity = callback.data.split(":", 1)[1]
    await state.update_data(crop_gravity=crop_gravity)
    await _ask_borders(callback, state)
    await callback.answer()


@dp.callback_query(Flow.choosing_borders, F.data.startswith(f"{TOGGLE_CB}:"))
async def on_toggle_border(callback: CallbackQuery, state: FSMContext):
    corner = callback.data.split(":", 1)[1]
    data = await state.get_data()
    hidden: list[str] = data.get("hidden_borders", [])
    if corner in hidden:
        hidden.remove(corner)
    else:
        hidden.append(corner)
    await state.update_data(hidden_borders=hidden)
    await callback.message.edit_reply_markup(
        reply_markup=borders_keyboard(Corner(data["logo_corner"]), hidden)
    )
    await callback.answer()


@dp.callback_query(Flow.choosing_borders, F.data == DONE_CB)
async def on_done(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    req = ProcessRequest(
        input_path=data["input_path"],
        preset_key=data["preset_key"],
        logo_corner=Corner(data["logo_corner"]),
        fit_mode=data.get("fit_mode", "crop"),
        crop_gravity=data.get("crop_gravity", "center"),
        hidden_borders=data.get("hidden_borders", []),
        border_fade_in=0.5,
        border_fade_out=0.5,
    )
    task = process_video_task.delay(req.model_dump(mode="json"))

    await state.clear()
    await callback.message.edit_text("⏳ Processando seu vídeo...")
    await callback.answer()

    # Acompanha o job e devolve o resultado quando pronto (sem bloquear o bot).
    asyncio.create_task(_deliver_when_ready(bot, callback.message.chat.id, task.id))


async def _deliver_when_ready(bot: Bot, chat_id: int, job_id: str, timeout: int = 600):
    """Faz polling do resultado do Celery e envia o vídeo final."""
    result = AsyncResult(job_id, app=celery_app)
    waited = 0
    while not result.ready() and waited < timeout:
        await asyncio.sleep(2)
        waited += 2

    if result.successful():
        await bot.send_video(chat_id, FSInputFile(result.result), caption="✅ Pronto!")
    elif result.failed():
        await bot.send_message(chat_id, f"❌ Falha no processamento: {result.result}")
    else:
        await bot.send_message(chat_id, "⌛ O processamento demorou demais. Tente novamente.")


async def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Defina TELEGRAM_BOT_TOKEN no ambiente (veja .env.example).")
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
