#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anel.py — Um anel de diamante feito só de letras, girando em 3D.

Gera o vídeo `assets/video/anel.mp4` (loop perfeito de 360°) e o pôster
`assets/video/anel-poster.webp` usados no site "Ela é simplesmente incrível".

Como funciona (sem nenhum programa 3D, só matemática + texto):
  1. A aliança é descrita como uma nuvem de pontos 3D:
       - o aro é um toro (uma "rosquinha") ligeiramente achatado;
       - a pedra é um diamante lapidado (coroa + pavilhão) com faces planas;
       - quatro garras seguram a pedra.
  2. A cada quadro, os pontos giram em torno do eixo Y e são projetados
     em perspectiva numa grade de caracteres (como um terminal).
  3. Um z-buffer guarda só o ponto mais próximo de cada célula.
  4. A luz (difusa + especular) decide o brilho de cada célula:
       - no aro, o caractere é uma letra de "LIVIA", e o brilho vira cor;
       - no diamante, cada face plana pisca quando reflete a luz.
  5. As células viram uma imagem (glifos pré-renderizados) e o ffmpeg
     junta tudo num MP4 leve, pronto para a web.

Uso:
    pip install -r tools/anel/requirements.txt
    python tools/anel/anel.py            # gera vídeo + pôster
    python tools/anel/anel.py --preview  # salva só um quadro de teste

Feito com amor por Lucas, para a Lívia. ♥
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "assets" / "video"

COLS, ROWS = 96, 96          # tamanho da grade de caracteres
CELL = 8                     # pixels por célula -> vídeo 768x768
FPS = 30
SECONDS = 8                  # uma volta completa = loop perfeito
TILT = math.radians(14)      # inclinação da câmera (olhando um pouco de cima)
CAM_DIST = 4.6               # distância da câmera
SCALE = 0.27                 # zoom da projeção

NAME = "LIVIA"               # o aro é escrito com o nome dela
SCRIPT_NAME = "Lívia"        # e o nome dela brilha no centro do anel
SCRIPT_FONT = ROOT / "tools" / ".cache" / "fonts" / "GreatVibes-Regular.ttf"
SCRIPT_FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/"
                   "ofl/greatvibes/GreatVibes-Regular.ttf")
DIAMOND_RAMP = " .:-=+*#%@"  # rampa de brilho da pedra
DIM_RAMP = " .:"             # partes escuras do aro

# Paleta rosé (do escuro ao brilho máximo)
BG = np.array([13, 5, 10], dtype=np.float32)
ROSE_DARK = np.array([92, 28, 52], dtype=np.float32)
ROSE_MID = np.array([255, 120, 165], dtype=np.float32)
ROSE_LIGHT = np.array([255, 228, 238], dtype=np.float32)
DIAMOND_TINT = np.array([235, 240, 255], dtype=np.float32)

rng = np.random.default_rng(14)  # semente fixa: o vídeo sai sempre igual


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------
def normalize(v: np.ndarray) -> np.ndarray:
    """Normaliza vetores linha a linha."""
    return v / np.linalg.norm(v, axis=-1, keepdims=True).clip(1e-9)


def make_band(R=1.0, a=0.085, b=0.16, nu=900, nv=70):
    """Aro: toro com seção elíptica (a = espessura radial, b = largura)."""
    u = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    v = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    U, V = np.meshgrid(u, v, indexing="ij")
    cu, su, cv, sv = np.cos(U), np.sin(U), np.cos(V), np.sin(V)
    pts = np.stack([(R + a * cv) * cu, (R + a * cv) * su, b * sv], -1)
    nrm = np.stack([cv / a * cu, cv / a * su, sv / b], -1)
    # "u" vira o índice da letra: o nome se repete ao longo do aro
    letter = (U / (2 * np.pi) * len(NAME) * 7).astype(int) % len(NAME)
    return pts.reshape(-1, 3), normalize(nrm.reshape(-1, 3)), letter.reshape(-1)


def make_diamond(y0=1.40, girdle=0.36, table=0.20, crown=0.16, pavilion=0.34,
                 sides=12, density=7000):
    """Diamante lapidado: faces planas (cada uma com sua normal) que piscam."""
    pts, nrms, facet = [], [], []
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    fid = 0

    def tri(p0, p1, p2, n_samples):
        nonlocal fid
        r1 = np.sqrt(rng.random(n_samples))[:, None]
        r2 = rng.random(n_samples)[:, None]
        p = (1 - r1) * p0 + r1 * (1 - r2) * p1 + r1 * r2 * p2
        n = np.cross(p1 - p0, p2 - p0)
        n = n / (np.linalg.norm(n) + 1e-9)
        # garante normal apontando para fora do centro da pedra
        center = np.array([0.0, y0, 0.0])
        if np.dot(n, p0 - center) < 0:
            n = -n
        pts.append(p)
        nrms.append(np.repeat(n[None], n_samples, 0))
        facet.append(np.full(n_samples, fid))
        fid += 1

    def ring_pt(r, y, t):
        return np.array([r * math.cos(t), y, r * math.sin(t)])

    per = density // (sides * 4)
    top = np.array([0.0, y0 + crown, 0.0])
    culet = np.array([0.0, y0 - pavilion, 0.0])
    for i in range(sides):
        t0, t1 = ang[i], ang[(i + 1) % sides]
        tm = (t0 + t1) / 2
        g0, g1 = ring_pt(girdle, y0, t0), ring_pt(girdle, y0, t1)
        k0, k1 = ring_pt(table, y0 + crown, t0), ring_pt(table, y0 + crown, t1)
        # coroa (estrela + bisel) dividida em dois triângulos
        tri(g0, g1, k0, per)
        tri(g1, k1, k0, per)
        # mesa (topo plano)
        tri(top, k0, k1, per // 2)
        # pavilhão (parte de baixo, em ponta), com faceta intermediária
        gm = ring_pt(girdle * 0.98, y0, tm)
        tri(g0, gm, culet, per // 2)
        tri(gm, g1, culet, per // 2)
    return np.concatenate(pts), np.concatenate(nrms), np.concatenate(facet)


def make_prongs(y_base=1.06, y_top=1.47, r_base=0.10, r_top=0.35, n=4,
                samples=500, thick=0.022):
    """Quatro garras finas que sobem do aro e abraçam a pedra."""
    pts, nrms = [], []
    for i in range(n):
        t = 2 * math.pi * i / n + math.pi / 4
        s = rng.random(samples)
        th = rng.random(samples) * 2 * np.pi
        r = r_base + (r_top - r_base) * s
        y = y_base + (y_top - y_base) * s
        cx, cz = r * math.cos(t), r * math.sin(t)
        x = cx + thick * np.cos(th) * math.cos(t)
        z = cz + thick * np.cos(th) * math.sin(t)
        yy = y + thick * np.sin(th)
        pts.append(np.stack([x * np.ones_like(s), yy, z * np.ones_like(s)], -1))
        nrms.append(normalize(np.stack([np.cos(th) * math.cos(t),
                                        np.sin(th),
                                        np.cos(th) * math.sin(t)], -1)))
    return np.concatenate(pts), np.concatenate(nrms)


# ---------------------------------------------------------------------------
# Glifos: cada caractere vira uma pequena máscara (alpha) pré-renderizada
# ---------------------------------------------------------------------------
def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("consolab.ttf", "consola.ttf", "DejaVuSansMono-Bold.ttf",
                 "DejaVuSansMono.ttf", "Menlo.ttc", "Courier New Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_glyphs(chars: str) -> np.ndarray:
    font = load_font(CELL + 2)
    masks = np.zeros((len(chars), CELL, CELL), dtype=np.float32)
    for i, ch in enumerate(chars):
        img = Image.new("L", (CELL, CELL), 0)
        d = ImageDraw.Draw(img)
        bbox = d.textbbox((0, 0), ch, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((CELL - w) / 2 - bbox[0], (CELL - h) / 2 - bbox[1]), ch,
               fill=255, font=font)
        masks[i] = np.asarray(img, dtype=np.float32) / 255.0
    return masks


def build_name_layer(width: int, height: int, cy: float):
    """Máscara (0..1) com "Lívia" em letra cursiva e um brilho suave em volta.

    Usa a fonte Great Vibes (SIL OFL), baixada do Google Fonts se precisar.
    """
    from PIL import ImageFilter
    if not SCRIPT_FONT.exists():
        import urllib.request
        SCRIPT_FONT.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(SCRIPT_FONT_URL, SCRIPT_FONT)
    font = ImageFont.truetype(str(SCRIPT_FONT), int(width * 0.16))
    img = Image.new("L", (width, height), 0)
    ImageDraw.Draw(img).text((width / 2, cy), SCRIPT_NAME, font=font,
                             fill=255, anchor="mm")
    sharp = np.asarray(img, dtype=np.float32) / 255.0
    glow = np.asarray(img.filter(ImageFilter.GaussianBlur(width * 0.018)),
                      dtype=np.float32) / 255.0
    return sharp, glow


# ---------------------------------------------------------------------------
# Renderização
# ---------------------------------------------------------------------------
def rot_y(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)


def rot_x(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)


class Ring:
    """Junta as peças e sabe desenhar um quadro em qualquer ângulo."""

    def __init__(self):
        bp, bn, bl = make_band()
        dp, dn, df = make_diamond()
        pp, pn = make_prongs()
        # material: 0 = aro, 1 = diamante, 2 = garras
        self.p = np.concatenate([bp, pp, dp])
        self.n = np.concatenate([bn, pn, dn])
        self.mat = np.concatenate([np.zeros(len(bp), int),
                                   np.full(len(pp), 2),
                                   np.ones(len(dp), int)])
        self.letter = np.concatenate([bl, np.zeros(len(pp), int),
                                      np.zeros(len(dp), int)])
        self.facet = np.concatenate([np.full(len(bp) + len(pp), -1), df])
        # centraliza verticalmente (aro + pedra)
        self.p[:, 1] -= 0.30

        self.chars = DIM_RAMP + NAME + DIAMOND_RAMP + "*" + "|"
        self.glyphs = build_glyphs(self.chars)
        self.idx_dim = 0
        self.idx_name = len(DIM_RAMP)
        self.idx_diam = len(DIM_RAMP) + len(NAME)
        self.idx_star = len(self.chars) - 2
        self.idx_prong = len(self.chars) - 1

        # duas luzes: uma principal (de cima, à esquerda) e uma de recorte
        self.l1 = normalize(np.array([-0.5, 0.8, 0.9]))
        self.l2 = normalize(np.array([0.7, 0.3, 0.6]))
        # vinheta de fundo calculada uma vez só
        yy, xx = np.mgrid[0:ROWS * CELL, 0:COLS * CELL].astype(np.float32)
        cx, cy = COLS * CELL / 2, ROWS * CELL / 2
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (COLS * CELL * 0.7)
        glow = np.clip(1 - dist, 0, 1) ** 2.2
        self.bg = BG[None, None] + glow[..., None] * np.array([38, 8, 22],
                                                              np.float32)
        # o nome dela, no centro do aro (atrás das letras do anel)
        self.name_sharp, self.name_glow = build_name_layer(
            COLS * CELL, ROWS * CELL, cy=ROWS * CELL * 0.56)

    def frame(self, theta: float) -> np.ndarray:
        M = rot_x(TILT) @ rot_y(theta)
        p = self.p @ M.T
        n = self.n @ M.T

        # projeção em perspectiva
        z = p[:, 2] + CAM_DIST
        f = SCALE * COLS / (z / CAM_DIST)
        col = (COLS / 2 + p[:, 0] * f).astype(int)
        row = (ROWS / 2 - p[:, 1] * f).astype(int)
        ok = (col >= 0) & (col < COLS) & (row >= 0) & (row < ROWS)

        # iluminação (câmera olhando para -z: o vetor de visão é +z)
        view = np.array([0.0, 0.0, -1.0])
        d1 = np.clip(-(n @ self.l1), 0, 1)
        d2 = np.clip(-(n @ self.l2), 0, 1)
        h1 = normalize(-self.l1 + view)
        s1 = np.clip(n @ h1, 0, 1)

        metal = 0.10 + 0.62 * d1 + 0.18 * d2 + 0.9 * s1 ** 28
        # diamante: cada face tem um "fogo" próprio que muda com o ângulo
        fire = np.abs(np.sin(self.facet * 2.3 + theta * 3.0))
        diam = 0.25 + 0.35 * d1 + 1.2 * s1 ** 10 + 0.45 * fire * d2
        lum = np.where(self.mat == 1, diam, metal)

        # descarta faces de costas para a câmera (só para o metal)
        facing = (n[:, 2] < 0.35) | (self.mat != 0)
        keep = ok & facing

        cell = row[keep] * COLS + col[keep]
        depth = z[keep]
        order = np.lexsort((depth, cell))
        cell_s = cell[order]
        first = np.ones(len(cell_s), bool)
        first[1:] = cell_s[1:] != cell_s[:-1]
        sel = np.nonzero(keep)[0][order][first]
        cells = cell_s[first]

        L = np.clip(lum[sel], 0, 1.6)
        mat = self.mat[sel]

        # escolhe o caractere de cada célula
        ch = np.zeros(COLS * ROWS, int)
        bright = np.zeros(COLS * ROWS, np.float32)
        kind = np.full(COLS * ROWS, -1)
        dim = (mat == 0) & (L < 0.24)
        ch_sel = np.where(
            mat == 1,
            self.idx_diam + np.clip((L / 1.25 * (len(DIAMOND_RAMP) - 1)), 1,
                                    len(DIAMOND_RAMP) - 1).astype(int),
            np.where(dim,
                     self.idx_dim + np.clip((L / 0.24 * len(DIM_RAMP)), 1,
                                            len(DIM_RAMP) - 1).astype(int),
                     self.idx_name + self.letter[sel]))
        # brilhos: as células mais intensas do diamante viram estrelinhas
        star = (mat == 1) & (L > 1.15)
        ch_sel = np.where(star, self.idx_star, ch_sel)
        # garras: traços finos de metal
        ch_sel = np.where(mat == 2, self.idx_prong, ch_sel)
        mat = np.where(mat == 2, 0, mat)
        ch[cells] = ch_sel
        bright[cells] = L
        kind[cells] = mat

        # cores por célula
        t = np.clip(bright, 0, 1.4)[:, None]
        rose = np.where(t < 0.55,
                        ROSE_DARK + (ROSE_MID - ROSE_DARK) * (t / 0.55),
                        ROSE_MID + (ROSE_LIGHT - ROSE_MID) *
                        np.clip((t - 0.55) / 0.6, 0, 1))
        ice = DIAMOND_TINT * np.clip(0.35 + t * 0.7, 0, 1.15)
        color = np.where((kind == 1)[:, None], ice, rose)
        color = np.where((kind == -1)[:, None], 0, color)

        # monta a imagem: glifo (máscara) x cor, por cima do fundo
        masks = self.glyphs[ch].reshape(ROWS, COLS, CELL, CELL)
        masks = masks.transpose(0, 2, 1, 3).reshape(ROWS * CELL, COLS * CELL)
        colimg = color.reshape(ROWS, COLS, 3).repeat(CELL, 0).repeat(CELL, 1)
        # fundo + nome pulsando devagar (o pulso também fecha o loop)
        pulse = 0.78 + 0.22 * math.sin(theta * 2)
        bg = self.bg + self.name_glow[..., None] * (ROSE_MID * 0.55 * pulse)
        n = (self.name_sharp * pulse)[..., None]
        bg = bg * (1 - n) + ROSE_LIGHT * n
        img = bg * (1 - masks[..., None]) + colimg * masks[..., None]
        return np.clip(img, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--preview", action="store_true",
                    help="salva só um quadro (anel-preview.png) e sai")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ring = Ring()

    # pôster: um ângulo bonito em que a pedra brilha
    poster = Image.fromarray(ring.frame(math.radians(32)))
    if args.preview:
        poster.save(OUT_DIR / "anel-preview.png")
        print("prévia salva em", OUT_DIR / "anel-preview.png")
        return
    poster.save(OUT_DIR / "anel-poster.webp", quality=88, method=6)

    import imageio_ffmpeg  # importado aqui para a prévia não depender dele

    total = FPS * SECONDS
    size = (COLS * CELL, ROWS * CELL)
    out = OUT_DIR / "anel.mp4"
    writer = imageio_ffmpeg.write_frames(
        str(out), size, fps=FPS, codec="libx264", quality=None,
        pix_fmt_out="yuv420p", macro_block_size=8,
        output_params=["-crf", "26", "-preset", "slow",
                       "-movflags", "+faststart", "-an"])
    writer.send(None)
    for i in range(total):
        theta = 2 * math.pi * i / total  # 0..360° sem repetir o último
        writer.send(np.ascontiguousarray(ring.frame(theta)))
        if i % FPS == 0:
            print(f"  quadro {i:3d}/{total}")
    writer.close()
    kb = os.path.getsize(out) / 1024
    print(f"vídeo pronto: {out} ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
