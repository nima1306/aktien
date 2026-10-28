"""Welche Aktien werden durchsucht? Aktuelle Indexlisten von Wikipedia, mit Ersatzliste."""
from io import StringIO

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Aktienscanner)"}

# Ersatzlisten, falls Wikipedia nicht erreichbar ist (Stand 2025/26, kann veraltet sein)
DAX_FALLBACK = ["ADS", "AIR", "ALV", "BAS", "BAYN", "BEI", "BMW", "BNR", "CBK", "CON", "DTG", "DTE", "DBK",
                "DB1", "DHL", "EOAN", "FRE", "FME", "G1A", "HNR1", "HEI", "HEN3", "IFX", "MBG", "MRK", "MTX",
                "MUV2", "P911", "PAH3", "QIA", "RHM", "RWE", "SAP", "SRT3", "SIE", "ENR", "SHL", "SY1", "VNA",
                "VOW3", "ZAL"]
SP500_FALLBACK = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "LLY", "AVGO", "JPM", "TSLA", "V",
                  "UNH", "XOM", "MA", "JNJ", "PG", "HD", "COST", "ABBV", "MRK", "WMT", "NFLX", "KO", "PEP", "BAC",
                  "CRM", "ORCL", "CVX", "AMD", "ADBE", "TMO", "MCD", "CSCO", "ACN", "ABT", "LIN", "DIS", "WFC",
                  "INTU", "TXN", "QCOM", "IBM", "CAT", "GE", "AMGN", "VZ", "PFE", "NOW", "ISRG", "SPGI", "UBER",
                  "GS", "HON", "UNP", "LOW", "BKNG", "RTX", "NEE", "PLD", "ELV", "SBUX", "DE", "BLK", "MDT", "ADP"]


def _tables(url):
    html = requests.get(url, headers=HEADERS, timeout=20).text
    return pd.read_html(StringIO(html))


def dax():
    try:
        for t in _tables("https://en.wikipedia.org/wiki/DAX"):
            col = next((c for c in t.columns if str(c).strip().lower() in ("ticker", "symbol")), None)
            if col is not None and 30 <= len(t) <= 45:
                syms = [str(s).strip().split(".")[0].split(":")[-1].strip() for s in t[col].dropna()]
                return [s + ".DE" for s in syms if s], "Wikipedia (aktuell)"
    except Exception:
        pass
    return [s + ".DE" for s in DAX_FALLBACK], "Ersatzliste (evtl. veraltet)"


def sp500():
    try:
        t = _tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        syms = [str(s).strip().replace(".", "-") for s in t["Symbol"].dropna()]
        if len(syms) > 400:
            return syms, "Wikipedia (aktuell)"
    except Exception:
        pass
    return SP500_FALLBACK, "Ersatzliste (nur große Werte)"


def build(cfg):
    u, out, info = cfg["universum"], [], []
    if u.get("dax"):
        s, src = dax(); out += s; info.append(f"DAX: {len(s)} Aktien, {src}")
    if u.get("sp500"):
        s, src = sp500(); out += s; info.append(f"S&P 500: {len(s)} Aktien, {src}")
    own = [str(x).strip().upper() for x in (u.get("eigene_liste") or [])]
    if own:
        out += own; info.append(f"Eigene Liste: {len(own)} Aktien")
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s); uniq.append(s)
    return uniq, info
