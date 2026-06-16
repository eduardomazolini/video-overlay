"""Modelo de overlays — tratados como DADOS, não como código.

Você tem 8 assets possíveis: 4 cantos x {logo, borda}. Em cada render,
exatamente UM canto recebe o logo e os outros 3 recebem borda. A convenção
de nome de arquivo permite escolher o conjunto certo sem hard-code:

    assets/overlays/top_left_logo.png
    assets/overlays/top_left_border.png
    assets/overlays/top_right_logo.png
    ... etc

No futuro, trocar PNG por WebM/VP9 com alpha (animação complexa) só muda o
asset_path — o resto do pipeline continua igual. Fade in/out já é resolvido
pelo ffmpeg sobre o PNG estático (ver ffmpeg_builder.py).
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Corner(str, Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass
class Overlay:
    asset_path: str  # caminho do PNG (ou futuramente .webm/.mov com alpha)
    corner: Corner  # em qual canto posicionar
    margin: int = 40  # distância da borda, em px
    fade_in: float = 0.0  # duração do fade in, em segundos (0 = sem fade)
    fade_out: float = 0.0  # duração do fade out, em segundos (0 = sem fade)


def corner_position(corner: Corner, margin: int) -> tuple[str, str]:
    """Retorna as expressões (x, y) do filtro overlay do ffmpeg.

    W/H = dimensões do vídeo base; w/h = dimensões do overlay.
    """
    m = margin
    return {
        Corner.TOP_LEFT: (f"{m}", f"{m}"),
        Corner.TOP_RIGHT: (f"W-w-{m}", f"{m}"),
        Corner.BOTTOM_LEFT: (f"{m}", f"H-h-{m}"),
        Corner.BOTTOM_RIGHT: (f"W-w-{m}", f"H-h-{m}"),
    }[corner]


def build_overlay_set(
    logo_corner: Corner,
    assets_dir: Path,
    *,
    hidden_borders: "set[Corner] | list[Corner] | tuple[Corner, ...]" = (),
    margin: int = 40,
    border_fade_in: float = 0.0,
    border_fade_out: float = 0.0,
) -> list[Overlay]:
    """Monta os overlays do render: logo no canto escolhido, borda nos outros.

    - O LOGO fica sempre visível (sem fade), para servir de thumbnail.
    - As BORDAS fazem fade in/out e podem ser ocultadas individualmente
      (`hidden_borders`).

    Ignora silenciosamente assets que não existem no disco, então funciona
    mesmo com o conjunto de PNGs incompleto durante o desenvolvimento.
    """
    hidden = set(hidden_borders)
    overlays: list[Overlay] = []
    for corner in Corner:
        is_logo = corner == logo_corner
        if not is_logo and corner in hidden:
            continue  # usuário optou por ocultar esta borda
        kind = "logo" if is_logo else "border"
        path = assets_dir / f"{corner.value}_{kind}.png"
        if not path.exists():
            continue
        overlays.append(
            Overlay(
                asset_path=str(path),
                corner=corner,
                margin=margin,
                # Logo: sem fade (permanece). Borda: fade in/out.
                fade_in=0.0 if is_logo else border_fade_in,
                fade_out=0.0 if is_logo else border_fade_out,
            )
        )
    return overlays
