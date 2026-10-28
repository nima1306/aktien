"""Insiderkäufe deutscher Aktien aus der BaFin-Datenbank "Directors' Dealings" (Art. 19 MAR).

Vorstände, Aufsichtsräte und ihnen nahestehende Personen müssen Geschäfte in Aktien der eigenen
Firma ab 20.000 € im Jahr melden. Die BaFin veröffentlicht sie in einer Datenbank mit CSV-Export.
Gezählt werden nur Käufe von Aktien (keine Verkäufe, Optionen, Anleihen, Zeichnungen).

Die Datenbank hat keine offizielle Schnittstelle. Falls die BaFin ihre Seite umbaut, meldet das
Modul das im Log und der Bot macht ohne DAX-Insider weiter.
"""
import csv
import io
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib.parse import urlencode, urljoin

import requests

from insider import zusammenfassung

BASE = "https://portal.mvp.bafin.de/database/DealingsInfo/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Aktienscanner; privates Projekt)", "Accept-Language": "de-DE,de;q=0.9"}
RECHTSFORM = {"ag", "se", "kgaa", "co", "und", "nv", "plc", "sa", "gmbh", "holding", "holdings", "group", "inc",
              "aktiengesellschaft", "vz", "st", "vorzugsaktien", "stammaktien", "europe", "ltd", "the"}


# ---------------------------------------------------------------- Helfer

def norm(name):
    """Firmenname vergleichbar machen: 'Mercedes-Benz Group AG' -> 'mercedes benz'."""
    s = unicodedata.normalize("NFKD", str(name).lower().replace("ß", "ss"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s.replace("&", " "))
    return " ".join(w for w in s.split() if w not in RECHTSFORM)


def zahl(s):
    s = str(s or "").strip().replace("\xa0", "").replace(" ", "")
    s = re.sub(r"[^0-9,.\-]", "", s)
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def datum(s):
    s = str(s or "").strip()[:10]
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def spalte(headers, *keys, ohne=()):
    """Spalte finden, deren Name alle Stichwörter enthält (BaFin ändert Beschriftungen gelegentlich)."""
    for h in headers:
        hl = h.lower()
        if all(k in hl for k in keys) and not any(o in hl for o in ohne):
            return h
    return None


def rolle(position, zeile):
    p = (position or "").lower()
    if "enger beziehung" in " ".join(str(v) for v in zeile.values()).lower():
        return "Nahestehende Person"
    if "vorsitz" in p and "vorstand" in p:
        return "Vorstandschef"
    if "vorstand" in p or "geschäftsführ" in p:
        return "Vorstand"
    if "aufsichtsrat" in p:
        return "Aufsichtsrat"
    return "Führungskraft"


def name_anzeigen(s):
    s = " ".join(str(s).split())
    if "," in s:                                       # "Klein, Christian" -> "Christian Klein"
        nach, vor = [x.strip() for x in s.split(",", 1)]
        s = f"{vor} {nach}"
    return s


# ---------------------------------------------------------------- Abruf

def csv_holen(tage):
    """Alle Meldungen der letzten `tage` Tage als CSV-Text holen."""
    ses = requests.Session()
    ses.headers.update(HEADERS)
    von, bis = (date.today() - timedelta(days=tage)).strftime("%d.%m.%Y"), date.today().strftime("%d.%m.%Y")
    suche = {"emittentName": "", "emittentIsin": "", "meldepflichtigerName": "", "zeitraumVon": von,
             "zeitraumBis": bis, "emittentButton": "Suche Emittent"}
    versuche = []
    try:
        r = ses.post(BASE + "sucheForm.do", data=suche, timeout=40)
        # Export-Link aus der Ergebnisseite lesen (robuster als ihn selbst zusammenzubauen)
        links = re.findall(r'href="([^"]*6578706f7274[^"]*)"', r.text)
        csv_links = [l for l in links if "csv" in l.lower() or re.search(r"-e=1(&|$)", l.replace("&amp;", "&"))]
        versuche += [urljoin(BASE, l.replace("&amp;", "&")) for l in (csv_links or links)]
    except requests.RequestException as e:
        print(f"  BaFin: Suche fehlgeschlagen ({str(e)[:60]})")
    versuche.append(BASE + "sucheForm.do?" + urlencode({**suche, "d-4000784-e": "1", "6578706f7274": "1"}))
    for url in versuche:
        try:
            r = ses.get(url, timeout=60)
        except requests.RequestException:
            continue
        roh = r.content
        for enc in ("utf-8-sig", "cp1252"):
            try:
                text = roh.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if r.status_code == 200 and "<html" not in text[:500].lower() and text.count("\n") >= 1:
            return text
    print("  BaFin: kein CSV-Export erhalten (Seite evtl. geändert).")
    return ""


def meldungen(tage=90):
    """Alle Aktienkäufe der letzten `tage` Tage: Liste von dicts inkl. 'emittent' und 'isin'."""
    text = csv_holen(tage)
    if not text:
        return []
    delim = ";" if text.split("\n", 1)[0].count(";") >= text.split("\n", 1)[0].count(",") else ","
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    if not rows:
        return []
    h = list(rows[0].keys())
    c = {
        "emittent": spalte(h, "emittent", ohne=("isin",)), "isin": spalte(h, "isin"),
        "name": spalte(h, "meldepflichtig"), "position": spalte(h, "position"),
        "art": spalte(h, "art des gesch") or spalte(h, "art", ohne=("instrument", "datum")),
        "instrument": spalte(h, "instrument"), "preis": spalte(h, "preis"), "volumen": spalte(h, "volumen"),
        "datum": spalte(h, "datum des gesch") or spalte(h, "geschäftsdatum") or spalte(h, "datum", ohne=("mitteil", "aktiv")),
        "waehrung": spalte(h, "währung") or spalte(h, "waehrung"),
    }
    fehlt = [k for k in ("emittent", "name", "art", "volumen", "datum") if not c[k]]
    if fehlt:
        print(f"  BaFin: Spalten nicht erkannt ({', '.join(fehlt)}). Gefunden: {h[:12]}")
        return []
    out, gesehen = [], set()
    for z in rows:
        art = (z.get(c["art"]) or "").strip().lower()
        if not art.startswith("kauf"):
            continue
        inst = (z.get(c["instrument"]) or "aktie").lower() if c["instrument"] else "aktie"
        if "aktie" not in inst:
            continue
        if c["waehrung"] and (z.get(c["waehrung"]) or "EUR").strip().upper() not in ("EUR", "€", ""):
            continue
        wert, preis, d = zahl(z.get(c["volumen"])), zahl(z.get(c["preis"])) if c["preis"] else None, datum(z.get(c["datum"]))
        if not wert or wert <= 0 or not d:
            continue
        name = name_anzeigen(z.get(c["name"]) or "Unbekannt")
        key = (z.get(c["emittent"]), name, d, round(wert))
        if key in gesehen:                                          # Korrekturmeldungen nicht doppelt zählen
            continue
        gesehen.add(key)
        out.append({"emittent": z.get(c["emittent"]) or "", "isin": (z.get(c["isin"]) or "") if c["isin"] else "",
                    "datum": d, "wert": wert, "preis": preis or 0.0, "stueck": wert / preis if preis else 0.0,
                    "name": name, "rolle": rolle(z.get(c["position"]) if c["position"] else "", z)})
    return out


def load(scanner_zeilen, cfg):
    """scanner_zeilen: [(ticker, name, marketCap)] deutscher Aktien. Gibt {ticker: zusammenfassung}."""
    tage = int((cfg.get("insider") or {}).get("tage", 90))
    de = [(t, n, m) for t, n, m in scanner_zeilen if t.endswith(".DE")]
    if not de:
        return {}
    print(f"BaFin: lade Directors' Dealings der letzten {tage} Tage ...")
    try:
        alle = meldungen(tage)
    except Exception as e:
        print(f"  BaFin: Fehler ({str(e)[:80]}), überspringe.")
        return {}
    print(f"  {len(alle)} Aktienkäufe insgesamt gemeldet.")
    res = {}
    for t, n, mcap in de:
        nn = norm(n)
        if not nn:
            continue
        treffer = [k for k in alle if (lambda e: e == nn or e.startswith(nn + " ") or nn.startswith(e + " "))(norm(k["emittent"]))]
        if treffer:
            for k in treffer:
                k["ticker"] = t
            res[t] = zusammenfassung(t, treffer, mcap, waehrung="EUR", quelle="BaFin")
    print(f"BaFin: {len(res)} deutsche Aktien mit Insiderkäufen.")
    return res
