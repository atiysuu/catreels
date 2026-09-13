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

# En yeniden eskiye Flash zinciri (kaynak: ai.google.dev/gemini-api/docs/models,
# 1 Eylul 2026'da dogrulandi). Google model basina ucretsiz kotayi artik
# yayimlamiyor ve yeni modeller free tier'a gecikmeli giriyor; bu yuzden tek
# bir kimlige bel baglamak yerine sirayla deniyoruz. Bir model yoksa (404),
# anahtara kapaliysa (403) ya da kotasi dolduysa (429) bir alttakine geciyoruz.
# Boylece "en yeni ucretsiz model" zamanla kendini gunceller.
#
# 1 Eylul 2026'da gercek bir anahtarla olculdu:
#   gemini-flash-latest    calisiyor (1.2sn) -- Google'in "en yeni Flash" takma adi
#   gemini-3.8-flash       calisiyor (1.6sn)
#   gemini-3.7-flash       503 -- aylardir surekli mesgul, zincirde alta alindi
#   gemini-3.6-flash       calisiyor (1.4sn)
#   gemini-2.5-flash       404 "no longer available to new users" -> cikarildi
#   gemini-3.1-pro-preview 429 -- Pro ucretsiz katmanda yok, faturalandirma ister
GEMINI_CHAIN = [
    # Google'in "her zaman en yeni Flash" takma adi. Yeni surum ciktiginda
    # kod degistirmeden otomatik ona geciyoruz.
    "gemini-flash-latest",
    "gemini-3.8-flash",        # 14 Eylul 2026'da en yeni acik surum
    "gemini-3.6-flash",        # 3.7 aylardir 503 veriyor, atlandi
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]

# Modelin bu anahtarla kullanilamadigini gosteren kodlar -> siradakine gec
_TRY_NEXT = {400, 403, 404, 429, 500, 503}


class TextGenError(RuntimeError):
    pass


class _GeminiHTTPError(TextGenError):
    """Zincirin siradaki modele gecip gecmeyecegine karar verebilmek icin
    HTTP kodunu tasir."""

    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status


def gemini_chain(cfg) -> list[str]:
    """GEMINI_MODEL verilmisse onu basa alir, ardindan varsayilan zincir gelir."""
    chain = [cfg.gemini_model] if cfg.gemini_model else []
    chain += [m for m in GEMINI_CHAIN if m != cfg.gemini_model]
    return chain


def _gemini(cfg, model: str, system: str, prompt: str) -> dict:
    url = f"{GEMINI_BASE}/{model}:generateContent"
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
    if r.status_code != 200:
        body = r.text[:300]
        # Gecersiz anahtar da 400 donuyor -- uydurma bir model kimligiyle ayni
        # kod. Ayirt etmezsek bozuk anahtarla zincirdeki her modeli bosuna
        # deneriz. Bu bir model sorunu degil, hemen dur.
        if "API_KEY_INVALID" in body or r.status_code == 401:
            raise TextGenError(
                "GEMINI_API_KEY gecersiz. aistudio.google.com/apikey adresinden "
                "yeni bir anahtar alip Secrets'a girin."
            )
        raise _GeminiHTTPError(r.status_code, body)

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
        for model in gemini_chain(cfg):
            try:
                out = _gemini(cfg, model, system, prompt)
                log.info(f"konsept metni: Gemini ({model})")
                return out
            except _GeminiHTTPError as exc:
                errors.append(f"{model}: {exc}")
                if exc.status in _TRY_NEXT:
                    log.warn(f"Gemini {model} kullanilamadi ({exc}); siradaki model deneniyor")
                    continue
                log.warn(f"Gemini {model} hatasi: {exc}")
                break
            except (TextGenError, requests.RequestException, json.JSONDecodeError) as exc:
                errors.append(f"{model}: {exc}")
                log.warn(f"Gemini {model} kullanilamadi: {exc}")
                break

    try:
        out = client.text_json(system, prompt)
        log.info(f"konsept metni: Pollinations ({cfg.text_model})")
        return out
    except (PollinationsError, json.JSONDecodeError) as exc:
        errors.append(f"pollinations: {exc}")

    raise TextGenError(" | ".join(errors))
