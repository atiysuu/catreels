"""Pollinations istemcisi: metin (bedava), gorsel (bedava), video (Pollen harcar).

Anonim kullanimda servis istek basina ~15 saniyelik bir bosluk bekliyor;
_Throttle bunu kendisi uygular, boylece 429 yemeden calisiriz.
"""
import json
import pathlib
import random
import time
import urllib.parse

import requests

from . import log

IMAGE_BASE = "https://image.pollinations.ai/prompt/"
TEXT_BASE = "https://text.pollinations.ai/"
GEN_BASE = "https://gen.pollinations.ai"

# Pollinations "referrer" alanini kotaya sayiyor; kendimizi tanitmak nazik olani.
REFERRER = "catreels-automation"


class PollinationsError(RuntimeError):
    pass


class _Throttle:
    """Ardisik istekler arasinda en az `gap` saniye birakir."""

    def __init__(self, gap: float):
        self.gap = gap
        self._last = 0.0

    def wait(self) -> None:
        delta = time.time() - self._last
        if delta < self.gap:
            time.sleep(self.gap - delta)
        self._last = time.time()


class Pollinations:
    def __init__(self, cfg):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "catreels/1.0 (+github actions)"
        # Anahtar varsa limitler cok daha genis; yoksa temkinli davran.
        gap = 2.0 if cfg.pollinations_key else 16.0
        self.throttle = _Throttle(gap)

    # -- ortak ---------------------------------------------------------------
    def _auth_headers(self) -> dict:
        if self.cfg.pollinations_key:
            return {"Authorization": f"Bearer {self.cfg.pollinations_key}"}
        return {}

    def _get(self, url: str, *, timeout: int, expect: str) -> requests.Response:
        last = None
        for attempt in range(1, self.cfg.http_retries + 1):
            self.throttle.wait()
            try:
                resp = self.session.get(url, headers=self._auth_headers(), timeout=timeout)
            except requests.RequestException as exc:
                last = f"baglanti hatasi: {exc}"
                log.warn(f"istek {attempt}/{self.cfg.http_retries} basarisiz ({last})")
                time.sleep(min(30, 4 * attempt))
                continue

            ctype = resp.headers.get("content-type", "")
            if resp.status_code == 200 and expect in ctype:
                return resp

            if resp.status_code == 401:
                raise PollinationsError(
                    "Pollinations 401: bu uc nokta API anahtari istiyor. "
                    "https://enter.pollinations.ai/keys adresinden ucretsiz anahtar alip "
                    "POLLINATIONS_API_KEY olarak tanimlayin."
                )
            if resp.status_code == 402:
                raise PollinationsError(
                    "Pollinations 402: Pollen bakiyesi yetersiz. VIDEO_BACKEND=free ile "
                    "ucretsiz gorsel yoluna gecebilir veya bakiye yukleyebilirsiniz."
                )

            body = resp.text[:200].replace("\n", " ")
            last = f"HTTP {resp.status_code} ctype={ctype} body={body}"
            log.warn(f"istek {attempt}/{self.cfg.http_retries} basarisiz ({last})")
            # 429 ve 5xx gecici: ustel bekle
            time.sleep(min(60, 5 * (2 ** (attempt - 1))))

        raise PollinationsError(f"{self.cfg.http_retries} denemede alinamadi -> {last}")

    # -- metin ---------------------------------------------------------------
    def text_json(self, system: str, prompt: str) -> dict:
        """OpenAI uyumlu uctan JSON sozluk dondurur.

        1 Eylul 2026 durumu: anonim katmanda metin ucu artik butce hatasi
        (402) donduruyor -- kisa istemler bile. Bu yuzden bu yol yalnizca
        POLLINATIONS_API_KEY tanimliysa anlamli; anahtarsizken hizlica
        pes edip cagirana yedege gecme sansi birakiyoruz.

        Ayrica anonim/eski katman `system` rolunu, `response_format` ve
        `temperature` alanlarini reddediyor; hepsi tek bir user mesajina
        katlanip JSON yanittan ayiklaniyor.
        """
        merged = f"{system.strip()}\n\n{prompt.strip()}"
        payload = {
            "model": self.cfg.text_model,
            "messages": [{"role": "user", "content": merged}],
            "referrer": REFERRER,
        }
        attempts = self.cfg.http_retries if self.cfg.pollinations_key else 1
        last = None
        for attempt in range(1, attempts + 1):
            self.throttle.wait()
            try:
                resp = self.session.post(
                    TEXT_BASE + "openai",
                    json=payload,
                    headers=self._auth_headers(),
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return extract_json(content)
                if resp.status_code in (401, 402) and not self.cfg.pollinations_key:
                    raise PollinationsError(
                        "anonim metin ucu kapali (HTTP %d). Konsept uretimi icin "
                        "GEMINI_API_KEY tanimlayin (AI Studio ucretsiz katmani) veya "
                        "POLLINATIONS_API_KEY ekleyin." % resp.status_code
                    )
                last = f"HTTP {resp.status_code}: {resp.text[:180]}"
            except (requests.RequestException, ValueError, KeyError) as exc:
                last = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                log.warn(f"metin uretimi {attempt}/{attempts} basarisiz ({last})")
                time.sleep(min(30, 4 * attempt))
        raise PollinationsError(f"metin uretilemedi -> {last}")

    # -- gorsel --------------------------------------------------------------
    def image(self, prompt: str, dest: pathlib.Path, *, seed: int,
              width: int, height: int) -> pathlib.Path:
        params = {
            "model": self.cfg.image_model,
            "width": width,
            "height": height,
            "seed": seed,
            "nologo": "true",
            "private": "true",
            "referrer": REFERRER,
        }
        url = IMAGE_BASE + urllib.parse.quote(prompt, safe="") + "?" + urllib.parse.urlencode(params)
        resp = self._get(url, timeout=180, expect="image/")
        dest.write_bytes(resp.content)
        if dest.stat().st_size < 4000:
            raise PollinationsError(f"gorsel supheli derecede kucuk: {dest.stat().st_size}b")
        return dest

    # -- video (Pollen harcar) ----------------------------------------------
    def video(self, prompt: str, dest: pathlib.Path, *, seed: int,
              seconds: int, aspect: str = "9:16",
              width: int | None = None, height: int | None = None,
              start_image: str | None = None) -> pathlib.Path:
        params = {
            "model": self.cfg.video_model,
            "duration": seconds,
            "aspectRatio": aspect,
            "seed": seed,
            "referrer": REFERRER,
        }
        # Cozunurluk acikca istenmezse model varsayilanini (genelde 480p)
        # veriyor; seedance-pro 1080p destekledigi icin acikca soruyoruz.
        if width and height:
            params["width"] = width
            params["height"] = height
        if start_image:
            params["image"] = start_image
        url = GEN_BASE + "/video/" + urllib.parse.quote(prompt, safe="") + "?" + urllib.parse.urlencode(params)
        # Video uretimi uzun surer; tek istekte senkron bekliyor.
        resp = self._get(url, timeout=600, expect="video/")
        dest.write_bytes(resp.content)
        if dest.stat().st_size < 20000:
            raise PollinationsError(f"video supheli derecede kucuk: {dest.stat().st_size}b")
        return dest


def extract_json(text: str) -> dict:
    """Serbest metnin icinden ilk dengeli JSON nesnesini cikarir.

    JSON modu olmadan calistigimiz icin model yaniti kod bloguna sarabilir
    veya onune bir cumle koyabilir; sayma yontemiyle gercek sinirlari buluruz.
    """
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
        t = t.strip()

    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass

    start = t.find("{")
    if start == -1:
        raise json.JSONDecodeError("JSON nesnesi bulunamadi", t, 0)

    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(t[start:i + 1])
    raise json.JSONDecodeError("JSON nesnesi kapanmadi", t, start)


def new_seed(cfg) -> int:
    return cfg.seed or random.randint(1, 2**31 - 1)
