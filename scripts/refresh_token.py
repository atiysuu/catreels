"""Instagram uzun omurlu tokenini yeniler ve yeni degeri GitHub secret'ina yazar.

Neden gerekli: uzun omurlu token 60 gunde doluyor. Yenilenmezse otomasyon
sessizce durur -- ve bunu ancak gonderi gelmeyince fark edersiniz.

Secret yazmak icin GITHUB_TOKEN YETMEZ; "Secrets: Read and write" izni olan
bir fine-grained PAT gerekir (GH_PAT). PAT yoksa betik tokeni yine yeniler,
yeni degeri maskeleyerek loglar ve hata koduyla biter -- boylece is akisi
kirmizi yanar ve sizi uyarir.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config, log  # noqa: E402
from src.instagram import InstagramError, refresh_long_lived_token  # noqa: E402


def main() -> int:
    cfg = config.load()
    if not cfg.ig_token:
        log.error("IG_ACCESS_TOKEN tanimli degil")
        return 2

    try:
        data = refresh_long_lived_token(cfg)
    except InstagramError as exc:
        log.error(f"token yenilenemedi: {exc}")
        return 1

    new_token = data.get("access_token", "")
    expires_in = int(data.get("expires_in", 0))
    days = expires_in // 86400
    if not new_token:
        log.error(f"yanitta access_token yok: {data}")
        return 1

    log.info(f"token yenilendi, {days} gun gecerli (...{new_token[-6:]})")
    log.summary(f"Instagram tokeni yenilendi - {days} gun gecerli.")

    # Bitis tarihini repoya yaz. Bu bir SIR DEGIL, sadece bir tarih; amac
    # gunluk calismanin "token X gun sonra oluyor" diye uyarabilmesi.
    # GH_PAT yoksa secret guncellenemiyor ama en azindan habersiz
    # yakalanmiyorsunuz.
    import datetime as _dt, json as _json
    exp = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=expires_in)
    (config.STATE / "token_expiry.json").write_text(
        _json.dumps({"expires_at": exp.isoformat(timespec="seconds"),
                     "checked_at": _dt.datetime.now(_dt.timezone.utc)
                                      .isoformat(timespec="seconds"),
                     "secret_updated": bool(os.getenv("GH_PAT"))}, indent=2),
        encoding="utf-8")
    log.info(f"bitis tarihi kaydedildi: {exp.date()}")

    pat = os.getenv("GH_PAT")
    repo = os.getenv("GITHUB_REPOSITORY")
    if not pat or not repo:
        log.error(
            "GH_PAT tanimli degil, secret otomatik guncellenemedi. "
            "Yeni tokeni elle IG_ACCESS_TOKEN secret'ina yapistirin."
        )
        # Degeri loga basmiyoruz; token gizli kalmali.
        return 1

    proc = subprocess.run(
        ["gh", "secret", "set", "IG_ACCESS_TOKEN", "--repo", repo, "--body", new_token],
        capture_output=True, text=True, env={**os.environ, "GH_TOKEN": pat},
    )
    if proc.returncode != 0:
        log.error(f"gh secret set basarisiz: {proc.stderr.strip()[:300]}")
        return 1

    log.info("IG_ACCESS_TOKEN secret'i guncellendi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
