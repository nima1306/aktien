"""Thema Bundesliga: tägliche Videos aus den Daten von OpenLigaDB (kostenlos, ohne Schlüssel).

Formate (der Bot wählt automatisch, jedes nur einmal):
  rueckblick   nach einem Spieltag: Ergebnisse, Überraschung, Tabelle, Zahlen      (meist Montag)
  vorschau     vor einem Spieltag: Paarungen, Topspiel, Formcheck, Tabelle         (meist Do/Fr)
  torjaeger / meisterrennen / abstiegskampf   an den Tagen dazwischen, im Wechsel

Keine Vereinslogos oder Spielerfotos (geschützt) - alles wird selbst gezeichnet.
"""
import random
import re
from datetime import date, datetime, timedelta

import requests

NAME = "bundesliga"
BRAND = "BUNDESLIGA-CHECK"
QUELLEN = "OpenLigaDB"
DISCLAIMER = "Ohne Gewähr"
API = "https://api.openligadb.de"
WOCHENTAG = ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."]
WOCHENTAG_LANG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
ZAHL = ["null", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn"]


# ---------------------------------------------------------------- Daten

def _get(pfad):
    r = requests.get(API + pfad, timeout=25, headers={"User-Agent": "Aktienscanner-Videobot/1.0 (privat)"})
    r.raise_for_status()
    return r.json()


def k(obj, *namen, default=None):
    """Feld unabhängig von Groß-/Kleinschreibung lesen (die API war da nicht immer einheitlich)."""
    if not isinstance(obj, dict):
        return default
    low = {str(a).lower(): b for a, b in obj.items()}
    for n in namen:
        if n.lower() in low and low[n.lower()] is not None:
            return low[n.lower()]
    return default


def saison(heute=None):
    heute = heute or date.today()
    return heute.year if heute.month >= 7 else heute.year - 1


def kurz(name):
    """'1. FC Union Berlin' -> 'Union Berlin', 'FC Bayern München' -> 'Bayern München'."""
    n = str(name or "").strip()
    for _ in range(3):
        n = re.sub(r"^(1\.\s*)?(FC|FSV|SV|VfL|VfB|TSG|SC|RB|BV|SpVgg|TSV|SG|DSC|SSV)\s+", "", n)
        n = re.sub(r"^1\.\s*", "", n)
    n = re.sub(r"\s+(0[0-9]|1[0-9]{3}|04|05|98|96)$", "", n)
    n = n.replace("Bayer 04 ", "Bayer ").replace("Borussia Mönchengladbach", "Gladbach")
    return n.strip() or str(name)


def team(m, nr):
    t = k(m, f"team{nr}") or {}
    return kurz(k(t, "teamName", "shortName", default="?"))


def ergebnis(m):
    res = k(m, "matchResults", default=[]) or []
    end = [r for r in res if k(r, "resultTypeID") == 2] or sorted(res, key=lambda r: k(r, "resultOrderID", default=0))
    if not end:
        return None
    r = end[-1]
    return int(k(r, "pointsTeam1", default=0)), int(k(r, "pointsTeam2", default=0))


def anstoss(m):
    s = str(k(m, "matchDateTime", default=""))[:19]
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def spieltag(m):
    return int(k(k(m, "group") or {}, "groupOrderID", default=0) or 0)


def fertig(m):
    return bool(k(m, "matchIsFinished", default=False)) and ergebnis(m) is not None


def laden():
    s = saison()
    alle = _get(f"/getmatchdata/bl1/{s}")
    tabelle = _get(f"/getbltable/bl1/{s}")
    try:
        torj = _get(f"/getgoalgetters/bl1/{s}")
    except Exception:
        torj = []
    return {"saison": s, "spiele": alle, "tabelle": tabelle, "torjaeger": torj}


# ---------------------------------------------------------------- Auswertung

def tabelle_zeilen(tab):
    out = []
    for i, z in enumerate(tab, 1):
        out.append({"platz": i, "team": kurz(k(z, "teamName", "shortName")), "pkt": int(k(z, "points", default=0)),
                    "sp": int(k(z, "matches", default=0)), "diff": int(k(z, "goalDiff", default=0)),
                    "tore": int(k(z, "goals", default=0)), "gegen": int(k(z, "opponentGoals", default=0))})
    return out


def zone(platz, n=18):
    return "top" if platz <= 4 else "relegation" if platz == n - 2 else "abstieg" if platz > n - 2 else None


def tabelle_szene(tz, titel, unter, oben=4, unten=3):
    zeilen = [dict(z, zone=zone(z["platz"], len(tz))) for z in tz[:oben]]
    if len(tz) > oben + unten:
        zeilen.append({"trenner": True})
    zeilen += [dict(z, zone=zone(z["platz"], len(tz))) for z in tz[-unten:]]
    return {"titel": titel, "unter": unter, "zeilen": zeilen}


def form(spiele, name, n=5):
    """Letzte n Ergebnisse eines Teams als S/U/N und Punkte."""
    erg = []
    for m in sorted((m for m in spiele if fertig(m)), key=lambda m: anstoss(m) or datetime.min):
        h, g = team(m, 1), team(m, 2)
        if name not in (h, g):
            continue
        a, b = ergebnis(m)
        eig, geg = (a, b) if name == h else (b, a)
        erg.append("S" if eig > geg else "U" if eig == geg else "N")
    erg = erg[-n:]
    return erg, sum(3 if e == "S" else 1 if e == "U" else 0 for e in erg)


def punkte_wort(p):
    return f"{p} Punkt" if p == 1 else f"{p} Punkte"


# ---------------------------------------------------------------- Formate

def _frage_szene(frage, tag_nr, cta_tag=True):
    return {"frage": frage, "tag": "Bundesliga", "hinweis": "Daten: OpenLigaDB",
            "hinweis2": "Ohne Gewähr · Community-Datenbank",
            "cta": f"Morgen: Tag {tag_nr + 1}" if tag_nr and cta_tag else "Folge für den nächsten Spieltag"}


def _outro_text(frage_lang, tag_nr):
    morgen = f" Morgen kommt Tag {tag_nr + 1}." if tag_nr else ""
    return f"Alle Daten von OpenLigaDB, ohne Gewähr.{morgen} Und jetzt du: {frage_lang}"


def rueckblick(D, st, tag_nr):
    spiele = [m for m in D["spiele"] if spieltag(m) == st]
    tz = tabelle_zeilen(D["tabelle"])
    platz = {z["team"]: z["platz"] for z in tz}
    zeilen, tore_ges, heim, aus, remis, schuetzen = [], 0, 0, 0, 0, {}
    ueberraschung, torreich = None, None
    for m in sorted(spiele, key=lambda m: anstoss(m) or datetime.min):
        h, g = team(m, 1), team(m, 2)
        a, b = ergebnis(m)
        tore_ges += a + b
        heim, aus, remis = heim + (a > b), aus + (b > a), remis + (a == b)
        zeilen.append({"heim": h, "gast": g, "tore_h": a, "tore_g": b})
        if a != b:
            sieger, verl = (h, g) if a > b else (g, h)
            diff = platz.get(sieger, 9) - platz.get(verl, 9)
            if diff >= 6 and (not ueberraschung or diff > ueberraschung[0]):
                ueberraschung = (diff, sieger, verl, max(a, b), min(a, b), len(zeilen) - 1)
        if not torreich or a + b > torreich[0]:
            torreich = (a + b, h, g, a, b, len(zeilen) - 1)
        for tor in k(m, "goals", default=[]) or []:
            if k(tor, "isOwnGoal"):
                continue
            nm = k(tor, "goalGetterName")
            if nm:
                schuetzen[nm] = schuetzen.get(nm, 0) + 1
    n = len(zeilen)
    mark = (ueberraschung or torreich)[5]
    zeilen[mark]["markiert"] = True
    if ueberraschung:
        _, s, v, x, y, _ = ueberraschung
        hook = (f"Spieltag {st}: {s} schlägt {v} {x} zu {y}. Platz {platz.get(s)} gegen Platz {platz.get(v)}. "
                f"Hier ist alles, was du wissen musst.")
        frage = ("Welches Ergebnis hat dich am meisten überrascht? Schreib es in die Kommentare.",
                 "Was hat dich überrascht?")
    else:
        hook = f"Spieltag {st} ist durch: {tore_ges} Tore in {n} Spielen. Hier ist alles in einer Minute."
        frage = ("Wer wird am Ende Meister? Dein Tipp in die Kommentare.", "Wer wird Meister?")
    top3 = sorted(range(n), key=lambda i: (i != mark, -(zeilen[i]["tore_h"] + zeilen[i]["tore_g"])))[:3]
    highlights = ", ".join(f"{zeilen[i]['heim']} gegen {zeilen[i]['gast']} {zeilen[i]['tore_h']} zu "
                           f"{zeilen[i]['tore_g']}" for i in top3)
    abst = tz[0]["pkt"] - tz[1]["pkt"]
    spitze = (f"In der Tabelle führt {tz[0]['team']} mit {tz[0]['pkt']} Punkten, "
              + (f"{punkte_wort(abst)} vor {tz[1]['team']}." if abst else f"punktgleich mit {tz[1]['team']}."))
    unten = f" Ganz unten stehen {tz[-2]['team']} und {tz[-1]['team']}."
    bester = max(schuetzen.items(), key=lambda x: x[1]) if schuetzen else None
    schnitt = tore_ges / max(1, n)
    fakten_text = (f"Insgesamt {tore_ges} Tore, im Schnitt {str(round(schnitt, 1)).replace('.', ',')} pro Spiel. "
                   f"{heim} Heimsiege, {aus} Auswärtssiege, " + (f"{remis} Unentschieden." if remis else "kein Unentschieden."))
    karten = [{"label": "Tore", "wert": str(tore_ges), "farbe": "green"},
              {"label": "Ø pro Spiel", "wert": str(round(schnitt, 1)).replace(".", ",")},
              {"label": "Heimsiege", "wert": str(heim)}, {"label": "Auswärtssiege", "wert": str(aus)},
              {"label": "Remis", "wert": str(remis)}]
    if bester and bester[1] >= 2:
        fakten_text += f" Mann des Spieltags: {bester[0]} mit {bester[1]} Toren."
        karten.append({"label": "Mann des Spieltags", "wert": f"{bester[0].split()[-1]} ({bester[1]})", "farbe": "gold"})
    titel_sz = {"name": "titel", "text": hook, "daten": {"tag": f"Spieltag {st}", "name": "Bundesliga",
                "kicker": "ÜBERRASCHUNG" if ueberraschung else "TORE AM SPIELTAG",
                "gross": f"{ueberraschung[3]} : {ueberraschung[4]}" if ueberraschung else str(tore_ges),
                "sub": f"{ueberraschung[1]} gegen {ueberraschung[2]}" if ueberraschung else f"in {n} Spielen",
                "farbe": "green"}}
    szenen = [
        titel_sz,
        {"name": "ergebnisse", "text": f"Die wichtigsten Ergebnisse: {highlights}.",
         "daten": {"titel": f"Spieltag {st}", "unter": "Alle Ergebnisse", "spiele": zeilen}},
        {"name": "tabelle", "text": spitze + unten,
         "daten": tabelle_szene(tz, "Tabelle", f"nach dem {st}. Spieltag")},
        {"name": "fakten", "text": fakten_text,
         "daten": {"titel": "Der Spieltag in Zahlen", "unter": f"{n} Spiele", "karten": karten}},
        {"name": "frage", "text": _outro_text(frage[0], tag_nr), "daten": _frage_szene(frage[1], tag_nr)},
    ]
    h0 = ueberraschung[1] if ueberraschung else torreich[1]
    g0 = ueberraschung[2] if ueberraschung else torreich[2]
    titel = [f"Spieltag {st} in 60 Sekunden ⚽",
             (f"{ueberraschung[1]} schlägt {ueberraschung[2]} {ueberraschung[3]}:{ueberraschung[4]} 😳"
              if ueberraschung else f"{tore_ges} Tore am {st}. Spieltag ⚽"),
             f"Bundesliga Spieltag {st}: Das musst du wissen"]
    tags = ["bundesliga", "fußball", "spieltag", _tag(h0), _tag(g0), "fussball", "bundesligatabelle", "fyp"]
    return {"id": f"rueckblick-{D['saison']}-{st}", "szenen": szenen, "titel": titel, "tags": tags,
            "frage": frage[1], "name": f"Spieltag {st} · Rückblick"}


def vorschau(D, st, tag_nr):
    spiele = sorted([m for m in D["spiele"] if spieltag(m) == st], key=lambda m: anstoss(m) or datetime.max)
    tz = tabelle_zeilen(D["tabelle"])
    platz = {z["team"]: z["platz"] for z in tz}
    zeilen, top = [], None
    for i, m in enumerate(spiele):
        h, g = team(m, 1), team(m, 2)
        an = anstoss(m)
        info = f"{WOCHENTAG[an.weekday()]} {an:%H:%M}" if an else "–"
        erg = ergebnis(m) if fertig(m) else None
        zeilen.append({"heim": h, "gast": g, "tore_h": erg[0] if erg else None, "tore_g": erg[1] if erg else None,
                       "info": info})
        summe = platz.get(h, 18) + platz.get(g, 18)
        if not erg and (not top or summe < top[0]):
            top = (summe, h, g, an, i)
    if not top:
        return None
    _, a, b, an, idx = top
    zeilen[idx]["markiert"] = True
    fa, pa = form(D["spiele"], a)
    fb, pb = form(D["spiele"], b)
    erstes = next((z for z, m in zip(zeilen, spiele) if z["tore_h"] is None), zeilen[0])
    an0 = anstoss(spiele[zeilen.index(erstes)])
    wann0 = WOCHENTAG_LANG[an0.weekday()] if an0 else "bald"
    hook = (f"Spieltag {st} steht an, und das Topspiel heißt {a} gegen {b}. Platz {platz.get(a)} gegen Platz "
            f"{platz.get(b)}.")
    paar = (f"Los geht es am {wann0} mit {erstes['heim']} gegen {erstes['gast']}. Das Topspiel läuft am "
            f"{WOCHENTAG_LANG[an.weekday()]} um {an:%H:%M} Uhr." if an else "")
    frage = ("Dein Tipp fürs Topspiel? Schreib dein Ergebnis in die Kommentare.", "Dein Tipp fürs Topspiel?")
    szenen = [
        {"name": "titel", "text": hook, "daten": {"tag": f"Spieltag {st}", "name": "Vorschau", "kicker": "TOPSPIEL",
         "gross": f"{a} – {b}", "sub": f"{WOCHENTAG[an.weekday()]} {an:%d.%m.} · {an:%H:%M} Uhr" if an else "",
         "sub2": f"Platz {platz.get(a)} gegen Platz {platz.get(b)}", "farbe": "green"}},
        {"name": "ergebnisse", "text": paar,
         "daten": {"titel": f"Spieltag {st}", "unter": "Alle Paarungen", "spiele": zeilen}},
        {"name": "fakten", "text": f"Die Form: {a} holte aus den letzten {len(fa)} Spielen {punkte_wort(pa)}, "
                                   f"{b} {punkte_wort(pb)}.",
         "daten": {"titel": "Formcheck", "unter": "letzte 5 Spiele (S/U/N)",
                   "karten": [{"label": a, "wert": " ".join(fa) or "–", "farbe": "green"},
                              {"label": b, "wert": " ".join(fb) or "–", "farbe": "green"},
                              {"label": f"Punkte {a}", "wert": str(pa)}, {"label": f"Punkte {b}", "wert": str(pb)}]}},
        {"name": "tabelle", "text": f"Vor dem Spieltag führt {tz[0]['team']} mit {tz[0]['pkt']} Punkten.",
         "daten": tabelle_szene(tz, "Tabelle", f"vor dem {st}. Spieltag")},
        {"name": "frage", "text": _outro_text(frage[0], tag_nr), "daten": _frage_szene(frage[1], tag_nr)},
    ]
    titel = [f"Spieltag {st}: Dein Tipp fürs Topspiel? ⚽", f"Topspiel: {a} gegen {b}",
             f"Bundesliga Vorschau Spieltag {st}"]
    tags = ["bundesliga", "fußball", "topspiel", _tag(a), _tag(b), "tippspiel", "fussball", "fyp"]
    return {"id": f"vorschau-{D['saison']}-{st}", "szenen": szenen, "titel": titel, "tags": tags, "frage": frage[1],
            "name": f"Spieltag {st} · Vorschau"}


def torjaeger(D, st, tag_nr):
    tj = sorted(D.get("torjaeger") or [], key=lambda x: -int(k(x, "goalCount", default=0)))
    tj = [x for x in tj if k(x, "goalGetterName")][:7]
    if len(tj) < 3:
        return None
    n1, t1 = k(tj[0], "goalGetterName"), int(k(tj[0], "goalCount"))
    tz = tabelle_zeilen(D["tabelle"])
    tore = sum(z["tore"] for z in tz)
    spiele = max(1, sum(z["sp"] for z in tz) // 2)
    offensiv = max(tz, key=lambda z: z["tore"])
    defensiv = min(tz, key=lambda z: z["gegen"])
    frage = ("Wer wird am Ende Torschützenkönig? Schreib deinen Tipp in die Kommentare.", "Wer wird Torschützenkönig?")
    szenen = [
        {"name": "titel", "text": (f"{n1} und {k(tj[1], 'goalGetterName')} führen mit je {t1} Toren nach {st} "
                                   f"Spieltagen. Wer setzt sich durch?" if int(k(tj[1], "goalCount")) == t1 else
                                   f"{n1} hat schon {t1} Tore nach {st} Spieltagen. Wer kann ihn noch stoppen?"),
         "daten": {"tag": "Torjäger", "name": "Bundesliga", "kicker": n1.upper(), "gross": f"{t1} Tore",
                   "sub": f"nach {st} Spieltagen", "farbe": "gold"}},
        {"name": "liste", "text": "Dahinter: " + ", ".join(
            f"{k(x, 'goalGetterName')} mit {k(x, 'goalCount')}" for x in tj[1:3]) + " Toren.",
         "daten": {"titel": "Torjägerliste", "unter": f"Saison {D['saison']}/{str(D['saison'] + 1)[2:]}",
                   "zeilen": [{"label": k(x, "goalGetterName"), "wert": int(k(x, "goalCount")),
                               "text": str(k(x, "goalCount")), "markiert": i == 0, "farbe": "gold" if i == 0 else "green"}
                              for i, x in enumerate(tj)]}},
        {"name": "fakten", "text": f"Die beste Offensive hat {offensiv['team']} mit {offensiv['tore']} Toren, "
                                   f"die beste Abwehr {defensiv['team']} mit nur {defensiv['gegen']} Gegentoren.",
         "daten": {"titel": "Die Saison in Zahlen", "unter": f"nach {st} Spieltagen",
                   "karten": [{"label": "Tore gesamt", "wert": str(tore), "farbe": "green"},
                              {"label": "Ø pro Spiel", "wert": str(round(tore / spiele, 1)).replace(".", ",")},
                              {"label": "Beste Offensive", "wert": f"{offensiv['team']}"},
                              {"label": "Beste Abwehr", "wert": f"{defensiv['team']}"}]}},
        {"name": "frage", "text": _outro_text(frage[0], tag_nr), "daten": _frage_szene(frage[1], tag_nr)},
    ]
    titel = [f"{n1}: {t1} Tore nach {st} Spieltagen 🔥", "Bundesliga Torjägerliste – wer holt die Kanone?",
             "Wer wird Torschützenkönig?"]
    tags = ["bundesliga", "fußball", "torjäger", _tag(n1.split()[-1]), "torjägerkanone", "fussball", "fyp"]
    return {"id": f"torjaeger-{date.today().isoformat()}", "szenen": szenen, "titel": titel, "tags": tags,
            "frage": frage[1], "name": "Torjäger-Check"}


def rennen(D, st, tag_nr, art):
    tz = tabelle_zeilen(D["tabelle"])
    if len(tz) < 10:
        return None
    if art == "meisterrennen":
        teil = tz[:6]
        abst = teil[0]["pkt"] - teil[3]["pkt"]
        hook = (f"Nach {st} Spieltagen trennen die ersten vier nur {punkte_wort(abst)}. Wie spannend ist das Meisterrennen "
                f"wirklich?" if abst <= 6 else f"{teil[0]['team']} enteilt: {punkte_wort(abst)} Vorsprung auf Platz vier "
                f"nach {st} Spieltagen.")
        frage = ("Wird es noch einmal spannend, oder ist das Rennen gelaufen? Was meinst du?", "Noch spannend?")
        titel_s, kicker, gross = "Meisterrennen", "VORSPRUNG AUF PLATZ 4", punkte_wort(abst)
        tags = ["bundesliga", "fußball", "meisterschaft", _tag(teil[0]["team"]), _tag(teil[1]["team"]), "fussball", "fyp"]
    else:
        teil = tz[-6:]
        abst = teil[3]["pkt"] - teil[-1]["pkt"]
        rette = tz[-4]
        hook = (f"Abstiegskampf nach {st} Spieltagen: Zwischen Platz {teil[0]['platz']} und dem letzten Platz liegen nur "
                f"{punkte_wort(teil[0]['pkt'] - teil[-1]['pkt'])}. Wer muss zittern?")
        frage = ("Wer steigt am Ende ab? Dein Tipp in die Kommentare.", "Wer steigt ab?")
        titel_s, kicker, gross = "Abstiegskampf", "ABSTAND PLATZ 15 ZU 18", punkte_wort(rette["pkt"] - tz[-1]["pkt"])
        tags = ["bundesliga", "fußball", "abstiegskampf", _tag(teil[-1]["team"]), _tag(teil[-2]["team"]), "fussball", "fyp"]
    zeilen = [dict(z, zone=zone(z["platz"], len(tz))) for z in teil]
    text_tab = " ".join(f"Platz {z['platz']}: {z['team']} mit {z['pkt']}." for z in (teil[:3] if art == "meisterrennen"
                                                                                       else teil[-3:]))
    szenen = [
        {"name": "titel", "text": hook, "daten": {"tag": titel_s, "name": f"nach {st} Spieltagen", "kicker": kicker,
                                                  "gross": gross, "farbe": "green" if art == "meisterrennen" else "red"}},
        {"name": "tabelle", "text": text_tab, "daten": {"titel": titel_s, "unter": f"Tabelle nach {st} Spieltagen",
                                                        "zeilen": zeilen}},
        {"name": "liste", "text": "So sieht es bei den Toren aus: " + ", ".join(
            f"{z['team']} {z['tore']} zu {z['gegen']}" for z in (teil[:3] if art == "meisterrennen" else teil[-3:])) + ".",
         "daten": {"titel": "Tore : Gegentore", "unter": titel_s,
                   "zeilen": [{"label": z["team"], "wert": max(z["tore"], 0.1), "text": f"{z['tore']}:{z['gegen']}",
                               "farbe": "green" if z["diff"] >= 0 else "red"} for z in teil]}},
        {"name": "frage", "text": _outro_text(frage[0], tag_nr), "daten": _frage_szene(frage[1], tag_nr)},
    ]
    titel = [f"Bundesliga {titel_s} nach {st} Spieltagen ⚽", f"{titel_s}: Die Zahlen", f"{frage[1]} 🤔"]
    return {"id": f"{art}-{date.today().isoformat()}", "szenen": szenen, "titel": titel, "tags": tags,
            "frage": frage[1], "name": titel_s}


def _tag(s):
    return "".join(c for c in str(s).lower() if c.isalnum())


# ---------------------------------------------------------------- Auswahl

def video_plan(D, erledigt, tag_nr, jetzt=None):
    """Wählt das Format des Tages. erledigt = Menge bereits gemachter IDs."""
    jetzt = jetzt or datetime.now()
    tage = {}
    for m in D["spiele"]:
        tage.setdefault(spieltag(m), []).append(m)
    fertige = [st for st, ms in tage.items() if st and all(fertig(m) for m in ms)]
    offene = sorted(st for st, ms in tage.items() if st and not all(fertig(m) for m in ms))
    letzter = max(fertige) if fertige else None
    if letzter:
        ende = max(anstoss(m) or datetime.min for m in tage[letzter])
        if (jetzt - ende) <= timedelta(days=3) and f"rueckblick-{D['saison']}-{letzter}" not in erledigt:
            return rueckblick(D, letzter, tag_nr)
    if offene:
        nst = offene[0]
        beginn = min(anstoss(m) or datetime.max for m in tage[nst] if not fertig(m))
        if timedelta(days=-1) <= (beginn - jetzt) <= timedelta(days=2) and f"vorschau-{D['saison']}-{nst}" not in erledigt:
            v = vorschau(D, nst, tag_nr)
            if v:
                return v
    st = letzter or 1
    reihe = ["torjaeger", "meisterrennen", "abstiegskampf"]
    start = date.today().toordinal() % 3
    for i in range(3):
        art = reihe[(start + i) % 3]
        if any(e.startswith(art) and e >= f"{art}-{(date.today() - timedelta(days=6)).isoformat()}" for e in erledigt):
            continue
        plan = torjaeger(D, st, tag_nr) if art == "torjaeger" else rennen(D, st, tag_nr, art)
        if plan:
            return plan
    return None


# ---------------------------------------------------------------- Demo (erfundene Liga, ohne Internet)

def demo_daten(art="rueckblick"):
    rnd = random.Random(3)
    teams = ["FC Nordhafen", "SV Bergstadt", "Union Talheim", "VfL Seeburg", "Borussia Lindental", "TSG Ostfeld",
             "Eintracht Rheinau", "SC Waldau", "1. FC Kronach", "Fortuna Elsing", "VfB Hollen", "RB Steinach",
             "Werder Mühlbach", "Hertha Auring", "SpVgg Falkenau", "FSV Brückendorf", "Arminia Teltau", "SC Moorbach"]
    stark = {t: 1.0 + (len(teams) - i) / 9 for i, t in enumerate(teams)}
    spieler = {t: [f"{v} {n}" for v, n in zip(["Lukas", "Jonas", "Mats"], [t.split()[-1][:3] + s for s in
                                                                            ("mann", "berg", "ling")])] for t in teams}
    paare = [(teams[i], teams[-1 - i]) for i in range(9)]
    spiele, start = [], datetime.now() - timedelta(days=9 * 7 - 2)
    jetzt_st = 10
    for st in range(1, jetzt_st + 1):
        tag0 = start + timedelta(days=7 * (st - 1))
        if art == "rueckblick" and st == jetzt_st:
            tag0 = datetime.now() - timedelta(days=2)
        if art != "rueckblick" and st == jetzt_st:
            tag0 = datetime.now() + timedelta(days=1)
        rot = teams[1:]
        rot = rot[st % 17:] + rot[:st % 17]
        runde = [teams[0]] + rot
        for i in range(9):
            h, g = runde[i], runde[-1 - i]
            if st % 2:
                h, g = g, h
            an = tag0.replace(hour=15, minute=30, second=0, microsecond=0) + timedelta(hours=(i % 3) * 3)
            m = {"matchDateTime": an.isoformat(), "group": {"groupOrderID": st}, "team1": {"teamName": h},
                 "team2": {"teamName": g}, "matchIsFinished": False, "matchResults": [], "goals": []}
            if an < datetime.now() and (art == "rueckblick" or st < jetzt_st):
                a = min(6, int(rnd.expovariate(1 / (1.3 * stark[h] / stark[g] ** 0.5))))
                b = min(6, int(rnd.expovariate(1 / (1.0 * stark[g] / stark[h] ** 0.5))))
                if art == "rueckblick" and st == jetzt_st and i == 4:   # Überraschung einbauen
                    a, b = (3, 0) if stark[h] < stark[g] else (0, 3)
                m["matchIsFinished"] = True
                m["matchResults"] = [{"resultTypeID": 2, "pointsTeam1": a, "pointsTeam2": b}]
                m["goals"] = ([{"goalGetterName": rnd.choice(spieler[k(m['team1'], 'teamName')])} for _ in range(a)] +
                              [{"goalGetterName": rnd.choice(spieler[k(m['team2'], 'teamName')])} for _ in range(b)])
            spiele.append(m)
    tab = {t: {"teamName": t, "points": 0, "goals": 0, "opponentGoals": 0, "matches": 0} for t in teams}
    torj = {}
    for m in spiele:
        if not fertig(m):
            continue
        h, g = k(m["team1"], "teamName"), k(m["team2"], "teamName")
        a, b = ergebnis(m)
        for t, x, y in ((h, a, b), (g, b, a)):
            tab[t]["goals"] += x
            tab[t]["opponentGoals"] += y
            tab[t]["matches"] += 1
            tab[t]["points"] += 3 if x > y else 1 if x == y else 0
        for tor in m["goals"]:
            torj[tor["goalGetterName"]] = torj.get(tor["goalGetterName"], 0) + 1
    tabelle = sorted(tab.values(), key=lambda z: (-z["points"], -(z["goals"] - z["opponentGoals"]), -z["goals"]))
    for z in tabelle:
        z["goalDiff"] = z["goals"] - z["opponentGoals"]
    return {"saison": saison(), "spiele": spiele, "tabelle": tabelle,
            "torjaeger": [{"goalGetterName": n, "goalCount": c} for n, c in torj.items()]}
