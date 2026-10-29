"""Erzeugt aus den Daten ein Hochkant-Video (1080x1920, 30 fps) mit KI-Stimme und Untertiteln.

Ablauf: Sprechtext je Szene -> Stimme (edge-tts, kostenlos) -> Szenenlängen an die Stimme
anpassen und auf mindestens `min_sekunden` strecken -> Bilder zeichnen (Pillow) -> ffmpeg.
Alle Bildschirm-Texte kommen aus sprache.py, dadurch gibt es jedes Video auf Deutsch und Englisch.
"""
import asyncio
import math
import os
import subprocess
import tempfile
import wave
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from sprache import MONATE_KURZ, L, branche, datum, geld, heute, kurs, prozent, rolle, zahl

W, H, FPS = 1080, 1920, 30
M = 64                                   # Seitenrand
C = dict(bg=(9, 12, 17), panel=(20, 25, 32), panel2=(28, 34, 43), ink=(242, 244, 247), muted=(138, 148, 160),
         line=(44, 52, 63), green=(34, 197, 94), green_d=(20, 83, 45), red=(239, 68, 68), red_d=(60, 24, 24),
         gold=(250, 204, 21), blue=(96, 165, 250))
ERSATZ_STIMMEN = {"de": ["de-DE-FlorianMultilingualNeural", "de-DE-ConradNeural", "de-DE-KillianNeural"],
                  "en": ["en-US-AndrewMultilingualNeural", "en-US-ChristopherNeural", "en-US-GuyNeural"]}

# ---------------------------------------------------------------- Schriften

_FONT_DIRS = ["fonts", "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
              "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts"]
_FONT_FILES = {
    "black": ["Inter-Black.otf", "Inter-Black.ttf", "Inter-ExtraBold.otf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
    "bold": ["Inter-Bold.otf", "Inter-Bold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
    "medium": ["Inter-Medium.otf", "Inter-Medium.ttf", "DejaVuSans.ttf", "arial.ttf"],
}
_fcache = {}


def font(size, weight="bold"):
    key = (size, weight)
    if key not in _fcache:
        f = None
        for name in _FONT_FILES[weight]:
            for d in _FONT_DIRS:
                p = os.path.join(d, name)
                if os.path.exists(p):
                    f = ImageFont.truetype(p, size)
                    break
            if f:
                break
        _fcache[key] = f or ImageFont.load_default(size)
    return _fcache[key]


# ---------------------------------------------------------------- Helfer

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def anim(t, start, dauer=0.5):
    return ease((t - start) / dauer)


def tw(d, text, f):
    return d.textlength(text, font=f)


def center(d, text, y, f, fill, stroke=0, sfill=(0, 0, 0)):
    d.text(((W - tw(d, text, f)) / 2, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)


def mix(c1, c2, a):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))


def with_alpha(c, a):
    return (*c[:3], int(255 * max(0.0, min(1.0, a))))


def passend(d, text, weight, size, maxw, minsize=24):
    f = font(size, weight)
    while tw(d, text, f) > maxw and f.size > minsize:
        f = font(f.size - 2, weight)
    return f


def pill(d, x, y, text, f, bg, fg, pad=(26, 12), anchor="l"):
    w = tw(d, text, f)
    h = f.size
    if anchor == "c":
        x = x - (w + 2 * pad[0]) / 2
    elif anchor == "r":
        x = x - (w + 2 * pad[0])
    d.rounded_rectangle([x, y, x + w + 2 * pad[0], y + h + 2 * pad[1]], radius=(h + 2 * pad[1]) // 2, fill=bg)
    d.text((x + pad[0], y + pad[1] - h * 0.08), text, font=f, fill=fg)
    return x + w + 2 * pad[0]


def warn_icon(d, x, y, s, col, bg=None):
    d.polygon([(x + s / 2, y), (x + s, y + s * 0.9), (x, y + s * 0.9)], fill=col)
    bg = bg or C["bg"]
    d.rectangle([x + s * 0.46, y + s * 0.3, x + s * 0.54, y + s * 0.6], fill=bg)
    d.rectangle([x + s * 0.46, y + s * 0.68, x + s * 0.54, y + s * 0.78], fill=bg)


def check_icon(d, x, y, s, col):
    d.ellipse([x, y, x + s, y + s], fill=col)
    d.line([(x + s * .27, y + s * .52), (x + s * .44, y + s * .68), (x + s * .74, y + s * .34)], fill=C["bg"],
           width=max(3, int(s * .12)), joint="curve")


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if tw(d, t, f) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def background():
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([14, 20, 28]), np.array(C["bg"])
    g = (top * (1 - y) + bot * y)[:, None, :].repeat(W, axis=1)
    img = Image.fromarray(g.astype(np.uint8).reshape(H, W, 3), "RGB")
    d = ImageDraw.Draw(img)
    for x in range(0, W, 90):                                     # feines Raster wie ein Trading-Terminal
        d.line([(x, 0), (x, H)], fill=(18, 24, 32), width=1)
    for yy in range(0, H, 90):
        d.line([(0, yy), (W, yy)], fill=(18, 24, 32), width=1)
    return img


# ---------------------------------------------------------------- Stimme

async def _edge(text, voice, rate, out_mp3):
    import edge_tts
    try:
        com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:                                               # ältere edge-tts-Version
        com = edge_tts.Communicate(text, voice, rate=rate)
    words, audio = [], bytearray()
    async for ch in com.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            s = ch["offset"] / 1e7
            words.append((s, s + ch["duration"] / 1e7, ch["text"]))
    with open(out_mp3, "wb") as f:
        f.write(audio)
    return words


def _wav_samples(path, sr):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768


def _pct(t, default=0):
    try:
        return int(str(t).replace("%", "").strip())
    except (TypeError, ValueError):
        return default


def sprechen_eleven(szenen, vcfg, lang, tmp, sr):
    """ElevenLabs für alle Szenen. Gibt True zurück, wenn alles geklappt hat (sonst Rückfall auf Gratis-Stimme).
    Der ganze Text wird in einem Stück gesprochen (natürlicher Fluss und Betonung über die Szenen hinweg)
    und danach an den Szenengrenzen geschnitten. Zahlen werden vorher ausgeschrieben (aussprache.py)."""
    import aussprache
    import tts_elevenlabs as el
    if not el.schluessel():
        print("  ElevenLabs: kein Schlüssel (GitHub-Secret ELEVENLABS_API_KEY) -> kostenlose Stimme.")
        return False
    paare = [aussprache.vorlesen(s["text"], lang) for s in szenen]
    texte = [" ".join(g for _, g in p) for p in paare]
    bedarf = sum(len(t) for t in texte)
    rest = el.restguthaben()
    if rest is not None and rest < bedarf:
        print(f"  ElevenLabs: Guthaben reicht nicht ({rest} Zeichen übrig, {bedarf} nötig) -> kostenlose Stimme.")
        return False
    tempo = float(vcfg.get("eleven_tempo", 1.0)) + (_pct(vcfg.get("tempo")) - _pct(vcfg.get("tempo_grund"),
                                                                                    _pct(vcfg.get("tempo")))) / 100
    arg = dict(modell=vcfg.get("eleven_modell", "eleven_multilingual_v2"), tempo=tempo,
               einstellungen=vcfg.get("eleven_einstellungen"), sprache=lang)
    stimme = vcfg.get("eleven_stimme") or "brian"
    try:
        ergebnisse = None
        if vcfg.get("eleven_am_stueck", True) and len(szenen) > 1:
            ergebnisse = _eleven_am_stueck(el, texte, stimme, arg, tmp, lang, sr)
        if ergebnisse is None:                                          # Szene für Szene
            ergebnisse = []
            for i, t in enumerate(texte):
                mp3 = os.path.join(tmp, f"el_{lang}{i}.mp3")
                woerter = el.sprechen(t, stimme, mp3, vorher=texte[i - 1] if i else None,
                                      nachher=texte[i + 1] if i + 1 < len(texte) else None, **arg)
                a = _wav_samples(mp3, sr)
                if len(a) < sr * 0.3:
                    raise RuntimeError("leere Audiodatei")
                ergebnisse.append((a, len(a) / sr, woerter))
        for s, p, t, (a, dur, woerter) in zip(szenen, paare, texte, ergebnisse):
            if not woerter:
                ws = t.split()
                woerter = [(k * dur / len(ws), (k + 1) * dur / len(ws), w) for k, w in enumerate(ws)]
            s.update(audio=a, sprech_dauer=dur, woerter=aussprache.untertitel(p, woerter))
        print(f"  [{lang}] ElevenLabs-Stimme ({bedarf} Zeichen)")
        return True
    except Exception as e:
        print(f"  ElevenLabs nicht verfügbar ({str(e)[:120]}) -> kostenlose Stimme.")
        return False


def _eleven_am_stueck(el, texte, stimme, arg, tmp, lang, sr):
    """Ein Aufruf für alle Szenen, danach Schnitt in der Pause zwischen zwei Szenen.
    Gibt None zurück, wenn die Zeitangaben nicht zum Text passen (dann Szene für Szene)."""
    trenner = "\n\n"
    voll = trenner.join(texte)
    mp3 = os.path.join(tmp, f"el_{lang}_voll.mp3")
    zeichen, starts, enden = el.sprechen(voll, stimme, mp3, roh=True, **arg)
    if len(zeichen) != len(voll) or not starts:
        print("  ElevenLabs: Zeitangaben passen nicht zum Text -> Szene für Szene.")
        return None
    a = _wav_samples(mp3, sr)
    gesamt = len(a) / sr
    bereiche, pos = [], 0
    for t in texte:
        bereiche.append((pos, pos + len(t)))
        pos += len(t) + len(trenner)
    erste = [min((starts[k] for k in range(b0, b1) if not zeichen[k].isspace()), default=None) for b0, b1 in bereiche]
    letzte = [max((enden[k] for k in range(b0, b1) if not zeichen[k].isspace()), default=None) for b0, b1 in bereiche]
    if None in erste or None in letzte:
        return None
    schnitte = [0.0] + [(letzte[i] + erste[i + 1]) / 2 for i in range(len(texte) - 1)] + [gesamt]
    out = []
    for i, (b0, b1) in enumerate(bereiche):
        t0, t1 = schnitte[i], schnitte[i + 1]
        stueck = a[int(t0 * sr):int(t1 * sr)]
        woerter = [(w0 - t0, w1 - t0, w) for w0, w1, w in
                   el.woerter_aus_zeichen(zeichen[b0:b1], starts[b0:b1], enden[b0:b1])]
        out.append((stueck, len(stueck) / sr, woerter))
    return out


def sprechen(szenen, vcfg, lang, tmp, sr=24000):
    """Fügt jeder Szene 'audio' (numpy), 'sprech_dauer' und 'woerter' [(start, ende, wort)] hinzu.
    Gibt zurück, ob die Stimme funktioniert hat."""
    if vcfg.get("anbieter") == "elevenlabs" and not vcfg.get("_eleven_aus"):
        if sprechen_eleven(szenen, vcfg, lang, tmp, sr):
            return True
        vcfg["_eleven_aus"] = True                                  # für diesen Lauf nicht nochmal versuchen
    stimmen = [vcfg.get("stimme")] + (ERSATZ_STIMMEN.get(lang, []) if vcfg.get("ersatz", True) else [])
    stimmen = [s for i, s in enumerate(stimmen) if s and s not in stimmen[:i]]
    rate = vcfg.get("tempo", "+5%")
    ton_ok = True
    for i, s in enumerate(szenen):
        a, words = None, []
        if ton_ok:
            for v in stimmen:
                try:
                    mp3 = os.path.join(tmp, f"{lang}{i}.mp3")
                    words = asyncio.run(_edge(s["text"], v, rate, mp3))
                    a = _wav_samples(mp3, sr)
                    if len(a) < sr * 0.3:
                        raise RuntimeError("leere Audiodatei")
                    if v != stimmen[0]:
                        stimmen = [v]                              # funktionierende Stimme behalten
                    break
                except Exception as e:
                    a, words, fehler = None, [], e
            if a is None:
                ton_ok = False
                print(f"  Stimme nicht verfügbar ({str(fehler)[:80]}) -> Video ohne Ton, Untertitel geschätzt.")
        if a is None:
            n = len(s["text"].split())
            a = np.zeros(int(sr * (n / 2.9 + 0.3)), dtype=np.float32)
        dur = len(a) / sr
        if not words:                                                 # Zeiten gleichmäßig schätzen
            ws = s["text"].split()
            step = dur / max(1, len(ws))
            words = [(k * step, (k + 1) * step, w) for k, w in enumerate(ws)]
        s.update(audio=a, sprech_dauer=dur, woerter=words)
    return ton_ok


def zeitplan(szenen, min_sek, lead=0.08, tail=0.28):
    for s in szenen:
        s["dauer"] = lead + s["sprech_dauer"] + tail
    total = sum(s["dauer"] for s in szenen)
    if total < min_sek:                                               # auf Mindestlänge strecken
        # Fehlende Zeit in kleinen Häppchen auf alle Szenen verteilen (keine langen Stillen),
        # etwas mehr am Ende, wo die Frage auf dem Bildschirm stehen bleibt.
        extra = min_sek - total
        gewicht = {s_i: s["sprech_dauer"] * (1.6 if s["name"] in ("outro", "frage") else 1.0)
                   for s_i, s in enumerate(szenen)}
        summe = sum(gewicht.values()) or 1
        for s_i, s in enumerate(szenen):
            s["dauer"] += extra * gewicht[s_i] / summe
    t = 0.0
    for s in szenen:
        s["start"], s["lead"] = t, lead
        t += s["dauer"]
    return t


# ---------------------------------------------------------------- Szenen

class Szenen:
    def __init__(self, D):
        self.D = D
        self.lang = D["lang"]
        self._chart = None

    def T(self, key, **kw):
        return L(self.lang, key, **kw)

    # ---- 1 Hook
    def hook(self, d, t, dur):
        D, hk = self.D, self.D["hook"]
        # Alles steht ab dem ersten Bild (die ersten 1-2 Sekunden entscheiden übers Weiterwischen).
        pill(d, W / 2, 380, D["tag"], font(56, "black"), C["green"], C["bg"], (34, 14), "c")
        center(d, D["kurzname"], 490, passend(d, D["kurzname"], "bold", 64, W - 2 * M), C["ink"])
        center(d, hk["kicker"], 640, font(58, "black"), C["muted"])
        txt = hk["text"] if hk.get("text") else hk["fmt"](hk["wert"])
        pop = 1 + 0.08 * math.sin(min(1.0, t / 0.35) * math.pi)          # kurzer Puls, kein Ausblenden
        f = passend(d, txt, "black", int(170 * pop), int((W - 2 * M) * pop), 90)
        center(d, txt, 720 - (f.size - 170) * 0.5, f, C[hk.get("farbe", "green")])
        center(d, hk["sub"], 930, passend(d, hk["sub"], "medium", 48, W - 2 * M), C["ink"])
        n = min(hk.get("personen") or 0, 8)                           # Personen-Symbole bei Insiderkäufen
        size, gap = 74, 26
        x0 = (W - (n * size + (n - 1) * gap)) / 2
        for i in range(n):
            ai = anim(t, 0.15 + i * 0.08, 0.25)
            if ai <= 0:
                continue
            x, y = x0 + i * (size + gap), 1050 + 20 * (1 - ai)
            col = with_alpha(C["green"], ai)
            d.ellipse([x + size * .3, y, x + size * .7, y + size * .4], fill=col)
            d.rounded_rectangle([x + size * .1, y + size * .46, x + size * .9, y + size], radius=24, fill=col)

    # ---- 2 Firmen-Steckbrief
    def intro(self, d, t, dur):
        D, lang = self.D, self.lang
        d.text((M, 340), D["kurzname"], font=passend(d, D["kurzname"], "black", 76, W - 2 * M), fill=C["ink"])
        d.text((M, 438), f"{D['ticker']} · {branche(D['branche'], lang)}", font=font(42, "medium"), fill=C["muted"])
        cur = D["waehrung"]
        r12 = D.get("rendite_12m")
        rows = [(self.T("kurs"), kurs(D["kurs"], cur, lang), C["ink"]),
                (self.T("mcap"), geld(D["marketCap"], cur, lang) if D.get("marketCap") else "–", C["ink"]),
                (self.T("r12"), prozent(r12, lang) if r12 is not None else "–",
                 C["green"] if (r12 or 0) >= 0 else C["red"]),
                (self.T("kgv"), zahl(D["forwardPE"], lang) if D.get("forwardPE") else "–", C["ink"]),
                (self.T("div"), prozent(D["div_rendite"], lang, vorzeichen=False) if D.get("div_rendite")
                 else self.T("keine"), C["ink"])]
        y = 560
        for i, (k, v, col) in enumerate(rows):
            a = anim(t, 0.25 + i * 0.18, 0.45)
            if a <= 0:
                continue
            off = 60 * (1 - a)
            d.rounded_rectangle([M + off, y, W - M + off, y + 104], radius=22, fill=with_alpha(C["panel"], a))
            d.text((M + 36 + off, y + 30), k, font=font(40, "medium"), fill=with_alpha(C["muted"], a))
            fv = font(48, "bold")
            d.text((W - M - 36 - tw(d, v, fv) + off, y + 25), v, font=fv, fill=with_alpha(col, a))
            y += 122
        pts = [p for _, p in D.get("preise_1j") or D["preise"]]
        if len(pts) > 3:                                              # Mini-Chart 12 Monate
            a = anim(t, 1.2, 0.8)
            x0, x1, y0, y1 = M, W - M, 1160, 1240
            lo, hi = min(pts), max(pts)
            n = max(2, int(len(pts) * a))
            xy = [(x0 + i * (x1 - x0) / (len(pts) - 1), y1 - (v - lo) / (hi - lo or 1) * (y1 - y0))
                  for i, v in enumerate(pts[:n])]
            d.line(xy, fill=C["green"] if pts[-1] >= pts[0] else C["red"], width=6, joint="curve")

    # ---- 3 Chart (mit Insiderkäufen, falls vorhanden)
    def _chart_layer(self):
        """Linie + Fläche einmal in doppelter Auflösung zeichnen (glatte Kanten), danach nur aufdecken."""
        D = self.D
        x0, x1, y0, y1 = M + 10, W - M - 130, 470, 1100
        pr = [p for _, p in D["preise"]]
        alle = pr + [k["preis"] for k in D["kaeufe"] if k.get("preis")]
        lo, hi = min(alle), max(alle)
        pad = (hi - lo) * 0.12 or 1
        lo, hi = lo - pad, hi + pad
        fx = lambda i: x0 + i * (x1 - x0) / (len(pr) - 1)
        fy = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
        S = 2
        big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        pts = [(fx(i) * S, fy(v) * S) for i, v in enumerate(pr)]
        col = C["green"] if pr[-1] >= pr[0] else C["red"]
        grad = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        ImageDraw.Draw(grad).polygon(pts + [(x1 * S, y1 * S), (x0 * S, y1 * S)], fill=(*col, 255))
        alpha = np.linspace(110, 0, (y1 - y0) * S + 1)                  # Verlauf nach unten ausblenden
        mask = np.zeros((H * S, W * S), dtype=np.uint8)
        mask[int(y0 * S) - 1:int(y0 * S) - 1 + len(alpha), :] = alpha[:, None].astype(np.uint8)
        ga = np.array(grad)
        ga[..., 3] = np.minimum(ga[..., 3], mask)
        big = Image.alpha_composite(big, Image.fromarray(ga))
        ImageDraw.Draw(big).line(pts, fill=(*col, 255), width=7 * S, joint="curve")
        layer = big.resize((W, H), Image.LANCZOS)
        self._chart = dict(layer=layer, fx=fx, fy=fy, x0=x0, x1=x1, y0=y0, y1=y1, lo=lo, hi=hi, col=col)

    def chart(self, d, t, dur, img=None):
        D, lang = self.D, self.lang
        if self._chart is None:
            self._chart_layer()
        c = self._chart
        d.text((M, 340), f"{D['kurzname']} · {self.T('monate', m=D['monate'])}",
               font=passend(d, f"{D['kurzname']} · {self.T('monate', m=D['monate'])}", "black", 54, W - 2 * M),
               fill=C["ink"])
        for k in range(5):                                           # Raster + Achsenbeschriftung
            v = c["lo"] + (c["hi"] - c["lo"]) * (k + 0.5) / 5
            y = c["fy"](v)
            d.line([(c["x0"], y), (c["x1"], y)], fill=C["line"], width=2)
            d.text((c["x1"] + 18, y - 18), zahl(v, lang, 0), font=font(30, "medium"), fill=C["muted"])
        dates = [dt for dt, _ in D["preise"]]
        last_m = None
        for i, dt in enumerate(dates):
            m = dt[5:7]
            if m != last_m and i > 3:
                d.text((c["fx"](i) - 24, c["y1"] + 20), MONATE_KURZ[lang][int(m) - 1], font=font(30, "medium"),
                       fill=C["muted"])
            last_m = m
        dauer_aufdecken = min(4.0, dur * 0.45)
        reveal = anim(t, 0.2, dauer_aufdecken)
        xr = int(c["x0"] + (c["x1"] - c["x0"]) * reveal) + 8
        if xr > c["x0"]:
            img.alpha_composite(c["layer"].crop((0, 0, xr, H)), (0, 0))
        idx = {dt: i for i, dt in enumerate(dates)}

        def naechster(iso):
            if iso in idx:
                return idx[iso]
            z = datetime.strptime(iso, "%Y-%m-%d")
            return min(range(len(dates)), key=lambda j: abs((datetime.strptime(dates[j], "%Y-%m-%d") - z).days))

        if D["kaeufe"]:
            vmax = max(k["wert"] for k in D["kaeufe"])
            for k in D["kaeufe"]:
                i = naechster(k["datum"])
                x, y = c["fx"](i), c["fy"](k.get("preis") or D["preise"][i][1])
                if x > xr:
                    continue
                r = 14 + 22 * math.sqrt(k["wert"] / vmax)
                puls = 0.5 + 0.5 * math.sin(t * 5 + i)
                e = r + 10 + 6 * puls
                d.ellipse([x - e, y - e, x + e, y + e], fill=(*C["green"], 60))
                d.ellipse([x - r, y - r, x + r, y + r], fill=C["green"], outline=C["ink"], width=4)
            g = D["groesster"]
            gi = naechster(g["datum"])
            if c["fx"](gi) <= xr:
                a = anim(t, 0.2 + (c["fx"](gi) - c["x0"]) / (c["x1"] - c["x0"]) * dauer_aufdecken, 0.4)
                x, y = c["fx"](gi), c["fy"](g.get("preis") or D["preise"][gi][1])
                txt = self.T("kauft", rolle=rolle(g["rolle"], lang), x=geld(g["wert"], D["iw"], lang))
                f = font(38, "bold")
                w = tw(d, txt, f) + 48
                bx = min(max(x - w / 2, M), W - M - w)
                by = y - 150 if y - 150 > c["y0"] - 40 else y + 60
                d.rounded_rectangle([bx, by, bx + w, by + 70], radius=20, fill=with_alpha(C["ink"], a))
                d.text((bx + 24, by + 13), txt, font=f, fill=with_alpha(C["bg"], a))
                d.line([(x, by + 70 if by < y else by), (x, y - 20 if by < y else y + 20)],
                       fill=with_alpha(C["ink"], a), width=3)
            d.ellipse([M, 1158, M + 30, 1188], fill=C["green"])
            d.text((M + 46, 1152), self.T("legende"), font=font(36, "medium"), fill=C["muted"])
        else:                                                         # ohne Insider: Hoch und Tief markieren
            pr = [p for _, p in D["preise"]]
            for lab, i, oben in [(self.T("hoch"), pr.index(max(pr)), True), (self.T("tief"), pr.index(min(pr)), False)]:
                x, y = c["fx"](i), c["fy"](pr[i])
                if x > xr:
                    continue
                a = anim(t, 0.2 + (x - c["x0"]) / (c["x1"] - c["x0"]) * dauer_aufdecken, 0.4)
                d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=with_alpha(C["ink"], a))
                txt = f"{lab} {kurs(pr[i], D['waehrung'], lang)}"
                f = font(34, "bold")
                w = tw(d, txt, f) + 40
                bx = min(max(x - w / 2, M), c["x1"] - w)
                by = y - 90 if oben else y + 34
                d.rounded_rectangle([bx, by, bx + w, by + 58], radius=18, fill=with_alpha(C["panel2"], a))
                d.text((bx + 20, by + 10), txt, font=f, fill=with_alpha(C["ink"], a))
        if reveal >= 1:                                               # aktueller Kurs
            a = anim(t, 0.2 + dauer_aufdecken, 0.4)
            y = c["fy"](D["preise"][-1][1])
            pill(d, W - M + 10, y - 30, zahl(D["preise"][-1][1], lang, 2), font(32, "black"),
                 with_alpha(c["col"], a), with_alpha(C["bg"], a), (14, 10), "r")

    # ---- 4 Wer hat gekauft?
    def insider(self, d, t, dur):
        D, lang = self.D, self.lang
        d.text((M, 340), self.T("wer"), font=font(70, "black"), fill=C["ink"])
        d.text((M, 432), self.T("wer_sub", q=D["quelle_kurz"], t=D["tage"]), font=font(38, "medium"), fill=C["muted"])
        top = sorted(D["kaeufe"], key=lambda k: -k["wert"])[:5]
        y = 510
        for i, k in enumerate(top):
            a = anim(t, 0.3 + i * 0.35, 0.45)
            if a <= 0:
                y += 120
                continue
            off = 80 * (1 - a)
            hl = k["name"] == D["groesster"]["name"] and k["wert"] == D["groesster"]["wert"]
            d.rounded_rectangle([M + off, y, W - M + off, y + 106], radius=24,
                                fill=with_alpha(C["green_d"] if hl else C["panel"], a))
            nm = k["name"] if len(k["name"]) <= 22 else k["name"][:21] + "…"
            d.text((M + 32 + off, y + 12), nm, font=font(42, "bold"), fill=with_alpha(C["ink"], a))
            d.text((M + 32 + off, y + 62), f"{rolle(k['rolle'], lang)} · {datum(k['datum'], lang, kurz=True)}",
                   font=font(32, "medium"), fill=with_alpha(C["muted"], a))
            v = geld(k["wert"], D["iw"], lang)
            fv = font(50, "black")
            d.text((W - M - 32 - tw(d, v, fv) + off, y + 26), v, font=fv, fill=with_alpha(C["green"], a))
            y += 120
        a = anim(t, 0.3 + len(top) * 0.35 + 0.2, 0.5)
        if a > 0:
            txt = self.T("gesamt", x=geld(D["summe"], D["iw"], lang), n=D["anzahl_kaeufer"], k=len(D["kaeufe"]))
            f = passend(d, txt, "bold", 38, W - 2 * M - 40)
            d.rounded_rectangle([M, y + 4, W - M, y + 84], radius=40, outline=with_alpha(C["green"], a), width=4)
            center(d, txt, y + 24, f, with_alpha(C["green"], a))

    # ---- 4b Was sagt das Netz? (Sentiment-Radar)
    def stimmung(self, d, t, dur):
        D, R, lang = self.D, self.D.get("radar") or {}, self.lang
        d.text((M, 340), self.T("netz"), font=font(70, "black"), fill=C["ink"])
        d.text((M, 432), self.T("netz_sub"), font=font(38, "medium"), fill=C["muted"])
        y, start = 510, 0.3

        def karte(h, a):
            off = 70 * (1 - a)
            d.rounded_rectangle([M + off, y, W - M + off, y + h], radius=26, fill=with_alpha(C["panel"], a))
            return off

        rd = R.get("reddit")
        if rd is not None:
            a = anim(t, start, 0.45)
            if a > 0:
                o = karte(230, a)
                d.text((M + 36 + o, y + 26), self.T("reddit"), font=font(34, "medium"), fill=with_alpha(C["muted"], a))
                m, m0 = rd["mentions"], rd["mentions_24h"]
                cnt = int(m * anim(t, start + 0.2, 1.0))
                if m >= 10:
                    d.text((M + 36 + o, y + 74), f"{cnt}", font=font(110, "black"), fill=with_alpha(C["ink"], a))
                    ch = (m - m0) / max(m0, 1)
                    lab = self.T("neu") if m0 < 3 else prozent(ch, lang)
                    col = C["green"] if ch >= 0 else C["red"]
                    pill(d, W - M - 36 + o, y + 26, lab, font(40, "black"), with_alpha(col, a), with_alpha(C["bg"], a),
                         (22, 10), "r")
                    mx = max(m, m0, 1)
                    bx = M + 470 + o
                    for j, (lb, v, c2) in enumerate([(self.T("vortag"), m0, C["muted"]), (self.T("heute"), m, col)]):
                        yy = y + 112 + j * 52
                        d.text((bx, yy), lb, font=font(28, "medium"), fill=with_alpha(C["muted"], a))
                        bw = (W - M - 36 - (bx + 150)) * v / mx * anim(t, start + 0.4, 0.8)
                        d.rounded_rectangle([bx + 150, yy + 6, bx + 150 + max(bw, 6), yy + 30], radius=8,
                                            fill=with_alpha(c2, a))
                else:
                    d.text((M + 36 + o, y + 84), self.T("funkstille"), font=font(78, "black"),
                           fill=with_alpha(C["gold"], a))
                    d.text((M + 36 + o, y + 176), self.T("unter_radar", m=m), font=font(32, "medium"),
                           fill=with_alpha(C["muted"], a))
            y += 250
            start += 0.5
        st = R.get("stocktwits")
        if st:
            a = anim(t, start, 0.45)
            if a > 0:
                o = karte(200, a)
                d.text((M + 36 + o, y + 26), self.T("st", n=st["bull"] + st["bear"]), font=font(34, "medium"),
                       fill=with_alpha(C["muted"], a))
                p = st["bull"] / (st["bull"] + st["bear"])
                q = anim(t, start + 0.2, 0.9)
                pa = p * q + 0.5 * (1 - q)
                bx0, bx1, by = M + 36 + o, W - M - 36 + o, y + 90
                split = bx0 + (bx1 - bx0) * pa
                d.rounded_rectangle([bx0, by, bx1, by + 34], radius=17, fill=with_alpha(C["red"], a))
                d.rounded_rectangle([bx0, by, max(split, bx0 + 34), by + 34], radius=17, fill=with_alpha(C["green"], a))
                f = font(40, "black")
                d.text((bx0, by + 50), f"{prozent(pa, lang, vorzeichen=False)} {self.T('bull')}", font=f,
                       fill=with_alpha(C["green"], a))
                tr = f"{prozent(1 - pa, lang, vorzeichen=False)} {self.T('bear')}"
                d.text((bx1 - tw(d, tr, f), by + 50), tr, font=f, fill=with_alpha(C["red"], a))
            y += 220
            start += 0.5
        nw = R.get("news")
        if nw:
            a = anim(t, start, 0.45)
            if a > 0:
                o = karte(170, a)
                d.text((M + 36 + o, y + 26), self.T("news", n=nw["anzahl"]), font=font(34, "medium"),
                       fill=with_alpha(C["muted"], a))
                w = max(-0.5, min(0.5, nw["stimmung"]))
                lab, col = ((self.T("pos"), C["green"]) if w >= .15 else (self.T("neg"), C["red"]) if w <= -.15
                            else (self.T("mix"), C["gold"]))
                f = font(40, "black")
                d.text((W - M - 36 - tw(d, lab, f) + o, y + 20), lab, font=f, fill=with_alpha(col, a))
                bx0, bx1, by = M + 36 + o, W - M - 36 + o, y + 100
                seg = (bx1 - bx0) / 3
                for j, c2 in enumerate([C["red"], C["gold"], C["green"]]):
                    d.rounded_rectangle([bx0 + j * seg + 3, by, bx0 + (j + 1) * seg - 3, by + 16], radius=8,
                                        fill=with_alpha(mix(c2, C["panel"], 0.55), a))
                x = bx0 + (bx1 - bx0) * (0.5 + w * anim(t, start + 0.2, 0.8))
                d.ellipse([x - 20, by - 12, x + 20, by + 28], fill=with_alpha(C["ink"], a))
            y += 190
            start += 0.5
        if R.get("index") is not None:
            a = anim(t, start, 0.5)
            col = C["green"] if R["index"] >= 50 else C["gold"] if R["index"] >= 35 else C["blue"]
            lab = self.T("hype_lab").get(R["label"], R["label"])
            pill(d, W / 2, y + 6, f"{self.T('hype')} {R['index'] * anim(t, start, 1.0):.0f}/100 · {lab}",
                 font(42, "black"), with_alpha(col, a), with_alpha(C["bg"], a), (32, 14), "c")

    # ---- 5 Scanner-Score
    def scanner(self, d, t, dur, img=None):
        D = self.D
        d.text((M, 340), self.T("score"), font=font(70, "black"), fill=C["ink"])
        d.text((M, 432), self.T("platz", r=D["rang"], n=D["n_aktien"]), font=font(40, "medium"), fill=C["muted"])
        p = anim(t, 0.2, 1.3)
        sc = D["score"] * p
        col = C["green"] if D["score"] >= 60 else C["gold"] if D["score"] >= 45 else C["red"]
        S, R = 2, 170                                                 # Ring (2x gezeichnet für glatte Kanten)
        ring = Image.new("RGBA", (2 * R * S + 20, 2 * R * S + 20), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        bb = [10, 10, 2 * R * S + 10, 2 * R * S + 10]
        rd.arc(bb, 135, 405, fill=C["panel2"], width=30 * S)
        if sc > 0.5:
            rd.arc(bb, 135, 135 + 270 * sc / 100, fill=col, width=30 * S)
        ring = ring.resize((ring.width // S, ring.height // S), Image.LANCZOS)
        cx, cy = W // 2, 700
        img.alpha_composite(ring, (cx - ring.width // 2, cy - ring.height // 2))
        center(d, f"{sc:.0f}", cy - 85, font(140, "black"), C["ink"])
        center(d, self.T("von100"), cy + 70, font(36, "medium"), C["muted"])
        kat = self.T("kat")
        colw = (W - 2 * M - 40) / 2
        for i, (key, v) in enumerate(D["kategorien"]):
            a = anim(t, 0.9 + i * 0.12, 0.6)
            cx0 = M + (i % 2) * (colw + 40)
            y = 920 + (i // 2) * 72
            d.text((cx0, y), kat[key], font=font(32, "medium"), fill=C["muted"])
            vt = f"{v * a:.0f}"
            d.text((cx0 + colw - tw(d, vt, font(32, "bold")), y), vt, font=font(32, "bold"), fill=C["ink"])
            d.rounded_rectangle([cx0, y + 44, cx0 + colw, y + 56], radius=6, fill=C["panel2"])
            bc = C["green"] if v >= 60 else C["gold"] if v >= 40 else C["red"]
            if v * a > 1:
                d.rounded_rectangle([cx0, y + 44, cx0 + colw * v * a / 100, y + 56], radius=6, fill=bc)

    # ---- 6 Dafür & dagegen
    def procontra(self, d, t, dur):
        D = self.D
        d.text((M, 340), self.T("pc"), font=font(70, "black"), fill=C["ink"])
        d.text((M, 432), self.T("pc_sub"), font=font(38, "medium"), fill=C["muted"])
        y = 510
        # Die Stimme spricht zuerst die Pro-, dann die Contra-Punkte: grob danach takten
        n_pro, n_con = len(D["pro"]), len(D["contra"])
        sprech = max(dur - 0.8, 2.0)
        t_con = 0.3 + sprech * (n_pro + 0.6) / (n_pro + n_con + 1.2)
        for blk, (titel, items, col, dunkel, icon, t0) in enumerate([
                (self.T("pro"), D["pro"], C["green"], C["green_d"], "check", 0.3),
                (self.T("contra"), D["contra"], C["red"], C["red_d"], "warn", t_con)]):
            a = anim(t, t0, 0.4)
            pill(d, M, y, titel, font(32, "black"), with_alpha(col, a), with_alpha(C["bg"], a), (20, 10))
            y += 76
            schritt = (sprech * 0.42) / max(1, len(items))
            for i, txt in enumerate(items):
                ai = anim(t, t0 + 0.25 + i * schritt, 0.4)
                f = font(40, "bold")
                lines = wrap(d, txt, f, W - 2 * M - 130)[:2]
                hh = 44 + 50 * len(lines)
                if ai > 0:
                    off = 70 * (1 - ai)
                    d.rounded_rectangle([M + off, y, W - M + off, y + hh], radius=24, fill=with_alpha(dunkel, ai))
                    if icon == "check":
                        check_icon(d, M + 30 + off, y + hh / 2 - 26, 52, with_alpha(col, ai))
                    else:
                        warn_icon(d, M + 30 + off, y + hh / 2 - 24, 50, with_alpha(col, ai), bg=dunkel)
                    for j, ln in enumerate(lines):
                        d.text((M + 108 + off, y + 20 + j * 50), ln, font=f, fill=with_alpha(C["ink"], ai))
                y += hh + 14
            y += 26

    # ---- 7 Abschluss mit offener Frage
    def outro(self, d, t, dur):
        D = self.D
        a = anim(t, 0.1, 0.5)
        f = font(96, "black")
        lines = wrap(d, D["frage_kurz"], f, W - 2 * M)
        if len(lines) > 2:
            f = font(80, "black")
            lines = wrap(d, D["frage_kurz"], f, W - 2 * M)[:3]
        y = 560 - len(lines) * f.size * 0.55
        for i, ln in enumerate(lines):
            center(d, ln, y, f, with_alpha(C["green"] if i == len(lines) - 1 else C["ink"], a))
            y += f.size * 1.12
        pill(d, W / 2, 720, f"{D['tag']}  ·  Score {D['score']:.0f}/100", font(38, "bold"),
             with_alpha(C["panel2"], anim(t, 0.4)), with_alpha(C["ink"], anim(t, 0.4)), (30, 18), "c")
        a2 = anim(t, 0.8, 0.5)
        d.rounded_rectangle([M + 40, 860, W - M - 40, 990], radius=30, outline=with_alpha(C["gold"], a2), width=4)
        center(d, self.T("disclaimer"), 885, font(46, "black"), with_alpha(C["gold"], a2))
        center(d, self.T("nur_daten"), 942, font(32, "medium"), with_alpha(C["muted"], a2))
        a3 = anim(t, 1.4, 0.5)
        cta = self.T("follow_insider" if D.get("modus") == "insider" else "follow_liste")
        if D.get("tag_nr") and D.get("modus") != "insider":
            cta = f"{'Morgen: Tag' if self.lang == 'de' else 'Tomorrow: day'} {D['tag_nr'] + 1}"
        center(d, cta, 1070, font(44, "bold"), with_alpha(C["ink"], a3))
        x, yb = W / 2, 1150 + 10 * math.sin(t * 4)
        d.polygon([(x - 34, yb), (x + 34, yb), (x, yb + 40)], fill=with_alpha(C["green"], a3))


# ---------------------------------------------------------------- Untertitel & Rahmen

def untertitel(d, woerter, t_sprech, stil=None):
    """Karaoke-Untertitel: 2-3 Wörter, das gerade gesprochene Wort ist gelb (ruhig: kleiner, gold)."""
    if not woerter or t_sprech < -0.1 or t_sprech > woerter[-1][1] + 0.35:
        return
    f = font(64, "bold") if stil == "ruhig" else font(80, "black")
    gruppen, cur, w_cur = [], [], 0
    for i, (s, e, w) in enumerate(woerter):
        ww = tw(d, w + " ", f)
        if cur and (len(cur) >= 3 or w_cur + ww > W - 2 * M - 40):
            gruppen.append(cur)
            cur, w_cur = [], 0
        cur.append(i)
        w_cur += ww
        if w.endswith((".", "?", "!", ":")):
            gruppen.append(cur)
            cur, w_cur = [], 0
    if cur:
        gruppen.append(cur)
    aktiv = max((i for i, (s, e, w) in enumerate(woerter) if s <= t_sprech), default=0)
    g = next(g for g in gruppen if aktiv in g)
    text = [woerter[i][2] for i in g]
    total = sum(tw(d, w + " ", f) for w in text) - tw(d, " ", f)
    x, y = (W - total) / 2, 1300
    for i, w in zip(g, text):
        if stil == "ruhig":
            d.text((x, y), w, font=f, fill=(233, 190, 96) if i == aktiv else (244, 240, 230), stroke_width=5,
                   stroke_fill=(0, 0, 0))
        else:
            d.text((x, y), w, font=f, fill=C["gold"] if i == aktiv else C["ink"], stroke_width=8, stroke_fill=(0, 0, 0))
        x += tw(d, w + " ", f)


def rahmen(d, t, total, D):
    lang = D["lang"]
    if D.get("rahmen_stil") == "minimal":                          # ruhiger Look: nur feine Linie, Marke, Hinweis
        d.line([(M, 210), (M + (W - 2 * M) * min(1, t / total), 210)], fill=(233, 190, 96), width=3)
        f = font(26, "medium")
        marke = D.get("brand", "")
        x = M
        for c in marke:
            d.text((x, 236), c, font=f, fill=(150, 146, 138))
            x += tw(d, c, f) + 5
        if D.get("tag_nr"):
            tt = f"{'TAG' if lang == 'de' else 'DAY'} {D['tag_nr']}"
            d.text((W - M - tw(d, tt, f), 236), tt, font=f, fill=(150, 146, 138))
        txt = D.get("disclaimer", "")
        center(d, txt, 1470, passend(d, txt, "medium", 24, W - 2 * M, 18), (110, 108, 102))
        return
    d.rounded_rectangle([M, 206, W - M, 214], radius=4, fill=(30, 36, 45))
    d.rounded_rectangle([M, 206, M + (W - 2 * M) * min(1, t / total), 214], radius=4, fill=C["green"])
    x = pill(d, M, 238, D.get("brand") or L(lang, "brand_insider" if D.get("modus") == "insider" else "brand"), font(28, "black"),
             C["green"], C["bg"], (18, 9))
    if D.get("tag_nr"):
        pill(d, x + 12, 238, f"{'TAG' if lang == 'de' else 'DAY'} {D['tag_nr']}", font(28, "black"), C["ink"], C["bg"],
             (18, 9))
    dt, txt_d = font(28, "bold"), heute(lang)
    d.text((W - M - tw(d, txt_d, dt), 246), txt_d, font=dt, fill=C["muted"])
    txt = f"{D.get('disclaimer') or L(lang, 'disclaimer')} · {L(lang, 'daten')}: {D['quellen']}"
    if D.get("haelt"):
        txt = f"{L(lang, 'haelt')} · " + txt
    center(d, txt, 1470, passend(d, txt, "medium", 26, W - 2 * M, 18), C["muted"])


# ---------------------------------------------------------------- Zusammenbau

def render(D, szenen, vcfg, out_path):
    """Gibt (Länge in Sekunden, Ton ok?) zurück."""
    with tempfile.TemporaryDirectory() as tmp:
        print(f"  [{D['lang']}] Stimme erzeugen ...")
        sr = 24000
        ton_ok = sprechen(szenen, vcfg, D["lang"], tmp, sr)
        min_sek = float(vcfg.get("min_sekunden", 61.5))
        total = zeitplan(szenen, min_sek)
        roh = sum(0.36 + s["sprech_dauer"] for s in szenen)       # Länge ohne Streckung
        ziel = float(vcfg.get("ziel_sekunden", 0) or 0)
        try:
            basis = int(str(vcfg.get("tempo", "+5%")).replace("%", ""))
        except ValueError:
            basis = 5
        neu = None
        if ton_ok and ziel and total > ziel + 2:                    # zu lang -> etwas schneller (max. +15 %)
            neu = basis + min(15, int(round((total / ziel - 1) * 100)))
        elif ton_ok and roh < min_sek - 1.5:                        # zu kurz -> etwas ruhiger statt Stille (max. -12 %)
            neu = basis - min(12, int(math.ceil((min_sek / roh - 1) * 100)))
        eleven_aktiv = vcfg.get("anbieter") == "elevenlabs" and not vcfg.get("_eleven_aus")
        if neu is not None and neu != basis and not eleven_aktiv:   # bei ElevenLabs nicht neu sprechen (kostet Guthaben)
            print(f"  [{D['lang']}] {roh:.0f} s Sprechzeit -> Tempo {neu:+d}%")
            ton_ok = sprechen(szenen, dict(vcfg, tempo=f"{neu:+d}%", tempo_grund=f"{basis:+d}%"), D["lang"], tmp, sr)
            total = zeitplan(szenen, min_sek)
        print(f"  [{D['lang']}] Länge: {total:.1f} s")
        audio = np.zeros(int(total * sr) + sr, dtype=np.float32)
        for s in szenen:
            i0 = int((s["start"] + s["lead"]) * sr)
            audio[i0:i0 + len(s["audio"])] += s["audio"]
        audio = audio[:int(total * sr)]
        wav = os.path.join(tmp, "ton.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())

        musik = vcfg.get("musik")
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(FPS), "-i", "-", "-i", wav]
        if musik and os.path.exists(musik):
            vol = float(vcfg.get("musik_lautstaerke", 0.12))
            cmd += ["-stream_loop", "-1", "-i", musik, "-filter_complex",
                    f"[2:a]volume={vol}[m];[1:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                    "-map", "0:v", "-map", "[a]"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}", "-movflags", "+faststart", out_path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        bg = (D.get("hintergrund") or background)().convert("RGBA")
        sz = D.get("szenen_obj") or Szenen(D)                      # Themen bringen ihre eigenen Szenen mit
        n_frames = int(math.ceil(total * FPS))
        si = 0
        for fi in range(n_frames):
            t = fi / FPS
            while si < len(szenen) - 1 and t >= szenen[si + 1]["start"]:
                si += 1
            s = szenen[si]
            tl = t - s["start"]
            img = bg.copy()
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            fn = getattr(sz, s["name"])
            sz.aktuell = s
            if s["name"] in ("chart", "scanner") or getattr(sz, "mit_img", False):
                fn(ld, tl, s["dauer"], img=layer)
            else:
                fn(ld, tl, s["dauer"])
            a = ease(tl / 0.25) if si > 0 else 1.0                    # Szenenwechsel: einblenden + leicht gleiten
            if a < 1:
                la = np.array(layer)
                la[..., 3] = (la[..., 3] * a).astype(np.uint8)
                img.alpha_composite(Image.fromarray(la), (0, int(30 * (1 - a))))
            else:
                img.alpha_composite(layer)
            d = ImageDraw.Draw(img)
            rahmen(d, t, total, D)
            untertitel(d, s["woerter"], tl - s["lead"], D.get("untertitel_stil"))
            proc.stdin.write(img.convert("RGB").tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg ist fehlgeschlagen")
    return total, ton_ok


def vorschaubild(D, out_png):
    """Titelbild (Hook-Szene, fertig aufgebaut) für die Vorschau in der App."""
    img = (D.get("hintergrund") or background)().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if D.get("szenen_obj"):
        obj = D["szenen_obj"]
        obj.aktuell = D["vorschau_szene"]
        getattr(obj, D["vorschau_szene"]["name"])(ImageDraw.Draw(layer), 3.0, 5.0, img=layer)
    else:
        Szenen(D).hook(ImageDraw.Draw(layer), 3.0, 5.0)
    img.alpha_composite(layer)
    rahmen(ImageDraw.Draw(img), 0, 1, D)
    img.convert("RGB").resize((540, 960), Image.LANCZOS).save(out_png, quality=85)
