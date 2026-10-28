"""Themen-Bot: tägliche Videos zu weiteren Themen, im selben Stil-System wie die Aktien-Videos.

  python themen_bot.py                     alle aktiven Themen (aktien_config.yaml -> themen:)
  python themen_bot.py --thema mindset     nur ein Thema
  python themen_bot.py --demo              Testvideos mit erfundenen Daten / Beispiel-Skripten

Neues Thema? Eine Datei thema_<name>.py nach dem Muster der vorhandenen anlegen und unten in THEMEN eintragen.
"""
import argparse
import copy
import os
from datetime import date, datetime

import mindset_szenen
import thema_bundesliga
import thema_ernaehrung
import thema_mindset
import video
import video_bot
from themen_szenen import ThemaSzenen

THEMEN = {"bundesliga": thema_bundesliga, "ernaehrung": thema_ernaehrung, "mindset": thema_mindset}
ANZEIGE = {"bundesliga": "Bundesliga", "ernaehrung": "Ernährung", "mindset": "Mindset"}
HINWEIS = {"bundesliga": {"de": "Daten: OpenLigaDB, ohne Gewähr."},
           "ernaehrung": {"de": "Werte: Open Food Facts (Herstellerangaben). Keine Ernährungsberatung."},
           "mindset": {"de": "Keine Finanzberatung, nur ein Denkanstoß.", "en": "Not financial advice, just food for thought."}}
VERLAUF = os.path.join(video_bot.SPEICHER, "themen_verlauf.json")


def serien_tag(name):
    pfad = os.path.join(video_bot.SPEICHER, f"serie_{name}.json")
    s = video_bot.json_laden(pfad, {"tag": 0, "datum": ""})
    heute = date.today().isoformat()
    if s.get("datum") != heute:
        s = {"tag": int(s.get("tag", 0)) + 1, "datum": heute}
        video_bot.json_speichern(pfad, s)
    return s["tag"]


def plan_fuer(name, erledigt, tag_nr, demo, tc):
    mod = THEMEN[name]
    if name == "bundesliga":
        daten = mod.demo_daten("rueckblick") if demo else mod.laden()
        return mod.video_plan(daten, erledigt, tag_nr)
    if name == "ernaehrung":
        return mod.video_plan(erledigt, tag_nr, mod.demo_quelle if demo else None)
    if name == "mindset":
        return mod.video_plan(erledigt, tag_nr, tuple(tc.get("sprachen") or ("de", "en")), demo)
    return mod.video_plan(erledigt, tag_nr)


def fassungen(plan):
    """Einheitlich: {sprache: {szenen, titel, tags, frage}}"""
    if "sprachen" in plan:
        return plan["sprachen"]
    return {"de": {k: plan[k] for k in ("szenen", "titel", "tags", "frage")}}


def stimm_cfg(vcfg, tc, lang):
    """Stimme je Thema und Sprache: anbieter edge (gratis) oder elevenlabs."""
    lcfg = dict(vcfg)
    lcfg["anbieter"] = tc.get("anbieter", "edge")
    st = tc.get("stimme")
    if isinstance(st, dict):
        st = st.get(lang)
    lcfg["stimme"] = st or (vcfg.get("stimmen") or {}).get(lang)
    el = tc.get("eleven_stimme")
    if isinstance(el, dict):
        el = el.get(lang)
    lcfg["eleven_stimme"] = el or "brian"
    for k in ("tempo", "eleven_tempo", "eleven_modell", "eleven_einstellungen"):
        if tc.get(k) is not None:
            lcfg[k] = tc[k]
    return lcfg


def erstellen(name, plan, tag_nr, vcfg, demo, tc):
    mod = THEMEN[name]
    os.makedirs("videos", exist_ok=True)
    eintraege = []
    for lang, fs in fassungen(plan).items():
        D = {"lang": lang, "tag_nr": tag_nr, "modus": "thema", "vorschau_szene": fs["szenen"][0],
             "brand": mod.BRAND[lang] if isinstance(mod.BRAND, dict) else mod.BRAND,
             "disclaimer": mod.DISCLAIMER[lang] if isinstance(mod.DISCLAIMER, dict) else mod.DISCLAIMER,
             "quellen": getattr(mod, "QUELLEN", "")}
        if name == "mindset":
            D.update(hintergrund=mindset_szenen.hintergrund, rahmen_stil="minimal", untertitel_stil="ruhig")
            D["szenen_obj"] = mindset_szenen.MindsetSzenen(D)
        else:
            D["szenen_obj"] = ThemaSzenen(D)
        datei = f"{date.today():%Y-%m-%d}_{name}_{lang}"
        mp4, jpg, txt = (os.path.join("videos", datei + e) for e in (".mp4", ".jpg", ".txt"))
        print(f"\nThema {name} [{lang}]: {plan['name']}")
        for s in fs["szenen"]:
            print(f"    ({s['name']}) {s['text']}")
        dauer, ton = video.render(D, copy.deepcopy(fs["szenen"]), stimm_cfg(vcfg, tc, lang), mp4)
        video.vorschaubild(D, jpg)
        wort = ("Tag" if lang == "de" else "Day")
        titel = [f"{wort} {tag_nr}: {t}" for t in fs["titel"]] if tag_nr else fs["titel"]
        hinweis = f"{fs['frage']} 👇\n{HINWEIS.get(name, {}).get(lang, '')}"
        text = f"{titel[0]}\n\n{hinweis}\n\n" + " ".join("#" + t for t in fs["tags"])
        with open(txt, "w", encoding="utf-8") as f:
            f.write(text + "\n\n---\n" + "\n".join(s["text"] for s in fs["szenen"]))
        print(f"  fertig: {mp4} ({dauer:.1f} s, Ton: {'ja' if ton else 'NEIN'})")
        eintraege.append({"id": datei, "datum": date.today().isoformat(), "ticker": ANZEIGE.get(name, name),
                          "name": fs["titel"][0] if name == "mindset" else plan["name"], "thema": name, "sprache": lang,
                          "mp4": datei + ".mp4", "bild": datei + ".jpg", "text": text, "titel": titel, "tags": fs["tags"],
                          "hinweis": hinweis, "frage": fs["frage"], "winkel": plan["id"], "dauer": round(dauer, 1),
                          "ton": ton, "demo": demo, "erstellt": datetime.now().isoformat(timespec="seconds")})
    return eintraege


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
        tc = tcfg.get(name) or {}
        if not args.demo and not tc.get("aktiv", name != "mindset"):
            print(f"Thema {name} ist ausgeschaltet.")
            continue
        try:
            erledigt = set((verlauf.get(name) or {}).keys())
            tag_nr = 7 if args.demo else (serien_tag(name) if tc.get("serie", True) else None)
            plan = plan_fuer(name, erledigt, tag_nr, args.demo, tc)
            if not plan:
                print(f"Thema {name}: heute kein passendes Video (keine Daten oder alles schon gemacht).")
                continue
            neu += erstellen(name, plan, tag_nr, vcfg, args.demo, tc)
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
