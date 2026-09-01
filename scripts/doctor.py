"""Kurulum tanisi: neyin hazir, neyin eksik oldugunu tek bakista gosterir.

  python scripts/doctor.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402

from src import config  # noqa: E402
from src.assemble import find_font  # noqa: E402

OK, WARN, BAD = "  OK  ", " UYARI", " EKSIK"
rows: list[tuple[str, str, str]] = []


def add(state: str, name: str, detail: str = "") -> None:
    rows.append((state, name, detail))


def check_tooling() -> None:
    for exe in ("ffmpeg", "ffprobe"):
        path = shutil.which(exe)
        add(OK if path else BAD, exe, path or "PATH uzerinde yok")
    font = find_font()
    add(OK if font else WARN, "kanca metni fontu",
        font or "bulunamadi -- metin katmani atlanacak")


def check_media(cfg) -> None:
    tracks = [p for p in config.MUSIC.glob("*")
              if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav", ".ogg")]
    add(OK if tracks else WARN, "muzik dosyalari",
        f"{len(tracks)} parca" if tracks
        else "assets/music bos -- videolar SESSIZ cikacak, dagitim cok duser")


def check_text(cfg) -> None:
    if cfg.gemini_api_key:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{cfg.gemini_model}:generateContent",
                headers={"x-goog-api-key": cfg.gemini_api_key},
                json={"contents": [{"parts": [{"text": "reply with: ok"}]}]},
                timeout=60,
            )
            add(OK if r.status_code == 200 else BAD, "Gemini",
                f"{cfg.gemini_model} -> HTTP {r.status_code}"
                + ("" if r.status_code == 200 else f" {r.text[:90]}"))
        except requests.RequestException as exc:
            add(BAD, "Gemini", str(exc)[:90])
    else:
        add(WARN, "Gemini", "GEMINI_API_KEY yok -- konseptler yerel sablondan gelecek")


def check_images(cfg) -> None:
    try:
        r = requests.get(
            "https://image.pollinations.ai/prompt/tiny%20test%20cat",
            params={"width": 256, "height": 256, "seed": 1, "nologo": "true"},
            timeout=120,
        )
        ok = r.status_code == 200 and "image" in r.headers.get("content-type", "")
        if ok:
            add(OK, "Pollinations gorsel",
                f"{len(r.content) // 1024}KB"
                + ("" if cfg.pollinations_key else "  (anonim: 576x1024 tavan)"))
        elif r.status_code == 429:
            # Hiz siniri, ariza degil: uretim hattinda throttle zaten var.
            add(WARN, "Pollinations gorsel",
                "HTTP 429 hiz siniri -- servis ayakta, biraz bekleyip tekrar deneyin")
        else:
            add(BAD, "Pollinations gorsel", f"HTTP {r.status_code} {r.text[:70]}")
    except requests.RequestException as exc:
        add(BAD, "Pollinations gorsel", str(exc)[:90])


def check_instagram(cfg) -> None:
    if not (cfg.ig_user_id and cfg.ig_token):
        add(BAD, "Instagram", "IG_USER_ID / IG_ACCESS_TOKEN tanimli degil")
        return
    try:
        r = requests.get(f"{cfg.graph_base}/{cfg.ig_user_id}",
                         params={"fields": "username,account_type",
                                 "access_token": cfg.ig_token}, timeout=60)
        if r.status_code == 200:
            d = r.json()
            add(OK, "Instagram", f"@{d.get('username')} ({d.get('account_type')})")
        else:
            err = r.json().get("error", {}).get("message", r.text[:90])
            add(BAD, "Instagram", f"HTTP {r.status_code}: {err[:80]}")
    except requests.RequestException as exc:
        add(BAD, "Instagram", str(exc)[:90])


def check_hosting(cfg) -> None:
    if cfg.host_mode == "release":
        missing = [n for n, v in (("GITHUB_REPOSITORY", cfg.gh_repo),
                                  ("GH_TOKEN", cfg.gh_token)) if not v]
        add(BAD if missing else OK, "barindirma (release)",
            f"eksik: {', '.join(missing)}" if missing else cfg.gh_repo)
    elif cfg.host_mode == "r2":
        missing = [k for k in ("r2_endpoint", "r2_bucket", "r2_access_key",
                               "r2_secret_key", "r2_public_base")
                   if not getattr(cfg, k)]
        add(BAD if missing else OK, "barindirma (r2)",
            f"eksik: {', '.join(m.upper() for m in missing)}" if missing
            else cfg.r2_public_base)
    else:
        add(WARN, f"barindirma ({cfg.host_mode})", "elle saglanan URL")


def main() -> int:
    cfg = config.load()
    check_tooling()
    check_media(cfg)
    check_text(cfg)
    check_images(cfg)
    check_instagram(cfg)
    check_hosting(cfg)

    width = max(len(n) for _, n, _ in rows)
    print()
    for state, name, detail in rows:
        print(f"[{state}] {name:<{width}}  {detail}")
    print()

    bad = sum(1 for s, _, _ in rows if s == BAD)
    warn = sum(1 for s, _, _ in rows if s == WARN)
    if bad:
        print(f"{bad} kritik eksik var -- yayin denemesi basarisiz olur.")
        print("Sadece video uretmek icin: python -m src.main --dry-run")
    elif warn:
        print(f"Yayina hazir ({warn} uyari var, kaliteyi etkiler).")
    else:
        print("Her sey hazir.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
