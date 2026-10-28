"""Video-Bot: macht aus dem Aktien-Scanner jeden Tag fertige TikTok-Videos (über 60 Sekunden),
auf Deutsch und Englisch, mit KI-Stimme und Untertiteln.

  python video_bot.py                  normaler Lauf (Modus aus aktien_config.yaml)
  python video_bot.py --ticker NVDA    Video für eine bestimmte Aktie (auch z. B. SAP.DE)
  python video_bot.py --modus insider  einmalig anderer Modus
  python video_bot.py --demo           Testvideos mit erfundenen Daten (ohne Scanner, schnell)
  python video_bot.py --demo liste     dasselbe ohne Insiderkäufe | --demo dax  deutsche Aktie
  python video_bot.py --stimmprobe     kurze Hörproben aller Stimmen (zum Aussuchen in der App)

Modi:
  liste    arbeitet die Rangliste des Scanners ab: jeden Tag die nächste Aktie, die noch kein Video hat.
           Gibt es Insiderkäufe oder Stimmungsdaten, kommen sie automatisch mit ins Video.
  insider  sucht täglich die stärkste Insider-Story (Insiderkäufe + Scanner + Hype-Index).

Ergebnis: Ordner 'videos' und das Archiv speicher/archiv (für die App) mit videos.json.
"""
import argparse
import json
import os
import random
import shutil
import sys
from datetime import date, datetime, timedelta

import skript
import video
from bewertung import KATEGORIEN

SPEICHER = "speicher"
VERLAUF = os.path.join(SPEICHER, "video_verlauf.json")
ARCHIV = os.path.join(SPEICHER, "archiv")
DEFAULT_VIDEO = {
    "modus": "liste", "anzahl": 1, "sprachen": ["de", "en"],
    "stimmen": {"de": "de-DE-FlorianMultilingualNeural", "en": "en-US-AndrewMultilingualNeural"}, "tempo": "+5%",
    "min_sekunden": 61.5, "chart_monate": 6, "musik": "musik.mp3", "musik_lautstaerke": 0.12,
    "liste_top": 150, "liste_filter": "alle", "wiederholen_nach_tagen": 180,
    "min_kaufsumme": 100_000, "gewicht_scanner": 0.4, "gewicht_insider": 0.6, "gewicht_stimmung": 0.1,
    "sperre_tage": 14, "archiv_tage": 10, "eigene_positionen": [],
    "ziel_sekunden": 68, "serie": True, "aktuell_bevorzugen": True,
    "anbieter": "edge", "eleven_stimmen": {"de": "brian", "en": "brian"},
}


def _f(x):
    try:
        x = float(x)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def json_laden(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def json_speichern(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def kursverlauf(sym, monate):
    import yfinance as yf
    h = yf.Ticker(sym).history(period=f"{monate}mo", auto_adjust=False)
    return [(i.date().isoformat(), round(float(c), 2)) for i, c in h["Close"].dropna().items()]


# ---------------------------------------------------------------- Daten aufbereiten

def daten_paket(r, ins, n_aktien, preise, tage, monate, radar, modus, haelt):
    """Sprachunabhängige Daten: a (für das Skript) und D (für das Bild)."""
    a = {k: (v if not isinstance(v, float) or v == v else None) for k, v in r.items()}
    a["kurs"] = preise[-1][1]                                 # frischer Schlusskurs statt Scanner-Stand
    jahr = [p for p in (r.get("_verlauf") or []) if p] + [preise[-1][1]]
    a["_abstand_hoch"] = preise[-1][1] / max(jahr) - 1 if jahr else None
    fenster = [p for _, p in preise]
    a["_fenster_hoch"] = max(fenster)
    a["_abstand_fenster_hoch"] = preise[-1][1] / max(fenster) - 1
    kaeufe = [k for k in (ins or {}).get("kaeufe", []) if k["datum"] >= preise[0][0]]
    if kaeufe:
        d0, d1 = min(k["datum"] for k in kaeufe), max(k["datum"] for k in kaeufe)
        basis = next((p for d, p in preise if d >= d0), None)
        a["_seit_erstem_kauf"] = preise[-1][1] / basis - 1 if basis else None
        ins = dict(ins, kaeufe=kaeufe, summe=sum(k["wert"] for k in kaeufe),
                   anzahl_kaeufer=len({k["name"] for k in kaeufe}), groesster=max(kaeufe, key=lambda k: k["wert"]),
                   spanne_tage=(datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d0, "%Y-%m-%d")).days + 1)
    else:
        ins = None
    q = []
    if ins:
        q.append(ins.get("quelle", "SEC Form 4"))
    q.append("Yahoo Finance")
    if radar and radar.get("quellen", 0) >= 2:
        if radar.get("reddit") is not None:
            q.append("ApeWisdom")
        if radar.get("stocktwits"):
            q.append("StockTwits")
    D = {
        "ticker": r["ticker"], "name": r["name"], "kurzname": skript.kurzname(r["name"]),
        "branche": r.get("branche") or "", "waehrung": r.get("waehrung") or "USD",
        "kurs": preise[-1][1], "marketCap": _f(r.get("marketCap")), "rendite_12m": _f(r.get("rendite_12m")),
        "forwardPE": _f(r.get("forwardPE")), "div_rendite": _f(r.get("div_rendite")),
        "score": float(r["score"]), "rang": int(r["rang"]), "n_aktien": n_aktien,
        "kategorien": [(c, float(r["k_" + c])) for c in KATEGORIEN],
        "preise": preise, "preise_1j": [(None, p) for p in (r.get("_verlauf") or [])],
        "kaeufe": kaeufe, "summe": ins["summe"] if ins else 0, "anzahl_kaeufer": ins["anzahl_kaeufer"] if ins else 0,
        "groesster": ins["groesster"] if ins else None, "iw": (ins or {}).get("waehrung", "USD"),
        "quelle_kurz": "BaFin" if (ins or {}).get("quelle") == "BaFin" else "SEC",
        "tage": tage, "monate": monate, "radar": radar if radar and radar.get("quellen", 0) >= 2 else {},
        "tag": "$" + r["ticker"] if "." not in r["ticker"] else r["ticker"].split(".")[0],
        "quellen": ", ".join(q), "modus": modus, "haelt": haelt,
    }
    return a, ins, D


def erstellen(a, ins, rad, D0, vcfg, n_aktien, demo=False, tag_nr=None):
    """Rendert das Video in allen Sprachen. Gibt Einträge für das Archiv zurück."""
    os.makedirs("videos", exist_ok=True)
    tk = D0["ticker"].replace(".", "-")
    seed = f"{D0['ticker']}{date.today()}"
    eintraege = []
    print(f"\nVideo: {D0['name']} ({D0['ticker']})")
    for lang in vcfg["sprachen"]:
        sk = skript.bauen(a, ins, rad, n_aktien, lang, D0["monate"], D0["modus"], D0["haelt"], seed, tag_nr)
        D = dict(D0, lang=lang, hook=sk["hook"], frage_kurz=sk["frage_kurz"], pro=sk["pro"], contra=sk["contra"],
                 tag_nr=tag_nr)
        print(f"  [{lang}] Aufhänger: {sk['winkel']}")
        for s in sk["szenen"]:
            print(f"    ({s['name']}) {s['text']}")
        name = f"{date.today():%Y-%m-%d}_{tk}_{lang}"
        mp4, jpg, txt = (os.path.join("videos", name + e) for e in (".mp4", ".jpg", ".txt"))
        lcfg = dict(vcfg, stimme=(vcfg.get("stimmen") or {}).get(lang),
                    eleven_stimme=(vcfg.get("eleven_stimmen") or {}).get(lang) or "brian")
        dauer, ton = video.render(D, sk["szenen"], lcfg, mp4)
        video.vorschaubild(D, jpg)
        text = skript.beschreibung(a, ins, lang, sk["frage_kurz"], sk["titel"][0], sk["tags"])
        with open(txt, "w", encoding="utf-8") as f:
            f.write(text + "\n\n---\n" + "\n".join(s["text"] for s in sk["szenen"]))
        print(f"  [{lang}] fertig: {mp4} ({dauer:.1f} s, Ton: {'ja' if ton else 'NEIN'})")
        eintraege.append({"id": name, "datum": date.today().isoformat(), "ticker": D0["ticker"], "name": D0["kurzname"],
                          "sprache": lang, "mp4": name + ".mp4", "bild": name + ".jpg", "text": text, "titel": sk["titel"], "tags": sk["tags"],
                          "hinweis": text.split("\n\n")[1],
                          "frage": sk["frage_kurz"], "winkel": sk["winkel"], "dauer": round(dauer, 1), "ton": ton,
                          "demo": demo, "erstellt": datetime.now().isoformat(timespec="seconds")})
    return eintraege


def archiv_aktualisieren(neu, vcfg, demo=False):
    """Neue Videos ins Archiv kopieren, alte löschen, videos.json für die App schreiben."""
    os.makedirs(ARCHIV, exist_ok=True)
    liste = json_laden(os.path.join(ARCHIV, "videos.json"), [])
    for e in neu:
        for datei in (e["mp4"], e["bild"]):
            shutil.copy(os.path.join("videos", datei), os.path.join(ARCHIV, datei))
    ids = {e["id"] for e in neu}
    grenze = (date.today() - timedelta(days=int(vcfg["archiv_tage"]))).isoformat()
    liste = [e for e in liste if e["id"] not in ids and e["datum"] >= grenze and (demo or not e.get("demo"))]
    liste = sorted(neu + liste, key=lambda e: (e["datum"], e.get("erstellt", "")), reverse=True)
    behalten = {e["mp4"] for e in liste} | {e["bild"] for e in liste}
    for datei in os.listdir(ARCHIV):
        if datei != "videos.json" and datei not in behalten:
            os.remove(os.path.join(ARCHIV, datei))
    json_speichern(os.path.join(ARCHIV, "videos.json"), liste)
    print(f"Archiv: {len(liste)} Videos für die App.")


# ---------------------------------------------------------------- Demo

def demo_daten(monate, art="us"):
    """Erfundene Firma, damit man das Video ohne Internet testen kann."""
    rnd = random.Random(7)
    preise, p = [], 84.0
    tag = date.today() - timedelta(days=int(monate * 30.4))
    while tag <= date.today():
        if tag.weekday() < 5:
            p *= 1 + rnd.gauss(0.0006, 0.017)
            if len(preise) == 70:
                p *= 0.86                                          # Kurssturz, danach kaufen die Insider
            preise.append((tag.isoformat(), round(p, 2)))
        tag += timedelta(days=1)
    n = len(preise)
    kauf = lambda i, name, rolle, stk: {"datum": preise[i][0], "preis": preise[i][1], "stueck": stk,
                                        "wert": stk * preise[i][1], "name": name, "rolle": rolle}
    r = {"ticker": "DEMO", "name": "Demo Robotics Inc.", "branche": "Technology", "waehrung": "USD",
         "marketCap": 18.4e9, "rendite_12m": -0.08, "forwardPE": 21.3, "div_rendite": 0.0, "score": 71.4, "rang": 23,
         "targetMeanPrice": preise[-1][1] * 1.27, "kursziel_potenzial": 0.27, "numberOfAnalystOpinions": 19,
         "operatingMargins": 0.24, "revenueGrowth": 0.14, "payoutRatio": None, "ueber_ma200": -0.04,
         "warnungen": ["Kurs zeitweise -24% eingebrochen (12 Monate)"],
         "_verlauf": [p for _, p in preise[::5]] + [p * 1.05 for _, p in preise[:10:5]]}
    for c, v in zip(KATEGORIEN, [62, 78, 74, 70, 41, 48, 66, 50]):
        r["k_" + c] = v
    radar = {"reddit": {"mentions": 152, "mentions_24h": 82, "rank": 41, "rank_24h": 77, "upvotes": 930},
             "stocktwits": {"bull": 18, "bear": 7, "n": 30, "pro_stunde": 4.2},
             "news": {"stimmung": 0.31, "anzahl": 6}, "index": 66, "label": "positiv", "quellen": 3}
    kaeufe = [kauf(n - 48, "Laura Brenner", "CEO", 25_000), kauf(n - 46, "Marcus Hale", "Finanzchef", 8_000),
              kauf(n - 41, "Sophie Lindqvist", "Board-Mitglied", 5_500), kauf(n - 30, "Laura Brenner", "CEO", 12_000),
              kauf(n - 12, "David Okafor", "Board-Mitglied", 3_000)]
    quelle = ("USD", "SEC Form 4")
    if art == "dax":
        r.update(ticker="DEMO.DE", name="Demo Maschinenbau AG", branche="Industrials", waehrung="EUR", marketCap=9.2e9)
        kaeufe = [kauf(n - 44, "Dr. Katrin Wendt", "Vorstandschef", 15_000), kauf(n - 43, "Jens Albers", "Vorstand", 6_000),
                  kauf(n - 20, "Ulrike Hagen", "Aufsichtsrat", 2_500)]
        radar = {"reddit": None, "stocktwits": None, "news": {"stimmung": 0.22, "anzahl": 4}, "index": 61,
                 "label": "positiv", "quellen": 1}
        quelle = ("EUR", "BaFin")
    if art in ("liste", "zahlen", "sprung"):
        kaeufe = []
        r.update(rang=4, score=78.2, warnungen=[])
    if art == "zahlen":
        r["_earnings"] = (date.today() + timedelta(days=2)).isoformat()
    if art == "sprung":
        r["_move_1d"] = 0.072
    from insider import zusammenfassung
    ins = zusammenfassung(r["ticker"], kaeufe, r["marketCap"], *quelle) if kaeufe else None
    return r, ins, preise, radar


# ---------------------------------------------------------------- Stimmprobe

STIMMPROBE = {
    "de": [("de-DE-FlorianMultilingualNeural", "Florian (natürlich)"), ("de-DE-SeraphinaMultilingualNeural",
            "Seraphina (natürlich, weiblich)"), ("de-DE-ConradNeural", "Conrad"), ("de-DE-KillianNeural", "Killian"),
           ("de-DE-KatjaNeural", "Katja (weiblich)"), ("de-DE-AmalaNeural", "Amala (weiblich)")],
    "en": [("en-US-AndrewMultilingualNeural", "Andrew (natural)"), ("en-US-BrianMultilingualNeural", "Brian (natural)"),
           ("en-US-AvaMultilingualNeural", "Ava (natural, female)"), ("en-US-EmmaMultilingualNeural",
            "Emma (natural, female)"), ("en-US-ChristopherNeural", "Christopher"), ("en-US-GuyNeural", "Guy")],
}


ELEVEN_PROBE = {"de": "Hallo! So klingt ab jetzt die Stimme in deinen Videos.",
                "en": "Hi! This is how your videos will sound from now on."}


def eleven_proben(cfg, vcfg):
    """ElevenLabs prüfen (kostet nichts) und je eingestellter Stimme einen Satz sprechen (ca. 50 Zeichen)."""
    import tts_elevenlabs as el
    print("ElevenLabs-Prüfung:")
    st = el.kontostatus()
    if not st["ok"]:
        print(f"  NICHT OK: {st['fehler']}")
        return []
    print(f"  OK - Tarif {st['tarif']}, noch {st['rest']:,} von {st['limit']:,} Zeichen übrig".replace(",", "."))
    proben = {}                                   # (stimme, modell, sprache) -> wofür
    if vcfg.get("anbieter") == "elevenlabs":
        for lang in vcfg["sprachen"]:
            sid = (vcfg.get("eleven_stimmen") or {}).get(lang) or "brian"
            proben.setdefault((sid, vcfg.get("eleven_modell", "eleven_multilingual_v2"), lang), []).append("Aktien")
    for name, tc in (cfg.get("themen") or {}).items():
        if (tc or {}).get("anbieter") != "elevenlabs":
            continue
        for lang in (tc.get("sprachen") or ["de"]):
            sid = tc.get("eleven_stimme") or "brian"
            sid = sid.get(lang, "brian") if isinstance(sid, dict) else sid
            modell = tc.get("eleven_modell") or vcfg.get("eleven_modell", "eleven_multilingual_v2")
            proben.setdefault((sid, modell, lang), []).append({"ernaehrung": "Ernährung"}.get(name, name.capitalize()))
    return proben


def stimmprobe(vcfg, monate, tage, modus, cfg=None):
    """Hook + Eckdaten mit jeder Stimme sprechen lassen -> kurze Videos in der App zum Vergleichen."""
    import copy
    r, ins, preise, radar = demo_daten(monate, "us")
    a, ins, D0 = daten_paket(r, ins, 480, preise, tage, monate, radar, modus, False)
    os.makedirs("videos", exist_ok=True)
    neu, jetzt = [], datetime.now()
    for lang in vcfg["sprachen"]:
        sk = skript.bauen(a, ins, D0["radar"], 480, lang, monate, modus, False, "stimmprobe")
        D = dict(D0, lang=lang, hook=sk["hook"], frage_kurz=sk["frage_kurz"], pro=sk["pro"], contra=sk["contra"])
        for i, (stimme, label) in enumerate(STIMMPROBE.get(lang, [])):
            name = f"stimme_{lang}_{stimme.split('-')[2]}"
            mp4 = os.path.join("videos", name + ".mp4")
            lcfg = dict(vcfg, anbieter="edge", stimme=stimme, ersatz=False, min_sekunden=0, musik=None)
            try:
                dauer, ton = video.render(D, copy.deepcopy(sk["szenen"][:2]), lcfg, mp4)
            except Exception as e:
                print(f"  {stimme}: fehlgeschlagen ({e})")
                continue
            if not ton:
                print(f"  {stimme}: diese Stimme gibt es nicht (mehr) - übersprungen")
                os.remove(mp4)
                continue
            video.vorschaubild(D, os.path.join("videos", name + ".jpg"))
            neu.append({"id": name, "datum": date.today().isoformat(), "ticker": stimme, "name": f"Stimme: {label}",
                        "sprache": lang, "mp4": name + ".mp4", "bild": name + ".jpg",
                        "text": f"Für aktien_config.yaml unter video: stimmen: {lang}: {stimme}",
                        "frage": f"{lang}: {stimme}", "winkel": "stimmprobe", "dauer": round(dauer, 1), "ton": True,
                        "demo": True, "erstellt": (jetzt - timedelta(seconds=i)).isoformat(timespec="seconds")})
            print(f"  {stimme}: ok")
    proben = eleven_proben(cfg or {}, vcfg)
    for k, ((sid, modell, lang), wofuer) in enumerate(proben.items()):
        if lang not in ELEVEN_PROBE:
            continue
        name = f"eleven_{lang}_{sid}_{modell.split('_')[1]}"[:60]
        mp4 = os.path.join("videos", name + ".mp4")
        sk = skript.bauen(a, ins, D0["radar"], 480, lang, monate, modus, False, "stimmprobe")
        D = dict(D0, lang=lang, hook=sk["hook"], frage_kurz=sk["frage_kurz"], pro=sk["pro"], contra=sk["contra"])
        sz = copy.deepcopy(sk["szenen"][:1])
        sz[0]["text"] = ELEVEN_PROBE[lang]
        lcfg = dict(vcfg, anbieter="elevenlabs", eleven_stimme=sid, eleven_modell=modell, eleven_tempo=1.0,
                    ersatz=False, min_sekunden=0, musik=None)
        try:
            dauer, ton = video.render(D, sz, lcfg, mp4)
        except Exception as e:
            print(f"  ElevenLabs {sid}: fehlgeschlagen ({e})")
            continue
        video.vorschaubild(D, os.path.join("videos", name + ".jpg"))
        modell_name = "Flash" if "flash" in modell else "Multilingual v2"
        neu.append({"id": name, "datum": date.today().isoformat(), "ticker": sid,
                    "name": f"ElevenLabs: {sid.capitalize()} ({modell_name}) - {', '.join(wofuer)}",
                    "sprache": lang, "mp4": name + ".mp4", "bild": name + ".jpg",
                    "text": f"ElevenLabs funktioniert. Stimme {sid}, Modell {modell}, genutzt für: {', '.join(wofuer)}",
                    "frage": f"{lang}: {sid}", "winkel": "stimmprobe", "dauer": round(dauer, 1), "ton": bool(ton),
                    "demo": True, "erstellt": (jetzt + timedelta(seconds=10 - k)).isoformat(timespec="seconds")})
    archiv_aktualisieren(neu, vcfg, demo=True)


# ---------------------------------------------------------------- Serie & aktuelle Themen

def serien_tag():
    """Tag-Nummer der Serie: zählt pro Kalendertag mit Video eins hoch (mehrere Läufe am selben Tag = gleiche Nummer)."""
    pfad = os.path.join(SPEICHER, "serie.json")
    s = json_laden(pfad, {"tag": 0, "datum": ""})
    heute = date.today().isoformat()
    if s.get("datum") != heute:
        s = {"tag": int(s.get("tag", 0)) + 1, "datum": heute}
        json_speichern(pfad, s)
    return s["tag"]


def aktualitaet_daten(tickers):
    """Vortagesbewegung und nächster Quartalszahlen-Termin für die Kandidaten."""
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor
    out = {t: {} for t in tickers}
    if not tickers:
        return out
    try:
        df = yf.download(tickers, period="7d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
        for t in tickers:
            try:
                c = (df[t]["Close"] if len(tickers) > 1 else df["Close"]).dropna()
                c = c.iloc[:, 0] if hasattr(c, "columns") else c
                if len(c) >= 2:
                    out[t]["move"] = float(c.iloc[-1] / c.iloc[-2] - 1)
            except Exception:
                pass
    except Exception as e:
        print(f"  Kursbewegungen nicht abrufbar ({str(e)[:60]})")

    def termin(t):
        try:
            cal = yf.Ticker(t).calendar
            d = cal.get("Earnings Date") if isinstance(cal, dict) else None
            if d is not None:
                d0 = d[0] if isinstance(d, (list, tuple)) and d else d
                return t, str(d0)[:10]
        except Exception:
            pass
        return t, None

    with ThreadPoolExecutor(max_workers=4) as pool:
        for t, d in pool.map(termin, tickers):
            if d:
                out[t]["earnings"] = d
    return out


def aktualitaet_score(info, rd):
    """0-100: Wie sehr ist die Aktie gerade Thema? (Zahlen bald, großer Kurssprung, Reddit-Trend)"""
    s = 0
    e = info.get("earnings")
    if e:
        try:
            n = (date.fromisoformat(e) - date.today()).days
            if 0 <= n <= 7:
                s += 45 - n * 3
        except ValueError:
            pass
    mv = abs(info.get("move") or 0)
    s += 35 if mv >= 0.06 else 25 if mv >= 0.04 else 12 if mv >= 0.025 else 0
    if rd and rd.get("mentions", 0) >= 30:
        s += 10 + (10 if rd["mentions"] >= 1.5 * max(rd.get("mentions_24h", 0), 1) else 0)
    return min(100, s)


# ---------------------------------------------------------------- Auswahl

def insider_fuer(ticker, name, mcap, cfg):
    """Insiderkäufe für eine einzelne Aktie (Listen-Modus)."""
    try:
        if "." not in ticker:
            import insider
            return insider.load([ticker], cfg, {ticker: mcap}).get(ticker)
        if ticker.endswith(".DE") and (cfg.get("stimmung") or {}).get("bafin", True):
            import bafin
            return bafin.load([(ticker, name, mcap)], cfg).get(ticker)
    except Exception as e:
        print(f"  Insider-Daten für {ticker} nicht verfügbar ({str(e)[:60]})")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", nargs="?", const="us", help="Testvideo: us, liste, dax, zahlen oder sprung")
    ap.add_argument("--ticker", help="bestimmte Aktie erzwingen, z. B. NVDA oder SAP.DE")
    ap.add_argument("--modus", choices=["liste", "insider"], help="Modus für diesen Lauf")
    ap.add_argument("--stimmprobe", action="store_true", help="Hörproben aller Stimmen erzeugen")
    args = ap.parse_args()

    import aktien
    cfg = aktien.load_config()
    vcfg = {**DEFAULT_VIDEO, **(cfg.get("video") or {})}
    vcfg["stimmen"] = {**DEFAULT_VIDEO["stimmen"], **(vcfg.get("stimmen") or {})}
    modus = args.modus or vcfg["modus"]
    monate = int(vcfg["chart_monate"])
    tage = int((cfg.get("insider") or {}).get("tage", 90))
    eigene = {str(t).upper() for t in vcfg.get("eigene_positionen") or []}

    if args.stimmprobe:
        stimmprobe(vcfg, monate, tage, modus, cfg)
        return

    if args.demo:
        vcfg["anbieter"] = "edge"          # Testvideos mit Gratis-Stimme: spart ElevenLabs-Guthaben
        r, ins, preise, radar = demo_daten(monate, args.demo)
        a, ins, D = daten_paket(r, ins, 480, preise, tage, monate, radar, modus, r["ticker"] in eigene)
        neu = erstellen(a, ins, D["radar"], D, vcfg, 480, demo=True, tag_nr=12 if vcfg.get("serie", True) else None)
        archiv_aktualisieren(neu, vcfg, demo=True)
        return

    import daten
    import stimmung
    import universum
    from bewertung import frame, score

    syms, _ = universum.build(cfg)
    raw, _ = daten.load(syms, threads=int(os.environ.get("AKTIEN_THREADS", cfg["filter"]["threads"])))
    if not raw:
        sys.exit("Keine Scanner-Daten. Internetverbindung prüfen.")
    df = score(frame(raw), cfg)
    n_aktien = len(df)
    scfg = cfg.get("stimmung") or {}
    reddit = stimmung.reddit_alle() if scfg.get("aktiv", True) and scfg.get("reddit", True) else None
    verlauf = json_laden(VERLAUF, {})
    heute = date.today()

    auswahl = []                                                     # [(scanner-zeile, insider)]
    akt = {}                                                         # Aktualität je Ticker (Zahlen-Termin, Vortag)
    if args.ticker:
        t = args.ticker.strip().upper()
        zeile = df[df["ticker"] == t]
        if zeile.empty:
            sys.exit(f"{t} ist nicht in der Scanner-Liste (Ticker wie bei Yahoo, z. B. NVDA oder SAP.DE).")
        r = zeile.iloc[0]
        auswahl.append((r, insider_fuer(t, r["name"], r["marketCap"], cfg)))
    elif modus == "liste":
        kand = df
        if vcfg["liste_filter"] == "ohne_warnungen":
            kand = kand[kand["warnungen"].apply(len) == 0]
        kand = kand.head(int(vcfg["liste_top"]))
        grenze = (heute - timedelta(days=int(vcfg["wiederholen_nach_tagen"]))).isoformat()
        offen = [r for _, r in kand.iterrows() if verlauf.get(r["ticker"], "") < grenze]
        if not offen:                                                # alles durch -> mit den ältesten neu anfangen
            offen = sorted((r for _, r in kand.iterrows()), key=lambda r: verlauf.get(r["ticker"], ""))
        print(f"Listen-Modus: {len(offen)} Aktien der Top {len(kand)} noch ohne Video.")
        if vcfg.get("aktuell_bevorzugen", True) and len(offen) > 1:
            infos = aktualitaet_daten([r["ticker"] for r in offen])
            akt.update(infos)
            bewertet = []
            for i, r in enumerate(offen):
                sc = aktualitaet_score(infos.get(r["ticker"], {}), (reddit or {}).get(r["ticker"]))
                bewertet.append((0.5 * r["score"] + sc - i * 0.05, sc, r))   # Rangliste bleibt Grundlage
            bewertet.sort(key=lambda x: -x[0])
            print("Aktuelle Themen unter den Kandidaten:")
            for k, sc, r in bewertet[:5]:
                inf = infos.get(r["ticker"], {})
                print(f"  {r['ticker']:<8} Aktualität {sc:3.0f} | Score {r['score']:4.0f} | "
                      f"Zahlen {inf.get('earnings', '-')} | Vortag {100 * (inf.get('move') or 0):+.1f} %")
            offen = [r for _, _, r in bewertet]
        for r in offen[: int(vcfg["anzahl"])]:
            auswahl.append((r, insider_fuer(r["ticker"], r["name"], r["marketCap"], cfg)))
    else:                                                            # Insider-Modus
        import bafin
        import insider
        ins_all = insider.load(list(df["ticker"]), cfg, dict(zip(df["ticker"], df["marketCap"])))
        if scfg.get("bafin", True):
            de = df[df["ticker"].str.endswith(".DE")]
            ins_all.update(bafin.load(list(zip(de["ticker"], de["name"], de["marketCap"])), cfg))
        sperre = (heute - timedelta(days=int(vcfg["sperre_tage"]))).isoformat()
        rows = []
        for _, r in df.iterrows():
            i = ins_all.get(r["ticker"])
            if not i or i["summe"] < float(vcfg["min_kaufsumme"]) or verlauf.get(r["ticker"], "") >= sperre:
                continue
            rad = stimmung.radar(r["ticker"], r.get("news_stimmung"), r.get("news_anzahl"), reddit, mit_stocktwits=False)
            kombi = (vcfg["gewicht_scanner"] * r["score"] + vcfg["gewicht_insider"] * i["insider_score"]
                     + vcfg["gewicht_stimmung"] * (rad["index"] if rad["index"] is not None else 50))
            rows.append((kombi, r, i))
        rows.sort(key=lambda x: -x[0])
        print("\nBeste Insider-Storys heute:")
        for kombi, r, i in rows[:10]:
            print(f"  {r['ticker']:<8} Kombi {kombi:5.1f} | Scanner {r['score']:4.0f} | Insider {i['insider_score']:4.0f}")
        auswahl = [(r, i) for _, r, i in rows[: int(vcfg["anzahl"])]]
        if not auswahl:
            print("Heute keine passende Insider-Story (min_kaufsumme evtl. senken oder modus: liste nutzen).")

    neu = []
    fehlend = [r["ticker"] for r, _ in auswahl if r["ticker"] not in akt]
    if fehlend:
        akt.update(aktualitaet_daten(fehlend))
    tag_nr = serien_tag() if auswahl and vcfg.get("serie", True) else None
    for r, ins in auswahl:
        try:
            preise = kursverlauf(r["ticker"], monate)
            if len(preise) < 30:
                print(f"  {r['ticker']}: zu wenig Kursdaten, überspringe.")
                continue
            rad = (stimmung.radar(r["ticker"], r.get("news_stimmung"), r.get("news_anzahl"), reddit,
                                  mit_stocktwits=scfg.get("stocktwits", True)) if scfg.get("aktiv", True) else {})
            zeile = r.to_dict()
            inf = akt.get(r["ticker"], {})
            zeile.update(_move_1d=inf.get("move"), _earnings=inf.get("earnings"))
            a, ins2, D = daten_paket(zeile, ins, n_aktien, preise, tage, monate, rad, modus,
                                     r["ticker"].upper() in eigene)
            neu += erstellen(a, ins2, D["radar"], D, vcfg, n_aktien, tag_nr=tag_nr)
            verlauf[r["ticker"]] = heute.isoformat()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  {r['ticker']}: Video fehlgeschlagen ({e})")
    json_speichern(VERLAUF, verlauf)
    archiv_aktualisieren(neu, vcfg)
    if auswahl and not neu:
        sys.exit("Es konnte kein Video erstellt werden (Details oben).")


if __name__ == "__main__":
    main()
