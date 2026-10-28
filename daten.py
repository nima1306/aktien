"""Daten von Yahoo Finance holen: Kennzahlen, Analystenprognosen, Kursverlauf, Nachrichten.
Ergebnisse werden pro Tag im Ordner 'daten' gespeichert, damit ein zweiter Lauf schnell geht."""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

INFO_FIELDS = [
    "longName", "shortName", "sector", "industry", "country", "currency", "marketCap", "currentPrice",
    "regularMarketPrice", "trailingPE", "forwardPE", "pegRatio", "trailingPegRatio", "priceToBook",
    "enterpriseToEbitda", "returnOnEquity", "returnOnAssets", "profitMargins", "operatingMargins",
    "grossMargins", "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth", "trailingEps",
    "forwardEps", "debtToEquity", "currentRatio", "freeCashflow", "totalCash", "totalDebt",
    "dividendYield", "trailingAnnualDividendRate", "trailingAnnualDividendYield", "payoutRatio",
    "fiveYearAvgDividendYield", "targetMeanPrice", "targetLowPrice", "targetHighPrice",
    "recommendationMean", "recommendationKey", "numberOfAnalystOpinions", "beta", "longBusinessSummary",
]

# Finanz-Wörterbuch für die Stimmung von Schlagzeilen (Englisch + Deutsch).
# Gezählt wird, ob ein Wort mit einem dieser Wortanfänge beginnt.
POSITIV = """beat beats tops topped exceed surpass upgrade upgraded outperform overweight raise raises raised
hike boost record surge soar jump rally gain gains climbs rises rose strong stronger robust growth grows
expand expansion profit profitable buyback repurchase dividend-increase approval approved wins win award
partnership breakthrough bullish optimistic beat-and-raise accelerat momentum upside
übertrifft übertroffen hebt angehoben erhöht rekord steigt gestiegen stark kaufempfehlung kursziel-anhebung
gewinnsprung wachstum wächst zulassung durchbruch aktienrückkauf""".split()
NEGATIV = """miss misses missed downgrade downgraded underperform underweight cut cuts cutting lower lowered
slash falls fell fall drop drops dropped plunge plunges slump slumps tumble sinks sink weak weaker weakness
loss losses lawsuit sued sue probe investigation recall fraud scandal warn warning warns layoff layoffs
job-cuts bearish decline declines slowing slowdown fine fined bankruptcy default halt halted delay delayed
concern concerns risk downside pessimistic selloff sell-off crash
fällt gefallen sinkt gesunken verlust verluste gewinnwarnung senkt gesenkt klage schwach stellenabbau
abstufung herabgestuft ermittlung rückruf betrug insolvenz einbruch bricht""".split()


def sentiment(text):
    """-1 (sehr negativ) bis +1 (sehr positiv)."""
    if not text:
        return 0.0
    words = [w.strip(".,:;!?\"'()[]").lower() for w in text.replace("-", " ").split()]
    pos = sum(any(w.startswith(p) for p in POSITIV) for w in words if len(w) > 2)
    neg = sum(any(w.startswith(n) for n in NEGATIV) for w in words if len(w) > 2)
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / (pos + neg) * min(1.0, (pos + neg) / 2)


def parse_news(items, limit=10):
    """Unterstützt das alte und das neue Nachrichtenformat von yfinance."""
    out = []
    for it in (items or [])[:limit * 2]:
        c = it.get("content", it)
        title = c.get("title")
        if not title:
            continue
        url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url") \
            or c.get("link") or it.get("link")
        prov = (c.get("provider") or {}).get("displayName") or c.get("publisher") or ""
        ts = c.get("pubDate") or c.get("displayTime")
        if ts:
            try:
                ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
            except ValueError:
                ts = None
        ts = ts or c.get("providerPublishTime") or it.get("providerPublishTime")
        out.append({"titel": title, "url": url, "quelle": prov, "zeit": ts,
                    "stimmung": round(sentiment(title + ". " + (c.get("summary") or "")), 3)})
        if len(out) >= limit:
            break
    return out


def fetch_news(sym, t):
    """Nachrichten holen. yfinance hat das mehrfach geändert, daher mehrere Wege nacheinander."""
    getters = [
        lambda: t.get_news(count=15, tab="news"),
        lambda: t.get_news(count=15),
        lambda: t.news,
        lambda: yf.Search(sym, news_count=10).news,
    ]
    for get in getters:
        try:
            items = parse_news(get() or [])
            if items:
                return items
        except Exception:
            continue
    return []


def fetch_one(sym, retries=3):
    for attempt in range(retries + 1):
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            if not info.get("marketCap") and not info.get("currentPrice") and not info.get("regularMarketPrice"):
                raise ValueError("keine Daten")
            d = {k: info.get(k) for k in INFO_FIELDS}
            d["news"] = fetch_news(sym, t)
            return sym, d, None
        except Exception as e:
            if attempt == retries:
                return sym, None, str(e)[:80]
            wait = 15 if "too many" in str(e).lower() or "rate" in str(e).lower() else 2
            time.sleep(wait * (attempt + 1))


def price_stats(close):
    """Kennzahlen aus dem Kursverlauf eines Jahres."""
    c = close.dropna()
    if len(c) < 120:
        return {}
    r = c.pct_change().dropna()
    one_month_ago = c.iloc[-22] if len(c) > 22 else c.iloc[0]
    return {
        "rendite_12m": float(c.iloc[-1] / c.iloc[0] - 1),
        "rendite_12m_ohne_1m": float(one_month_ago / c.iloc[0] - 1),
        "rendite_6m": float(c.iloc[-1] / c.iloc[-min(126, len(c))] - 1),
        "ueber_ma200": float(c.iloc[-1] / c.iloc[-200:].mean() - 1),
        "volatilitaet": float(r.std() * np.sqrt(252)),
        "max_drawdown": float((c / c.cummax() - 1).min()),
        "verlauf": [round(float(x), 2) for x in c.iloc[::5]],   # für Mini-Chart im Bericht
    }


def fetch_prices(symbols):
    out = {}
    for i in range(0, len(symbols), 100):
        chunk = symbols[i:i + 100]
        df = yf.download(chunk, period="1y", auto_adjust=True, progress=False, group_by="ticker", threads=True)
        for s in chunk:
            try:
                close = df[s]["Close"] if isinstance(df.columns, pd.MultiIndex) else df["Close"]
                out[s] = price_stats(close)
            except Exception:
                out[s] = {}
    return out


def load(symbols, threads=6, cache_dir="daten"):
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"rohdaten_v2_{date.today():%Y-%m-%d}.json")
    cache = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
    todo = [s for s in symbols if s not in cache]
    failed = []
    if todo:
        print(f"Lade Kennzahlen und Nachrichten für {len(todo)} Aktien (gespeichert: {len(symbols) - len(todo)}) ...")
        with ThreadPoolExecutor(max_workers=threads) as pool:
            futs = [pool.submit(fetch_one, s) for s in todo]
            for n, fu in enumerate(as_completed(futs), 1):
                sym, d, err = fu.result()
                if d:
                    cache[sym] = d
                else:
                    failed.append(f"{sym} ({err})")
                if n % 20 == 0 or n == len(todo):
                    print(f"  {n}/{len(todo)} ...", end="\r", flush=True)
        print()
        ok = [s for s in todo if s in cache]
        if ok:
            print("Lade Kursverläufe ...")
            for s, ps in fetch_prices(ok).items():
                cache[s].update(ps)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        with_news = sum(1 for s in ok if cache[s].get("news"))
        print(f"Nachrichten gefunden für {with_news} von {len(ok)} Aktien.")
    data = {s: cache[s] for s in symbols if s in cache}
    return data, failed


def latest_cache(cache_dir="daten"):
    """Neueste gespeicherte Rohdaten (für die Einzelanalyse)."""
    if not os.path.isdir(cache_dir):
        return {}
    files = sorted(f for f in os.listdir(cache_dir) if f.startswith("rohdaten_"))
    if not files:
        return {}
    with open(os.path.join(cache_dir, files[-1]), encoding="utf-8") as f:
        return json.load(f)


def age_days(ts):
    """Alter einer Meldung in Tagen. Ohne Datum gilt sie als aktuell."""
    return (datetime.now(timezone.utc).timestamp() - ts) / 86400 if ts else 0
