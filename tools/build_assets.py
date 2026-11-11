#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_assets.py — Gera todas as imagens do site a partir das fotos originais.

O que este script produz:
  • assets/img/fotos/livia-XX.webp      fotos tratadas (900 px) para a galeria
  • assets/img/fotos/livia-XX-sm.webp   miniaturas (480 px) para celular
  • assets/img/social/*.jpg             banners para WhatsApp, Instagram,
                                        Facebook, LinkedIn, X/Twitter, etc.
  • assets/icons/*                      favicons e ícones do app (PWA)
  • docs/banner.png                     banner do README / prévia do GitHub

As fotos originais NÃO ficam no repositório (são pesadas e pessoais em
resolução máxima). Por padrão, elas são lidas de `../_originais/fotos`
(a pasta ao lado do repositório). Use `--fotos CAMINHO` para trocar.

Uso:
    pip install Pillow
    python tools/build_assets.py

As fontes usadas nos banners (Great Vibes, Playfair Display e Quicksand,
todas com licença SIL Open Font License) são baixadas automaticamente do
repositório oficial do Google Fonts para `tools/.cache/fonts`.
"""

from __future__ import annotations

import argparse
import math
import random
import urllib.request
from pathlib import Path

from PIL import (Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter,
                 ImageFont, ImageOps)

ROOT = Path(__file__).resolve().parents[1]
FOTOS_OUT = ROOT / "assets" / "img" / "fotos"
SOCIAL_OUT = ROOT / "assets" / "img" / "social"
ICONS_OUT = ROOT / "assets" / "icons"
DOCS_OUT = ROOT / "docs"
FONT_CACHE = ROOT / "tools" / ".cache" / "fonts"

# Paleta do site (mesmos tons do CSS)
WINE = (26, 7, 16)
WINE_2 = (74, 20, 44)
ROSE = (255, 110, 160)
ROSE_SOFT = (255, 192, 214)
CREAM = (255, 244, 248)

# ---------------------------------------------------------------------------
# Curadoria: ordem da galeria, recortes e ajustes de cada foto.
#   src   = índice da foto original (ordem alfabética dos arquivos)
#   crop  = fração da altura a manter, a partir do topo (stories duplicados)
#   light = ajuste de brilho (1.0 = original)
#   cap   = legenda (aparece na galeria, no slideshow e no lightbox)
#   alt   = descrição para leitores de tela e para o Google
# ---------------------------------------------------------------------------
CURADORIA = [
    dict(src=3,
         cap="Esse sorriso é o meu lugar favorito.",
         alt="Lívia sorrindo, com os cabelos cacheados soltos"),
    dict(src=19,
         cap="Nós dois: minha parte preferida de qualquer dia.",
         alt="Lívia e Gabriel lado a lado, olhando para a câmera"),
    dict(src=12,
         cap="Luz dourada, mas quem brilha é você.",
         alt="Lívia sorrindo sob uma luz dourada"),
    dict(src=4, crop=0.47,
         cap="Até o sol fica com inveja.",
         alt="Lívia sorrindo ao lado de uma piscina, num dia de sol"),
    dict(src=2,
         cap="Elegante sem nem tentar.",
         alt="Lívia de corpo inteiro com um vestido longo florido"),
    dict(src=0, crop=0.50,
         cap="Esse jeitinho que me desmonta.",
         alt="Lívia sorrindo com a mão perto do rosto"),
    dict(src=18,
         cap="Arraiá do nosso amor.",
         alt="Lívia e Gabriel juntos numa festa junina, ele de chapéu de cowboy"),
    dict(src=6,
         cap="Por você, eu fico. Sempre.",
         alt="Lívia olhando para a câmera, com os cachos caindo no ombro"),
    dict(src=13,
         cap="Linda de um jeito que nem dá pra explicar.",
         alt="Lívia com o cabelo liso, olhando para a câmera"),
    dict(src=1, crop=0.50,
         cap="Seu olhar conversa comigo.",
         alt="Lívia deitada, sorrindo de leve"),
    dict(src=17,
         cap="Minha calma no meio do caos.",
         alt="Lívia sorrindo, com um colar delicado"),
    dict(src=20,
         cap="Qualquer lugar fica especial com você.",
         alt="Gabriel e Lívia juntos à noite"),
    dict(src=8, crop=0.333,
         cap="Delicada como uma flor.",
         alt="Lívia com a mão no queixo, sorrindo"),
    dict(src=5,
         cap="Simples assim: perfeita.",
         alt="Lívia deitada, com o cabelo espalhado"),
    dict(src=11,
         cap="Seu sorriso contagia todo mundo.",
         alt="Lívia sorrindo ao lado de uma amiga"),
    dict(src=16, crop=0.38,
         cap="Seus olhos são meu poema favorito.",
         alt="Close do rosto da Lívia, com a mão no rosto"),
    dict(src=14,
         cap="Momentos que viram memória.",
         alt="Montagem de fotos da Lívia com a família e amigos numa festa junina"),
    dict(src=15,
         cap="Sorriso que ilumina qualquer noite.",
         alt="Selfie da Lívia sorrindo com alguém querido"),
    dict(src=7, crop=0.50, light=1.45,
         cap="Mesmo no escuro, você brilha.",
         alt="Lívia num ambiente com pouca luz, sorrindo"),
    dict(src=10, light=1.25,
         cap="Do jeitinho que eu amo.",
         alt="Lívia olhando para a câmera, com o cabelo solto"),
    dict(src=9, light=2.3,
         cap="Meu pensamento favorito, todo dia.",
         alt="Lívia com a mão perto do rosto, à noite"),
]

FONTS = {
    "script": ("ofl/greatvibes/GreatVibes-Regular.ttf", "GreatVibes-Regular.ttf"),
    "serif": ("ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
              "PlayfairDisplay[wght].ttf"),
    "serif_i": ("ofl/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf",
                "PlayfairDisplay-Italic[wght].ttf"),
    "sans": ("ofl/quicksand/Quicksand%5Bwght%5D.ttf", "Quicksand[wght].ttf"),
}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def font(kind: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    """Carrega (e baixa, se preciso) uma fonte do Google Fonts."""
    remote, local = FONTS[kind]
    path = FONT_CACHE / local
    if not path.exists():
        FONT_CACHE.mkdir(parents=True, exist_ok=True)
        url = "https://raw.githubusercontent.com/google/fonts/main/" + remote
        print("baixando fonte", local)
        urllib.request.urlretrieve(url, path)
    f = ImageFont.truetype(str(path), size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except (OSError, AttributeError):
            pass
    return f


def heart_polygon(cx: float, cy: float, size: float, steps: int = 180):
    """Pontos de um coração (curva clássica) centrado em (cx, cy)."""
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * size / 32, cy - y * size / 32 - size * 0.05))
    return pts


def gradient(size, top, bottom, radial=False):
    """Degradê linear (vertical) ou radial entre duas cores."""
    w, h = size
    if radial:
        g = Image.radial_gradient("L").resize((w, h))
    else:
        g = Image.linear_gradient("L").resize((w, h))
    return Image.composite(Image.new("RGB", size, bottom),
                           Image.new("RGB", size, top), g)


def draw_heart(img: Image.Image, cx, cy, size, fill, ss=4):
    """Desenha um coração suavizado (supersampling) por cima da imagem."""
    pad = int(size * 0.2)
    box = int(size + pad * 2)
    mask = Image.new("L", (box * ss, box * ss), 0)
    ImageDraw.Draw(mask).polygon(
        heart_polygon(box * ss / 2, box * ss / 2, size * ss), fill=255)
    mask = mask.resize((box, box), Image.LANCZOS)
    if isinstance(fill, Image.Image):
        layer = fill.resize((box, box))
    else:
        layer = Image.new("RGBA", (box, box), fill)
    alpha = mask
    if layer.mode == "RGBA":
        alpha = ImageChops.multiply(mask, layer.getchannel("A"))
    img.paste(layer.convert("RGB"), (int(cx - box / 2), int(cy - box / 2)), alpha)


def heart_gradient_fill(size):
    return gradient((size, size), (255, 150, 190), (214, 40, 102))


def load_photo(path: Path, spec: dict) -> Image.Image:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if "crop" in spec:
        im = im.crop((0, 0, im.width, int(im.height * spec["crop"])))
    if "light" in spec:
        im = ImageEnhance.Brightness(im).enhance(spec["light"])
        im = ImageEnhance.Contrast(im).enhance(1.05)
    return im


def fit_width(im: Image.Image, width: int) -> Image.Image:
    if im.width <= width:
        return im.copy()
    h = round(im.height * width / im.width)
    return im.resize((width, h), Image.LANCZOS)


def cover(im: Image.Image, size, focus_y=0.35) -> Image.Image:
    """Recorta a foto para preencher `size`, priorizando o rosto (topo)."""
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, focus_y))


def polaroid(im: Image.Image, w: int, angle: float) -> Image.Image:
    """Moldura de polaroid com sombra suave, já rotacionada."""
    border = int(w * 0.06)
    photo_w = w - border * 2
    photo = cover(im, (photo_w, int(photo_w * 1.18)))
    card = Image.new("RGB", (w, photo.height + border + int(w * 0.2)), CREAM)
    card.paste(photo, (border, border))
    # coraçãozinho no rodapé da polaroid
    draw_heart(card, w / 2, photo.height + border + w * 0.1, w * 0.07,
               heart_gradient_fill(64))
    card = card.convert("RGBA")
    rot = card.rotate(angle, resample=Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", rot.size, (0, 0, 0, 0))
    shadow.putalpha(rot.getchannel("A").point(lambda a: int(a * 0.55)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(w * 0.04))
    out = Image.new("RGBA", (rot.width + 40, rot.height + 40), (0, 0, 0, 0))
    out.alpha_composite(shadow, (26, 32))
    out.alpha_composite(rot, (20, 20))
    return out


def bokeh(img: Image.Image, n=40, seed=7):
    """Corações e pontinhos de luz desfocados ao fundo."""
    rnd = random.Random(seed)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = img.size
    for _ in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        s = rnd.uniform(w * 0.006, w * 0.03)
        a = rnd.randint(25, 90)
        if rnd.random() < 0.45:
            d.polygon(heart_polygon(x, y, s * 2), fill=(255, 140, 180, a))
        else:
            d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 190, 215, a))
    layer = layer.filter(ImageFilter.GaussianBlur(w * 0.002))
    img.alpha_composite(layer) if img.mode == "RGBA" else img.paste(layer, (0, 0), layer)


def text_center(d: ImageDraw.ImageDraw, xy, text, fnt, fill, spacing=0):
    """Escreve texto centralizado em xy (com espaçamento entre letras)."""
    if spacing:
        widths = [d.textlength(c, font=fnt) for c in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = xy[0] - total / 2
        for c, cw in zip(text, widths):
            d.text((x, xy[1]), c, font=fnt, fill=fill, anchor="lm")
            x += cw + spacing
        return
    d.text(xy, text, font=fnt, fill=fill, anchor="mm")


def text_left(d, xy, text, fnt, fill, spacing=0):
    x = xy[0]
    for c in text:
        d.text((x, xy[1]), c, font=fnt, fill=fill, anchor="lm")
        x += d.textlength(c, font=fnt) + spacing
    return x


# ---------------------------------------------------------------------------
# 1) Fotos da galeria
# ---------------------------------------------------------------------------
GALLERY_START = "<!-- GALERIA:INICIO -->"
GALLERY_END = "<!-- GALERIA:FIM -->"


def update_gallery_html(sizes: list[tuple[int, int]]):
    """Reescreve a galeria do index.html (entre os marcadores GALERIA)."""
    index = ROOT / "index.html"
    html = index.read_text(encoding="utf-8")
    start, end = html.index(GALLERY_START), html.index(GALLERY_END)
    indent = " " * 8
    items = [GALLERY_START]
    for i, (spec, (w, h)) in enumerate(zip(CURADORIA, sizes), start=1):
        name = f"/assets/img/fotos/livia-{i:02d}"
        items.append(
            f'<li class="gallery__item reveal">'
            f'<button class="gallery__btn" type="button" data-index="{i - 1}" '
            f'data-full="{name}.webp" data-caption="{spec["cap"]}">'
            f'<img src="{name}-sm.webp" srcset="{name}-sm.webp 480w, {name}.webp 900w" '
            f'sizes="(max-width: 600px) 50vw, (max-width: 1000px) 33vw, 300px" '
            f'width="{w}" height="{h}" loading="lazy" decoding="async" alt="{spec["alt"]}">'
            f'<span class="gallery__cap">{spec["cap"]}</span>'
            f'</button></li>')
    block = ("\n" + indent).join(items) + "\n" + indent
    index.write_text(html[:start] + block + html[end:], encoding="utf-8")
    print("galeria do index.html atualizada")


def build_photos(src_dir: Path) -> list[Image.Image]:
    files = sorted(p for p in src_dir.iterdir()
                   if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    if len(files) < 21:
        raise SystemExit(f"Esperava 21 fotos em {src_dir}, achei {len(files)}.")
    FOTOS_OUT.mkdir(parents=True, exist_ok=True)
    out, sizes = [], []
    for i, spec in enumerate(CURADORIA, start=1):
        im = load_photo(files[spec["src"]], spec)
        lg, sm = fit_width(im, 900), fit_width(im, 480)
        name = f"livia-{i:02d}"
        lg.save(FOTOS_OUT / f"{name}.webp", quality=80, method=6)
        sm.save(FOTOS_OUT / f"{name}-sm.webp", quality=76, method=6)
        print(f"{name}: {lg.width}x{lg.height}  (sm {sm.width}x{sm.height})")
        out.append(im)
        sizes.append(lg.size)
    update_gallery_html(sizes)
    return out


# ---------------------------------------------------------------------------
# 2) Banners para redes sociais
# ---------------------------------------------------------------------------
def base_canvas(size):
    img = gradient(size, WINE_2, WINE, radial=True).convert("RGBA")
    bokeh(img, n=int(size[0] * size[1] / 16000))
    return img


def paste_polaroids(img, photos, centers, width, angles):
    for ph, (cx, cy), ang in zip(photos, centers, angles):
        p = polaroid(ph, width, ang)
        img.alpha_composite(p, (int(cx - p.width / 2), int(cy - p.height / 2)))


def banner_landscape(photos, size=(1200, 630)):
    w, h = size
    img = base_canvas(size)
    s = w / 1200
    paste_polaroids(img, [photos[0], photos[2], photos[1]],
                    [(w * 0.64, h * 0.52), (w * 0.88, h * 0.5),
                     (w * 0.76, h * 0.52)],
                    int(250 * s), [9, -8, -2])
    d = ImageDraw.Draw(img)
    x0 = int(70 * s)
    text_left(d, (x0, h * 0.25), "PARA A LÍVIA", font("sans", int(24 * s), 700),
              ROSE_SOFT, spacing=int(6 * s))
    d.text((x0, h * 0.40), "Ela é simplesmente", font=font("serif", int(50 * s), 600),
           fill=CREAM, anchor="lm")
    d.text((x0 - 4, h * 0.58), "incrível", font=font("script", int(118 * s)),
           fill=ROSE, anchor="lm")
    d.text((x0, h * 0.76), "Um site feito com todo o amor do Gabriel",
           font=font("sans", int(25 * s), 500), fill=ROSE_SOFT, anchor="lm")
    draw_heart(img, x0 + 14 * s, h * 0.88, 26 * s, heart_gradient_fill(64))
    d.text((x0 + 38 * s, h * 0.88), "pra-livia.netlify.app",
           font=font("sans", int(21 * s), 600), fill=(255, 220, 232), anchor="lm")
    return img.convert("RGB")


def banner_portrait(photos, size):
    w, h = size
    img = base_canvas(size)
    tall = h / w > 1.4
    pw = int(w * (0.42 if tall else 0.34))
    cy = h * (0.30 if tall else 0.36)
    paste_polaroids(img, [photos[0], photos[2], photos[1]],
                    [(w * 0.27, cy + pw * 0.08), (w * 0.73, cy + pw * 0.08),
                     (w * 0.5, cy)], pw, [8, -8, -1])
    d = ImageDraw.Draw(img)
    base = h * (0.60 if tall else 0.71)
    k = w / 1080
    text_center(d, (w / 2, base), "PARA A LÍVIA", font("sans", int(34 * k), 700),
                ROSE_SOFT, spacing=int(9 * k))
    text_center(d, (w / 2, base + 95 * k), "Ela é simplesmente",
                font("serif", int(70 * k), 600), CREAM)
    text_center(d, (w / 2, base + 225 * k), "incrível",
                font("script", int(170 * k)), ROSE)
    text_center(d, (w / 2, base + (360 if tall else 340) * k),
                "com todo o amor do Gabriel", font("sans", int(36 * k), 500),
                ROSE_SOFT)
    if tall:
        draw_heart(img, w / 2, base + 470 * k, 44 * k, heart_gradient_fill(64))
        text_center(ImageDraw.Draw(img), (w / 2, base + 545 * k),
                    "pra-livia.netlify.app", font("sans", int(32 * k), 600),
                    (255, 220, 232))
    return img.convert("RGB")


def build_social(photos):
    SOCIAL_OUT.mkdir(parents=True, exist_ok=True)
    DOCS_OUT.mkdir(parents=True, exist_ok=True)
    # 1200x630: WhatsApp, Facebook, LinkedIn, X/Twitter, Telegram, Discord…
    banner_landscape(photos).save(SOCIAL_OUT / "og-image.jpg", quality=88,
                                  optimize=True, progressive=True)
    # 1080x1080: post do Instagram / feed
    banner_portrait(photos, (1080, 1080)).save(
        SOCIAL_OUT / "instagram-post.jpg", quality=90, optimize=True)
    # 1080x1350: retrato do Instagram (4:5)
    banner_portrait(photos, (1080, 1350)).save(
        SOCIAL_OUT / "instagram-retrato.jpg", quality=90, optimize=True)
    # 1080x1920: stories do Instagram e status do WhatsApp
    banner_portrait(photos, (1080, 1920)).save(
        SOCIAL_OUT / "stories.jpg", quality=90, optimize=True)
    # 1280x640: README e prévia social do GitHub
    banner_landscape(photos, (1280, 640)).save(DOCS_OUT / "banner.png",
                                               optimize=True)
    print("banners prontos")


# ---------------------------------------------------------------------------
# 3) Favicons e ícones do app
# ---------------------------------------------------------------------------
def icon(size, bg=None, scale=0.78):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0) if bg is None else bg)
    if bg is not None:
        glow = gradient((size, size), WINE_2, WINE, radial=True).convert("RGBA")
        img = glow
    draw_heart(img, size / 2, size / 2 + size * 0.03, size * scale,
               heart_gradient_fill(256))
    return img


def build_icons():
    ICONS_OUT.mkdir(parents=True, exist_ok=True)
    icon(48, scale=0.92).save(ICONS_OUT / "favicon.ico",
                              sizes=[(16, 16), (32, 32), (48, 48)])
    icon(32, scale=0.92).save(ICONS_OUT / "favicon-32x32.png")
    icon(16, scale=0.95).save(ICONS_OUT / "favicon-16x16.png")
    icon(180, bg=WINE, scale=0.62).convert("RGB").save(ICONS_OUT / "apple-touch-icon.png")
    icon(192, bg=WINE, scale=0.62).save(ICONS_OUT / "icon-192.png")
    icon(512, bg=WINE, scale=0.62).save(ICONS_OUT / "icon-512.png")
    # maskable: o coração fica dentro da "zona segura" (80% central)
    icon(512, bg=WINE, scale=0.46).save(ICONS_OUT / "icon-maskable-512.png")
    print("ícones prontos")


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Gera fotos, banners e ícones.")
    ap.add_argument("--fotos", type=Path,
                    default=ROOT.parent / "_originais" / "fotos",
                    help="pasta com as fotos originais")
    args = ap.parse_args()

    photos = build_photos(args.fotos)
    # para os banners: 1 = sorriso, 2 = nós dois, 3 = luz dourada
    build_social([photos[0], photos[1], photos[2]])
    build_icons()


if __name__ == "__main__":
    main()
