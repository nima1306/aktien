"""Leuchtende Linien-Symbole, die sich selbst zeichnen (für das Mindset-Thema).

Jedes Symbol besteht aus Strichen in einem 100x100-Raster. zeichne() deckt sie Stück für Stück auf
(fortschritt 0..1) und malt sie mit weichem Leuchten. Neue Symbole: einfach unten in SYMBOLE ergänzen.
"""
import math

from PIL import Image, ImageDraw

WEISS = (244, 240, 230)
GOLD = (233, 190, 96)


# ---------------------------------------------------------------- Formen

def kreis(cx, cy, r, a0=0, a1=360, n=None, ry=None):
    ry = ry if ry is not None else r
    n = n or max(12, int(abs(a1 - a0) / 6))
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def rechteck(x0, y0, x1, y1, r=0):
    if r <= 0:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    p = []
    for cx, cy, a in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        p += kreis(cx, cy, r, a, a + 90, n=6)
    return p + [p[0]]


def blatt(x0, y0, x1, y1, b=0.35, n=10):
    """Blattform zwischen zwei Punkten (zwei Bögen)."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0) * b, (x1 - x0) * b
    def bez(cx, cy):
        return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1,
                 (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1) for t in (i / n for i in range(n + 1))]
    return bez(mx + nx, my + ny) + bez(mx - nx, my - ny)[::-1]


def pfeil(x0, y0, x1, y1, k=7):
    w = math.atan2(y1 - y0, x1 - x0)
    return [[(x0, y0), (x1, y1)],
            [(x1 - k * math.cos(w - 0.5), y1 - k * math.sin(w - 0.5)), (x1, y1),
             (x1 - k * math.cos(w + 0.5), y1 - k * math.sin(w + 0.5))]]


def person(cx, top, s=1.0):
    return [kreis(cx, top + 9 * s, 8 * s), [(cx - 16 * s, top + 52 * s), (cx - 16 * s, top + 34 * s),
            (cx - 10 * s, top + 24 * s), (cx + 10 * s, top + 24 * s), (cx + 16 * s, top + 34 * s), (cx + 16 * s, top + 52 * s)]]


SYMBOLE = {
    "sparschwein": [kreis(46, 56, 31, ry=22), [(30, 37), (34, 24), (42, 34)], kreis(81, 56, 6, ry=8),
                    [(26, 74), (26, 86)], [(38, 77), (38, 86)], [(56, 77), (56, 86)], [(66, 74), (66, 86)],
                    [(40, 34), (54, 34)], kreis(13, 50, 4, 0, 300), kreis(64, 48, 1.5)],
    "muenze": [kreis(50, 50, 32), kreis(50, 50, 24), [(55, 38), (46, 38), (42, 44), (42, 56), (46, 62), (55, 62)],
               [(38, 47), (52, 47)], [(38, 53), (52, 53)]],
    "muenzstapel": [kreis(50, 30, 26, ry=8), kreis(50, 30, 26, 0, 180, ry=8)[::-1] and kreis(50, 44, 26, 0, 180, ry=8),
                    kreis(50, 58, 26, 0, 180, ry=8), kreis(50, 72, 26, 0, 180, ry=8), [(24, 30), (24, 72)], [(76, 30), (76, 72)]],
    "geldschein": [rechteck(12, 30, 88, 70, 4), kreis(50, 50, 11), rechteck(18, 36, 82, 64, 2)],
    "haus": [[(16, 48), (50, 18), (84, 48)], rechteck(24, 44, 76, 84), rechteck(43, 62, 57, 84)],
    "auto": [[(10, 66), (10, 54), (22, 52), (32, 38), (66, 38), (78, 52), (90, 56), (90, 66), (80, 66)],
             [(36, 66), (64, 66)], kreis(28, 68, 8), kreis(72, 68, 8), [(34, 52), (74, 52)]],
    "uhr": [kreis(50, 50, 34), [(50, 50), (50, 28)], [(50, 50), (66, 58)], kreis(50, 50, 2)],
    "sanduhr": [[(28, 14), (72, 14)], [(28, 86), (72, 86)], [(32, 14), (32, 22), (50, 50), (32, 78), (32, 86)],
                [(68, 14), (68, 22), (50, 50), (68, 78), (68, 86)], [(40, 78), (50, 66), (60, 78)]],
    "kalender": [rechteck(16, 22, 84, 84, 4), [(16, 38), (84, 38)], [(32, 14), (32, 28)], [(68, 14), (68, 28)],
                 kreis(32, 54, 2), kreis(50, 54, 2), kreis(68, 54, 2), kreis(32, 70, 2), kreis(50, 70, 2)],
    "gluehbirne": [kreis(50, 40, 24, 140, 400), [(38, 60), (38, 72), (62, 72), (62, 60)], [(40, 80), (60, 80)],
                   [(44, 87), (56, 87)], [(44, 52), (50, 44), (56, 52)]],
    "schloss": [kreis(50, 40, 16, 180, 360), [(34, 40), (34, 48)], [(66, 40), (66, 48)], rechteck(24, 48, 76, 86, 5),
                kreis(50, 63, 5), [(50, 68), (50, 76)]],
    "schluessel": [kreis(30, 50, 14), [(44, 50), (88, 50)], [(76, 50), (76, 62)], [(86, 50), (86, 60)]],
    "waage": [[(50, 16), (50, 84)], [(36, 84), (64, 84)], [(18, 26), (82, 26)], [(18, 26), (10, 52)],
              [(18, 26), (26, 52)], kreis(18, 52, 8, 0, 180), [(82, 26), (74, 52)], [(82, 26), (90, 52)],
              kreis(82, 52, 8, 0, 180)],
    "treppe": [[(10, 86), (30, 86), (30, 68), (50, 68), (50, 50), (70, 50), (70, 32), (90, 32)]] + pfeil(64, 22, 90, 10),
    "berg": [[(6, 84), (34, 40), (46, 56), (62, 26), (94, 84), (6, 84)], [(62, 26), (62, 8)], [(62, 8), (76, 12), (62, 17)]],
    "pfeil_hoch": pfeil(22, 80, 78, 22, 14),
    "pfeil_runter": pfeil(22, 22, 78, 80, 14),
    "person": person(50, 18, 1.4),
    "personen": person(34, 26, 1.0) + person(66, 26, 1.0),
    "handy": [rechteck(30, 10, 70, 90, 6), [(44, 18), (56, 18)], kreis(50, 80, 3)],
    "einkaufswagen": [[(8, 20), (20, 20), (30, 64), (78, 64), (86, 32), (24, 32)], kreis(36, 76, 5), kreis(72, 76, 5)],
    "buch": [[(50, 26), (50, 82)], [(50, 26), (34, 20), (12, 22), (12, 78), (34, 76), (50, 82)],
             [(50, 26), (66, 20), (88, 22), (88, 78), (66, 76), (50, 82)]],
    "zielscheibe": [kreis(46, 54, 34), kreis(46, 54, 22), kreis(46, 54, 10)] + pfeil(88, 12, 48, 52, 8),
    "pflanze": [[(50, 88), (50, 34)], blatt(50, 62, 24, 46), blatt(50, 48, 76, 32), blatt(50, 36, 42, 14, 0.3),
                [(28, 88), (72, 88)]],
    "baum": [[(50, 90), (50, 54)], [(50, 66), (38, 56)], [(50, 62), (62, 52)], kreis(50, 36, 26)],
    "prozent": [kreis(30, 30, 10), kreis(70, 70, 10), [(76, 18), (24, 82)]],
    "tresor": [rechteck(14, 16, 86, 82, 4), kreis(50, 49, 16), kreis(50, 49, 3), [(50, 33), (50, 38)],
               [(66, 49), (61, 49)], [(22, 82), (22, 90)], [(78, 82), (78, 90)]],
    "kaffee": [[(20, 40), (24, 84), (64, 84), (68, 40), (20, 40)], kreis(70, 58, 10, 270, 450),
               kreis(34, 24, 5, 180, 360), kreis(44, 24, 5, 0, 180), kreis(54, 24, 5, 180, 360)],
    "kreditkarte": [rechteck(10, 26, 90, 76, 6), [(10, 40), (90, 40)], rechteck(20, 50, 34, 62, 2), [(56, 64), (80, 64)]],
    "aktenkoffer": [rechteck(12, 32, 88, 84, 5), rechteck(38, 18, 62, 32, 3), [(12, 54), (88, 54)], [(46, 50), (54, 50)]],
    "rakete": [[(50, 8), (62, 26), (62, 66), (38, 66), (38, 26), (50, 8)], kreis(50, 34, 6), [(38, 52), (26, 70), (38, 66)],
               [(62, 52), (74, 70), (62, 66)], [(44, 74), (50, 90), (56, 74)]],
    "kette": [kreis(28, 50, 14, ry=9), kreis(50, 50, 14, ry=9), kreis(72, 50, 14, ry=9)],
    "herz": [[(50, 84), (16, 50)] + kreis(32, 36, 17, 140, 320)[1:] + kreis(68, 36, 17, 220, 400)[1:] + [(84, 50), (50, 84)]],
}
SYMBOLE["muenzstapel"] = [kreis(50, 28, 26, ry=8), kreis(50, 42, 26, 0, 180, ry=8), kreis(50, 56, 26, 0, 180, ry=8),
                          kreis(50, 70, 26, 0, 180, ry=8), [(24, 28), (24, 70)], [(76, 28), (76, 70)]]


def striche(name):
    return SYMBOLE.get(name) or SYMBOLE["muenze"]


# ---------------------------------------------------------------- Zeichnen

def _laenge(p):
    return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))


def teilstuecke(strokes, fortschritt):
    """Schneidet die Striche so ab, dass nur 'fortschritt' (0..1) der Gesamtlänge sichtbar ist."""
    total = sum(_laenge(s) for s in strokes) or 1
    rest = total * max(0.0, min(1.0, fortschritt))
    out, spitze = [], None
    for s in strokes:
        if rest <= 0:
            break
        L = _laenge(s)
        if L <= rest:
            out.append(s)
            rest -= L
            spitze = s[-1]
            continue
        teil = [s[0]]
        for i in range(len(s) - 1):
            seg = math.dist(s[i], s[i + 1])
            if seg >= rest:
                f = rest / seg if seg else 0
                pkt = (s[i][0] + (s[i + 1][0] - s[i][0]) * f, s[i][1] + (s[i + 1][1] - s[i][1]) * f)
                teil.append(pkt)
                spitze = pkt
                break
            teil.append(s[i + 1])
            rest -= seg
        out.append(teil)
        rest = 0
    return out, spitze


def leuchtlinien(d, strokes, farbe, breite=6, alpha=1.0, spitze=None):
    """Malt Striche mit weichem Leuchten (erst alle Schein-Schichten, dann die Kernlinie)."""
    for w, a in ((breite * 5, 22), (breite * 2.6, 60), (breite, 255)):
        col = (*farbe, int(a * alpha))
        for s in strokes:
            if len(s) >= 2:
                d.line(s, fill=col, width=int(w), joint="curve")
            r = w / 2
            for x, y in (s[0], s[-1]):
                d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    if spitze:
        x, y = spitze
        for r, a in ((breite * 4, 50), (breite * 2, 120), (breite * 0.9, 255)):
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(a * alpha)))


def symbol_bild(name, groesse, fortschritt, farbe=WEISS, breite=None, alpha=1.0):
    """Gibt ein RGBA-Bild (groesse x groesse) mit dem teilweise gezeichneten Symbol zurück."""
    rand = groesse * 0.12
    k = (groesse - 2 * rand) / 100
    px = [[(rand + x * k, rand + y * k) for x, y in s] for s in striche(name)]
    teile, spitze = teilstuecke(px, fortschritt)
    img = Image.new("RGBA", (groesse, groesse), (0, 0, 0, 0))
    leuchtlinien(ImageDraw.Draw(img), teile, farbe, breite or max(3, groesse / 85), alpha,
                 spitze if fortschritt < 0.999 else None)
    return img
