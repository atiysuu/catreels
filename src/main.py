"""Uctan uca: fikir -> video -> public URL -> Instagram Reels.

Kullanim:
  python -m src.main                # tam akis (uretir + yayinlar)
  python -m src.main --dry-run      # sadece videoyu uretir, yayinlamaz
  python -m src.main --check        # Instagram baglantisini ve kotayi dener
  python -m src.main --backend free # bu calisma icin yolu zorla
"""
import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys
import traceback

from . import assemble, audio, config, host, ideas, log
from .backends import ai_video, free_motion
from .instagram import Instagram, InstagramError
from .pollinations import Pollinations

HISTORY = config.STATE / "history.json"
TOKEN_EXPIRY = config.STATE / "token_expiry.json"

# Bu esigin altina inince her calismada yuksek sesle uyar.
TOKEN_WARN_DAYS = 14

# Instagram Reels sinirlari
MIN_SECONDS = 5.0
MAX_SECONDS = 90.0


def load_history() -> list[dict]:
    if HISTORY.exists():
        try:
            return json.loads(HISTORY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warn("history.json bozuk, sifirdan baslaniyor")
    return []


def save_history(entries: list[dict], cfg) -> None:
    HISTORY.write_text(
        json.dumps(entries[-cfg.history_limit:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def check_token_expiry() -> None:
    """Token bitisine az kaldiysa uyar.

    Uzun omurlu token 60 gunde doluyor ve yenilemenin secret'a yazilmasi
    GH_PAT gerektiriyor. PAT yoksa yayin bir sabah sessizce durur ve sebebi
    aranir. Tarih dosyasi bunu gorunur kiliyor.
    """
    if not TOKEN_EXPIRY.exists():
        return
    try:
        data = json.loads(TOKEN_EXPIRY.read_text(encoding="utf-8"))
        exp = dt.datetime.fromisoformat(data["expires_at"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return
    left = (exp - dt.datetime.now(dt.timezone.utc)).days
    if left <= 0:
        log.error(f"Instagram tokeninin suresi DOLDU ({exp.date()}). "
                  f"Meta panelinden yeni token uretip IG_ACCESS_TOKEN "
                  f"secret'ini guncelleyin.")
    elif left <= TOKEN_WARN_DAYS:
        log.warn(f"Instagram tokeni {left} gun sonra doluyor ({exp.date()}). "
                 f"GH_PAT tanimliysa otomatik yenilenir; degilse elle "
                 f"guncellemeniz gerekecek.")
        log.summary(f"> Uyari: Instagram tokeni {left} gun sonra doluyor "
                    f"({exp.date()}).")


def build_caption(idea: dict) -> str:
    tags = " ".join(idea["hashtags"])
    return f"{idea['caption']}\n\n{tags}"


def check_duration(path: pathlib.Path) -> float:
    secs = assemble.probe_duration(path)
    if secs < MIN_SECONDS:
        raise RuntimeError(
            f"video {secs:.1f}sn -- Reels en az {MIN_SECONDS:.0f}sn istiyor. "
            f"REEL_SHOTS veya SHOT_SECONDS degerini artirin."
        )
    if secs > MAX_SECONDS:
        raise RuntimeError(
            f"video {secs:.1f}sn -- Reels en fazla {MAX_SECONDS:.0f}sn kabul ediyor."
        )
    return secs


def produce_video(client, cfg, idea: dict, workdir: pathlib.Path) -> pathlib.Path:
    """Secilen yolu dener; ucretli yol patlarsa ucretsize duser."""
    if cfg.backend == "pollinations" and not cfg.pollinations_key:
        log.warn("VIDEO_BACKEND=pollinations secili ama POLLINATIONS_API_KEY yok; "
                 "ucretsiz yola geciliyor")
    elif cfg.backend == "pollinations":
        try:
            return ai_video.produce(client, cfg, idea, workdir)
        except Exception as exc:  # kredi bitti, model dustu, vs.
            log.warn(f"AI video yolu basarisiz ({exc}); ucretsiz yola dusuluyor")
            for stale in workdir.glob("clip*.mp4"):
                stale.unlink(missing_ok=True)
    return free_motion.produce(client, cfg, idea, workdir)


def run(args) -> int:
    cfg = config.load()
    if args.backend:
        cfg.backend = args.backend
    if args.dry_run:
        cfg.dry_run = True

    log.group("Ayarlar")
    log.info(f"backend={cfg.backend} host={cfg.host_mode} "
             f"{cfg.width}x{cfg.height}@{cfg.fps} shots={cfg.shots} "
             f"dry_run={cfg.dry_run}")

    client = Pollinations(cfg)

    # --check: sadece Instagram tarafini dogrula
    if args.check:
        log.group("Instagram baglanti testi")
        missing = [m for m in cfg.validate_for_publish() if m.startswith("IG_")]
        if missing:
            log.error(f"eksik ayar: {', '.join(missing)}")
            return 2
        ig = Instagram(cfg)
        me = ig.whoami()
        log.info(f"hesap: @{me.get('username')} ({me.get('account_type')}) id={me.get('id')}")
        q = ig.quota()
        if q:
            log.info(f"24 saatlik kota: {q.get('quota_usage')}/{(q.get('config') or {}).get('quota_total')}")
        return 0

    if not cfg.dry_run:
        missing = cfg.validate_for_publish()
        if missing:
            log.error("Yayinlamak icin eksik ayarlar: " + ", ".join(missing))
            log.error("Sadece video uretmek icin --dry-run kullanin.")
            return 2

    check_token_expiry()
    history = load_history()
    recent_titles = [h.get("title", "") for h in history]

    # --- 1) fikir ---------------------------------------------------------
    log.group("Konsept uretimi")
    # Bolum numarasi gecmisten geliyor: dizi hissi icin sayac surekli artiyor.
    episode = len(history) + 1
    recent_casts = [h.get("cast") for h in history if h.get("cast")]
    idea = ideas.generate(client, cfg, recent_titles, episode=episode,
                          recent_casts=recent_casts)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    workdir = config.OUT / stamp
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "idea.json").write_text(
        json.dumps(idea, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- 2) video ---------------------------------------------------------
    log.group("Video uretimi")
    joined = produce_video(client, cfg, idea, workdir)

    # Model kendi sesini urettiyse (seedance-2.5) burada ayirilir; sonraki
    # adimlar videodan sesi siliyor, o yuzden once cikariyoruz.
    source_audio = assemble.extract_audio(joined, workdir / "source_audio.m4a")
    if source_audio:
        log.info("modelin urettigi ses korunuyor")

    log.group("Son kurgu")
    # Uretim butcesi cekim sayisini kirpmis olabilir; once alt siniri garanti et.
    padded = assemble.ensure_min_duration(joined, workdir / "padded.mp4",
                                          MIN_SECONDS + 1.0)
    hooked = assemble.overlay_hook(padded, workdir / "hooked.mp4", cfg, idea["hook"])
    vid_len = assemble.probe_duration(hooked)
    spec = audio.plan(cfg, vid_len, source_audio=source_audio)
    log.info(f"ses: {audio.describe(spec)}")
    track = audio.build_track(cfg, workdir / "audio.m4a", vid_len, spec)
    final = workdir / f"reel-{stamp}.mp4"
    assemble.finalize(hooked, final, cfg, track)

    secs = check_duration(final)
    log.info(f"cikti: {assemble.describe(final)}")

    caption = build_caption(idea)
    (workdir / "caption.txt").write_text(caption, encoding="utf-8")

    # En son uretilen videoyu sabit bir yola da kopyala (kolay onizleme)
    latest = config.OUT / "latest.mp4"
    shutil.copy(final, latest)

    record = {
        "stamp": stamp,
        "title": idea["title"],
        "episode": idea["episode"],
        "cast": idea["cast"],
        "backend": cfg.backend,
        "seconds": round(secs, 1),
        "file": str(final.relative_to(config.ROOT)),
        "published": False,
    }

    if cfg.dry_run:
        log.group("DRY RUN -- yayinlanmadi")
        log.summary(
            f"### Kuru calisma tamam\n\n"
            f"- **Konsept:** {idea['title']} ({idea['theme']})\n"
            f"- **Video:** `{final.name}` - {assemble.describe(final)}\n\n"
            f"**Aciklama:**\n\n> {idea['caption']}\n"
        )
        history.append(record)
        save_history(history, cfg)
        return 0

    # --- 3) public URL ----------------------------------------------------
    log.group("Public barindirma")
    url = host.upload(cfg, final)
    host.verify(url)

    # --- 4) Instagram -----------------------------------------------------
    log.group("Instagram yayini")
    ig = Instagram(cfg)
    me = ig.whoami()
    log.info(f"hesap: @{me.get('username')} ({me.get('account_type')})")

    result = ig.post_reel(url, caption)
    permalink = result.get("permalink", "(permalink alinamadi)")
    log.info(f"YAYINLANDI: {permalink}")

    record |= {"published": True, "media_id": result.get("id"),
               "permalink": result.get("permalink"), "video_url": url}
    history.append(record)
    save_history(history, cfg)

    log.summary(
        f"### Reel yayinlandi\n\n"
        f"- **Konsept:** {idea['title']} ({idea['theme']})\n"
        f"- **Sure:** {secs:.1f}sn - {assemble.describe(final)}\n"
        f"- **Link:** {permalink}\n\n"
        f"**Aciklama:**\n\n> {idea['caption']}\n"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="AI kedi Reels otomasyonu")
    ap.add_argument("--dry-run", action="store_true", help="uret ama yayinlama")
    ap.add_argument("--check", action="store_true", help="sadece Instagram baglantisini dene")
    ap.add_argument("--backend", choices=["free", "pollinations"], help="video yolunu zorla")
    args = ap.parse_args()

    try:
        return run(args)
    except InstagramError as exc:
        log.error(f"Instagram hatasi: {exc}")
        return 1
    except Exception as exc:
        log.error(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
