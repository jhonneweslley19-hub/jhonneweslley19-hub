#!/usr/bin/env python3
"""dotify.py — converte uma foto em um retrato SVG de matriz de pontos
(dot-matrix), com uma animação de "revelação" (linha por linha) via CSS.

Gera duas versões (tema claro e escuro), pensadas pra usar num <picture>
com prefers-color-scheme no README do GitHub.

Uso:
    python3 scripts/dotify.py <foto_de_entrada> --out-light assets/portrait.svg --out-dark assets/portrait-dark.svg
"""
import argparse
import sys
from PIL import Image, ImageOps

GRID_COLS = 64  # colunas da grade (a imagem de entrada deve ser quadrada)
CELL = 14  # tamanho de cada célula em px no SVG final
MAX_RADIUS_RATIO = 0.46  # raio máximo do ponto, como fração da célula
GAMMA = 1.9  # curva de resposta do raio em função da "tinta" (escuro=tinta) — mais alto = fundo claro desaparece mais rápido


def load_luminance_grid(path: str, cols: int):
    """Carrega a imagem, normaliza e devolve uma grade cols x cols de
    luminância (0.0 = escuro, 1.0 = claro)."""
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)  # respeita orientação EXIF (fotos de celular)
    im = im.convert("RGB")

    w, h = im.size
    # crop quadrado mais fechado (75% da menor dimensão) pra reduzir fundo
    # e enquadrar cabeça + ombros, levemente deslocado pra cima (retrato
    # costuma ter a cabeça no terço superior da foto original)
    side = int(min(w, h) * 0.75)
    x0 = (w - side) // 2
    y0 = max(0, int((h - side) * 0.06))
    im = im.crop((x0, y0, x0 + side, y0 + side))

    im = im.resize((cols, cols), Image.LANCZOS)
    gray = ImageOps.autocontrast(im.convert("L"), cutoff=1)

    grid = []
    px = gray.load()
    for y in range(cols):
        row = [px[x, y] / 255.0 for x in range(cols)]
        grid.append(row)
    return grid


def build_svg(grid, dot_color: str, bg: str, reveal: bool) -> str:
    cols = len(grid)
    size = cols * CELL
    max_r = CELL * MAX_RADIUS_RATIO

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" role="img" aria-label="Retrato em matriz de pontos">'
    )
    if bg:
        parts.append(f'<rect width="{size}" height="{size}" fill="{bg}" />')

    if reveal:
        parts.append("<style>")
        parts.append(
            ".row{animation:reveal .6s ease forwards;opacity:0;}"
            "@keyframes reveal{to{opacity:1;}}"
        )
        for r in range(cols):
            delay = r * 0.035
            parts.append(f".row-{r}{{animation-delay:{delay:.3f}s;}}")
        parts.append("</style>")

    for y, row in enumerate(grid):
        parts.append(f'<g class="row row-{y}">' if reveal else "<g>")
        for x, v in enumerate(row):
            ink = 1.0 - v  # tom escuro da foto = mais "tinta" (ponto maior)
            r = max_r * (ink**GAMMA)
            if r < 2.1:
                continue
            cx = x * CELL + CELL / 2
            cy = y * CELL + CELL / 2
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="{dot_color}" />'
            )
        parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="foto de entrada (jpg/png)")
    ap.add_argument("--cols", type=int, default=GRID_COLS)
    ap.add_argument("--out-light", required=True)
    ap.add_argument("--out-dark", required=True)
    ap.add_argument("--no-reveal", action="store_true")
    args = ap.parse_args()

    grid = load_luminance_grid(args.input, args.cols)
    reveal = not args.no_reveal

    # tema claro: pontos em azul escuro (combina com o banner do README),
    # sem fundo (transparente) pra herdar o branco da página do GitHub.
    light_svg = build_svg(grid, dot_color="#1E3A8A", bg=None, reveal=reveal)
    with open(args.out_light, "w") as f:
        f.write(light_svg)

    # tema escuro: pontos em azul claro, também transparente.
    dark_svg = build_svg(grid, dot_color="#60A5FA", bg=None, reveal=reveal)
    with open(args.out_dark, "w") as f:
        f.write(dark_svg)

    print(f"OK: {args.out_light} e {args.out_dark} gerados ({args.cols}x{args.cols} pontos)")


if __name__ == "__main__":
    sys.exit(main())
