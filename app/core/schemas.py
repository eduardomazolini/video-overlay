"""Contrato de dados entre as interfaces (web/telegram) e o core.

Como o Celery serializa o job para o Redis, o pedido precisa ser um objeto
simples e serializável. Por isso usamos pydantic e passamos um `dict`.
"""

from typing import Literal

from pydantic import BaseModel, Field

from .overlays import Corner


class ProcessRequest(BaseModel):
    """Tudo que o core precisa para processar um vídeo.

    Independente de web ou Telegram: ambas as interfaces só preenchem isto.
    """

    input_path: str  # vídeo enviado pelo usuário
    preset_key: str  # qual proporção (ver presets.py)
    logo_corner: Corner = Corner.BOTTOM_RIGHT  # canto que recebe o logo
    hidden_borders: list[Corner] = Field(default_factory=list)  # bordas a ocultar
    fit_mode: Literal["crop", "blur"] = "crop"  # cortar ou fundo borrado
    crop_gravity: Literal["center", "top", "bottom"] = "center"  # posição do corte (só p/ crop)
    margin: int = 40
    # Fade aplicado só às BORDAS; o logo permanece visível (vira thumbnail).
    border_fade_in: float = 0.0
    border_fade_out: float = 0.0
    crf: int = Field(default=20, ge=0, le=51)  # qualidade (menor = melhor)
