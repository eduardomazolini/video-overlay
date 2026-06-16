# Overlays

Coloque os PNGs aqui seguindo a convenção de nome
`{canto}_{tipo}.png`. São 8 arquivos possíveis (4 cantos x 2 tipos):

```
top_left_logo.png       top_left_border.png
top_right_logo.png      top_right_border.png
bottom_left_logo.png    bottom_left_border.png
bottom_right_logo.png   bottom_right_border.png
```

A cada render, o canto escolhido para o logo usa `*_logo.png` e os outros
três usam `*_border.png`. PNGs ausentes são ignorados, então dá para testar
com um subconjunto.

**Importante:** os PNGs devem ter fundo transparente (canal alpha). O fade
in/out é aplicado pelo ffmpeg sobre o PNG estático — não precisa de GIF nem
vídeo. Para animações complexas no futuro, troque por `.webm` (VP9 com alpha)
ou `.mov` (ProRes 4444) e ajuste apenas o `asset_path`.
