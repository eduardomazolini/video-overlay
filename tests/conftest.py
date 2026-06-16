"""Fixtures compartilhadas dos testes."""

import pytest

from app.core.overlays import Corner


@pytest.fixture
def assets_dir(tmp_path):
    """Cria os 8 PNGs de overlay (vazios) num diretório temporário.

    build_overlay_set só checa se o arquivo existe, então não precisam ser
    imagens de verdade para os testes do core.
    """
    for corner in Corner:
        for kind in ("logo", "border"):
            (tmp_path / f"{corner.value}_{kind}.png").write_bytes(b"")
    return tmp_path
