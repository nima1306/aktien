"""HTML-Bericht (öffnet sich im Browser) und Excel-Export."""
import html
import json
from datetime import date, datetime

import numpy as np

from bewertung import KATEGORIEN, METRIKEN, strengths_weaknesses

E = html.escape


def stand():
    """Zeitpunkt der Erstellung in deutscher Zeit."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y, %H:%M Uhr")
    except Exception:
        return datetime.now().strftime("%d.%m.%Y, %H:%M Uhr")


def pct(x, d=1, sign=False):
    if x is None or x != x:
        return "–"
    s = f"{x * 100:+.{d}f} %" if sign else f"{x * 100:.{d}f} %"
    return s.replace(".", ",")


def num(x, d=1):
    return "–" if x is None or x != x else f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def color(v):
    """0..100 -> Farbklasse."""
    if v != v:
        return "n"
    return "g2" if v >= 75 else "g1" if v >= 60 else "r2" if v < 25 else "r1" if v < 40 else "n"


def spark(values, w=160, h=36):
    if len(values) < 3:
        return ""
    v = np.array(values, dtype=float)
    lo, hi = v.min(), v.max()
    rng = hi - lo or 1
    pts = " ".join(f"{i * w / (len(v) - 1):.1f},{h - (x - lo) / rng * (h - 4) - 2:.1f}" for i, x in enumerate(v))
    cls = "up" if v[-1] >= v[0] else "down"
    return f'<svg class="spark {cls}" viewBox="0 0 {w} {h}" width="{w}" height="{h}"><polyline points="{pts}"/></svg>'


def news_html(items, n):
    if not items:
        return "<p class='muted'>Keine aktuellen Nachrichten gefunden.</p>"
    out = []
    for it in items[:n]:
        s = it.get("stimmung", 0)
        cls, lab = ("pos", "positiv") if s >= 0.2 else ("neg", "negativ") if s <= -0.2 else ("neu", "neutral")
        when = datetime.fromtimestamp(it["zeit"]).strftime("%d.%m.%Y") if it.get("zeit") else ""
        title = E(it["titel"])
        link = f'<a href="{E(it["url"])}" target="_blank" rel="noopener">{title}</a>' if it.get("url") else title
        out.append(f'<li><span class="badge {cls}">{lab}</span> {link} '
                   f'<span class="muted">{E(it.get("quelle") or "")} {when}</span></li>')
    return "<ul class='news'>" + "".join(out) + "</ul>"


def detail_card(r, cfg):
    good, bad = strengths_weaknesses(r)
    cats = "".join(f'<div class="cat {color(r["k_" + c])}"><span>{lab}</span><b>{r["k_" + c]:.0f}</b></div>'
                   for c, lab in KATEGORIEN.items())
    kz = [
        ("Kurs", f'{num(r["kurs"], 2)} {E(r["waehrung"])}'),
        ("Marktwert", f'{num(r["marketCap"] / 1e9, 0)} Mrd.' if r["marketCap"] == r["marketCap"] else "–"),
        ("KGV erwartet / aktuell", f'{num(r["forwardPE"])} / {num(r["trailingPE"])}'),
        ("PEG-Ratio", num(r["peg"], 2)),
        ("Free-Cashflow-Rendite", pct(r["fcf_rendite"])),
        ("Eigenkapitalrendite", pct(r["returnOnEquity"])),
        ("Operative Marge", pct(r["operatingMargins"])),
        ("Verschuldung (D/E)", num(r["debtToEquity"] / 100, 2) if r["debtToEquity"] == r["debtToEquity"] else "–"),
        ("Umsatzwachstum", pct(r["revenueGrowth"], sign=True)),
        ("Gewinnwachstum", pct(r["earningsGrowth"], sign=True)),
        ("Erw. Gewinnwachstum", pct(r["eps_wachstum_erw"], sign=True)),
        ("Kursziel Analysten", f'{num(r["targetMeanPrice"], 2)} ({pct(r["kursziel_potenzial"], sign=True)})'),
        ("Empfehlung (1–5)", f'{num(r["empfehlung"], 2)} · {int(r["numberOfAnalystOpinions"]) if r["numberOfAnalystOpinions"] == r["numberOfAnalystOpinions"] else 0} Analysten'),
        ("Rendite 12 Monate", pct(r["rendite_12m"], sign=True)),
        ("Größter Rückgang 12 M.", pct(r["max_drawdown"])),
        ("Volatilität", pct(r["volatilitaet"], 0)),
        ("Dividendenrendite", pct(r["div_rendite"], 2)),
        ("Ausschüttungsquote", pct(r["payoutRatio"], 0)),
    ]
    kz_html = "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in kz)
    warn = "".join(f"<li>{E(w)}</li>" for w in r["warnungen"])
    desc = E(r["_beschreibung"][:420] + ("…" if len(r["_beschreibung"]) > 420 else ""))
    return f"""
<details class="card" id="{E(r['ticker'])}">
  <summary>
    <span class="rank">#{r['rang']}</span>
    <span class="title"><b>{E(r['name'])}</b> <span class="muted">{E(r['ticker'])} · {E(r['branche'])}</span></span>
    {spark(r['_verlauf'])}
    <span class="score {color(r['score'])}">{r['score']:.0f}</span>
  </summary>
  <div class="body">
    <p class="desc">{desc}</p>
    <div class="cats">{cats}</div>
    <div class="sw">
      <div><h4>Stärken</h4><p>{', '.join(good) or '–'}</p></div>
      <div><h4>Schwächen</h4><p>{', '.join(bad) or '–'}</p></div>
      <div><h4>Warnsignale</h4>{'<ul class="warn">' + warn + '</ul>' if warn else '<p>keine</p>'}</div>
    </div>
    <h4>Kennzahlen</h4>
    <div class="kz">{kz_html}</div>
    <h4>Aktuelle Nachrichten</h4>
    {news_html(r['_news'], cfg['bericht']['nachrichten_pro_aktie'])}
  </div>
</details>"""


def table_rows(df):
    rows = []
    for _, r in df.iterrows():
        cells = "".join(f'<td class="c {color(r["k_" + c])}" data-v="{r["k_" + c]:.1f}">{r["k_" + c]:.0f}</td>'
                        for c in KATEGORIEN)
        pot = r["kursziel_potenzial"]
        rows.append(
            f'<tr data-branche="{E(r["branche"])}"><td data-v="{r["rang"]}">{r["rang"]}</td>'
            f'<td class="name"><a href="#{E(r["ticker"])}" onclick="openCard(\'{E(r["ticker"])}\')">{E(r["name"])}</a>'
            f'<br><span class="muted">{E(r["ticker"])}</span></td>'
            f'<td>{E(r["branche"])}</td>'
            f'<td data-v="{r["score"]:.2f}"><div class="bar"><i style="width:{r["score"]:.0f}%"></i></div>'
            f'<b>{r["score"]:.0f}</b></td>{cells}'
            f'<td data-v="{pot if pot == pot else -9}">{pct(pot, 0, True)}</td>'
            f'<td data-v="{r["forwardPE"] if r["forwardPE"] == r["forwardPE"] else 9999}">{num(r["forwardPE"])}</td>'
            f'<td data-v="{r["div_rendite"]}">{pct(r["div_rendite"])}</td>'
            f'<td data-v="{len(r["warnungen"])}" title="{E("; ".join(r["warnungen"]))}">'
            f'{"⚠ " + str(len(r["warnungen"])) if r["warnungen"] else "–"}</td></tr>')
    return "\n".join(rows)


def sector_best(df, n=2):
    """Die besten Aktien je Branche ohne Warnsignale - Grundlage für ein gestreutes Depot."""
    clean = df[df["warnungen"].apply(len) == 0]
    rows = []
    for b, g in clean.groupby("branche"):
        g = g.sort_values("score", ascending=False).head(n)
        cells = "".join(f'<td><b>{E(r["name"])}</b> <span class="muted">{E(r["ticker"])}</span>'
                        f'<br><span class="score-s {color(r["score"])}">{r["score"]:.0f}</span> '
                        f'<span class="muted">Div. {pct(r["div_rendite"])} · KGV {num(r["forwardPE"])}</span></td>'
                        for _, r in g.iterrows())
        cells += "<td></td>" * (n - len(g))
        rows.append((g["score"].max(), f"<tr><td>{E(b)}</td>{cells}</tr>"))
    rows.sort(key=lambda x: -x[0])
    return ("<div class='tw'><table><thead><tr><th>Branche</th><th>Beste</th><th>Zweitbeste</th></tr></thead>"
            "<tbody>" + "".join(r for _, r in rows) + "</tbody></table></div>")


def sector_bars(top):
    counts = top["branche"].value_counts()
    mx = counts.max()
    return "".join(f'<div class="sb"><span>{E(b)}</span><div class="bar"><i style="width:{n / mx * 100:.0f}%"></i></div>'
                   f'<b>{n}</b></div>' for b, n in counts.items())


def write_html(df, cfg, info, failed, path="aktien_bericht.html"):
    n_top = cfg["bericht"]["top"]
    top = df.head(n_top)
    branchen = sorted(df["branche"].unique())
    heads = "".join(f'<th class="c" title="{lab}">{lab[:5]}.</th>' for lab in KATEGORIEN.values())
    weights = ", ".join(f"{KATEGORIEN[k]} {v}" for k, v in cfg["gewichte"].items())
    method = "".join(f"<li><b>{KATEGORIEN[c]}</b>: " +
                     ", ".join(v[3] for m, v in METRIKEN.items() if v[0] == c) + "</li>" for c in KATEGORIEN)
    page = f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Aktien-Scanner</title>
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Aktien"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="icon.png"><link rel="icon" href="icon.png">
<style>
:root{{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e4e3de;--acc:#2f5d50;
--g2:#cfe8d6;--g1:#e6f2e8;--r1:#f8e3df;--r2:#f0c9c1;--warn:#a1471f}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151614;--card:#1e201d;--ink:#e9e8e3;--muted:#9a9a93;--line:#30322e;
--acc:#8cc4ae;--g2:#244a33;--g1:#1f3528;--r1:#43251f;--r2:#5a2c22;--warn:#f0a07a}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1280px;margin:0 auto;padding:28px 16px 60px}}
h1{{font-size:28px;margin:0 0 4px}}h2{{font-size:20px;margin:36px 0 12px}}h4{{margin:16px 0 6px;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}}
.muted{{color:var(--muted);font-size:13px}}.box{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}}
.notice{{border-left:4px solid var(--warn)}}.grid2{{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-top:16px}}
@media(max-width:800px){{.grid2{{grid-template-columns:1fr}}}}
.bar{{display:inline-block;width:70px;height:8px;background:var(--line);border-radius:4px;margin-right:6px;vertical-align:middle;overflow:hidden}}
.bar i{{display:block;height:100%;background:var(--acc)}}
.sb{{display:grid;grid-template-columns:1fr 90px 24px;align-items:center;gap:6px;font-size:13px}}.sb .bar{{width:100%}}
.tools{{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}}input,select{{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}}
.tw{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}
th{{cursor:pointer;position:sticky;top:0;background:var(--card);user-select:none}}th:hover{{color:var(--acc)}}
td.c,th.c{{text-align:center;width:44px}}td.name{{white-space:normal;min-width:180px}}a{{color:var(--acc)}}
.g2{{background:var(--g2)}}.g1{{background:var(--g1)}}.r1{{background:var(--r1)}}.r2{{background:var(--r2)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:10px 0}}
.card summary{{display:flex;align-items:center;gap:14px;padding:12px 16px;cursor:pointer;list-style:none}}
.card summary::-webkit-details-marker{{display:none}}.rank{{font-weight:700;color:var(--muted);width:36px}}
.title{{flex:1;min-width:0}}.score-s{{font-weight:700;padding:0 6px;border-radius:5px}}.score{{font-weight:700;font-size:18px;padding:4px 10px;border-radius:8px}}
.spark polyline{{fill:none;stroke-width:1.6}}.spark.up polyline{{stroke:#3c8c5a}}.spark.down polyline{{stroke:#c0553b}}
@media(max-width:600px){{.spark{{display:none}}}}
.body{{padding:0 16px 16px}}.desc{{color:var(--muted);font-size:14px}}
.cats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:6px}}
.cat{{border-radius:8px;padding:6px 10px;display:flex;justify-content:space-between;font-size:13px;border:1px solid var(--line)}}
.sw{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}.warn{{color:var(--warn);margin:0;padding-left:18px}}
.kz{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:4px 16px;font-size:13px}}
.kz div{{display:flex;justify-content:space-between;border-bottom:1px dotted var(--line);padding:3px 0}}
.news{{padding-left:0;list-style:none;font-size:14px}}.news li{{margin:6px 0}}
.badge{{font-size:11px;padding:1px 7px;border-radius:10px;margin-right:4px}}.pos{{background:var(--g2)}}.neg{{background:var(--r2)}}.neu{{background:var(--line)}}
</style></head><body><main>
<h1>Aktien-Scanner</h1>
<p><a href="app/" target="_top"><b>Video-App öffnen →</b></a></p>
<p class="muted">Stand {stand()} · {len(df)} Aktien bewertet · {' · '.join(E(i) for i in info)}</p>

<div class="box notice"><b>Keine Anlageberatung.</b> Die Bewertung vergleicht Aktien nur untereinander und
beruht auf Daten von Yahoo Finance, die verzögert oder fehlerhaft sein können. Ein hoher Score sagt nicht
voraus, dass eine Aktie steigt, und dieses Verfahren lässt sich mangels historischer Kennzahlen nicht
zuverlässig zurücktesten. Nutze es als <b>Startpunkt für eigene Recherche</b>, streue über viele Aktien und
Branchen, und investiere nur Geld, das du langfristig nicht brauchst.</div>

<div class="grid2">
  <div class="box"><h4>So entsteht der Score</h4>
  <p>Jede Aktie bekommt in 8 Kategorien 0–100 Punkte, je nachdem, wie sie im Vergleich zu allen anderen
  abschneidet (100 = beste). Bewertung und Verschuldung werden innerhalb der eigenen Branche verglichen.
  Der Gesamtscore ist der gewichtete Durchschnitt (Gewichte: {weights}); jedes Warnsignal kostet
  {cfg['filter']['abzug_pro_warnung']} Punkte.</p><ul class="muted">{method}</ul></div>
  <div class="box"><h4>Branchen in den Top {n_top}</h4>{sector_bars(top)}
  <p class="muted">Ballen sich die Top-Werte in einer Branche, ist das ein Klumpenrisiko. Für ein
  gestreutes Depot lieber die besten je Branche betrachten.</p></div>
</div>

<h2>Beste je Branche</h2>
<p class="muted">Je Branche die zwei höchstbewerteten Aktien <b>ohne Warnsignale</b>. Wer aus mehreren Zeilen
auswählt, streut automatisch über verschiedene Branchen und senkt das Klumpenrisiko.</p>
{sector_best(df)}

<h2>Rangliste</h2>
<div class="tools"><input id="q" placeholder="Suche Name oder Ticker" oninput="filt()">
<select id="br" onchange="filt()"><option value="">Alle Branchen</option>
{''.join(f'<option>{E(b)}</option>' for b in branchen)}</select>
<label class="muted"><input type="checkbox" id="nw" onchange="filt()"> nur ohne Warnsignale</label></div>
<div class="tw"><table id="t"><thead><tr><th>#</th><th>Aktie</th><th>Branche</th><th>Score</th>{heads}
<th>Potenzial</th><th>KGV erw.</th><th>Div.</th><th>Warn.</th></tr></thead><tbody>
{table_rows(df)}
</tbody></table></div>
<p class="muted">Spaltenköpfe anklicken zum Sortieren. Grün = stark, Rot = schwach im Vergleich.
Potenzial = Abstand zum durchschnittlichen Kursziel der Analysten.</p>

<h2>Details: Top {n_top}</h2>
{''.join(detail_card(r, cfg) for _, r in top.iterrows())}

{'<h2>Nicht abrufbar</h2><p class="muted">' + E(', '.join(failed)) + '</p>' if failed else ''}
</main>
<script>
function filt(){{const q=document.getElementById('q').value.toLowerCase(),b=document.getElementById('br').value,
nw=document.getElementById('nw').checked;
document.querySelectorAll('#t tbody tr').forEach(tr=>{{const ok=tr.textContent.toLowerCase().includes(q)&&
(!b||tr.dataset.branche===b)&&(!nw||tr.lastElementChild.textContent.trim()==='–');tr.style.display=ok?'':'none'}})}}
document.querySelectorAll('#t th').forEach((th,i)=>{{let asc=false;th.onclick=()=>{{asc=!asc;
const tb=document.querySelector('#t tbody');const rows=[...tb.rows];rows.sort((a,b)=>{{
const x=a.cells[i].dataset.v??a.cells[i].textContent,y=b.cells[i].dataset.v??b.cells[i].textContent;
const nx=parseFloat(x),ny=parseFloat(y);const c=(!isNaN(nx)&&!isNaN(ny))?nx-ny:String(x).localeCompare(String(y));
return asc?c:-c}});rows.forEach(r=>tb.appendChild(r))}}}});
function openCard(id){{const d=document.getElementById(id);if(d)d.open=true}}
</script></body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


def write_excel(df, path="aktien_rangliste.xlsx"):
    cols = {"rang": "Rang", "ticker": "Ticker", "name": "Name", "branche": "Branche", "land": "Land",
            "score": "Score", **{"k_" + c: lab for c, lab in KATEGORIEN.items()},
            "kurs": "Kurs", "waehrung": "Währung", "forwardPE": "KGV erw.", "trailingPE": "KGV",
            "kursziel_potenzial": "Potenzial Kursziel", "empfehlung": "Empfehlung (1-5)",
            "numberOfAnalystOpinions": "Analysten", "revenueGrowth": "Umsatzwachstum",
            "returnOnEquity": "Eigenkapitalrendite", "div_rendite": "Dividendenrendite",
            "rendite_12m": "Rendite 12M", "max_drawdown": "Max. Rückgang 12M"}
    out = df[list(cols)].rename(columns=cols).copy()
    out["Warnsignale"] = df["warnungen"].apply("; ".join)
    try:
        out.round(3).to_excel(path, index=False)
    except Exception:
        path = path.replace(".xlsx", ".csv")
        out.round(3).to_csv(path, index=False, sep=";", decimal=",")
    return path
