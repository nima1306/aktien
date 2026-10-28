"""KI-Texte über die Claude-API (Anthropic). Schlüssel: GitHub-Secret ANTHROPIC_API_KEY.

Kosten: Claude Sonnet 5.5 kostet ca. 2 $ pro Mio. Eingabe- und 10 $ pro Mio. Ausgabe-Tokens.
Ein Skript (Deutsch + Englisch) braucht grob 2.000 + 2.500 Tokens -> etwa 3 Cent pro Tag.
"""
import json
import os
import re

import requests

API = "https://api.anthropic.com/v1/messages"
MODELL = "claude-sonnet-5-5"


def schluessel():
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def json_anfrage(system, nutzer, modell=None, max_tokens=4000):
    """Schickt eine Anfrage und gibt das erste JSON-Objekt aus der Antwort zurück."""
    r = requests.post(API, timeout=180, headers={
        "x-api-key": schluessel(), "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": modell or MODELL, "max_tokens": max_tokens, "system": system,
              "messages": [{"role": "user", "content": nutzer}]})
    if r.status_code != 200:
        raise RuntimeError(f"Claude-API {r.status_code}: {r.text[:200]}")
    text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError("Antwort enthielt kein JSON")
    return json.loads(m.group(0))
