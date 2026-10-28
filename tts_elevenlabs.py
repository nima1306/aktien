"""ElevenLabs-Stimme (kostenpflichtig, sehr natürlich) mit genauen Wortzeiten für die Untertitel.

Der Schlüssel kommt aus dem GitHub-Secret ELEVENLABS_API_KEY. Fehlt er, ist das Guthaben leer oder
antwortet der Dienst nicht, nimmt der Bot automatisch die kostenlose Stimme - es kommt immer ein Video.
"""
import base64
import os

import requests

API = "https://api.elevenlabs.io/v1"
STANDARD_STIMMEN = {                     # ElevenLabs-Standardstimmen (in jedem Konto verfügbar)
    "brian": "nPczCjzI2devNBz1zQrb",     # tief, ruhig - Erzähler
    "bill": "pqHfZKP75CvOlQylNhV4",      # vertrauenswürdig, Doku-Stil
    "daniel": "onwK4e9ZLuTAKqWW03F9",    # britisch, autoritär
    "george": "JBFqnCBsd6RMkjVDRZzb",    # britisch, warm
    "callum": "N2lVS1w4EtoT3dr4eOWO",    # intensiv
    "liam": "TX3LPaxmHKxFdv7VOQHJ",      # klar, artikuliert
    "sarah": "EXAVITQu4vr4xnSDxMaL",     # weiblich, sanft
    "alice": "Xb7hH8MSUJpSbSDYk0k2",     # weiblich, britisch, selbstbewusst
}
_guthaben = {}


def schluessel():
    return os.environ.get("ELEVENLABS_API_KEY", "").strip()


def stimmen_id(name_oder_id):
    s = str(name_oder_id or "brian").strip()
    return STANDARD_STIMMEN.get(s.lower(), s)


def restguthaben():
    """Verbleibende Zeichen im Abo (None = unbekannt)."""
    if "rest" in _guthaben:
        return _guthaben["rest"]
    rest = None
    try:
        r = requests.get(f"{API}/user/subscription", headers={"xi-api-key": schluessel()}, timeout=20)
        if r.status_code == 200:
            j = r.json()
            rest = int(j.get("character_limit", 0)) - int(j.get("character_count", 0))
    except requests.RequestException:
        pass
    _guthaben["rest"] = rest
    return rest


def kontostatus():
    """Prüft Schlüssel und Abo, ohne Zeichen zu verbrauchen."""
    if not schluessel():
        return {"ok": False, "fehler": "kein Schlüssel - GitHub-Secret ELEVENLABS_API_KEY fehlt oder ist falsch benannt"}
    try:
        r = requests.get(f"{API}/user/subscription", headers={"xi-api-key": schluessel()}, timeout=20)
    except requests.RequestException as e:
        return {"ok": False, "fehler": f"ElevenLabs nicht erreichbar ({e})"}
    if r.status_code == 401:
        if "permission" in r.text.lower():         # Schlüssel gültig, darf nur das Guthaben nicht lesen
            return {"ok": True, "tarif": "?", "limit": None, "rest": None,
                    "hinweis": "Schlüssel gültig, aber ohne Berechtigung 'User: Read' - Guthaben unbekannt"}
        return {"ok": False, "fehler": f"Schlüssel ungültig - neu kopieren oder neuen anlegen ({r.text[:120]})"}
    if r.status_code != 200:
        return {"ok": False, "fehler": f"ElevenLabs antwortet mit {r.status_code}: {r.text[:120]}"}
    j = r.json()
    limit, genutzt = int(j.get("character_limit", 0)), int(j.get("character_count", 0))
    _guthaben["rest"] = limit - genutzt
    return {"ok": True, "tarif": j.get("tier", "?"), "limit": limit, "rest": limit - genutzt}


def verbrauchen(n):
    if _guthaben.get("rest") is not None:
        _guthaben["rest"] -= n


def sprechen(text, stimme, mp3_pfad, modell="eleven_multilingual_v2", tempo=1.0, einstellungen=None,
             vorher=None, nachher=None, sprache=None):
    """Erzeugt die Audiodatei und gibt Wortzeiten [(start, ende, wort)] zurück."""
    st = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True}
    st.update(einstellungen or {})
    st["speed"] = max(0.7, min(1.2, float(tempo)))
    body = {"text": text, "model_id": modell, "voice_settings": st}
    if vorher:
        body["previous_text"] = vorher[-400:]                  # sorgt für natürlichen Übergang zwischen Szenen
    if nachher:
        body["next_text"] = nachher[:400]
    if sprache:
        body["language_code"] = sprache
    r = requests.post(f"{API}/text-to-speech/{stimmen_id(stimme)}/with-timestamps",
                      params={"output_format": "mp3_44100_128"}, json=body, timeout=120,
                      headers={"xi-api-key": schluessel(), "Content-Type": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:160]}")
    j = r.json()
    with open(mp3_pfad, "wb") as f:
        f.write(base64.b64decode(j["audio_base64"]))
    verbrauchen(len(text))
    al = j.get("alignment") or j.get("normalized_alignment") or {}
    return woerter_aus_zeichen(al.get("characters") or [], al.get("character_start_times_seconds") or [],
                               al.get("character_end_times_seconds") or [])


def woerter_aus_zeichen(zeichen, starts, enden):
    woerter, wort, w_start, w_ende = [], "", None, None
    for c, s, e in zip(zeichen, starts, enden):
        if c.isspace():
            if wort:
                woerter.append((w_start, w_ende, wort))
            wort, w_start = "", None
            continue
        if w_start is None:
            w_start = s
        wort += c
        w_ende = e
    if wort:
        woerter.append((w_start, w_ende, wort))
    return woerter
