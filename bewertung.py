"""Bewertung jeder Aktie in 8 Kategorien (0-100) und Warnsignale.

Jede Kennzahl wird mit allen anderen Aktien verglichen (Perzentil-Rang): 100 = beste,
0 = schlechteste. Bewertungs-Kennzahlen (KGV usw.) werden innerhalb der eigenen Branche
verglichen, weil z. B. Software-Firmen immer höher bewertet sind als Banken.
Fehlt eine Kennzahl, zählt sie nicht. Fehlt eine ganze Kategorie, gilt sie als neutral (50).
"""
import numpy as np
import pandas as pd

from daten import age_days

KATEGORIEN = {
    "bewertung": "Bewertung", "qualitaet": "Qualität", "wachstum": "Wachstum", "analysten": "Analysten",
    "momentum": "Momentum", "stabilitaet": "Stabilität", "nachrichten": "Nachrichten", "dividende": "Dividende",
}

# Kennzahl: (Kategorie, höher ist besser?, branchenrelativ?, Anzeigename)
METRIKEN = {
    "forwardPE":          ("bewertung", False, True, "KGV (erwartet)"),
    "trailingPE":         ("bewertung", False, True, "KGV (aktuell)"),
    "peg":                ("bewertung", False, True, "PEG-Ratio"),
    "fcf_rendite":        ("bewertung", True, True, "Free-Cashflow-Rendite"),
    "enterpriseToEbitda": ("bewertung", False, True, "EV/EBITDA"),
    "returnOnEquity":     ("qualitaet", True, False, "Eigenkapitalrendite"),
    "operatingMargins":   ("qualitaet", True, False, "Operative Marge"),
    "profitMargins":      ("qualitaet", True, False, "Nettomarge"),
    "debtToEquity":       ("qualitaet", False, True, "Verschuldung (Debt/Equity)"),
    "revenueGrowth":      ("wachstum", True, False, "Umsatzwachstum"),
    "earningsGrowth":     ("wachstum", True, False, "Gewinnwachstum"),
    "eps_wachstum_erw":   ("wachstum", True, False, "Erwartetes Gewinnwachstum"),
    "kursziel_potenzial": ("analysten", True, False, "Potenzial zum Kursziel"),
    "empfehlung":         ("analysten", False, False, "Analysten-Empfehlung (1=Kaufen, 5=Verkaufen)"),
    "rendite_12m_ohne_1m": ("momentum", True, False, "Rendite 12 Monate (ohne letzten Monat)"),
    "ueber_ma200":        ("momentum", True, False, "Abstand zum 200-Tage-Durchschnitt"),
    "volatilitaet":       ("stabilitaet", False, False, "Schwankung (Volatilität)"),
    "max_drawdown":       ("stabilitaet", True, False, "Größter Rückgang 12 Monate"),
    "beta":               ("stabilitaet", False, False, "Beta (Marktabhängigkeit)"),
    "news_stimmung":      ("nachrichten", True, False, "Stimmung der Nachrichten"),
    "div_rendite":        ("dividende", True, False, "Dividendenrendite"),
}


def _num(x):
    try:
        x = float(x)
        return x if np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan


def frame(raw):
    """Rohdaten -> Tabelle mit allen Kennzahlen."""
    rows = []
    for sym, d in raw.items():
        r = {"ticker": sym, "name": d.get("longName") or d.get("shortName") or sym,
             "branche": d.get("sector") or "Unbekannt", "land": d.get("country") or "",
             "waehrung": d.get("currency") or ""}
        for k in ["marketCap", "trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda", "returnOnEquity",
                  "profitMargins", "operatingMargins", "revenueGrowth", "earningsGrowth", "debtToEquity",
                  "currentRatio", "freeCashflow", "payoutRatio", "targetMeanPrice", "recommendationMean",
                  "numberOfAnalystOpinions", "beta", "trailingEps", "forwardEps", "rendite_12m",
                  "rendite_12m_ohne_1m", "rendite_6m", "ueber_ma200", "volatilitaet", "max_drawdown"]:
            r[k] = _num(d.get(k))
        price = _num(d.get("currentPrice")) if d.get("currentPrice") else _num(d.get("regularMarketPrice"))
        r["kurs"] = price
        # negative KGV sind nicht "billig", sondern Verluste -> als fehlend behandeln (Warnsignal kommt separat)
        for k in ["trailingPE", "forwardPE", "enterpriseToEbitda"]:
            if r[k] <= 0:
                r[k] = np.nan
        r["peg"] = _num(d.get("pegRatio") or d.get("trailingPegRatio"))
        if r["peg"] <= 0:
            r["peg"] = np.nan
        r["fcf_rendite"] = r["freeCashflow"] / r["marketCap"] if r["marketCap"] else np.nan
        r["eps_wachstum_erw"] = (r["forwardEps"] / r["trailingEps"] - 1
                                 if r["trailingEps"] > 0 and r["forwardEps"] > 0 else np.nan)
        r["kursziel_potenzial"] = r["targetMeanPrice"] / price - 1 if price and r["targetMeanPrice"] > 0 else np.nan
        r["empfehlung"] = r["recommendationMean"]
        # Dividendenrendite robust berechnen (Yahoo liefert sie mal als Bruch, mal in Prozent)
        rate = _num(d.get("trailingAnnualDividendRate"))
        if rate > 0 and price > 0:
            r["div_rendite"] = rate / price
        else:
            dy = _num(d.get("dividendYield"))
            r["div_rendite"] = (dy / 100 if dy > 0.2 else dy) if dy == dy else 0.0
        if not r["div_rendite"] == r["div_rendite"]:
            r["div_rendite"] = 0.0
        news = [n for n in (d.get("news") or []) if age_days(n.get("zeit")) <= 45]
        r["news_anzahl"] = len(news)
        r["news_stimmung"] = float(np.mean([n["stimmung"] for n in news])) if news else np.nan
        r["_news"] = d.get("news") or []
        r["_verlauf"] = d.get("verlauf") or []
        r["_beschreibung"] = d.get("longBusinessSummary") or ""
        rows.append(r)
    df = pd.DataFrame(rows)
    # Mehrere Aktiengattungen derselben Firma (z. B. GOOG/GOOGL) nur einmal zählen
    return (df.sort_values("marketCap", ascending=False, na_position="last")
              .drop_duplicates("name").reset_index(drop=True))


def score(df, cfg):
    df = df.copy()
    min_mcap = cfg["filter"]["min_marktkapitalisierung_mrd"] * 1e9
    # Marktkapitalisierung in EUR/USD grob vergleichbar; kleine Werte herausfiltern
    df = df[(df["marketCap"].isna()) | (df["marketCap"] >= min_mcap)].reset_index(drop=True)

    ranks = {}
    for m, (cat, higher, sector_rel, _) in METRIKEN.items():
        s = df[m]
        if sector_rel:
            sizes = df.groupby("branche")[m].transform("count")
            r_sec = df.groupby("branche")[m].rank(pct=True, ascending=higher)
            r_all = s.rank(pct=True, ascending=higher)
            r = r_sec.where(sizes >= 5, r_all)
        else:
            r = s.rank(pct=True, ascending=higher)
        ranks[m] = r * 100
    rk = pd.DataFrame(ranks)
    for m in METRIKEN:
        df["r_" + m] = rk[m]

    for cat in KATEGORIEN:
        cols = [m for m, v in METRIKEN.items() if v[0] == cat]
        df["k_" + cat] = rk[cols].mean(axis=1, skipna=True).fillna(50)

    # Analysten: wenige Analysten = weniger aussagekräftig -> Richtung 50 ziehen
    conf = (df["numberOfAnalystOpinions"].fillna(0) / 10).clip(0, 1)
    df["k_analysten"] = 50 + (df["k_analysten"] - 50) * conf
    # Nachrichten: wenige Meldungen -> Richtung 50 ziehen
    df["k_nachrichten"] = 50 + (df["k_nachrichten"] - 50) * (df["news_anzahl"] / 5).clip(0, 1)
    # Dividende: Ausschüttung höher als Gewinn ist nicht nachhaltig
    df.loc[df["payoutRatio"] > 1, "k_dividende"] *= 0.5

    w = cfg["gewichte"]
    wsum = sum(w.values()) or 1
    df["score_roh"] = sum(df["k_" + c] * w.get(c, 0) for c in KATEGORIEN) / wsum

    df["warnungen"] = df.apply(warnings, axis=1)
    df["score"] = (df["score_roh"] - df["warnungen"].apply(len) * cfg["filter"]["abzug_pro_warnung"]).clip(0, 100)
    df["daten_vollstaendig"] = rk.notna().mean(axis=1)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df["rang"] = df.index + 1
    return df


def warnings(r):
    w = []
    if r["trailingEps"] < 0 or r["profitMargins"] < 0:
        w.append("Macht aktuell Verlust")
    if r["debtToEquity"] > 200 and r["branche"] not in ("Financial Services", "Real Estate", "Utilities"):
        w.append("Hohe Verschuldung")
    if r["freeCashflow"] < 0:
        w.append("Negativer Free Cashflow")
    if r["payoutRatio"] > 1:
        w.append("Dividende höher als Gewinn")
    if r["max_drawdown"] < -0.4:
        w.append(f"Kurs zeitweise {r['max_drawdown']:.0%} eingebrochen (12 Monate)")
    if r["news_anzahl"] >= 3 and r["news_stimmung"] < -0.25:
        w.append("Überwiegend negative Nachrichten")
    if r["empfehlung"] >= 3.3:
        w.append("Analysten überwiegend skeptisch")
    if not r["numberOfAnalystOpinions"] >= 3:
        w.append("Kaum Analysten-Abdeckung")
    if r["revenueGrowth"] < -0.1:
        w.append(f"Umsatz schrumpft ({r['revenueGrowth']:.0%})")
    return w


def strengths_weaknesses(r):
    cats = sorted(KATEGORIEN, key=lambda c: r["k_" + c], reverse=True)
    good = [KATEGORIEN[c] for c in cats[:3] if r["k_" + c] >= 60]
    bad = [KATEGORIEN[c] for c in cats[-2:] if r["k_" + c] <= 40]
    return good, bad
