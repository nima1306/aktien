"""Allgemeine Szenen für alle Themen (Bundesliga, Ernährung, ...).

Jedes Thema beschreibt seine Szenen als Daten, zum Beispiel
  {"name": "liste", "text": "<Sprechtext>", "daten": {"titel": ..., "zeilen": [...]}}
und diese Klasse zeichnet sie im Stil der Aktien-Videos. So sehen alle Konten einheitlich aus,
und ein neues Thema braucht keinen eigenen Zeichen-Code.
"""
import math

from video import C, H, M, W, anim, center, check_icon, font, mix, passend, pill, tw, with_alpha, wrap


class ThemaSzenen:
    mit_img = True

    def __init__(self, D):
        self.D = D
        self.aktuell = None

    @property
    def x(self):
        return (self.aktuell or {}).get("daten", {})

    def _kopf(self, d, titel, unter=None):
        d.text((M, 340), titel, font=passend(d, titel, "black", 70, W - 2 * M), fill=C["ink"])
        if unter:
            d.text((M, 432), unter, font=passend(d, unter, "medium", 38, W - 2 * M), fill=C["muted"])

    # ---- Einstieg: alles sofort sichtbar
    def titel(self, d, t, dur, img=None):
        x = self.x
        if x.get("tag"):
            pill(d, W / 2, 380, x["tag"], font(56, "black"), C["green"], C["bg"], (34, 14), "c")
        if x.get("name"):
            center(d, x["name"], 490, passend(d, x["name"], "bold", 64, W - 2 * M), C["ink"])
        center(d, x.get("kicker", ""), 640, passend(d, x.get("kicker", ""), "black", 58, W - 2 * M), C["muted"])
        pop = 1 + 0.08 * math.sin(min(1.0, t / 0.35) * math.pi)
        big = x.get("gross", "")
        maxw = int((W - 2 * M) * pop)
        unten = 0
        f = passend(d, big, "black", int(170 * pop), maxw, 80)
        if tw(d, big, f) <= maxw:
            center(d, big, 720 - (f.size - 170) * 0.5, f, C[x.get("farbe", "green")])
        else:                                   # zu lang (z. B. zwei Vereinsnamen) -> zwei Zeilen
            teile = big.split(" – ", 1)
            zeilen = [teile[0] + " –", teile[1]] if len(teile) == 2 else wrap(d, big, font(90, "black"), maxw)[:2]
            groesse = min(int(92 * pop), min(passend(d, z, "black", int(92 * pop), maxw, 40).size for z in zeilen))
            f = font(groesse, "black")
            y0 = 822 - len(zeilen) * (groesse + 10) / 2
            unten = 45
            for i, z in enumerate(zeilen):
                center(d, z, y0 + i * (groesse + 10), f, C[x.get("farbe", "green")])
        if x.get("sub"):
            center(d, x["sub"], 930 + unten, passend(d, x["sub"], "medium", 48, W - 2 * M), C["ink"])
        if x.get("sub2"):
            center(d, x["sub2"], 1010 + unten, passend(d, x["sub2"], "medium", 40, W - 2 * M), C["muted"])

    # ---- Rangliste mit Balken (z. B. Zucker je Produkt, Torjäger)
    def liste(self, d, t, dur, img=None):
        x = self.x
        self._kopf(d, x.get("titel", ""), x.get("unter"))
        zeilen = x.get("zeilen", [])[:7]
        mx = max([z["wert"] for z in zeilen] + [x.get("max", 0)]) or 1
        y, h = 510, min(104, 700 // max(1, len(zeilen)))
        schritt = min(0.45, (dur * 0.5) / max(1, len(zeilen)))
        for i, z in enumerate(zeilen):
            a = anim(t, 0.25 + i * schritt, 0.45)
            if a <= 0:
                y += h + 12
                continue
            off = 60 * (1 - a)
            hl = z.get("markiert")
            d.rounded_rectangle([M + off, y, W - M + off, y + h], radius=22,
                                fill=with_alpha(C["green_d"] if hl else C["panel"], a))
            lab = z["label"]
            f = font(36 if h >= 96 else 32, "bold")
            wert = z.get("text", str(z["wert"]))
            fw = font(40 if h >= 96 else 34, "black")
            platz = W - 2 * M - 64 - tw(d, wert, fw) - 30
            lines = wrap(d, lab, f, platz)[:2]
            ty = y + (h - len(lines) * (f.size + 6)) / 2 - 8
            for j, ln in enumerate(lines):
                d.text((M + 30 + off, ty + j * (f.size + 6)), ln, font=f, fill=with_alpha(C["ink"], a))
            col = C[z.get("farbe", "green")]
            d.text((W - M - 30 - tw(d, wert, fw) + off, y + (h - fw.size) / 2 - 6), wert, font=fw,
                   fill=with_alpha(col, a))
            bw = (W - 2 * M - 60) * (z["wert"] / mx) * anim(t, 0.4 + i * schritt, 0.7)
            d.rounded_rectangle([M + 30 + off, y + h - 16, M + 30 + off + max(bw, 8), y + h - 8], radius=4,
                                fill=with_alpha(col, a))
            y += h + 12

    # ---- Spielergebnisse / Paarungen
    def ergebnisse(self, d, t, dur, img=None):
        x = self.x
        self._kopf(d, x.get("titel", ""), x.get("unter"))
        spiele = x.get("spiele", [])[:9]
        y, h = 500, min(84, 720 // max(1, len(spiele)) - 8)
        schritt = min(0.3, (dur * 0.5) / max(1, len(spiele)))
        for i, s in enumerate(spiele):
            a = anim(t, 0.2 + i * schritt, 0.4)
            if a <= 0:
                y += h + 8
                continue
            off = 50 * (1 - a)
            d.rounded_rectangle([M + off, y, W - M + off, y + h], radius=18,
                                fill=with_alpha(C["green_d"] if s.get("markiert") else C["panel"], a))
            f = passend(d, "Mönchengladbach", "bold", 34, 330)
            mitte = W / 2 + off
            if s.get("tore_h") is not None:
                erg = f"{s['tore_h']} : {s['tore_g']}"
                fe = font(40, "black")
                d.text((mitte - tw(d, erg, fe) / 2, y + (h - fe.size) / 2 - 6), erg, font=fe, fill=with_alpha(C["ink"], a))
            else:
                erg = s.get("info", "–")
                fe = font(28, "bold")
                d.text((mitte - tw(d, erg, fe) / 2, y + (h - fe.size) / 2 - 4), erg, font=fe, fill=with_alpha(C["muted"], a))
            hn, gn = s["heim"], s["gast"]
            fh = passend(d, hn, "bold", 34, 300, 22)
            fg = passend(d, gn, "bold", 34, 300, 22)
            d.text((mitte - 110 - tw(d, hn, fh), y + (h - fh.size) / 2 - 5), hn, font=fh, fill=with_alpha(C["ink"], a))
            d.text((mitte + 110, y + (h - fg.size) / 2 - 5), gn, font=fg, fill=with_alpha(C["ink"], a))
            y += h + 8

    # ---- Tabelle
    def tabelle(self, d, t, dur, img=None):
        x = self.x
        self._kopf(d, x.get("titel", ""), x.get("unter"))
        zeilen = x.get("zeilen", [])
        y, h = 510, 78
        f, fb = font(34, "bold"), font(34, "black")
        d.text((W - M - 250, y - 44), "Sp.", font=font(26, "bold"), fill=C["muted"])
        d.text((W - M - 160, y - 44), "Diff", font=font(26, "bold"), fill=C["muted"])
        d.text((W - M - 64, y - 44), "Pkt", font=font(26, "bold"), fill=C["muted"])
        for i, z in enumerate(zeilen):
            if z.get("trenner"):
                d.text((W / 2 - 20, y + 4), "···", font=font(40, "black"), fill=C["muted"])
                y += 54
                continue
            a = anim(t, 0.2 + i * 0.12, 0.4)
            if a <= 0:
                y += h + 8
                continue
            zone = {"top": C["green"], "abstieg": C["red"], "relegation": C["gold"]}.get(z.get("zone"))
            d.rounded_rectangle([M, y, W - M, y + h], radius=16, fill=with_alpha(C["panel"], a))
            if zone:
                d.rounded_rectangle([M, y, M + 10, y + h], radius=5, fill=with_alpha(zone, a))
            d.text((M + 30, y + 20), f"{z['platz']}.", font=fb, fill=with_alpha(C["muted"], a))
            name = z["team"]
            fn = passend(d, name, "bold", 34, W - 2 * M - 420, 22)
            d.text((M + 110, y + 20), name, font=fn, fill=with_alpha(C["ink"], a))
            d.text((W - M - 250, y + 20), str(z.get("sp", "")), font=f, fill=with_alpha(C["muted"], a))
            diff = z.get("diff", 0)
            d.text((W - M - 160, y + 20), f"{diff:+d}" if isinstance(diff, int) else str(diff), font=f,
                   fill=with_alpha(C["muted"], a))
            pk = str(z.get("pkt", ""))
            d.text((W - M - 30 - tw(d, pk, fb), y + 20), pk, font=fb, fill=with_alpha(C["ink"], a))
            y += h + 8

    # ---- Faktenkarten (2 Spalten)
    def fakten(self, d, t, dur, img=None):
        x = self.x
        self._kopf(d, x.get("titel", ""), x.get("unter"))
        karten = x.get("karten", [])[:6]
        colw = (W - 2 * M - 24) / 2
        for i, k in enumerate(karten):
            a = anim(t, 0.25 + i * 0.25, 0.45)
            if a <= 0:
                continue
            cx = M + (i % 2) * (colw + 24)
            cy = 510 + (i // 2) * 230 + 30 * (1 - a)
            d.rounded_rectangle([cx, cy, cx + colw, cy + 210], radius=26, fill=with_alpha(C["panel"], a))
            d.text((cx + 30, cy + 26), k["label"], font=passend(d, k["label"], "medium", 32, colw - 60),
                   fill=with_alpha(C["muted"], a))
            w = k["wert"]
            d.text((cx + 30, cy + 84), w, font=passend(d, w, "black", 76, colw - 60, 30),
                   fill=with_alpha(C[k.get("farbe", "ink")], a))

    # ---- Großer Hinweis mit Vergleichsbalken (z. B. WHO-Empfehlung)
    def info(self, d, t, dur, img=None):
        x = self.x
        self._kopf(d, x.get("titel", ""), x.get("unter"))
        a = anim(t, 0.2, 0.5)
        d.rounded_rectangle([M, 510, W - M, 1180], radius=30, fill=with_alpha(C["panel"], a))
        g = x.get("gross", "")
        center(d, g, 560, passend(d, g, "black", 120, W - 2 * M - 80, 50), with_alpha(C[x.get("farbe", "gold")], a))
        f = font(40, "bold")
        y = 730
        for ln in wrap(d, x.get("text", ""), f, W - 2 * M - 100)[:4]:
            center(d, ln, y, f, with_alpha(C["ink"], a))
            y += 54
        b = x.get("balken")
        if b:
            bx0, bx1, by = M + 60, W - M - 60, 1020
            anteil = b["anteil"] * anim(t, 0.6, 1.0)
            d.rounded_rectangle([bx0, by, bx1, by + 40], radius=20, fill=C["panel2"])
            voll = min(anteil, 1.0)
            col = C["red"] if b["anteil"] >= 1 else C["gold"] if b["anteil"] >= 0.5 else C["green"]
            d.rounded_rectangle([bx0, by, bx0 + max(40, (bx1 - bx0) * voll), by + 40], radius=20, fill=col)
            lab = b.get("label", "")
            center(d, lab, by + 64, passend(d, lab, "bold", 36, W - 2 * M - 120), C["muted"])

    # ---- Abschluss mit offener Frage
    def frage(self, d, t, dur, img=None):
        x = self.x
        a = anim(t, 0.1, 0.5)
        f = font(96, "black")
        lines = wrap(d, x.get("frage", ""), f, W - 2 * M)
        if len(lines) > 2:
            f = font(78, "black")
            lines = wrap(d, x.get("frage", ""), f, W - 2 * M)[:3]
        y = 560 - len(lines) * f.size * 0.55
        for i, ln in enumerate(lines):
            center(d, ln, y, f, with_alpha(C["green"] if i == len(lines) - 1 else C["ink"], a))
            y += f.size * 1.12
        if x.get("tag"):
            pill(d, W / 2, 720, x["tag"], font(38, "bold"), with_alpha(C["panel2"], anim(t, 0.4)),
                 with_alpha(C["ink"], anim(t, 0.4)), (30, 18), "c")
        a2 = anim(t, 0.8, 0.5)
        d.rounded_rectangle([M + 40, 860, W - M - 40, 990], radius=30, outline=with_alpha(C["gold"], a2), width=4)
        center(d, x.get("hinweis", ""), 885, passend(d, x.get("hinweis", ""), "black", 46, W - 2 * M - 120),
               with_alpha(C["gold"], a2))
        center(d, x.get("hinweis2", ""), 942, passend(d, x.get("hinweis2", ""), "medium", 32, W - 2 * M - 120),
               with_alpha(C["muted"], a2))
        a3 = anim(t, 1.4, 0.5)
        center(d, x.get("cta", ""), 1070, font(44, "bold"), with_alpha(C["ink"], a3))
        xm, yb = W / 2, 1150 + 10 * math.sin(t * 4)
        d.polygon([(xm - 34, yb), (xm + 34, yb), (xm, yb + 40)], fill=with_alpha(C["green"], a3))
