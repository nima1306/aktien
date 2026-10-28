"""Sentiment-Radar: Wie stark und wie positiv wird über eine Aktie geredet?

Quellen (alle kostenlos, ohne Schlüssel):
- Reddit-Erwähnungen über ApeWisdom (zählt Ticker in r/wallstreetbets, r/stocks, r/investing usw.)
  -> Erwähnungen der letzten 24 Std. und Veränderung zum Vortag. Nur US-Ticker.
- StockTwits: die letzten 30 Beiträge zu einem Ticker, von den Autoren als "Bullish"/"Bearish" markiert.
- Nachrichten: Stimmung der Schlagzeilen, die der Scanner schon ausgewertet hat.

Daraus entsteht ein Hype-Index 0-100. Fällt eine Quelle aus, wird mit den übrigen gerechnet.
"""
import math
from datetime import datetime

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Aktienscanner; privates Projekt)", "Accept": "application/json"}


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def reddit_alle(seiten=5):
    """{ticker: {mentions, mentions_24h, rank, rank_24h, upvotes}} für die meistgenannten US-Aktien."""
    out = {}
    for p in range(1, seiten + 1):
        try:
            r = requests.get(f"https://apewisdom.io/api/v1.0/filter/all-stocks/page/{p}", headers=HEADERS, timeout=20)
            j = r.json() if r.status_code == 200 else {}
        except (requests.RequestException, ValueError):
            break
        for e in j.get("results") or []:
            t = str(e.get("ticker", "")).upper().replace(".", "-")
            if t and t not in out:
                out[t] = {"mentions": _int(e.get("mentions")), "mentions_24h": _int(e.get("mentions_24h_ago")),
                          "rank": _int(e.get("rank")), "rank_24h": _int(e.get("rank_24h_ago")),
                          "upvotes": _int(e.get("upvotes"))}
        if p >= _int(j.get("pages")):
            break
    print(f"Stimmung: Reddit-Daten für {len(out)} Ticker geladen." if out else "Stimmung: Reddit (ApeWisdom) nicht erreichbar.")
    return out


def stocktwits(sym):
    """Anteil bullisher Beiträge unter den letzten 30. None, wenn nicht erreichbar."""
    if "." in sym:                                    # deutsche Ticker gibt es dort kaum
        return None
    try:
        r = requests.get(f"https://api.stocktwits.com/api/2/streams/symbol/{sym}.json", headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        msgs = r.json().get("messages") or []
    except (requests.RequestException, ValueError):
        return None
    if not msgs:
        return None
    bull = sum(1 for m in msgs if ((m.get("entities") or {}).get("sentiment") or {}).get("basic") == "Bullish")
    bear = sum(1 for m in msgs if ((m.get("entities") or {}).get("sentiment") or {}).get("basic") == "Bearish")
    zeiten = []
    for m in msgs:
        try:
            zeiten.append(datetime.fromisoformat(str(m.get("created_at")).replace("Z", "+00:00")))
        except ValueError:
            pass
    stunden = (max(zeiten) - min(zeiten)).total_seconds() / 3600 if len(zeiten) > 1 else None
    return {"bull": bull, "bear": bear, "n": len(msgs),
            "pro_stunde": round(len(msgs) / stunden, 1) if stunden and stunden > 0 else None}


def radar(ticker, news_stimmung=None, news_anzahl=0, reddit=None, mit_stocktwits=True):
    """Alle Quellen für eine Aktie + Hype-Index."""
    teile, gew = [], []
    rd = (reddit or {}).get(ticker.upper()) if reddit is not None and "." not in ticker else None
    if reddit is not None and "." not in ticker and rd is None:
        rd = {"mentions": 0, "mentions_24h": 0, "rank": 0, "rank_24h": 0, "upvotes": 0}   # nicht in den Top-Listen
    if rd is not None:
        lvl = min(1.0, math.log10(1 + rd["mentions"]) / math.log10(500))
        chg = (rd["mentions"] - rd["mentions_24h"]) / max(rd["mentions_24h"], 5)
        teile.append(0.6 * lvl + 0.4 * max(0.0, min(1.0, chg / 2)))
        gew.append(0.4)
    st = stocktwits(ticker) if mit_stocktwits else None
    if st and st["bull"] + st["bear"] >= 5:
        teile.append(st["bull"] / (st["bull"] + st["bear"]))
        gew.append(0.35)
    nw = None
    if news_stimmung is not None and news_stimmung == news_stimmung and (news_anzahl or 0) >= 2:
        nw = {"stimmung": float(news_stimmung), "anzahl": int(news_anzahl)}
        teile.append(max(0.0, min(1.0, (nw["stimmung"] + 0.5))))          # -0,5..+0,5 -> 0..1
        gew.append(0.25)
    idx = round(100 * sum(t * g for t, g in zip(teile, gew)) / sum(gew)) if gew else None
    label = None if idx is None else "heiß" if idx >= 70 else "positiv" if idx >= 50 else "neutral" if idx >= 35 else "kühl"
    return {"reddit": rd, "stocktwits": st if st and st["bull"] + st["bear"] >= 5 else None, "news": nw,
            "index": idx, "label": label, "quellen": len(gew)}
