"""Szenen im Mindset-Stil: schwarz, ruhig, leuchtende Linien in Weiß und Gold, viel Leerraum.

Szenen-Typen (vom Skript als Daten geliefert, Texte schon in der richtigen Sprache):
  symbol     ein großes Symbol, darüber Beschriftung + Wert         {"icon", "label", "wert"}
  vergleich  zwei Symbole nebeneinander                              {"links": {...}, "rechts": {...}}
  kurve      Diagramm mit 1-2 Kurven (linear, exponentiell, ...)      {"kurven": [{"form", "label"}], "y", "x"}
  zahl       eine große Zahl                                          {"wert", "label"}
  satz       ein kurzer Satz als Aussage                              {"text"}
  liste      bis zu 3 Punkte mit Symbol                               {"punkte": [{"icon", "text"}]}
  frage      Abschluss mit offener Frage
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

import linien
from video import H, W, font, passend, tw, wrap

M = 80
SCHWARZ = (6, 6, 8)
WEISS = linien.WEISS
GOLD = linien.GOLD
GRAU = (130, 128, 122)


def hintergrund():
    """Tiefes Schwarz mit leichtem Lichtschein in der Mitte und feinem Staub."""
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.42) / H) ** 2)
    hell = np.clip(1 - r * 1.6, 0, 1) ** 2 * 14
    g = np.stack([SCHWARZ[i] + hell for i in range(3)], -1)
    img = Image.fromarray(g.astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)
    rnd = random.Random(5)
    for _ in range(220):
        px, py, b = rnd.randrange(W), rnd.randrange(H), rnd.randint(18, 48)
        d.point((px, py), fill=(b, b, b))
    for gx in range(0, W, 60):                                   # sehr dezentes Punkteraster
        for gy in range(0, H, 60):
            d.point((gx, gy), fill=(22, 22, 26))
    return img


def gesperrt(d, text, mitte_x, y, f, fill, sperrung=0.18):
    """Text mit Buchstabenabstand (edler Look für Beschriftungen), zentriert."""
    text = text.upper()
    abst = f.size * sperrung
    breite = sum(tw(d, c, f) for c in text) + abst * (len(text) - 1)
    x = mitte_x - breite / 2
    for c in text:
        d.text((x, y), c, font=f, fill=fill)
        x += tw(d, c, f) + abst
    return breite


def leuchttext(d, text, mitte_x, y, f, farbe, a=1.0):
    """Text mit weichem Schein."""
    w = tw(d, text, f)
    x = mitte_x - w / 2
    for sw, al in ((10, 18), (5, 40)):
        d.text((x, y), text, font=f, fill=(*farbe, int(al * a)), stroke_width=sw, stroke_fill=(*farbe, int(al * a)))
    d.text((x, y), text, font=f, fill=(*farbe, int(255 * a)))


def ein(t, start=0.0, dauer=0.6):
    x = max(0.0, min(1.0, (t - start) / dauer))
    return 1 - (1 - x) ** 3


FORMEN = {
    "linear": lambda x: 0.08 + 0.62 * x,
    "exponentiell": lambda x: 0.05 + 0.85 * (math.exp(3.2 * x) - 1) / (math.exp(3.2) - 1),
    "flach": lambda x: 0.32 + 0.025 * math.sin(x * 25),
    "abwaerts": lambda x: 0.82 - 0.62 * x + 0.02 * math.sin(x * 30),
    "zickzack": lambda x: 0.3 + 0.35 * x + 0.06 * math.sin(x * 34),
    "s_kurve": lambda x: 0.08 + 0.8 / (1 + math.exp(-10 * (x - 0.5))),
    "anstieg_stillstand": lambda x: 0.06 + 1.1 * x if x < 0.42 else 0.522 + 0.02 * math.sin(x * 40),
}


class MindsetSzenen:
    mit_img = True

    def __init__(self, D):
        self.D = D
        self.aktuell = None

    @property
    def x(self):
        return (self.aktuell or {}).get("daten", {})

    def _symbol(self, layer, name, cx, cy, groesse, fortschritt, farbe=WEISS, alpha=1.0):
        bild = linien.symbol_bild(name, int(groesse), fortschritt, farbe, alpha=alpha)
        layer.alpha_composite(bild, (int(cx - groesse / 2), int(cy - groesse / 2)))

    def _zeit(self, dur):
        return min(2.6, max(1.2, dur * 0.45))

    # ---- ein großes Symbol
    def symbol(self, d, t, dur, img=None):
        x = self.x
        a = ein(t, 0.2)
        if x.get("label"):
            gesperrt(d, x["label"], W / 2, 400, font(34, "medium"), (*GRAU, int(255 * a)))
        if x.get("wert"):
            leuchttext(d, x["wert"], W / 2, 450, passend(d, x["wert"], "black", 120, W - 2 * M, 60), WEISS, a)
        self._symbol(img, x.get("icon", "muenze"), W / 2, 860, 600, ein(t, 0.1, self._zeit(dur)),
                     GOLD if x.get("gold") else WEISS)

    # ---- zwei Symbole im Vergleich
    def vergleich(self, d, t, dur, img=None):
        x = self.x
        for i, seite in enumerate(("links", "rechts")):
            s = x.get(seite) or {}
            cx = W * (0.27 if i == 0 else 0.73)
            start = 0.1 + i * 0.6
            farbe = GOLD if i == 1 else WEISS
            self._symbol(img, s.get("icon", "muenze"), cx, 720, 400, ein(t, start, self._zeit(dur) * 0.8), farbe)
            a = ein(t, start + 0.5)
            if s.get("label"):
                gesperrt(d, s["label"], cx, 950, passend(d, s["label"].upper(), "medium", 32, W / 2 - 60), (*GRAU, int(255 * a)))
            if s.get("wert"):
                leuchttext(d, s["wert"], cx, 1000, passend(d, s["wert"], "black", 76, W / 2 - 70, 40), farbe, a)
        a = ein(t, 0.6)
        gesperrt(d, "vs", W / 2, 700, font(30, "medium"), (*GRAU, int(200 * a)))

    # ---- Diagramm
    def kurve(self, d, t, dur, img=None):
        x = self.x
        x0, x1, y0, y1 = M + 40, W - M, 470, 1130
        a = ein(t, 0.0, 0.5)
        d.line([(x0, y0 - 20), (x0, y1), (x1 + 10, y1)], fill=(*WEISS, int(200 * a)), width=4)
        fl = font(30, "medium")
        if x.get("y"):
            gesperrt(d, x["y"], x0 + 30 + tw(d, x["y"].upper(), fl) * 0.62, y0 - 44, fl, (*GRAU, int(255 * a)))
        if x.get("x"):
            gesperrt(d, x["x"], x1 - tw(d, x["x"].upper(), fl) * 0.62, y1 + 24, fl, (*GRAU, int(255 * a)))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        for i, k in enumerate((x.get("kurven") or [{"form": "exponentiell"}])[:2]):
            f = FORMEN.get(k.get("form"), FORMEN["linear"])
            pts = [(x0 + (x1 - x0) * j / 120, y1 - (y1 - y0) * f(j / 120)) for j in range(121)]
            farbe = GOLD if i == 1 or len(x.get("kurven", [])) == 1 else WEISS
            p = ein(t, 0.3 + i * 0.5, self._zeit(dur) * 1.2)
            teile, spitze = linien.teilstuecke([pts], p)
            linien.leuchtlinien(ld, teile, farbe, 6, 1.0, spitze if p < 0.999 else pts[-1])
            if k.get("label") and p > 0.85:
                al = ein(t, 0.3 + i * 0.5 + self._zeit(dur) * 1.2 * 0.85, 0.5)
                lab = k["label"].upper()
                fl = font(30, "medium")
                bw = sum(tw(d, c, fl) for c in lab) + fl.size * 0.18 * (len(lab) - 1) + 56
                zwei = len(x.get("kurven") or []) > 1
                if zwei and i == 0:                                    # erste Kurve: Beschriftung unterhalb, weiter links
                    ex, ey = pts[int(len(pts) * 0.4)]
                    bx, by = max(x0 + 20, ex - bw / 2), ey - 96
                else:                                                  # sonst: über dem Kurvenende
                    ex, ey = pts[-1]
                    bx, by = min(ex - bw + 30, x1 - bw), max(y0 - 10, ey - 100)
                d.rounded_rectangle([bx, by, bx + bw, by + 60], radius=30, fill=(*WEISS, int(235 * al)))
                gesperrt(d, lab, bx + bw / 2, by + 12, fl, (*SCHWARZ, int(255 * al)))
        img.alpha_composite(lay)

    # ---- große Zahl
    def zahl(self, d, t, dur, img=None):
        x = self.x
        a = ein(t, 0.1)
        if x.get("label"):
            gesperrt(d, x["label"], W / 2, 600, passend(d, x["label"].upper(), "medium", 36, W - 2 * M), (*GRAU, int(255 * a)))
        pop = 1 + 0.05 * math.sin(min(1.0, t / 0.4) * math.pi)
        wert = x.get("wert", "")
        f = passend(d, wert, "black", int(200 * pop), W - 2 * M, 80)
        leuchttext(d, wert, W / 2, 680, f, GOLD, ein(t, 0.0, 0.4))
        bw = (W - 2 * M - 200) * ein(t, 0.5, 1.2)
        if bw > 4:
            d.line([(W / 2 - bw / 2, 940), (W / 2 + bw / 2, 940)], fill=(*GOLD, 160), width=3)

    # ---- kurze Aussage
    def satz(self, d, t, dur, img=None):
        x = self.x
        f = font(78, "bold")
        zeilen = wrap(d, x.get("text", ""), f, W - 2 * M - 40)
        if len(zeilen) > 4:
            f = font(64, "bold")
            zeilen = wrap(d, x.get("text", ""), f, W - 2 * M - 40)[:5]
        y = 760 - len(zeilen) * f.size * 0.62
        for i, z in enumerate(zeilen):
            a = ein(t, 0.15 + i * 0.25, 0.6)
            leuchttext(d, z, W / 2, y, f, GOLD if i == len(zeilen) - 1 else WEISS, a)
            y += f.size * 1.25
        bw = 160 * ein(t, 0.6, 0.8)
        d.line([(W / 2 - bw, y + 30), (W / 2 + bw, y + 30)], fill=(*GOLD, 200), width=3)

    # ---- bis zu 3 Punkte
    def liste(self, d, t, dur, img=None):
        punkte = (self.x.get("punkte") or [])[:3]
        y = 500
        schritt = min(1.2, dur / max(1, len(punkte)) * 0.6)
        for i, p in enumerate(punkte):
            start = 0.2 + i * schritt
            self._symbol(img, p.get("icon", "muenze"), M + 110, y + 90, 200, ein(t, start, 1.0),
                         GOLD if i == len(punkte) - 1 else WEISS)
            a = ein(t, start + 0.3)
            f = font(52, "bold")
            zl = wrap(d, p.get("text", ""), f, W - 2 * M - 260)[:2]
            ty = y + 90 - len(zl) * 33
            for j, z in enumerate(zl):
                d.text((M + 250, ty + j * 64), z, font=f, fill=(*WEISS, int(255 * a)))
            y += 230

    # ---- Abschluss
    def frage(self, d, t, dur, img=None):
        x = self.x
        f = font(88, "black")
        zeilen = wrap(d, x.get("frage", ""), f, W - 2 * M)
        if len(zeilen) > 3:
            f = font(72, "black")
            zeilen = wrap(d, x.get("frage", ""), f, W - 2 * M)[:4]
        y = 600 - len(zeilen) * f.size * 0.6
        for i, z in enumerate(zeilen):
            leuchttext(d, z, W / 2, y, f, GOLD if i == len(zeilen) - 1 else WEISS, ein(t, 0.1 + i * 0.15))
            y += f.size * 1.15
        a = ein(t, 0.8)
        gesperrt(d, x.get("hinweis", ""), W / 2, 900, passend(d, x.get("hinweis", "").upper(), "medium", 30, W - 2 * M),
                 (*GRAU, int(255 * a)))
        a3 = ein(t, 1.3)
        if x.get("cta"):
            leuchttext(d, x["cta"], W / 2, 1000, font(44, "bold"), WEISS, a3)
            xm, yb = W / 2, 1090 + 10 * math.sin(t * 3)
            d.polygon([(xm - 26, yb), (xm + 26, yb), (xm, yb + 30)], fill=(*GOLD, int(255 * a3)))
