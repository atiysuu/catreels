"""Tum ayarlar tek yerde. Ortam degiskeni yoksa makul varsayilan kullanilir."""
import os
import pathlib
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
STATE = ROOT / "state"
MUSIC = ROOT / "assets" / "music"
SFX = ROOT / "assets" / "sfx"


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on", "evet")


def _int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _str(name: str, default: str = "") -> str:
    return (os.getenv(name) or "").strip() or default


@dataclass
class Config:
    # --- video uretim yolu -------------------------------------------------
    # "pollinations" -> gercek AI video (seedance-2.5, Pollen harcar)
    # "free"         -> flux gorselleri + ffmpeg hareket (bedava, sinirsiz)
    #
    # Varsayilan bilerek "pollinations": bakiye bitse bile produce_video()
    # ucretsize dusuyor, yani riski yok. Varsayilan "free" birakilinca is
    # akisi YAML'i ile kod celisiyordu ve yerel calistirmalar sessizce
    # ucretsiz yola gidiyordu.
    backend: str = field(default_factory=lambda: _str("VIDEO_BACKEND", "pollinations"))

    # --- Gemini (konsept metni; AI Studio ucretsiz katmani) ----------------
    gemini_api_key: str = field(default_factory=lambda: _str("GEMINI_API_KEY"))
    # Bos birakilirsa textgen.py'deki zincirin basindan baslanir.
    gemini_model: str = field(default_factory=lambda: _str("GEMINI_MODEL"))

    # --- Pollinations ------------------------------------------------------
    pollinations_key: str = field(default_factory=lambda: _str("POLLINATIONS_API_KEY"))
    image_model: str = field(default_factory=lambda: _str("IMAGE_MODEL", "flux"))
    text_model: str = field(default_factory=lambda: _str("TEXT_MODEL", "openai"))
    # seedance-2.5: 0.1028 $/sn, klip suresi TAM 4sn (min=max=4), 720p tavan,
    # ses uretebiliyor. 2 klip x 4sn = 8sn = 0.82 $/Reel; 2 gunde bir yayinla
    # ayda ~12.34 $. Klipler arasi gecis 0 -> tam 8.00sn ve smash cut.
    video_model: str = field(default_factory=lambda: _str("VIDEO_MODEL", "seedance-2.5"))
    video_clip_seconds: int = field(default_factory=lambda: _int("VIDEO_CLIP_SECONDS", 4))
    # DIKKAT: 720p, seedance-2.5'te fiyati 2.25 katina cikariyor
    # (0.1028 -> 0.2312 $/sn). Varsayilan bilerek 480p.
    video_resolution: str = field(default_factory=lambda: _str("VIDEO_RESOLUTION", "480p"))
    # Ucretli yolda kac klip uretilecek. Cekim sayisindan ayri tutuluyor:
    # her cekim icin klip uretmek maliyeti 3 katina cikariyordu.
    video_clips: int = field(default_factory=lambda: _int("VIDEO_CLIPS", 3))

    # --- reel bicimi -------------------------------------------------------
    width: int = field(default_factory=lambda: _int("REEL_WIDTH", 1080))
    height: int = field(default_factory=lambda: _int("REEL_HEIGHT", 1920))
    fps: int = field(default_factory=lambda: _int("REEL_FPS", 30))
    # 6 x 3.0sn - 5 gecis ~ 15.8sn. Reels dagitiminda belirleyici olan
    # tamamlanma orani; 15-18sn bandi bu icerik icin en yuksegini veriyor.
    shots: int = field(default_factory=lambda: _int("REEL_SHOTS", 6))
    shot_seconds: float = field(default_factory=lambda: float(_str("SHOT_SECONDS", "3.0")))
    transition_seconds: float = field(default_factory=lambda: float(_str("TRANSITION_SECONDS", "0.5")))
    # Cekim ici gecisleri uzatir: poz degisimi kesme yerine hareket gibi okunur.
    # Slayt hissini kiran en etkili ucretsiz ayar, bu yuzden varsayilan acik.
    morph: bool = field(default_factory=lambda: _bool("MORPH", True))
    keyframes_per_shot: int = field(default_factory=lambda: _int("KEYFRAMES_PER_SHOT", 2))

    # --- Instagram ---------------------------------------------------------
    ig_user_id: str = field(default_factory=lambda: _str("IG_USER_ID"))
    ig_token: str = field(default_factory=lambda: _str("IG_ACCESS_TOKEN"))
    ig_api_version: str = field(default_factory=lambda: _str("IG_API_VERSION", "v23.0"))
    # "instagram" -> graph.instagram.com (Instagram Login)
    # "facebook"  -> graph.facebook.com  (Facebook Login for Business)
    ig_flavor: str = field(default_factory=lambda: _str("IG_API_FLAVOR", "instagram"))
    share_to_feed: bool = field(default_factory=lambda: _bool("SHARE_TO_FEED", True))

    # --- public barindirma -------------------------------------------------
    # "release" -> GitHub Release asset  |  "r2" -> Cloudflare R2  |  "url" -> hazir link
    host_mode: str = field(default_factory=lambda: _str("HOST_MODE", "release"))
    gh_repo: str = field(default_factory=lambda: _str("GITHUB_REPOSITORY"))
    gh_token: str = field(default_factory=lambda: _str("GH_TOKEN") or _str("GITHUB_TOKEN"))
    release_tag: str = field(default_factory=lambda: _str("RELEASE_TAG", "reels"))
    keep_assets: int = field(default_factory=lambda: _int("KEEP_ASSETS", 20))
    r2_endpoint: str = field(default_factory=lambda: _str("R2_ENDPOINT"))
    r2_bucket: str = field(default_factory=lambda: _str("R2_BUCKET"))
    r2_access_key: str = field(default_factory=lambda: _str("R2_ACCESS_KEY_ID"))
    r2_secret_key: str = field(default_factory=lambda: _str("R2_SECRET_ACCESS_KEY"))
    r2_public_base: str = field(default_factory=lambda: _str("R2_PUBLIC_BASE"))

    # --- davranis ----------------------------------------------------------
    dry_run: bool = field(default_factory=lambda: _bool("DRY_RUN", False))
    # Gorsel uretimi icin ust sinir; asilirsa eldeki cekimlerle tamamlanir.
    max_gen_minutes: int = field(default_factory=lambda: _int("MAX_GEN_MINUTES", 35))
    seed: int = field(default_factory=lambda: _int("SEED", 0))  # 0 -> rastgele
    history_limit: int = field(default_factory=lambda: _int("HISTORY_LIMIT", 120))
    http_retries: int = field(default_factory=lambda: _int("HTTP_RETRIES", 4))

    @property
    def graph_base(self) -> str:
        host = "graph.instagram.com" if self.ig_flavor == "instagram" else "graph.facebook.com"
        return f"https://{host}/{self.ig_api_version}"

    def validate_for_publish(self) -> list[str]:
        """Yayinlamadan once eksik olanlari dondurur (bos liste = hazir)."""
        missing = []
        # IG_USER_ID bilerek zorunlu degil: bos birakilirsa
        # Instagram.resolve_user_id() tokenden bulur.
        if not self.ig_token:
            missing.append("IG_ACCESS_TOKEN")
        if self.host_mode == "release" and not self.gh_repo:
            missing.append("GITHUB_REPOSITORY")
        if self.host_mode == "release" and not self.gh_token:
            missing.append("GH_TOKEN / GITHUB_TOKEN")
        if self.host_mode == "r2":
            for k in ("r2_endpoint", "r2_bucket", "r2_access_key", "r2_secret_key", "r2_public_base"):
                if not getattr(self, k):
                    missing.append(k.upper())
        # VIDEO_BACKEND=pollinations icin anahtar bilerek ZORUNLU degil:
        # main.produce_video() ucretli yol her ne sebeple duserse (anahtar yok,
        # bakiye bitti, model dustu) ucretsize geciyor. Burada sert hata vermek
        # bakiye bittigi gun tum yayini durdururdu.
        return missing


def load() -> Config:
    # .env varsa yerelde okunur (CI'da secrets zaten ortamda)
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    OUT.mkdir(exist_ok=True)
    STATE.mkdir(exist_ok=True)
    MUSIC.mkdir(parents=True, exist_ok=True)
    SFX.mkdir(parents=True, exist_ok=True)
    return Config()
