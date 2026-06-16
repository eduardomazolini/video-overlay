"""Montagem do comando ffmpeg (filtergraph).

Esta é a peça central. Ela NÃO executa nada — só constrói a lista de
argumentos. Isso deixa o comando fácil de logar, testar e inspecionar.

Pipeline aplicado:
  1. Vídeo base: scale + crop para a proporção da rede (corte central tipo "cover").
  2. Cada overlay: format=rgba + fade in/out no canal alpha.
  3. Encadeia os overlays por cima do base, um a um.
"""

from .overlays import Overlay, corner_position
from .presets import AspectPreset

BLUR_SIGMA = 20  # intensidade do desfoque do fundo no modo "blur"


def _crop_expr(w: int, h: int, gravity: str) -> str:
    """Expressão do filtro crop conforme a gravidade escolhida.

    Horizontal sempre centralizado; vertical varia: centro, topo ou base.
    iw/ih = dimensões já escaladas; ow/oh = dimensões finais do corte.
    """
    x = "(iw-ow)/2"
    y = {
        "top": "0",
        "bottom": "ih-oh",
        "center": "(ih-oh)/2",
    }.get(gravity, "(ih-oh)/2")
    return f"crop={w}:{h}:{x}:{y}"


def _base_filters(w: int, h: int, fit_mode: str, crop_gravity: str) -> list[str]:
    """Filtros que transformam o vídeo de entrada [0:v] no quadro base [base].

    Duas estratégias para encaixar qualquer proporção em WxH:

    - "crop"  (cover): escala cobrindo o quadro e corta o excesso. Não sobra
      borda, mas perde conteúdo nas pontas. Bom quando a proporção é parecida.

    - "blur" (fundo borrado): mostra o vídeo INTEIRO (sem cortar) por cima de
      um fundo que é o próprio vídeo ampliado e desfocado. Resolve casos
      extremos (ex.: vídeo vertical em proporção horizontal) sem barras pretas
      e sem perder conteúdo. É o que apps como Instagram/TikTok fazem.
    """
    if fit_mode == "blur":
        return [
            "[0:v]split=2[bgsrc][fgsrc]",
            # Fundo: cobre o quadro, corta o excesso e desfoca.
            f"[bgsrc]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},gblur=sigma={BLUR_SIGMA},setsar=1[bg]",
            # Frente: vídeo inteiro cabendo dentro do quadro (sem cortar).
            f"[fgsrc]scale={w}:{h}:force_original_aspect_ratio=decrease,setsar=1[fg]",
            # Centraliza a frente sobre o fundo borrado.
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[base]",
        ]
    # "crop" (padrão): cobre e corta na posição escolhida.
    return [
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"{_crop_expr(w, h, crop_gravity)},setsar=1[base]"
    ]


def build_command(
    input_path: str,
    output_path: str,
    preset: AspectPreset,
    overlays: list[Overlay],
    total_duration: float,
    *,
    fit_mode: str = "crop",
    crop_gravity: str = "center",
    crf: int = 20,
) -> list[str]:
    """Constrói a lista de argumentos do ffmpeg.

    `total_duration` (segundos) é usado para calcular o início do fade out.
    `fit_mode` define como encaixar a proporção: "crop" ou "blur".
    `crop_gravity` define a posição do corte (só vale para "crop").
    """
    cmd: list[str] = ["ffmpeg", "-y", "-i", input_path]
    for ov in overlays:
        # PNG é uma imagem estática (1 frame em t=0). Sem -loop, o fade não
        # teria frames ao longo do tempo e o overlay ficaria preso no alpha
        # do instante 0. -loop 1 + -t transforma a imagem num stream contínuo
        # com a duração do vídeo, para o fade in/out funcionar.
        cmd += ["-loop", "1", "-t", str(total_duration), "-i", ov.asset_path]

    # (1) Base: encaixa o vídeo na proporção alvo (crop ou fundo borrado).
    w, h = preset.width, preset.height
    filters: list[str] = _base_filters(w, h, fit_mode, crop_gravity)

    last = "base"
    for idx, ov in enumerate(overlays):
        input_idx = idx + 1  # input 0 é o vídeo; overlays começam em 1
        ov_label = f"ov{idx}"

        # (2) Prepara o overlay: alpha + fades opcionais.
        steps = ["format=rgba"]
        if ov.fade_in > 0:
            steps.append(f"fade=in:st=0:d={ov.fade_in}:alpha=1")
        if ov.fade_out > 0:
            start = max(0.0, total_duration - ov.fade_out)
            steps.append(f"fade=out:st={start}:d={ov.fade_out}:alpha=1")
        filters.append(f"[{input_idx}:v]" + ",".join(steps) + f"[{ov_label}]")

        # (3) Compõe sobre o resultado anterior.
        x, y = corner_position(ov.corner, ov.margin)
        out_label = f"t{idx}"
        filters.append(f"[{last}][{ov_label}]overlay={x}:{y}[{out_label}]")
        last = out_label

    cmd += ["-filter_complex", ";".join(filters)]
    cmd += ["-map", f"[{last}]", "-map", "0:a?"]  # áudio do original, se houver
    cmd += [
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        output_path,
    ]
    return cmd
