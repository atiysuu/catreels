"""Hazir bir mp4'u Instagram'a Reel olarak yayinlar.

  python scripts/publish_file.py --video manual/reel.mp4 --caption manual/reel.txt

Gunluk otomasyondan farki: video URETILMEZ, elinizdeki dosya yayinlanir.
Elle hazirlanmis ya da daha once uretilmis bir Reel'i gondermek icin.

Barindirma yine GitHub Release uzerinden; bu yuzden GH_TOKEN gerekiyor ve
pratikte is akisi icinden calistirilir (orada token otomatik gelir).
"""
import argparse
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import assemble, config, host, log  # noqa: E402
from src.instagram import Instagram, InstagramError  # noqa: E402

MIN_SECONDS, MAX_SECONDS = 5.0, 90.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="yayinlanacak mp4")
    ap.add_argument("--caption", help="aciklama dosyasi (utf-8)")
    ap.add_argument("--dry-run", action="store_true", help="yukle ve dogrula, yayinlama")
    args = ap.parse_args()

    cfg = config.load()
    video = pathlib.Path(args.video)
    if not video.exists():
        log.error(f"video bulunamadi: {video}")
        return 2

    missing = cfg.validate_for_publish()
    if missing and not args.dry_run:
        log.error("Eksik ayarlar: " + ", ".join(missing))
        return 2

    # Reels sartlarini gondermeden once biz kontrol edelim; Meta'nin hata
    # mesajlari bu konuda cok az sey soyluyor.
    secs = assemble.probe_duration(video)
    if not (MIN_SECONDS <= secs <= MAX_SECONDS):
        log.error(f"video {secs:.1f}sn -- Reels {MIN_SECONDS:.0f}-{MAX_SECONDS:.0f}sn istiyor")
        return 2
    log.info(f"video: {assemble.describe(video)}")
    if not assemble.has_audio(video):
        log.warn("videoda ses akisi yok -- sessiz Reel'ler cok az dagitiliyor")

    caption = ""
    if args.caption:
        cp = pathlib.Path(args.caption)
        if cp.exists():
            caption = cp.read_text(encoding="utf-8").strip()
    log.info(f"aciklama: {caption.splitlines()[0][:70] if caption else '(bos)'}")

    log.group("Public barindirma")
    # dry-run'da bile gercekten yukluyoruz: amac Meta'nin indirebilecegi bir
    # adres olustugunu KANITLAMAK. Bu yuzden burada da GH_TOKEN gerekiyor ve
    # betik pratikte is akisi icinden calisiyor.
    try:
        url = host.upload(cfg, video)
        host.verify(url)
    except host.HostError as exc:
        log.error(f"barindirma basarisiz: {exc}")
        if not cfg.gh_token:
            log.error("GH_TOKEN yok -- bu betigi 'Hazir videoyu yayinla' is "
                      "akisindan calistirin, token orada otomatik geliyor.")
        return 2

    if args.dry_run:
        log.info(f"DRY RUN -- yayinlanmadi. URL: {url}")
        return 0

    log.group("Instagram yayini")
    ig = Instagram(cfg)
    me = ig.whoami()
    log.info(f"hesap: @{me.get('username')}")
    try:
        result = ig.post_reel(url, caption)
    except InstagramError as exc:
        log.error(f"yayinlanamadi: {exc}")
        return 1

    link = result.get("permalink", "(permalink alinamadi)")
    log.info(f"YAYINLANDI: {link}")
    log.summary(f"### Reel yayinlandi\n\n- **Dosya:** `{video.name}`\n"
                f"- **Sure:** {secs:.1f}sn\n- **Link:** {link}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
