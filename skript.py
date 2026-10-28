"""Sprechtext für ein Video, auf Deutsch und Englisch.

Aufbau: Hook (datengetrieben, wählt den spannendsten Aufhänger) -> Eckdaten -> Chart ->
[Insiderkäufe] -> [Stimmung im Netz] -> Scanner-Score -> Dafür & dagegen -> offene Frage.
Szenen in eckigen Klammern gibt es nur, wenn Daten da sind.

Beide Sprachen ziehen dieselbe Variante (gleicher Zufallsstart), dadurch sind die Videos inhaltlich
identisch. Eigene Formulierungen: einfach weitere Varianten in die Listen schreiben, aber in beiden
Sprachen gleich viele, damit die Fassungen zusammenpassen.
"""
import random
from datetime import date

from sprache import LABELS, L, branche, datum, geld, kurs, prozent, rolle, warnung, zahl

ZAHLWORT = {"de": ["", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn"],
            "en": ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]}

T = {
    "de": {
        "hook": {
            "insider": [
                "{wer} {hat} gerade {summe} aus eigener Tasche in {kn} investiert. Was weiß das Management, "
                "was der Markt noch nicht eingepreist hat?",
                "Insider verkaufen aus hundert Gründen. Kaufen tun sie aus genau einem. Bei {kn} haben sie gerade "
                "für {summe} zugeschlagen.",
            ],
            "still": [
                "Bei {kn} kaufen die Insider für {summe}, aber auf Reddit spricht kaum jemand darüber. "
                "Genau diese Lücke finde ich spannend.",
                "{summe} Insiderkäufe bei {kn}, und im Netz herrscht fast Funkstille. Entweder übersieht der Markt "
                "etwas, oder die Insider irren sich.",
            ],
            "dip": [
                "{kn} notiert {dd} unter dem Jahreshoch, obwohl die Fundamentaldaten zu den stärksten in meinem "
                "Scanner gehören. Übertreibung nach unten oder berechtigte Skepsis?",
                "Minus {dd} vom Hoch, aber die Zahlen sehen solide aus. Bei {kn} erzählen Kurs und Fundamentaldaten "
                "gerade zwei verschiedene Geschichten.",
            ],
            "upside": [
                "{n_an} Analysten sehen bei {kn} im Schnitt {pot} Kurspotenzial. Die eigentliche Frage ist: "
                "Warum glaubt der Markt ihnen nicht?",
                "Laut Analysten ist {kn} rund {pot} unterbewertet. Schauen wir, ob die Daten das stützen.",
            ],
            "hype": [
                "{kn} geht auf Reddit gerade steil: {mentions} Erwähnungen in 24 Stunden. Steckt Substanz dahinter "
                "oder nur Lärm?",
                "Plötzlich reden alle über {kn}. Hier sind die Zahlen hinter dem Hype.",
            ],
            "momentum": [
                "Plus {r12} in zwölf Monaten. Ist {kn} jetzt zu teuer, oder fängt die Geschichte gerade erst an?",
                "{kn} hat in einem Jahr {r12} zugelegt. Wer jetzt einsteigen will, sollte diese Zahlen kennen.",
            ],
            "dividend": [
                "{div} Dividende und trotzdem eine solide Bilanz? Bei {kn} lohnt sich ein genauer Blick.",
                "Hohe Dividenden sind oft eine Falle. {kn} zahlt {div}. Schauen wir, ob das nachhaltig ist.",
            ],
            "top": [
                "Von {n} Aktien landet {kn} in meinem Scanner gerade auf Platz {rang}. Hier ist, warum, und wo "
                "der Haken liegen könnte.",
                "Platz {rang} von {n}: Laut meinem Scanner gehört {kn} zu den stärksten Aktien am Markt. "
                "Aber hält das einer genaueren Prüfung stand?",
            ],
            "score": [
                "{kn} im Daten-Check: {score} von 100 Punkten in meinem Scanner. Was steckt hinter der Zahl?",
                "Heute auf dem Prüfstand: {kn}. Acht Kriterien, ein klares Bild.",
            ],
        },
        "intro": ["Die Eckdaten: {kn} aus der Branche {branche}, Börsenwert rund {mcap}, Kurs aktuell {kurs}. "
                  "{rendite} {kgv}"],
        "rendite_plus": "Auf Jahressicht steht ein Plus von {x}.",
        "rendite_minus": "Auf Jahressicht ein Minus von {x}.",
        "rendite_flat": "Auf Jahressicht praktisch unverändert.",
        "kgv": "Das erwartete KGV liegt bei {x}.",
        "chart_ins": ["Die letzten {m} Monate, jeder grüne Punkt ist ein Insiderkauf. {seit}"],
        "seit_plus": "Seit dem ersten Kauf liegt die Aktie {x} im Plus.",
        "seit_minus": "Seit dem ersten Kauf ist sie {x} gefallen. Die Insider sitzen also selbst auf Verlusten "
                      "und kaufen trotzdem.",
        "seit_flat": "Seit dem ersten Kauf hat sich der Kurs kaum bewegt.",
        "chart": ["Die letzten {m} Monate im Überblick. {hoch} {trend}"],
        "hoch_weg": "Vom Hoch bei {h} ist die Aktie {x} entfernt.",
        "hoch_nah": "Die Aktie notiert nahe ihrem Hoch.",
        "trend_up": "Sie liegt {x} über dem 200-Tage-Durchschnitt, der langfristige Trend ist also intakt.",
        "trend_down": "Sie notiert {x} unter dem 200-Tage-Durchschnitt, der Trend ist angeschlagen.",
        "trend_flat": "Sie liegt genau am 200-Tage-Durchschnitt, einer wichtigen Marke für viele Anleger.",
        "insider": ["Der größte Einzelkauf: {rolle} {name} mit {wert} am {datum}. {cluster} Und wichtig: Das sind "
                    "Käufe am offenen Markt, keine geschenkten Aktienoptionen."],
        "cluster_n": "Insgesamt haben {n} verschiedene Insider innerhalb von {t} Tagen gekauft.",
        "cluster_k": "Insgesamt {k} Käufe in {t} Tagen.",
        "netz_start": ["Und was sagt das Netz?", "Und die Stimmung im Netz?", "Wer redet eigentlich darüber?"],
        "rd_null": "Auf Reddit praktisch kein Thema.",
        "rd_wenig": "Auf Reddit kaum ein Thema, nur {m} Erwähnungen.",
        "rd_neu": "Reddit: plötzlich {m} Erwähnungen in 24 Stunden, vorher fast keine.",
        "rd": "Reddit: {m} Erwähnungen in 24 Stunden{v}.",
        "rd_mehr": ", {x} mehr als am Vortag", "rd_weniger": ", {x} weniger als am Vortag",
        "st_bull": "StockTwits: {p} bullisch.", "st_bear": "Auf StockTwits überwiegen die Skeptiker, nur {p} bullisch.",
        "nw_pos": "Die Schlagzeilen sind überwiegend positiv.", "nw_neg": "Die Schlagzeilen sind eher negativ.",
        "nw_mix": "Die Schlagzeilen sind gemischt.", "hype": "Hype-Index: {i} von 100.",
        "scanner": ["Mein Scanner vergleicht {n} Aktien nach acht Kriterien. {kn} kommt auf {score} von 100 Punkten, "
                    "das ist Platz {rang}. {st}"],
        "stark": "Am stärksten: {x}.", "schwach1": "Die Schwachstelle: {x}.", "schwach": "Die Schwachstellen: {x}.",
        "pc": ["Was dafür spricht: {pro}. Was dagegen spricht: {contra}."],
        "outro": ["Wie immer: keine Anlageberatung, nur Daten. {haelt}{cta} Und jetzt du: {frage}"],
        "haelt": "Offenlegung: Ich besitze die Aktie selbst. ",
        "cta_liste": "Morgen nehme ich mir die nächste Aktie aus meinem Scanner vor.",
        "cta_insider": "Folg mir für die nächsten Insiderkäufe.",
        "und": "und",
    },
    "en": {
        "hook": {
            "insider": [
                "{wer} just put {summe} of their own money into {kn}. So what does management know that the market "
                "hasn't priced in yet?",
                "Insiders sell for a hundred reasons. They buy for exactly one. And at {kn}, they just bought {summe} "
                "worth of stock.",
            ],
            "still": [
                "Insiders are buying {summe} worth of {kn}, yet almost nobody on Reddit is talking about it. "
                "That gap is exactly what interests me.",
                "{summe} in insider buying at {kn}, and online it's almost radio silence. Either the market is missing "
                "something, or the insiders are wrong.",
            ],
            "dip": [
                "{kn} is trading {dd} below its 52-week high, even though its fundamentals rank among the strongest in "
                "my scanner. Overreaction or justified skepticism?",
                "Down {dd} from the high, yet the numbers look solid. At {kn}, the price and the fundamentals are "
                "telling two different stories.",
            ],
            "upside": [
                "{n_an} analysts see an average upside of {pot} for {kn}. The real question is: why isn't the market "
                "buying it?",
                "According to analysts, {kn} is about {pot} undervalued. Let's see whether the data backs that up.",
            ],
            "hype": [
                "{kn} is blowing up on Reddit right now: {mentions} mentions in 24 hours. Is there substance behind it, "
                "or just noise?",
                "Suddenly everyone is talking about {kn}. Here are the numbers behind the hype.",
            ],
            "momentum": [
                "Up {r12} in twelve months. Is {kn} too expensive now, or is the story just getting started?",
                "{kn} has gained {r12} in a year. If you're thinking of buying now, you should know these numbers.",
            ],
            "dividend": [
                "A {div} dividend yield and still a solid balance sheet? {kn} deserves a closer look.",
                "High dividends are often a trap. {kn} pays {div}. Let's see if that's sustainable.",
            ],
            "top": [
                "Out of {n} stocks, {kn} currently ranks number {rang} in my scanner. Here's why, and where the catch "
                "might be.",
                "Rank {rang} out of {n}: according to my scanner, {kn} is one of the strongest stocks out there. "
                "But does that hold up under scrutiny?",
            ],
            "score": [
                "{kn} under the microscope: {score} out of 100 in my scanner. What's behind that number?",
                "Today on the test bench: {kn}. Eight criteria, one clear picture.",
            ],
        },
        "intro": ["The basics: {kn}, {branche} sector, market cap around {mcap}, currently trading at {kurs}. "
                  "{rendite} {kgv}"],
        "rendite_plus": "Over the past year, it's up {x}.",
        "rendite_minus": "Over the past year, it's down {x}.",
        "rendite_flat": "Over the past year, it's roughly flat.",
        "kgv": "The forward P/E is {x}.",
        "chart_ins": ["The last {m} months, and every green dot is an insider buy. {seit}"],
        "seit_plus": "Since the first purchase, the stock is up {x}.",
        "seit_minus": "Since the first purchase, it's down {x}. So the insiders are sitting on losses themselves, "
                      "and still buying.",
        "seit_flat": "Since the first purchase, the price has barely moved.",
        "chart": ["Here are the last {m} months at a glance. {hoch} {trend}"],
        "hoch_weg": "It's {x} below its high of {h}.",
        "hoch_nah": "The stock is trading near its high.",
        "trend_up": "It's {x} above its 200-day average, so the long-term trend is intact.",
        "trend_down": "It's {x} below its 200-day average, so the trend is damaged.",
        "trend_flat": "It's sitting right at its 200-day average, a key level for many investors.",
        "insider": ["The largest single purchase: {rolle} {name}, {wert} on {datum}. {cluster} And importantly, these "
                    "are open-market purchases, not free stock options."],
        "cluster_n": "In total, {n} different insiders bought within {t} days.",
        "cluster_k": "That's {k} purchases in {t} days.",
        "netz_start": ["So what's the internet saying?", "And the mood online?", "Who's actually talking about it?"],
        "rd_null": "On Reddit, practically no one is talking about it.",
        "rd_wenig": "On Reddit, barely a topic, just {m} mentions.",
        "rd_neu": "Reddit: suddenly {m} mentions in 24 hours, almost none before.",
        "rd": "Reddit: {m} mentions in 24 hours{v}.",
        "rd_mehr": ", up {x} from yesterday", "rd_weniger": ", down {x} from yesterday",
        "st_bull": "StockTwits: {p} bullish.", "st_bear": "On StockTwits the skeptics dominate, only {p} bullish.",
        "nw_pos": "Headlines are mostly positive.", "nw_neg": "Headlines lean negative.",
        "nw_mix": "Headlines are mixed.", "hype": "Hype index: {i} out of 100.",
        "scanner": ["My scanner ranks {n} stocks on eight criteria. {kn} scores {score} out of 100, that's rank "
                    "{rang}. {st}"],
        "stark": "Strongest areas: {x}.", "schwach1": "The weak spot: {x}.", "schwach": "Weak spots: {x}.",
        "pc": ["The bull case: {pro}. The bear case: {contra}."],
        "outro": ["As always: not financial advice, just data. {haelt}{cta} Now over to you: {frage}"],
        "haelt": "Disclosure: I own this stock myself. ",
        "cta_liste": "Tomorrow I'll break down the next stock from my scanner.",
        "cta_insider": "Follow for the next insider buys.",
        "und": "and",
    },
}

# Offene Fragen am Ende: (gesprochen, kurz für den Bildschirm)
FRAGEN = {
    "de": {
        "insider": ("Wissen die Insider mehr als der Markt, oder kaufen sie einfach zu früh? Schreib's in die "
                    "Kommentare.", "Wissen die Insider mehr?"),
        "dip": ("Schnäppchen oder Value-Falle: Was meinst du?", "Schnäppchen oder Falle?"),
        "upside": ("Haben die Analysten recht, oder ist das Kursziel zu optimistisch? Ich bin gespannt.",
                   "Haben die Analysten recht?"),
        "hype": ("Substanz oder nur Hype: Wie siehst du das?", "Substanz oder Hype?"),
        "momentum": ("Würdest du jetzt noch einsteigen, oder auf einen Rücksetzer warten?", "Einsteigen oder warten?"),
        "dividend": ("Ist diese Dividende sicher, oder zu schön, um wahr zu sein?", "Sicher oder zu schön?"),
        "top": ("Was übersieht mein Scanner bei {kn}? Schreib es in die Kommentare.", "Was übersehe ich?"),
    },
    "en": {
        "insider": ("Do the insiders know more than the market, or are they just early? Tell me in the comments.",
                    "Do insiders know more?"),
        "dip": ("Bargain or value trap? What do you think?", "Bargain or value trap?"),
        "upside": ("Are the analysts right, or is that target too optimistic? Let me know.", "Are the analysts right?"),
        "hype": ("Substance or just hype? What's your take?", "Substance or hype?"),
        "momentum": ("Would you still buy here, or wait for a pullback?", "Buy now or wait?"),
        "dividend": ("Is this dividend safe, or too good to be true?", "Safe or too good to be true?"),
        "top": ("What is my scanner missing on {kn}? Drop it in the comments.", "What am I missing?"),
    },
}
FRAGE_VON = {"insider": "insider", "still": "insider", "dip": "dip", "upside": "upside", "hype": "hype",
             "momentum": "momentum", "dividend": "dividend", "top": "top", "score": "top"}


# ---------------------------------------------------------------- Helfer

def kurzname(name):
    """'Apple Inc.' -> 'Apple' (klingt natürlicher)."""
    for suf in [", Inc.", " Inc.", " Incorporated", " Corporation", " Corp.", " Company", " Co.", " plc", " PLC",
                " Holdings", " Group", " Aktiengesellschaft", " AG", " SE", " N.V.", " Ltd.", ", Inc", " Inc",
                " & Co. KGaA", " KGaA"]:
        if name.endswith(suf):
            name = name[: -len(suf)]
    return name.strip(" ,")


def _f(x):
    try:
        x = float(x)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def aufzaehlung(teile, lang):
    teile = [t for t in teile if t]
    if len(teile) <= 1:
        return "".join(teile)
    return ", ".join(teile[:-1]) + f" {T[lang]['und']} " + teile[-1]


def _pick(lst, seed, key):
    """Gleicher Index in allen Sprachen, damit DE und EN dasselbe Video sind."""
    return lst[int(random.Random(f"{seed}|{key}").random() * len(lst))]


def kategorien_sortiert(a):
    from bewertung import KATEGORIEN
    return sorted(KATEGORIEN, key=lambda c: -(_f(a.get("k_" + c)) or 50))


# ---------------------------------------------------------------- Aufhänger (Hook-Winkel)

def winkel(a, ins, rad):
    """Welche Geschichte ist heute die stärkste? Gibt den Schlüssel des Aufhängers zurück."""
    kandidaten = [("score", 40)]
    rd = (rad or {}).get("reddit")
    if ins and ins.get("kaeufe"):
        still = rd is not None and rd["mentions"] < 10
        kandidaten.append(("still" if still else "insider", 60 + ins.get("insider_score", 0) / 2))
    dd, q = _f(a.get("_abstand_hoch")), _f(a.get("k_qualitaet")) or 0
    if dd is not None and dd <= -0.25 and (q >= 60 or a["score"] >= 60):
        kandidaten.append(("dip", 55 + abs(dd) * 50))
    pot, n_an = _f(a.get("kursziel_potenzial")), int(_f(a.get("numberOfAnalystOpinions")) or 0)
    if pot is not None and pot >= 0.25 and n_an >= 8:
        kandidaten.append(("upside", 50 + pot * 50))
    if rd and rd["mentions"] >= 50 and rd["mentions"] >= 1.5 * max(rd["mentions_24h"], 1):
        kandidaten.append(("hype", 52 + min(20, rd["mentions"] / 20)))
    r12 = _f(a.get("rendite_12m"))
    if r12 is not None and r12 >= 0.4:
        kandidaten.append(("momentum", 45 + min(25, r12 * 20)))
    div, pay = _f(a.get("div_rendite")) or 0, _f(a.get("payoutRatio"))
    if div >= 0.04 and (pay is None or pay < 0.9):
        kandidaten.append(("dividend", 45 + div * 300))
    if int(a.get("rang") or 999) <= 10:
        kandidaten.append(("top", 46 + (10 - int(a["rang"]))))
    return max(kandidaten, key=lambda k: k[1])[0]


def hook_bild(key, a, ins, rad, lang, n_aktien):
    """Was im Hook groß auf dem Bildschirm steht."""
    de = lang == "de"
    if key in ("insider", "still"):
        iw = ins.get("waehrung", "USD")
        return {"kicker": "INSIDER KAUFEN" if de else "INSIDERS ARE BUYING", "wert": ins["summe"],
                "fmt": lambda v: geld(v, iw, lang), "farbe": "green", "personen": ins["anzahl_kaeufer"],
                "sub": f"{L(lang, 'tage', t=ins['spanne_tage'])} · {ins['anzahl_kaeufer']} {L(lang, 'kaeufer')}"}
    if key == "dip":
        return {"kicker": "VOM JAHRESHOCH" if de else "FROM 52-WEEK HIGH", "wert": a["_abstand_hoch"],
                "fmt": lambda v: prozent(v, lang), "farbe": "red",
                "sub": f"{L(lang, 'kat')['qualitaet']} {_f(a.get('k_qualitaet')) or 0:.0f}/100"}
    if key == "upside":
        n = int(_f(a.get("numberOfAnalystOpinions")) or 0)
        return {"kicker": "KURSPOTENZIAL" if de else "ANALYST UPSIDE", "wert": a["kursziel_potenzial"],
                "fmt": lambda v: prozent(v, lang), "farbe": "green",
                "sub": f"{n} {'Analysten' if de else 'analysts'}"}
    if key == "hype":
        rd = rad["reddit"]
        ch = (rd["mentions"] - rd["mentions_24h"]) / max(rd["mentions_24h"], 1)
        return {"kicker": "REDDIT-ERWÄHNUNGEN" if de else "REDDIT MENTIONS", "wert": rd["mentions"],
                "fmt": lambda v: f"{v:.0f}", "farbe": "green",
                "sub": f"{prozent(ch, lang)} {'in 24 Std.' if de else 'in 24h'}"}
    if key == "momentum":
        return {"kicker": "12 MONATE" if de else "12 MONTHS", "wert": a["rendite_12m"],
                "fmt": lambda v: prozent(v, lang), "farbe": "green", "sub": f"Score {a['score']:.0f}/100"}
    if key == "dividend":
        pay = _f(a.get("payoutRatio"))
        sub = (f"{'Ausschüttung' if de else 'Payout'} {prozent(pay, lang, vorzeichen=False)}"
               + (" vom Gewinn" if de else " of earnings")) if pay else f"Score {a['score']:.0f}/100"
        return {"kicker": "DIVIDENDENRENDITE" if de else "DIVIDEND YIELD", "wert": a["div_rendite"],
                "fmt": lambda v: (zahl(v * 100, lang, 1) + (" %" if de else "%")), "farbe": "gold", "sub": sub}
    if key == "top":
        return {"kicker": "SCANNER-RANG" if de else "SCANNER RANK", "wert": float(a["rang"]),
                "fmt": lambda v: f"#{max(1, round(v))}", "farbe": "green", "von_oben": True,
                "sub": f"{'von' if de else 'of'} {n_aktien} {'Aktien' if de else 'stocks'}"}
    return {"kicker": "SCANNER-SCORE" if de else "SCANNER SCORE", "wert": a["score"],
            "fmt": lambda v: f"{v:.0f}/100", "farbe": "green", "sub": branche(a.get("branche"), lang)}


# ---------------------------------------------------------------- Dafür & dagegen

def pro_contra(a, ins, rad, lang):
    """Je bis zu 3 Punkte: [(Bildschirm, gesprochen)], nach Gewicht sortiert."""
    de = lang == "de"
    k = lambda c: _f(a.get("k_" + c)) or 50
    pro, contra = [], []
    if ins and ins.get("kaeufe"):
        iw = ins.get("waehrung", "USD")
        pro.append((95, f"Insider kaufen für {geld(ins['summe'], iw, lang)}" if de else
                    f"Insiders bought {geld(ins['summe'], iw, lang)}",
                    f"Insiderkäufe über {geld(ins['summe'], iw, lang, True)}" if de else
                    f"insider buying worth {geld(ins['summe'], iw, lang, True)}"))
    pot, n_an = _f(a.get("kursziel_potenzial")), int(_f(a.get("numberOfAnalystOpinions")) or 0)
    if pot is not None and n_an >= 5:
        if pot >= 0.1:
            pro.append((60 + pot * 100, f"Kursziel {prozent(pot, lang)} ({n_an} Analysten)" if de else
                        f"Price target {prozent(pot, lang)} ({n_an} analysts)",
                        f"{prozent(pot, lang, True)} Kurspotenzial laut Analysten" if de else
                        f"{prozent(pot, lang, True)} upside according to analysts"))
        elif pot < 0:
            contra.append((70, "Kurs über dem Analysten-Ziel" if de else "Price above analyst target",
                           "ein Kurs, der schon über dem Analystenziel liegt" if de else
                           "a price already above the analyst target"))
    om, rg, pe = _f(a.get("operatingMargins")), _f(a.get("revenueGrowth")), _f(a.get("forwardPE"))
    if k("qualitaet") >= 65 and om and om > 0:
        pro.append((k("qualitaet"), f"Operative Marge {prozent(om, lang, vorzeichen=False)}" if de else
                    f"Operating margin {prozent(om, lang, vorzeichen=False)}",
                    f"eine operative Marge von {prozent(om, lang, True)}" if de else
                    f"an operating margin of {prozent(om, lang, True)}"))
    if k("wachstum") >= 65 and rg and rg > 0.05:
        pro.append((k("wachstum"), f"Umsatz {prozent(rg, lang)} zum Vorjahr" if de else f"Revenue {prozent(rg, lang)} YoY",
                    f"ein Umsatzwachstum von {prozent(rg, lang, True)}" if de else
                    f"revenue growth of {prozent(rg, lang, True)}"))
    elif k("wachstum") <= 35:
        contra.append((100 - k("wachstum"), "Schwaches Wachstum" if de else "Weak growth",
                       "schwaches Wachstum" if de else "weak growth"))
    if pe and k("bewertung") >= 65:
        pro.append((k("bewertung"), f"Günstig: KGV {zahl(pe, lang)}" if de else f"Cheap: P/E {zahl(pe, lang)}",
                    f"eine günstige Bewertung mit einem KGV von {zahl(pe, lang)}" if de else
                    f"a cheap valuation at {zahl(pe, lang)} times earnings"))
    elif pe and k("bewertung") <= 35:
        contra.append((100 - k("bewertung"), f"Teuer: KGV {zahl(pe, lang)}" if de else f"Pricey: P/E {zahl(pe, lang)}",
                       f"eine hohe Bewertung mit einem KGV von {zahl(pe, lang)}" if de else
                       f"a rich valuation at {zahl(pe, lang)} times earnings"))
    div = _f(a.get("div_rendite")) or 0
    if div >= 0.03:
        pro.append((55 + div * 300, f"Dividende {zahl(div * 100, lang)} %" if de else f"Dividend {zahl(div * 100, lang)}%",
                    f"eine Dividende von {prozent(div, lang, True)}" if de else
                    f"a {prozent(div, lang, True)} dividend yield"))
    r12 = _f(a.get("rendite_12m"))
    if k("momentum") >= 70 and r12 and r12 > 0.15:
        pro.append((k("momentum") - 5, f"Aufwärtstrend: {prozent(r12, lang)} in 12 M." if de else
                    f"Uptrend: {prozent(r12, lang)} in 12 mo.",
                    "ein intakter Aufwärtstrend" if de else "an intact uptrend"))
    elif k("momentum") <= 30 and r12 is not None and r12 < 0:
        contra.append((100 - k("momentum"), f"Abwärtstrend: {prozent(r12, lang)} in 12 M." if de else
                       f"Downtrend: {prozent(r12, lang)} in 12 mo.",
                       "ein klarer Abwärtstrend" if de else "a clear downtrend"))
    if k("stabilitaet") >= 75:
        pro.append((k("stabilitaet") - 10, "Geringe Schwankungen" if de else "Low volatility",
                    "vergleichsweise geringe Schwankungen" if de else "relatively low volatility"))
    elif k("stabilitaet") <= 25:
        contra.append((100 - k("stabilitaet") - 10, "Hohe Schwankungen" if de else "High volatility",
                       "hohe Schwankungen" if de else "high volatility"))
    idx = (rad or {}).get("index")
    if idx is not None and idx >= 62 and (rad or {}).get("quellen", 0) >= 2:
        pro.append((50, "Positive Stimmung im Netz" if de else "Positive online sentiment",
                    "positive Stimmung im Netz" if de else "positive sentiment online"))
    for w in a.get("warnungen") or []:
        s, g = warnung(w, lang)
        contra.append((85, s, g))
    if not contra:
        contra.append((10, "Vieles evtl. schon eingepreist" if de else "Good news may be priced in",
                       "die Gefahr, dass vieles schon eingepreist ist" if de else
                       "the risk that the good news is already priced in"))
    if not pro:
        pro.append((10, f"Platz {a['rang']} im Scanner" if de else f"Rank {a['rang']} in my scanner",
                    f"Platz {a['rang']} in meinem Scanner" if de else f"rank {a['rang']} in my scanner"))
    pro = [(s, g) for _, s, g in sorted(pro, key=lambda x: -x[0])[:3]]
    contra = [(s, g) for _, s, g in sorted(contra, key=lambda x: -x[0])[:3]]
    return pro, contra


# ---------------------------------------------------------------- Skript bauen

def bauen(a, ins, rad, n_aktien, lang="de", monate=6, modus="liste", haelt=False, seed=None):
    """Gibt {'szenen': [...], 'hook': {...}, 'frage_kurz', 'pro', 'contra', 'winkel'} zurück."""
    t = T[lang]
    seed = seed or f"{a['ticker']}{date.today()}"
    cur = a.get("waehrung") or "USD"
    kn = kurzname(a["name"])
    hat_ins = bool(ins and ins.get("kaeufe"))
    key = winkel(a, ins, rad)
    rd = (rad or {}).get("reddit")
    pot, r12 = _f(a.get("kursziel_potenzial")), _f(a.get("rendite_12m"))
    mc = _f(a.get("marketCap"))
    w = dict(kn=kn, n=n_aktien, rang=int(a["rang"]), score=int(round(a["score"])),
             branche=branche(a.get("branche"), lang), kurs=kurs(a["kurs"], cur, lang, True),
             mcap=geld(mc, cur, lang, True) if mc else ("unbekannt" if lang == "de" else "unknown"),
             pot=prozent(pot, lang, True) if pot is not None else "",
             n_an=int(_f(a.get("numberOfAnalystOpinions")) or 0), mentions=rd["mentions"] if rd else 0,
             r12=prozent(abs(r12), lang, True) if r12 is not None else "",
             div=prozent(_f(a.get("div_rendite")) or 0, lang, True),
             dd=prozent(abs(a["_abstand_hoch"]), lang, True) if a.get("_abstand_hoch") is not None else "")

    # --- Hook
    if hat_ins:
        iw = ins.get("waehrung", "USD")
        n_k = ins["anzahl_kaeufer"]
        g = ins["groesster"]
        w["summe"] = geld(ins["summe"], iw, lang, True)
        if n_k > 1:
            zw = ZAHLWORT[lang][min(n_k, 10)].capitalize()
            w["wer"], w["hat"] = f"{zw} Insider" if lang == "de" else f"{zw} insiders", "haben"
        else:
            w["wer"], w["hat"] = f"{rolle(g['rolle'], lang)} {g['name']}", "hat"
    szenen = [{"name": "hook", "text": _pick(t["hook"][key], seed, "hook").format(**w)}]

    # --- Eckdaten
    if r12 is None:
        rendite = ""
    elif r12 > 0.05:
        rendite = t["rendite_plus"].format(x=prozent(r12, lang, True))
    elif r12 < -0.05:
        rendite = t["rendite_minus"].format(x=prozent(abs(r12), lang, True))
    else:
        rendite = t["rendite_flat"]
    pe = _f(a.get("forwardPE"))
    kurz = hat_ins or (rad or {}).get("quellen", 0) >= 2          # langes Video -> Eckdaten knapper halten
    kgv = t["kgv"].format(x=zahl(pe, lang)) if pe and not kurz else ""
    szenen.append({"name": "intro", "text": _pick(t["intro"], seed, "intro").format(**w, rendite=rendite, kgv=kgv)})

    # --- Chart
    if hat_ins:
        sk = a.get("_seit_erstem_kauf")
        seit = ("" if sk is None else t["seit_plus"].format(x=prozent(sk, lang, True)) if sk > 0.02 else
                t["seit_minus"].format(x=prozent(abs(sk), lang, True)) if sk < -0.02 else t["seit_flat"])
        txt = _pick(t["chart_ins"], seed, "chart").format(m=monate, seit=seit)
    else:
        ah, hoch_k = _f(a.get("_abstand_fenster_hoch")), _f(a.get("_fenster_hoch"))
        hoch = (t["hoch_weg"].format(x=prozent(abs(ah), lang, True), h=kurs(hoch_k, cur, lang, True))
                if ah is not None and ah <= -0.03 and hoch_k else t["hoch_nah"])
        ma = _f(a.get("ueber_ma200"))
        trend = ("" if ma is None else t["trend_up"].format(x=prozent(ma, lang, True)) if ma > 0.02 else
                 t["trend_down"].format(x=prozent(abs(ma), lang, True)) if ma < -0.02 else t["trend_flat"])
        txt = _pick(t["chart"], seed, "chart").format(m=monate, hoch=hoch, trend=trend)
    szenen.append({"name": "chart", "text": txt})

    # --- Insiderkäufe
    if hat_ins:
        k = ins["kaeufe"]
        g = ins["groesster"]
        iw = ins.get("waehrung", "USD")
        if ins["anzahl_kaeufer"] >= 2:
            cluster = t["cluster_n"].format(n=ZAHLWORT[lang][min(ins["anzahl_kaeufer"], 10)], t=ins["spanne_tage"])
        elif len(k) > 1:
            cluster = t["cluster_k"].format(k=len(k), t=ins["spanne_tage"])
        else:
            cluster = ""
        szenen.append({"name": "insider", "text": _pick(t["insider"], seed, "ins").format(
            rolle=rolle(g["rolle"], lang), name=g["name"], wert=geld(g["wert"], iw, lang, True),
            datum=datum(g["datum"], lang), cluster=cluster)})

    # --- Stimmung im Netz
    st_text = stimmung_text(rad, lang, seed)
    if st_text:
        szenen.append({"name": "stimmung", "text": st_text})

    # --- Scanner
    kat = LABELS[lang]["kat"]
    sortiert = kategorien_sortiert(a)
    stark = [kat[c] for c in sortiert[:2] if (_f(a.get("k_" + c)) or 0) >= 60]
    schwach = [kat[c] for c in sortiert[-2:] if (_f(a.get("k_" + c)) or 100) <= 40]
    if lang == "en":
        stark, schwach = [s.lower() for s in stark], [s.lower() for s in schwach]
    st = t["stark"].format(x=aufzaehlung(stark, lang)) if stark else ""
    if schwach:
        st += " " + (t["schwach1"] if len(schwach) == 1 else t["schwach"]).format(x=aufzaehlung(schwach, lang))
    szenen.append({"name": "scanner", "text": _pick(t["scanner"], seed, "scan").format(**w, st=st.strip())})

    # --- Dafür & dagegen
    pro, contra = pro_contra(a, ins, rad, lang)
    szenen.append({"name": "procontra", "text": _pick(t["pc"], seed, "pc").format(
        pro=aufzaehlung([g for _, g in pro], lang), contra=aufzaehlung([g for _, g in contra], lang))})

    # --- Abschluss mit offener Frage (steht ganz am Ende -> mehr Kommentare)
    frage, frage_kurz = FRAGEN[lang][FRAGE_VON[key]]
    cta = t["cta_insider"] if modus == "insider" else t["cta_liste"]
    szenen.append({"name": "outro", "text": _pick(t["outro"], seed, "outro").format(
        haelt=t["haelt"] if haelt else "", cta=cta, frage=frage.format(kn=kn))})

    for s in szenen:
        s["text"] = " ".join(s["text"].split())
    return {"szenen": szenen, "hook": hook_bild(key, a, ins, rad, lang, n_aktien), "frage_kurz": frage_kurz,
            "pro": [s for s, _ in pro], "contra": [s for s, _ in contra], "winkel": key}


def stimmung_text(rad, lang, seed):
    """Sprechtext der Szene 'Was sagt das Netz?'. Leer, wenn weniger als 2 Quellen da sind."""
    if not rad or rad.get("quellen", 0) < 2:
        return ""
    t = T[lang]
    s = [_pick(t["netz_start"], seed, "netz")]
    rd = rad.get("reddit")
    if rd is not None:
        m, m0 = rd["mentions"], rd["mentions_24h"]
        if m == 0:
            s.append(t["rd_null"])
        elif m < 10:
            s.append(t["rd_wenig"].format(m=m))
        elif m0 < 3:
            s.append(t["rd_neu"].format(m=m))
        else:
            ch = (m - m0) / m0
            v = (t["rd_mehr"].format(x=prozent(ch, lang, True)) if ch > 0.1 else
                 t["rd_weniger"].format(x=prozent(abs(ch), lang, True)) if ch < -0.1 else "")
            s.append(t["rd"].format(m=m, v=v))
    st = rad.get("stocktwits")
    if st:
        p = st["bull"] / (st["bull"] + st["bear"])
        s.append((t["st_bull"] if p >= 0.5 else t["st_bear"]).format(p=prozent(p, lang, True)))
    nw = rad.get("news")
    if nw and not (rd is not None and st):           # nur vorlesen, wenn sonst wenig da ist (steht ja im Bild)
        x = nw["stimmung"]
        s.append(t["nw_pos"] if x >= 0.15 else t["nw_neg"] if x <= -0.15 else t["nw_mix"])
    if rad.get("index") is not None:
        s.append(t["hype"].format(i=rad["index"]))
    return " ".join(s)


def beschreibung(a, ins, lang, frage_kurz):
    """Text für das TikTok-Beschreibungsfeld."""
    kn = kurzname(a["name"])
    tag = "".join(c for c in kn if c.isalnum()).lower()
    tk = a["ticker"].split(".")[0].lower().replace("-", "")
    q = ", ".join(x for x in ((ins or {}).get("quelle"), "Yahoo Finance") if x)
    hat_ins = bool(ins and ins.get("kaeufe"))
    if lang == "de":
        return (f"{kn} im Daten-Check: {frage_kurz} 👇 Keine Anlageberatung, nur Daten ({q}).\n"
                f"#aktien #{tag} #{tk} #börse #investieren #finanzen #aktienanalyse"
                + (" #insider" if hat_ins else "") + " #fyp")
    return (f"{kn} by the numbers: {frage_kurz} 👇 Not financial advice, just data ({q}).\n"
            f"#stocks #{tag} #{tk} #stockmarket #investing #finance"
            + (" #insiderbuying" if hat_ins else "") + " #fyp")
