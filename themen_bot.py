"""Themen-Bot: tägliche Videos zu weiteren Themen (nur Deutsch), im selben Stil wie die Aktien-Videos.

  python themen_bot.py                     alle aktiven Themen (aktien_config.yaml -> themen:)
  python themen_bot.py --thema bundesliga  nur ein Thema
  python themen_bot.py --demo              Testvideos mit erfundenen Daten (ohne Internet)

Neues Thema? Eine Datei thema_<name>.py nach dem Muster von thema_ernaehrung.py anlegen und unten in
THEMEN eintragen. Die Szenen (titel, liste, ergebnisse, tabelle, fakten, info, frage) gibt es schon.
"""
import argparse
import copy
import os
from datetime import date, datetime

import thema_bundesliga
import thema_ernaehrung
import video
import video_bot
from themen_szenen import ThemaSzenen

THEMEN = {"bundesliga": thema_bundesliga, "ernaehrung": thema_ernaehrung}
HINWEIS = {"bundesliga": "Daten: OpenLigaDB, ohne Gewähr.",
           "ernaehrung": "Werte: Open Food Facts (Herstellerangaben). Keine Ernährungsberatung."}
VERLAUF = os.path.join(video_bot.SPEICHER, "themen_verlauf.json")


def serien_tag(name):
    pfad = os.path.join(video_bot.SPEICHER, f"serie_{name}.json")
    s = video_bot.json_laden(pfad, {"tag": 0, "datum": ""})
    heute = date.today().isoformat()
    if s.get("datum") != heute:
        s = {"tag": int(s.get("tag", 0)) + 1, "datum": heute}
        video_bot.json_speichern(pfad, s)
    return s["tag"]


def plan_fuer(name, erledigt, tag_nr, demo):
    mod = THEMEN[name]
    if name == "bundesliga":
        daten = mod.demo_daten("rueckblick") if demo else mod.laden()
        return mod.video_plan(daten, erledigt, tag_nr)
    if name == "ernaehrung":
        return mod.video_plan(erledigt, tag_nr, mod.demo_quelle if demo else None)
    return mod.video_plan(erledigt, tag_nr)


def erstellen(name, plan, tag_nr, vcfg, demo, tcfg=None):
    mod = THEMEN[name]
    os.makedirs("videos", exist_ok=True)
    D = {"lang": "de", "brand": mod.BRAND, "disclaimer": mod.DISCLAIMER, "quellen": mod.QUELLEN, "tag_nr": tag_nr,
         "modus": "thema", "vorschau_szene": plan["szenen"][0]}
    D["szenen_obj"] = ThemaSzenen(D)
    datei = f"{date.today():%Y-%m-%d}_{name}_de"
    mp4, jpg, txt = (os.path.join("videos", datei + e) for e in (".mp4", ".jpg", ".txt"))
    print(f"\nThema {name}: {plan['name']}")
    for s in plan["szenen"]:
        print(f"    ({s['name']}) {s['text']}")
    eigen = (tcfg or {}).get(name) or {}
    lcfg = dict(vcfg, stimme=eigen.get("stimme") or (vcfg.get("stimmen") or {}).get("de"))
    if eigen.get("tempo"):
        lcfg["tempo"] = eigen["tempo"]
    dauer, ton = video.render(D, copy.deepcopy(plan["szenen"]), lcfg, mp4)
    video.vorschaubild(D, jpg)
    titel = [f"Tag {tag_nr}: {t}" for t in plan["titel"]] if tag_nr else plan["titel"]
    hinweis = f"{plan['frage']} 👇\n{HINWEIS.get(name, '')}"
    text = f"{titel[0]}\n\n{hinweis}\n\n" + " ".join("#" + t for t in plan["tags"])
    with open(txt, "w", encoding="utf-8") as f:
        f.write(text + "\n\n---\n" + "\n".join(s["text"] for s in plan["szenen"]))
    print(f"  fertig: {mp4} ({dauer:.1f} s, Ton: {'ja' if ton else 'NEIN'})")
    return {"id": datei, "datum": date.today().isoformat(), "ticker": {"bundesliga": "Bundesliga",
            "ernaehrung": "Ernährung"}.get(name, name), "name": plan["name"], "thema": name, "sprache": "de",
            "mp4": datei + ".mp4", "bild": datei + ".jpg", "text": text, "titel": titel, "tags": plan["tags"],
            "hinweis": hinweis, "frage": plan["frage"], "winkel": plan["id"], "dauer": round(dauer, 1), "ton": ton,
            "demo": demo, "erstellt": datetime.now().isoformat(timespec="seconds")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thema", default="alle", help="alle, " + ", ".join(THEMEN))
    ap.add_argument("--demo", action="store_true", help="Testvideos mit erfundenen Daten")
    args = ap.parse_args()

    import aktien
    cfg = aktien.load_config()
    vcfg = {**video_bot.DEFAULT_VIDEO, **(cfg.get("video") or {})}
    vcfg["stimmen"] = {**video_bot.DEFAULT_VIDEO["stimmen"], **(vcfg.get("stimmen") or {})}
    tcfg = cfg.get("themen") or {}
    namen = list(THEMEN) if args.thema == "alle" else [args.thema]
    verlauf = video_bot.json_laden(VERLAUF, {})
    neu = []
    for name in namen:
        if name not in THEMEN:
            print(f"Unbekanntes Thema: {name}")
            continue
        if not args.demo and not (tcfg.get(name) or {}).get("aktiv", True):
            print(f"Thema {name} ist ausgeschaltet.")
            continue
        try:
            erledigt = set((verlauf.get(name) or {}).keys())
            tag_nr = 7 if args.demo else (serien_tag(name) if (tcfg.get(name) or {}).get("serie", True) else None)
            plan = plan_fuer(name, erledigt, tag_nr, args.demo)
            if not plan:
                print(f"Thema {name}: heute kein passendes Video (keine Daten oder alles schon gemacht).")
                continue
            neu.append(erstellen(name, plan, tag_nr, vcfg, args.demo, tcfg))
            if not args.demo:
                verlauf.setdefault(name, {})[plan["id"]] = date.today().isoformat()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Thema {name}: fehlgeschlagen ({e})")
    if not args.demo:
        video_bot.json_speichern(VERLAUF, verlauf)
    if neu:
        video_bot.archiv_aktualisieren(neu, vcfg, demo=args.demo)


if __name__ == "__main__":
    main()
