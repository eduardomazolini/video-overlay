"""Teclados inline do bot, montados a partir dos mesmos dados do core."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.overlays import Corner
from app.core.presets import PRESETS

# Prefixos de callback_data para distinguir as escolhas.
PRESET_CB = "preset"
CORNER_CB = "corner"
FIT_CB = "fit"  # crop x blur
CROP_CB = "crop"
TOGGLE_CB = "toggle"  # alterna ocultar/mostrar uma borda
DONE_CB = "done"  # confirma e gera o vídeo

CORNER_LABELS = {
    Corner.TOP_LEFT: "↖ Superior esquerdo",
    Corner.TOP_RIGHT: "↗ Superior direito",
    Corner.BOTTOM_LEFT: "↙ Inferior esquerdo",
    Corner.BOTTOM_RIGHT: "↘ Inferior direito",
}


def presets_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in PRESETS.values():
        kb.button(text=p.label, callback_data=f"{PRESET_CB}:{p.key}")
    kb.adjust(1)
    return kb.as_markup()


def corners_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for corner in Corner:
        kb.button(text=CORNER_LABELS[corner], callback_data=f"{CORNER_CB}:{corner.value}")
    kb.adjust(2)
    return kb.as_markup()


def fit_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✂️ Cortar (preenche o quadro)", callback_data=f"{FIT_CB}:crop")
    kb.button(text="🌫 Fundo borrado (vídeo inteiro)", callback_data=f"{FIT_CB}:blur")
    kb.adjust(1)
    return kb.as_markup()


def crop_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for value, label in (("center", "Centro"), ("top", "Topo"), ("bottom", "Base")):
        kb.button(text=label, callback_data=f"{CROP_CB}:{value}")
    kb.adjust(3)
    return kb.as_markup()


def borders_keyboard(logo_corner: Corner, hidden: list[str]) -> InlineKeyboardMarkup:
    """Teclado para alternar quais bordas ocultar (o canto do logo não entra)."""
    kb = InlineKeyboardBuilder()
    for corner in Corner:
        if corner == logo_corner:
            continue  # o canto do logo é sempre mantido
        mark = "🚫" if corner.value in hidden else "✅"
        kb.button(
            text=f"{mark} {CORNER_LABELS[corner]}", callback_data=f"{TOGGLE_CB}:{corner.value}"
        )
    kb.button(text="▶️ Gerar vídeo", callback_data=DONE_CB)
    kb.adjust(1)
    return kb.as_markup()
