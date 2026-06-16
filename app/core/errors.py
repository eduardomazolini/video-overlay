"""Exceções do core de processamento."""


class ProcessingError(Exception):
    """Falha ao processar o vídeo (ffmpeg/ffprobe ou validação).

    Carrega uma mensagem amigável; quando vem do ffmpeg, inclui o final do
    stderr para facilitar o diagnóstico.
    """
