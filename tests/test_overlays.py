"""Testes da montagem do conjunto de overlays (regras de logo/borda)."""

from app.core.overlays import Corner, build_overlay_set, corner_position


def _by_corner(overlays):
    return {o.corner: o for o in overlays}


def test_default_tem_logo_e_tres_bordas(assets_dir):
    ovs = build_overlay_set(Corner.BOTTOM_RIGHT, assets_dir)
    assert len(ovs) == 4
    logos = [o for o in ovs if o.asset_path.endswith("_logo.png")]
    assert len(logos) == 1
    assert logos[0].corner == Corner.BOTTOM_RIGHT


def test_logo_nunca_some_mesmo_se_marcado_para_ocultar(assets_dir):
    # Mesmo pedindo para ocultar o canto do logo, o logo permanece.
    ovs = build_overlay_set(Corner.BOTTOM_RIGHT, assets_dir, hidden_borders=[Corner.BOTTOM_RIGHT])
    by = _by_corner(ovs)
    assert Corner.BOTTOM_RIGHT in by
    assert by[Corner.BOTTOM_RIGHT].asset_path.endswith("_logo.png")


def test_bordas_ocultas_sao_removidas(assets_dir):
    ovs = build_overlay_set(
        Corner.BOTTOM_RIGHT,
        assets_dir,
        hidden_borders=[Corner.TOP_LEFT, Corner.TOP_RIGHT],
    )
    corners = {o.corner for o in ovs}
    assert Corner.TOP_LEFT not in corners
    assert Corner.TOP_RIGHT not in corners
    assert corners == {Corner.BOTTOM_LEFT, Corner.BOTTOM_RIGHT}


def test_logo_sem_fade_bordas_com_fade(assets_dir):
    ovs = build_overlay_set(
        Corner.BOTTOM_RIGHT, assets_dir, border_fade_in=0.5, border_fade_out=0.5
    )
    by = _by_corner(ovs)
    logo = by[Corner.BOTTOM_RIGHT]
    assert logo.fade_in == 0.0 and logo.fade_out == 0.0  # logo permanece (thumbnail)
    bordas = [o for o in ovs if o.corner != Corner.BOTTOM_RIGHT]
    assert all(o.fade_in == 0.5 and o.fade_out == 0.5 for o in bordas)


def test_assets_inexistentes_sao_ignorados(tmp_path):
    # Sem nenhum PNG no diretório, não há overlays.
    assert build_overlay_set(Corner.BOTTOM_RIGHT, tmp_path) == []


def test_corner_position_expressoes():
    assert corner_position(Corner.TOP_LEFT, 40) == ("40", "40")
    assert corner_position(Corner.TOP_RIGHT, 40) == ("W-w-40", "40")
    assert corner_position(Corner.BOTTOM_LEFT, 40) == ("40", "H-h-40")
    assert corner_position(Corner.BOTTOM_RIGHT, 40) == ("W-w-40", "H-h-40")
