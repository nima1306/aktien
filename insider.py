"""Insiderkäufe aus den offiziellen SEC-Meldungen (Form 4) für US-Aktien.

Form 4 muss jeder Vorstand, Direktor und Großaktionär (>10 %) innerhalb von 2 Werktagen
einreichen, wenn er Aktien der eigenen Firma kauft oder verkauft. Gezählt werden nur echte
Käufe am Markt (Code "P") - keine Aktienoptionen, Gehaltsaktien oder Steuer-Verkäufe.

Die SEC verlangt in jeder Anfrage einen Namen + E-Mail (Einstellung 'insider.sec_kontakt')
und erlaubt höchstens 10 Anfragen pro Sekunde.
"""
import json
import math
import os
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import requests

SPEICHER = "speicher"                      # bleibt zwischen den GitHub-Läufen erhalten (Actions-Cache)
CACHE_DATEI = os.path.join(SPEICHER, "insider_form4.json")

_lock = threading.Lock()
_last = [0.0]
_session = requests.Session()


def _get(url, kontakt, tries=3):
    """Höflicher Abruf: max. ~8 Anfragen pro Sekunde, mit Wiederholung bei Fehlern."""
    for attempt in range(tries):
        with _lock:
            wait = 0.125 - (time.time() - _last[0])
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        try:
            r = _session.get(url, headers={"User-Agent": kontakt, "Accept-Encoding": "gzip, deflate"}, timeout=20)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return None


def ticker_cik_map(kontakt):
    r = _get("https://www.sec.gov/files/company_tickers.json", kontakt)
    if not r:
        return {}
    return {v["ticker"].upper().replace(".", "-"): int(v["cik_str"]) for v in r.json().values()}


def _txt(node, path):
    el = node.find(path)
    return (el.text or "").strip() if el is not None and el.text else ""


def _flag(node, path):
    return _txt(node, path).lower() in ("1", "true")


def anzeigename(raw):
    """'COOK TIMOTHY D' -> 'Timothy Cook'. Firmen/Fonds bleiben, wie sie sind."""
    raw = " ".join(raw.replace(",", " ").split())
    firma = {"INC", "LLC", "LP", "L.P.", "TRUST", "FUND", "CORP", "HOLDINGS", "CAPITAL", "PARTNERS", "LTD", "GROUP"}
    if any(w.upper().strip(".") in firma for w in raw.split()):
        return raw.title()
    t = raw.split()
    if len(t) < 2:
        return raw.title()
    rest = [w for w in t[1:] if len(w.strip(".")) > 1]
    return " ".join(rest + [t[0]]).title()


def rolle(rel):
    """Rolle auf Deutsch für Video und Sprechtext."""
    titel = rel.get("titel", "")
    tu = titel.upper()
    if "CHIEF EXECUTIVE" in tu or tu.startswith("CEO") or " CEO" in f" {tu}":
        return "CEO"
    if "CHIEF FINANCIAL" in tu or "CFO" in tu:
        return "Finanzchef"
    if "CHAIR" in tu:
        return "Chairman"
    if "PRESIDENT" in tu:
        return "President"
    if rel.get("officer"):
        return "Manager"
    if rel.get("director"):
        return "Board-Mitglied"
    if rel.get("zehn_prozent"):
        return "Großaktionär"
    return "Insider"


def parse_form4(xml_text):
    """Alle echten Käufe (Code P) aus einer Form-4-XML."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    owners = []
    for ro in root.findall("reportingOwner"):
        rel = {
            "director": _flag(ro, "reportingOwnerRelationship/isDirector"),
            "officer": _flag(ro, "reportingOwnerRelationship/isOfficer"),
            "zehn_prozent": _flag(ro, "reportingOwnerRelationship/isTenPercentOwner"),
            "titel": _txt(ro, "reportingOwnerRelationship/officerTitle"),
        }
        owners.append({"name": anzeigename(_txt(ro, "reportingOwnerId/rptOwnerName")), "rolle": rolle(rel)})
    if not owners:
        return []
    out = []
    for tx in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        if _txt(tx, "transactionCoding/transactionCode") != "P":
            continue
        if _txt(tx, "transactionAmounts/transactionAcquiredDisposedCode/value") not in ("A", ""):
            continue
        try:
            stk = float(_txt(tx, "transactionAmounts/transactionShares/value") or 0)
            preis = float(_txt(tx, "transactionAmounts/transactionPricePerShare/value") or 0)
        except ValueError:
            continue
        if stk <= 0 or preis <= 0:
            continue
        out.append({"datum": _txt(tx, "transactionDate/value")[:10], "stueck": stk, "preis": preis,
                    "wert": stk * preis, "name": owners[0]["name"], "rolle": owners[0]["rolle"]})
    return out


def kaeufe_einer_aktie(sym, cik, kontakt, tage, cache):
    """Liste aller Insiderkäufe der letzten `tage` Tage."""
    r = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", kontakt)
    if not r:
        return []
    rec = r.json().get("filings", {}).get("recent", {})
    grenze = (date.today() - timedelta(days=tage)).isoformat()
    out = []
    for form, acc, fdat, doc in zip(rec.get("form", []), rec.get("accessionNumber", []),
                                    rec.get("filingDate", []), rec.get("primaryDocument", [])):
        if form != "4" or fdat < grenze:
            continue
        if acc not in cache:
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc.split('/')[-1]}"
            x = _get(url, kontakt)
            if x is None:
                continue
            cache[acc] = parse_form4(x.content)
        out += [dict(k, ticker=sym, meldung=fdat) for k in cache[acc] if k["datum"] >= grenze]
    return out


def insider_score(kaeufe, market_cap=None):
    """0-100: Wie stark ist das Kaufsignal? Viel Geld, mehrere Käufer, Chefetage, frisch."""
    if not kaeufe:
        return 0.0
    summe = sum(k["wert"] for k in kaeufe)
    kaeufer = {k["name"] for k in kaeufe}
    s = max(0.0, min(45.0, 15 * math.log10(max(summe, 1) / 50_000) + 20))      # 50k $ -> 20, 5 Mio $ -> 45
    s += min(30.0, (len(kaeufer) - 1) * 12)                                      # "Cluster"-Kauf
    if any(k["rolle"] in ("CEO", "Finanzchef", "Chairman", "President", "Vorstandschef", "Vorstand") for k in kaeufe):
        s += 15
    letzter = max(k["datum"] for k in kaeufe)
    if (date.today() - datetime.strptime(letzter, "%Y-%m-%d").date()).days <= 14:
        s += 10
    if market_cap and market_cap > 0 and summe / market_cap > 0.0005:            # >0,05 % des Börsenwerts
        s += 5
    return round(min(100.0, s), 1)


def zusammenfassung(sym, kaeufe, market_cap=None, waehrung="USD", quelle="SEC Form 4"):
    kaeufe = sorted(kaeufe, key=lambda k: k["datum"])
    return {
        "ticker": sym, "waehrung": waehrung, "quelle": quelle,
        "kaeufe": kaeufe,
        "summe": sum(k["wert"] for k in kaeufe),
        "anzahl_kaeufer": len({k["name"] for k in kaeufe}),
        "groesster": max(kaeufe, key=lambda k: k["wert"]) if kaeufe else None,
        "insider_score": insider_score(kaeufe, market_cap),
    }


def load(symbols, cfg, market_caps=None):
    """Insiderkäufe für alle US-Aktien in `symbols`. Gibt {ticker: zusammenfassung} zurück."""
    icfg = cfg.get("insider", {})
    kontakt = os.environ.get("SEC_KONTAKT") or icfg.get("sec_kontakt", "")
    if "@" not in kontakt or "deine@mail" in kontakt:
        print("Insider: Bitte in aktien_config.yaml unter insider.sec_kontakt Name + E-Mail eintragen "
              "(Pflicht bei der SEC). Insider-Daten werden übersprungen.")
        return {}
    tage = int(icfg.get("tage", 90))
    us = [s for s in symbols if "." not in s][: int(icfg.get("max_aktien", 600))]
    os.makedirs(SPEICHER, exist_ok=True)
    cache = {}
    if os.path.exists(CACHE_DATEI):
        with open(CACHE_DATEI, encoding="utf-8") as f:
            cache = json.load(f)
    ciks = ticker_cik_map(kontakt)
    if not ciks:
        print("Insider: SEC nicht erreichbar, überspringe.")
        return {}
    todo = [(s, ciks[s.upper()]) for s in us if s.upper() in ciks]
    print(f"Insider: prüfe Form-4-Meldungen der letzten {tage} Tage für {len(todo)} US-Aktien ...")
    res = {}

    def work(item):
        s, cik = item
        try:
            return s, kaeufe_einer_aktie(s, cik, kontakt, tage, cache)
        except Exception as e:                       # eine kaputte Meldung soll nicht alles stoppen
            print(f"  {s}: {str(e)[:60]}")
            return s, []

    with ThreadPoolExecutor(max_workers=4) as pool:
        for n, (s, k) in enumerate(pool.map(work, todo), 1):
            if k:
                res[s] = zusammenfassung(s, k, (market_caps or {}).get(s))
            if n % 50 == 0:
                print(f"  {n}/{len(todo)} ...", flush=True)
    # Cache klein halten: nur Meldungen der letzten ~200 Tage sind interessant, aber Schlüssel haben kein Datum,
    # deshalb ab 60.000 Einträgen einfach neu anfangen.
    if len(cache) > 60_000:
        cache = {}
    with open(CACHE_DATEI, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    print(f"Insider: {len(res)} Aktien mit Insiderkäufen gefunden.")
    return res
