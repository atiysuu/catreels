"""Konsept metnini ureten katman -- ucu sirayla dener, ilk basarili olan kazanir.

  1. Gemini (AI Studio ucretsiz katmani; kredi karti istemez)
  2. Pollinations metin ucu (anahtarsiz, ama anonim katmanda kirilgan)
  3. Yerel sablon (ideas.py icindeki yedek; internet olmasa bile calisir)

Gemini'nin ucretsiz katmani gunde ~200-1000 istek veriyor; gunde birkac Reel
uretimi bunun cok altinda kaliyor, dolayisiyla pratikte hep 1. secenek calisir.
"""
import json

import requests

from . import log
from .pollinations import PollinationsError, extract_json

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class TextGenError(RuntimeError):
    pass


def _gemini(cfg, system: str, prompt: str) -> dict:
    url = f"{GEMINI_BASE}/{cfg.gemini_model}:generateContent"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 1.15,
            "responseMimeType": "application/json",
        },
    }
    r = requests.post(
        url,
        headers={"x-goog-api-key": cfg.gemini_api_key, "content-type": "application/json"},
        json=body,
        timeout=120,
    )
    if r.status_code == 429:
        raise TextGenError("Gemini gunluk ucretsiz kota doldu (429)")
    if r.status_code != 200:
        raise TextGenError(f"Gemini HTTP {r.status_code}: {r.text[:220]}")

    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        # Guvenlik filtresi devreye girmis olabilir
        reason = (data.get("candidates") or [{}])[0].get("finishReason", "?")
        raise TextGenError(f"Gemini yaniti okunamadi (finishReason={reason}): {exc}")
    return extract_json(text)


def concept_json(client, cfg, system: str, prompt: str) -> dict:
    """Sirayla saglayicilari dener. Hepsi duserse TextGenError firlatir."""
    errors = []

    if cfg.gemini_api_key:
        try:
            out = _gemini(cfg, system, prompt)
            log.info(f"konsept metni: Gemini ({cfg.gemini_model})")
            return out
        except (TextGenError, requests.RequestException, json.JSONDecodeError) as exc:
            errors.append(f"gemini: {exc}")
            log.warn(f"Gemini kullanilamadi: {exc}")

    try:
        out = client.text_json(system, prompt)
        log.info(f"konsept metni: Pollinations ({cfg.text_model})")
        return out
    except (PollinationsError, json.JSONDecodeError) as exc:
        errors.append(f"pollinations: {exc}")

    raise TextGenError(" | ".join(errors))
