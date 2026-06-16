"""Testes do montador do comando ffmpeg (função pura — sem rodar ffmpeg)."""

import pytest

from app.core.ffmpeg_builder import build_command
from app.core.overlays import Corner, Overlay
from app.core.presets import AspectPreset

PRESET = AspectPreset("reels", "Reels", 1080, 1920)


def _filter_complex(cmd):
    """Extrai a string do filtergraph do comando."""
    return cmd[cmd.index("-filter_complex") + 1]


def _logo():
    return Overlay(asset_path="/x/bottom_right_logo.png", corner=Corner.BOTTOM_RIGHT)


def _border(fade=0.0):
    return Overlay(
        asset_path="/x/top_left_border.png",
        corner=Corner.TOP_LEFT,
        fade_in=fade,
        fade_out=fade,
    )


def test_crop_mode_usa_cover_e_crop():
    cmd = build_command("in.mp4", "out.mp4", PRESET, [], 5.0, fit_mode="crop")
    fc = _filter_complex(cmd)
    assert "force_original_aspect_ratio=increase" in fc
    assert "crop=1080:1920" in fc
    assert "gblur" not in fc  # crop não desfoca


def test_blur_mode_usa_split_gblur_e_overlay_centralizado():
    cmd = build_command("in.mp4", "out.mp4", PRESET, [], 5.0, fit_mode="blur")
    fc = _filter_complex(cmd)
    assert "split=2" in fc
    assert "gblur" in fc
    assert "force_original_aspect_ratio=decrease" in fc  # frente cabe inteira
    assert "overlay=(W-w)/2:(H-h)/2" in fc


@pytest.mark.parametrize(
    "gravity,expected_y",
    [("top", ":0"), ("bottom", "ih-oh"), ("center", "(ih-oh)/2")],
)
def test_crop_gravity_posiciona_o_corte(gravity, expected_y):
    cmd = build_command("in.mp4", "out.mp4", PRESET, [], 5.0, crop_gravity=gravity)
    assert expected_y in _filter_complex(cmd)


def test_overlay_imagem_usa_loop_e_duracao():
    # Sem -loop a imagem estática quebraria o fade (frame único em t=0).
    cmd = build_command("in.mp4", "out.mp4", PRESET, [_logo()], 7.0)
    assert "-loop" in cmd and "1" in cmd
    # -t com a duração do vídeo aparece junto da imagem.
    assert "7.0" in cmd


def test_borda_com_fade_gera_filtros_de_fade():
    fc = _filter_complex(build_command("in.mp4", "out.mp4", PRESET, [_border(0.5)], 5.0))
    assert "fade=in:st=0:d=0.5:alpha=1" in fc
    assert "fade=out:st=4.5:d=0.5:alpha=1" in fc  # 5.0 - 0.5


def test_logo_sem_fade_nao_gera_filtro_de_fade():
    fc = _filter_complex(build_command("in.mp4", "out.mp4", PRESET, [_logo()], 5.0))
    assert "fade=" not in fc


def test_encode_args_e_dimensoes_pares():
    cmd = build_command("in.mp4", "out.mp4", PRESET, [], 5.0)
    assert "libx264" in cmd and "yuv420p" in cmd and "+faststart" in cmd
    assert cmd[-1] == "out.mp4"
    # Dimensões do preset são pares (requisito do yuv420p).
    assert PRESET.width % 2 == 0 and PRESET.height % 2 == 0


def test_overlays_encadeados_mapeiam_o_ultimo_resultado():
    cmd = build_command("in.mp4", "out.mp4", PRESET, [_border(), _logo()], 5.0)
    # Dois overlays => o último rótulo encadeado é t1.
    assert "[t1]" in _filter_complex(cmd)
    assert cmd[cmd.index("-map") + 1] == "[t1]"
