"""Aktien-Scanner für langfristige Anlage.

  python aktien.py                 alle Aktien aus der Konfiguration bewerten -> aktien_bericht.html
  python aktien.py --aktie SAP.DE  eine einzelne Aktie analysieren (im Vergleich zum letzten Scan)
"""
import argparse
import os
import sys

import yaml

import bericht
import daten
import universum
from bewertung import KATEGORIEN, frame, score, strengths_weaknesses

DEFAULTS = {
    "universum": {"dax": True, "sp500": True, "eigene_liste": []},
    "gewichte": {k: 1 for k in KATEGORIEN},
    "filter": {"min_marktkapitalisierung_mrd": 5, "abzug_pro_warnung": 3, "threads": 6},
    "bericht": {"top": 30, "nachrichten_pro_aktie": 5},
}


def load_config(path="aktien_config.yaml"):
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for k, v in (yaml.safe_load(f) or {}).items():
                cfg[k] = {**cfg.get(k, {}), **v} if isinstance(v, dict) else v
    return cfg


def scan(cfg):
    syms, info = universum.build(cfg)
    print("\n".join(info))
    threads = int(os.environ.get("AKTIEN_THREADS", cfg["filter"]["threads"]))
    raw, failed = daten.load(syms, threads=threads)
    if not raw:
        sys.exit("Es konnten keine Daten geladen werden. Internetverbindung prüfen.")
    df = score(frame(raw), cfg)
    html_path = bericht.write_html(df, cfg, info, failed)
    xls = bericht.write_excel(df)

    print(f"\n{len(df)} Aktien bewertet ({len(failed)} nicht abrufbar). Top 15:\n")
    print(f"{'#':>3}  {'Aktie':<32}{'Branche':<24}{'Score':>6}  Warnsignale")
    for _, r in df.head(15).iterrows():
        print(f"{r['rang']:>3}  {r['name'][:30]:<32}{r['branche'][:22]:<24}{r['score']:>6.0f}  "
              f"{len(r['warnungen']) or '-'}")
    print(f"\nBericht: {html_path}  |  Tabelle: {xls}")


def single(cfg, sym):
    sym = sym.strip().upper()
    raw = daten.latest_cache()
    if len(raw) < 30:
        print("Hinweis: Noch kein vollständiger Scan vorhanden. Für einen fairen Vergleich zuerst einmal "
              "den kompletten Scan ausführen. Die Aktie wird jetzt nur mit den gespeicherten Werten verglichen.\n")
    _, d, err = daten.fetch_one(sym)
    if not d:
        sys.exit(f"Keine Daten für {sym} gefunden ({err}). Ticker prüfen, z. B. SAP.DE, AAPL, ASML.AS")
    d.update(daten.fetch_prices([sym]).get(sym, {}))
    raw[sym] = d
    cfg = {**cfg, "filter": {**cfg["filter"], "min_marktkapitalisierung_mrd": 0}}
    df = score(frame(raw), cfg)
    r = df[df["ticker"] == sym].iloc[0]
    good, bad = strengths_weaknesses(r)
    print(f"\n{r['name']} ({sym}) - {r['branche']}")
    print(f"Score {r['score']:.0f}/100, Rang {r['rang']} von {len(df)}\n")
    for c, lab in KATEGORIEN.items():
        v = r["k_" + c]
        print(f"  {lab:<12} {v:5.0f}  " + "#" * int(v / 5))
    print(f"\n  Stärken:     {', '.join(good) or '-'}")
    print(f"  Schwächen:   {', '.join(bad) or '-'}")
    print(f"  Warnsignale: {'; '.join(r['warnungen']) or 'keine'}")
    print(f"\n  KGV erwartet {bericht.num(r['forwardPE'])} | Kursziel-Potenzial "
          f"{bericht.pct(r['kursziel_potenzial'], 0, True)} | Dividende {bericht.pct(r['div_rendite'])} | "
          f"Rendite 12M {bericht.pct(r['rendite_12m'], 0, True)}")
    print("\n  Nachrichten:")
    for n in r["_news"][:6]:
        s = n["stimmung"]
        tag = "+" if s >= 0.2 else "-" if s <= -0.2 else " "
        print(f"   [{tag}] {n['titel'][:110]}")
    print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--aktie", help="einzelne Aktie analysieren, z. B. SAP.DE oder AAPL")
    a = ap.parse_args()
    c = load_config()
    single(c, a.aktie) if a.aktie else scan(c)
