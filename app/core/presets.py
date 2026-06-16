"""Presets de proporção (aspect ratio) por rede social.

Adicionar uma rede nova = adicionar uma entrada aqui. Nenhuma outra parte
do código precisa mudar.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AspectPreset:
    key: str  # identificador usado na API
    label: str  # nome amigável
    width: int  # largura final em px
    height: int  # altura final em px


PRESETS: dict[str, AspectPreset] = {
    "reels": AspectPreset("reels", "Reels / TikTok / Shorts (9:16)", 1080, 1920),
    "feed_vertical": AspectPreset("feed_vertical", "Feed vertical (4:5)", 1080, 1350),
    "quadrado": AspectPreset("quadrado", "Feed quadrado (1:1)", 1080, 1080),
    "horizontal": AspectPreset("horizontal", "YouTube / horizontal (16:9)", 1920, 1080),
}


def get_preset(key: str) -> AspectPreset:
    try:
        return PRESETS[key]
    except KeyError:
        raise ValueError(f"Preset desconhecido: {key!r}. Opções: {', '.join(PRESETS)}") from None
