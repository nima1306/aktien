"""Thema Ernährung: tägliche Produkt-Checks mit echten Nährwerten aus Open Food Facts.

Jeden Tag eine andere Kategorie (Softdrinks, Frühstücksflocken, Müsliriegel, Proteinriegel, ...).
Verglichen werden die in Deutschland am häufigsten gescannten Produkte. Es werden nur Fakten gezeigt
(Herstellerangaben), keine Diät-Tipps und keine Bewertungen wie "ungesund".

Datenquelle: Open Food Facts (Open Database License) - die Quelle steht in jedem Video.
"""
import json
import os
import random
import re
import time
from datetime import date, timedelta

import requests

NAME = "ernaehrung"
BRAND = "FOOD-CHECK"
QUELLEN = "Open Food Facts (Herstellerangaben)"
DISCLAIMER = "Keine Ernährungsberatung"
WUERFEL_G = 3.0                     # ein Stück Würfelzucker wiegt etwa 3 g

# portion = Bezugsgröße für den Aufhänger (immer im Video genannt), who = WHO-Vergleich sinnvoll?
KATEGORIEN = [
    {"tag": "sodas", "name": "Softdrinks", "art": "zucker", "e": "ml", "portion": 500,
     "in": "einem halben Liter", "nom": "Ein halber Liter", "pro": "0,5 Liter", "who": True},
    {"tag": "breakfast-cereals", "name": "Frühstücksflocken", "art": "zucker", "e": "g", "portion": 40,
     "in": "einer Schale", "nom": "Eine Schale", "pro": "Schale (40 g)", "who": True},
    {"tag": "energy-drinks", "name": "Energy Drinks", "art": "zucker", "e": "ml", "portion": 250,
     "in": "einer Dose", "nom": "Eine Dose", "pro": "Dose (250 ml)", "who": True},
    {"tag": "cereal-bars", "name": "Müsliriegel", "art": "zucker", "e": "g", "portion": 25,
     "in": "einem Riegel", "nom": "Ein Riegel", "pro": "Riegel (25 g)", "who": True},
    {"tag": "protein-bars", "name": "Proteinriegel", "art": "protein", "e": "g", "portion": None,
     "in": "", "pro": "100 kcal", "who": False},
    {"tag": "fruit-juices", "name": "Fruchtsäfte", "art": "zucker", "e": "ml", "portion": 250,
     "in": "einem Glas", "nom": "Ein Glas", "pro": "Glas (250 ml)", "who": True},
    {"tag": "yogurts", "name": "Joghurts", "art": "zucker", "e": "g", "portion": 150,
     "in": "einem Becher", "nom": "Ein Becher", "pro": "Becher (150 g)", "who": False},
    {"tag": "iced-teas", "name": "Eistees", "art": "zucker", "e": "ml", "portion": 500,
     "in": "einem halben Liter", "nom": "Ein halber Liter", "pro": "0,5 Liter", "who": True},
    {"tag": "hazelnut-spreads", "name": "Nuss-Nougat-Cremes", "art": "zucker", "e": "g", "portion": 20,
     "in": "einer Brotportion", "nom": "Eine Brotportion", "pro": "Portion (20 g)", "who": True},
    {"tag": "chocolate-milks", "name": "Kakao-Drinks", "art": "zucker", "e": "ml", "portion": 500,
     "in": "einem halben Liter", "nom": "Ein halber Liter", "pro": "0,5 Liter", "who": False},
]


def _z(x, d=1):
    s = f"{x:.{d}f}".replace(".", ",")
    return re.sub(r",0$", "", s)


def _tag(s):
    return "".join(c for c in str(s).lower() if c.isalnum())


def produktname(p):
    name = (p.get("product_name_de") or p.get("product_name") or "").strip()
    marke = (p.get("brands") or "").split(",")[0].strip()
    if marke and marke.lower() not in name.lower():
        name = f"{marke} {name}".strip()
    name = re.sub(r"\s+", " ", name)
    return name[:42].rstrip(" ,-") if name else ""


CACHE = os.path.join("speicher", "ernaehrung_produkte.json")
FELDER = "code,product_name,product_name_de,brands,nutriments,nutriscore_grade"
KOPF = {"User-Agent": "TikTok-Videobot/1.0 (privates Projekt)"}


def _abfragen(kat):
    """Open Food Facts ist oft langsam oder kurz überlastet: mehrere Versuche, zwei Schnittstellen."""
    wege = [("https://world.openfoodfacts.org/api/v2/search",
             {"categories_tags_en": kat["tag"], "countries_tags_en": "germany", "sort_by": "unique_scans_n",
              "page_size": 60, "fields": FELDER}),
            ("https://world.openfoodfacts.org/cgi/search.pl",
             {"action": "process", "tagtype_0": "categories", "tag_contains_0": "contains", "tag_0": kat["tag"],
              "tagtype_1": "countries", "tag_contains_1": "contains", "tag_1": "germany",
              "sort_by": "unique_scans_n", "page_size": 60, "json": 1, "fields": FELDER})]
    fehler = None
    for versuch in range(3):
        for url, params in wege:
            try:
                r = requests.get(url, timeout=60, headers=KOPF, params=params)
                r.raise_for_status()
                produkte = r.json().get("products") or []
                if produkte:
                    return produkte
            except (requests.RequestException, ValueError) as e:
                fehler = e
        time.sleep(10 * (versuch + 1))
    raise RuntimeError(f"nicht erreichbar ({str(fehler)[:60]})")


def laden(kat, n=6):
    """Die beliebtesten Produkte einer Kategorie in Deutschland mit vollständigen Nährwerten.
    Klappt die Abfrage nicht, nimmt der Bot die zuletzt gespeicherten Daten der Kategorie."""
    try:
        cache = json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    try:
        produkte = _abfragen(kat)
        cache[kat["tag"]] = produkte
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception as e:
        if not cache.get(kat["tag"]):
            raise
        print(f"  Open Food Facts ({kat['tag']}): {str(e)[:60]} - nehme gespeicherte Daten")
        produkte = cache[kat["tag"]]
    return auswahl(produkte, kat, n)


def auswahl(produkte, kat, n=6):
    out, gesehen = [], set()
    for p in produkte:
        nm = produktname(p)
        nu = p.get("nutriments") or {}
        try:
            kcal = float(nu.get("energy-kcal_100g"))
            zucker = float(nu.get("sugars_100g"))
            eiweiss = float(nu.get("proteins_100g"))
        except (TypeError, ValueError):
            continue
        if not nm or not (0 < kcal < 900) or not (0 <= zucker <= 100) or not (0 <= eiweiss <= 100):
            continue
        schluessel = re.sub(r"[^a-z]", "", nm.lower())[:18]
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        try:
            fett = float(nu.get("fat_100g"))
        except (TypeError, ValueError):
            fett = None
        out.append({"name": nm, "kcal": kcal, "zucker": zucker, "eiweiss": eiweiss, "fett": fett,
                    "ns": (p.get("nutriscore_grade") or "").upper() if (p.get("nutriscore_grade") or "") in "abcde" else ""})
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------- Video bauen

def _outro(frage_lang, tag_nr):
    morgen = f" Morgen kommt Tag {tag_nr + 1}." if tag_nr else ""
    return (f"Das war der Check. Alle Werte aus Open Food Facts, nach Herstellerangaben und ohne Gewähr.{morgen} "
            f"Und jetzt du: {frage_lang}")


def _frage_daten(kurz, tag_nr, kat):
    return {"frage": kurz, "tag": kat["name"], "hinweis": "Keine Ernährungsberatung",
            "hinweis2": "Werte: Open Food Facts · Herstellerangaben",
            "cta": f"Morgen: Tag {tag_nr + 1}" if tag_nr else "Folge für den nächsten Check"}


def video(kat, produkte, tag_nr):
    if len(produkte) < 3:
        return None
    e_lang = "Milliliter" if kat["e"] == "ml" else "Gramm"
    if kat["art"] == "protein":
        for p in produkte:
            p["wert"] = p["eiweiss"] / p["kcal"] * 100
        liste = sorted(produkte, key=lambda p: -p["wert"])
        top, low = liste[0], liste[-1]
        hook = (f"Welcher Proteinriegel liefert am meisten Eiweiß pro Kalorie? Platz eins: {top['name']} mit "
                f"{_z(top['wert'])} Gramm pro 100 Kilokalorien.")
        titel_d = {"tag": "Protein-Check", "name": kat["name"], "kicker": "EIWEISS PRO 100 KCAL",
                   "gross": f"{_z(top['wert'])} g", "sub": top["name"], "sub2": "Platz 1 der beliebtesten Riegel",
                   "farbe": "green"}
        liste_text = (f"Ich habe die {len(liste)} beliebtesten Proteinriegel in Deutschland verglichen. Auf Platz zwei: "
                      f"{liste[1]['name']} mit {_z(liste[1]['wert'])} Gramm. Am wenigsten Eiweiß pro Kalorie hat "
                      f"{low['name']}, mit nur {_z(low['wert'])} Gramm.")
        liste_titel, einheit_wert = "Eiweiß pro 100 kcal", "g"
        frage = ("Welchen Riegel isst du am liebsten? Schreib es in die Kommentare.", "Welcher ist dein Favorit?")
        titel = [f"Der Proteinriegel mit dem meisten Protein? 💪", f"{kat['name']} im Check: Protein pro Kalorie",
                 "Welcher Riegel liefert am meisten Protein?"]
        tags = ["ernährung", "protein", "proteinriegel", _tag(top["name"].split()[0]), "lebensmittel", "foodcheck",
                "fitness", "fyp"]
    else:
        for p in produkte:
            p["wert"] = p["zucker"]
        liste = sorted(produkte, key=lambda p: -p["wert"])
        top, low = liste[0], liste[-1]
        g_portion = top["zucker"] * kat["portion"] / 100
        wuerfel = max(1, round(g_portion / WUERFEL_G))
        hook = (f"{wuerfel} Stück Würfelzucker! So viel Zucker steckt in {kat['in']} {top['name']}. "
                f"Hättest du das gedacht?")
        titel_d = {"tag": "Zucker-Check", "name": kat["name"], "kicker": f"ZUCKER PRO {kat['pro'].upper()}",
                   "gross": f"{wuerfel} Würfel", "sub": top["name"], "sub2": f"= {_z(g_portion, 0)} g Zucker",
                   "farbe": "gold"}
        zweit = liste[1]
        liste_text = (f"Ich habe die {len(liste)} beliebtesten {kat['name']} in Deutschland verglichen. Platz eins beim "
                      f"Zucker: {top['name']}, mit {_z(top['zucker'])} Gramm pro 100 {e_lang}. Dahinter {zweit['name']} "
                      f"mit {_z(zweit['zucker'])} Gramm. Und am wenigsten? {low['name']}, mit nur {_z(low['zucker'])} "
                      f"Gramm.")
        liste_titel, einheit_wert = f"Zucker pro 100 {kat['e']}", "g"
        frage = ("Welches Produkt hat dich am meisten überrascht? Schreib es in die Kommentare.", "Hättest du das gedacht?")
        titel = [f"{wuerfel} Würfel Zucker in {kat['in']} {top['name']}? 😳", f"{kat['name']} im Zucker-Check",
                 "Hättest du das gedacht? 🍬"]
        tags = ["ernährung", "zucker", _tag(kat["name"]), _tag(top["name"].split()[0]), "lebensmittel", "foodcheck",
                "wissen", "fyp"]
    zeilen = [{"label": p["name"], "wert": max(p["wert"], 0.05), "text": f"{_z(p['wert'])} {einheit_wert}",
               "markiert": p is top, "farbe": "gold" if p is top and kat["art"] == "zucker" else "green"} for p in liste]
    karten = [{"label": "Kalorien", "wert": f"{_z(top['kcal'], 0)} kcal"},
              {"label": "Zucker", "wert": f"{_z(top['zucker'])} g", "farbe": "gold"},
              {"label": "Eiweiß", "wert": f"{_z(top['eiweiss'])} g", "farbe": "green"}]
    if top.get("fett") is not None:
        karten.append({"label": "Fett", "wert": f"{_z(top['fett'])} g"})
    if top.get("ns"):
        karten.append({"label": "Nutri-Score", "wert": top["ns"],
                       "farbe": "green" if top["ns"] in "AB" else "gold" if top["ns"] == "C" else "red"})
    detail = (f"Schauen wir genauer hin. {top['name']}, pro 100 {e_lang}: {_z(top['kcal'], 0)} Kilokalorien. "
              f"{_z(top['zucker'])} Gramm Zucker. Und {_z(top['eiweiss'])} Gramm Eiweiß."
              + (f" Der Nutri-Score: {top['ns']}." if top.get("ns") else ""))
    # Vergleichs-Szene: WHO-Empfehlung (nur wo sinnvoll) oder Faktor bestes/schlechtestes Produkt
    if kat["art"] == "zucker" and kat["who"]:
        anteil = g_portion / 50
        info = {"titel": "Zum Vergleich", "unter": "WHO-Empfehlung für Erwachsene", "gross": f"{_z(anteil * 100, 0)} %",
                "farbe": "red" if anteil >= 1 else "gold",
                "text": f"Die WHO empfiehlt höchstens 50 g freien Zucker pro Tag, besser unter 25 g. {kat['pro']} "
                        f"{top['name']}: {_z(g_portion, 0)} g.",
                "balken": {"anteil": anteil, "label": f"{_z(g_portion, 0)} g von 50 g"}}
        info_text = (f"Zum Vergleich. Die WHO empfiehlt Erwachsenen höchstens 50 Gramm freien Zucker am Tag. Besser sogar "
                     f"unter 25. {kat.get('nom', kat['pro'])} {top['name']} liefert {_z(g_portion, 0)} Gramm. Das sind "
                     f"{_z(anteil * 100, 0)} Prozent der Tagesgrenze. Mein Tipp: Achte auf der Packung auf die Zeile "
                     f"davon Zucker.")
    else:
        faktor = top["wert"] / max(low["wert"], 0.1)
        info = {"titel": "Der Unterschied", "unter": f"{top['name']} vs. {low['name']}", "gross": f"{_z(faktor)}×",
                "farbe": "gold", "text": f"{top['name']} hat {_z(faktor)}-mal so viel "
                                         f"{'Eiweiß pro Kalorie' if kat['art'] == 'protein' else 'Zucker'} wie {low['name']}."}
        info_text = (f"Der Unterschied ist riesig. {top['name']} hat {_z(faktor)} mal so viel "
                     f"{'Eiweiß pro Kalorie' if kat['art'] == 'protein' else 'Zucker'} wie {low['name']}."
                     + (" Bei Joghurt zählt dabei auch der natürliche Milchzucker mit." if kat["tag"] == "yogurts" else ""))
    szenen = [
        {"name": "titel", "text": hook, "daten": titel_d},
        {"name": "liste", "text": liste_text, "daten": {"titel": f"{kat['name']}: {liste_titel}",
                                                        "unter": "Die beliebtesten Produkte in Deutschland", "zeilen": zeilen}},
        {"name": "fakten", "text": detail, "daten": {"titel": top["name"], "unter": f"pro 100 {kat['e']}", "karten": karten}},
        {"name": "info", "text": info_text, "daten": info},
        {"name": "frage", "text": _outro(frage[0], tag_nr), "daten": _frage_daten(frage[1], tag_nr, kat)},
    ]
    return {"id": f"{kat['tag']}-{date.today().isoformat()}", "szenen": szenen, "titel": titel, "tags": tags,
            "frage": frage[1], "name": f"{kat['name']} · {'Protein' if kat['art'] == 'protein' else 'Zucker'}-Check"}


def video_plan(erledigt, tag_nr, daten_quelle=None):
    """Kategorie des Tages wählen (keine Wiederholung innerhalb von 10 Tagen) und Video bauen."""
    grenze = (date.today() - timedelta(days=10)).isoformat()
    kuerzlich = {e.rsplit("-", 3)[0] for e in erledigt if e[-10:] >= grenze}
    start = date.today().toordinal() % len(KATEGORIEN)
    reihe = KATEGORIEN[start:] + KATEGORIEN[:start]
    reihe = [k for k in reihe if k["tag"] not in kuerzlich] + [k for k in reihe if k["tag"] in kuerzlich]
    ausfaelle = 0
    for kat in reihe[:5]:
        try:
            produkte = (daten_quelle or laden)(kat)
        except Exception as e:
            print(f"  Open Food Facts ({kat['tag']}): {str(e)[:70]}")
            ausfaelle += 1
            if ausfaelle >= 2:          # Dienst ist gerade weg - nicht ewig weiterprobieren
                break
            continue
        plan = video(kat, produkte, tag_nr)
        if plan:
            return plan
        print(f"  {kat['name']}: zu wenige vollständige Produkte, nächste Kategorie.")
    return None


# ---------------------------------------------------------------- Demo (erfundene Produkte)

def demo_quelle(kat):
    rnd = random.Random(kat["tag"])
    marken = ["Sprudelix", "Frischhof", "Nordquell", "Bergkraft", "Sonnwerk", "Alpaca", "Morgenrot"]
    out = []
    for i, m in enumerate(marken[:6]):
        if kat["art"] == "protein":
            kcal, eiw, zuck = rnd.uniform(330, 420), rnd.uniform(18, 36), rnd.uniform(1, 25)
        else:
            kcal, zuck, eiw = rnd.uniform(30, 60), rnd.uniform(4, 13), rnd.uniform(0, 1)
        out.append({"name": f"{m} {kat['name'][:-1] if kat['name'].endswith('s') else kat['name']} Classic",
                    "kcal": kcal, "zucker": zuck, "eiweiss": eiw, "fett": rnd.uniform(0, 10), "ns": "ABCDE"[i % 5]})
    return out
