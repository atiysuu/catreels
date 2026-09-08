"""ffmpeg montaj katmani: durgun kareleri hareketli bir Reel'e cevirir.

Tasarim notu -- keskinlik icin kareler once hedeften %25 buyuge (1350x2400)
olceklenir, Ken Burns penceresi (zoompan) o buyuk tuval icinde gezer ve
1080x1920 keser. Boylece yakinlastirma yumusama yaratmaz.
"""
import json
import pathlib
import random
import shutil
import subprocess

from . import log

# GitHub Actions (ubuntu) ve tipik Windows kurulumlarinda bulunan font adaylari.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
]

OVERSCAN = 1.25  # kaynak tuvalin hedefe orani


class FFmpegError(RuntimeError):
    pass


def _ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise FFmpegError("ffmpeg PATH uzerinde bulunamadi")
    return exe


def _ffprobe_bin() -> str:
    exe = shutil.which("ffprobe")
    if not exe:
        raise FFmpegError("ffprobe PATH uzerinde bulunamadi")
    return exe


def run(args: list[str], *, what: str, cwd: pathlib.Path | None = None) -> None:
    cmd = [_ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          cwd=str(cwd) if cwd else None)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip()[-1500:]
        raise FFmpegError(f"{what} basarisiz (exit {proc.returncode}):\n{tail}")


def probe_duration(path: pathlib.Path) -> float:
    out = subprocess.run(
        [_ffprobe_bin(), "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise FFmpegError(f"ffprobe okuyamadi: {path.name}")
    return float(json.loads(out.stdout)["format"]["duration"])


def find_font() -> str | None:
    for c in FONT_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    return None


# ---------------------------------------------------------------------------
# 1) Tek cekim klibi: karelerin arasinda gecis + Ken Burns
# ---------------------------------------------------------------------------

def build_shot_clip(frames: list[pathlib.Path], dest: pathlib.Path, cfg,
                    *, seconds: float, index: int) -> pathlib.Path:
    """Bir cekimin karelerinden hareketli klip uretir.

    Tek kare varsa saf Ken Burns; birden fazlaysa kareler arasinda morph
    (MORPH=1 ise hareket kestirimli, degilse yumusak carpraz gecis) uygulanir.
    """
    if not frames:
        raise FFmpegError(f"cekim {index}: kare yok")

    big_w = int(cfg.width * OVERSCAN) // 2 * 2
    big_h = int(cfg.height * OVERSCAN) // 2 * 2
    # Kaynak kareler 576x1024 civari geliyor (Pollinations anonim tavani), yani
    # ~2.3x buyutuyoruz. lanczos + cas + hafif unsharp bu buyutmeyi tolere
    # edilebilir kiliyor; sirasi onemli, keskinlestirme olceklemeden sonra.
    cover = (
        f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={big_w}:{big_h},cas=strength=0.45,unsharp=5:5:0.45:5:5:0.0,"
        f"setsar=1,fps={cfg.fps},format=yuv420p"
    )

    inputs: list[str] = []
    parts: list[str] = []

    if len(frames) == 1:
        inputs += ["-loop", "1", "-t", f"{seconds:.3f}", "-i", str(frames[0])]
        parts.append(f"[0:v]{cover}[kb]")
    else:
        # Kareleri esit paylastir; gecisler icin her birine yarim gecis payi ekle.
        #
        # Cekim ICI gecis uzun tutulur: ayni kedinin iki pozu arasindaki uzun
        # carpisma, kesme gibi degil hareket gibi okunuyor. (minterpolate ile
        # gercek hareket kestirimi denendi ve elendi: iki karelik girdide sifir
        # kare uretiyor, mci modu da buyuk poz farklarinda goruntuyu deforme
        # ediyor.) MORPH=1 bu carpismayi daha da uzatir.
        ratio = 2.4 if cfg.morph else 1.6
        xf = min(cfg.transition_seconds * ratio, seconds / len(frames))
        hold = (seconds + xf * (len(frames) - 1)) / len(frames)
        for i, f in enumerate(frames):
            inputs += ["-loop", "1", "-t", f"{hold:.3f}", "-i", str(f)]
            parts.append(f"[{i}:v]{cover}[f{i}]")

        trans = "dissolve" if cfg.morph else "fade"
        prev = "f0"
        for i in range(1, len(frames)):
            offset = hold * i - xf * i
            out = f"x{i}"
            parts.append(
                f"[{prev}][f{i}]xfade=transition={trans}:duration={xf:.3f}:"
                f"offset={offset:.3f}[{out}]"
            )
            prev = out
        parts.append(f"[{prev}]null[kb]")

    # Ken Burns: cekim sirasina gore yon degistir, monotonluk kirilsin.
    zoom_in = index % 2 == 0
    total_frames = max(2, int(seconds * cfg.fps))
    amount = 0.16
    if zoom_in:
        z = f"1+{amount}*on/{total_frames}"
    else:
        z = f"{1 + amount}-{amount}*on/{total_frames}"
    drift = ["iw/2-(iw/zoom/2)", "iw/2-(iw/zoom/2)+(on/%d)*40-20" % total_frames][index % 2]
    ydrift = ["ih/2-(ih/zoom/2)-(on/%d)*30+15" % total_frames, "ih/2-(ih/zoom/2)"][index % 2]

    parts.append(
        f"[kb]zoompan=z='{z}':d=1:x='{drift}':y='{ydrift}':"
        f"s={cfg.width}x{cfg.height}:fps={cfg.fps},"
        f"trim=duration={seconds:.3f},setpts=PTS-STARTPTS[out]"
    )

    args = [*inputs, "-filter_complex", ";".join(parts), "-map", "[out]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", str(dest)]
    run(args, what=f"cekim {index} klibi")
    return dest


# ---------------------------------------------------------------------------
# 2) Klipleri gecislerle birlestir
# ---------------------------------------------------------------------------

def join_clips(clips: list[pathlib.Path], dest: pathlib.Path, cfg) -> pathlib.Path:
    if not clips:
        raise FFmpegError("birlestirilecek klip yok")
    if len(clips) == 1:
        shutil.copy(clips[0], dest)
        return dest

    durations = [probe_duration(c) for c in clips]
    xf = cfg.transition_seconds
    # Gecis, en kisa klibin yarisindan uzun olamaz.
    xf = min(xf, min(durations) / 2.2)

    transitions = ["fade", "smoothleft", "circleopen", "smoothup", "fadeblack",
                   "wipeleft", "diagtl", "radial"]

    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]

    parts = []
    prev = "0:v"
    offset = 0.0
    for i in range(1, len(clips)):
        offset += durations[i - 1] - xf
        t = transitions[(i - 1) % len(transitions)]
        out = f"j{i}"
        parts.append(
            f"[{prev}][{i}:v]xfade=transition={t}:duration={xf:.3f}:"
            f"offset={offset:.3f}[{out}]"
        )
        prev = out

    parts.append(f"[{prev}]format=yuv420p[v]")
    args = [*inputs, "-filter_complex", ";".join(parts), "-map", "[v]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", str(dest)]
    run(args, what="klipleri birlestirme")
    return dest


# ---------------------------------------------------------------------------
# 3) Kanca metni (istege bagli)
# ---------------------------------------------------------------------------

def _wrap(text: str, *, max_chars: int, max_lines: int = 2) -> list[str]:
    """Kelime siniri koruyarak en fazla `max_lines` satira boler."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = f"{cur} {w}".strip()
        if len(candidate) <= max_chars or not cur:
            cur = candidate
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines - 1:
                break
    rest = " ".join(words[sum(len(l.split()) for l in lines):]) if lines else cur
    lines.append(rest.strip() or cur)
    return [l for l in lines[:max_lines] if l]


def overlay_hook(src: pathlib.Path, dest: pathlib.Path, cfg, text: str) -> pathlib.Path:
    """Ilk saniyelerde ekrana kanca metni basar.

    Windows'ta 'C:/...' yolundaki iki nokta drawtext filtre dizgesini bozuyor
    ve kacis karakterleri iki kat cozumlendigi icin guvenilir sekilde
    kacirilamiyor. Cozum: fontu calisma klasorune kopyalayip ffmpeg'i orada
    calistirmak, boylece filtre dizgesinde hic iki nokta gecmiyor.
    """
    font = find_font()
    if not font or not text.strip():
        shutil.copy(src, dest)
        return dest

    workdir = dest.parent
    local_font = workdir / "_hookfont.ttf"
    try:
        if not local_font.exists():
            shutil.copy(font, local_font)
    except OSError as exc:
        log.warn(f"font kopyalanamadi ({exc}); kanca metni atlaniyor")
        shutil.copy(src, dest)
        return dest

    safe = (text.replace("\\", "").replace(":", " ").replace("'", "")
            .replace("%", "").replace(",", " ").strip())[:60]
    lines = _wrap(safe, max_chars=24)
    # Kalin sans fontta karakter genisligi ~0.55 * punto. Punto'yu en uzun
    # satira gore cozup kadrajin %88'ini asmamasini garanti ediyoruz --
    # sabit punto uzun basliklarda iki yandan tasiyordu.
    longest = max(len(l) for l in lines)
    size = int(min(cfg.width * 0.075, (cfg.width * 0.88) / (0.55 * longest)))
    size = max(size, int(cfg.width * 0.030))
    border = max(3, int(size * 0.075))
    alpha = "if(lt(t,0.4),t/0.4,if(lt(t,3.6),1,max(0,1-(t-3.6)/0.5)))"

    draws = []
    for n, line in enumerate(lines):
        y = f"h*0.12+{n * int(size * 1.22)}"
        draws.append(
            f"drawtext=fontfile={local_font.name}:text='{line}':"
            f"fontcolor=white:fontsize={size}:"
            f"borderw={border}:bordercolor=black@0.85:"
            f"x=(w-text_w)/2:y={y}:alpha='{alpha}'"
        )
    vf = ",".join(draws)

    try:
        run(["-i", str(src), "-vf", vf, "-c:v", "libx264", "-preset", "medium",
             "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dest)],
            what="kanca metni", cwd=workdir)
    except FFmpegError as exc:
        log.warn(f"kanca metni eklenemedi, metinsiz devam ediliyor: {exc}")
        shutil.copy(src, dest)
    finally:
        local_font.unlink(missing_ok=True)
    return dest


# ---------------------------------------------------------------------------
# 4) Ses + son kodlama (Instagram Reels uyumlu)
# ---------------------------------------------------------------------------

def pick_music(cfg) -> pathlib.Path | None:
    tracks = sorted(
        p for p in cfg_music_dir(cfg).glob("*")
        if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav", ".ogg")
    )
    return random.choice(tracks) if tracks else None


def cfg_music_dir(cfg):
    from .config import MUSIC
    return MUSIC


def finalize(src: pathlib.Path, dest: pathlib.Path, cfg,
             audio: pathlib.Path | None) -> pathlib.Path:
    """Reels spesifikasyonuna gore son cikti: H.264 High + AAC + faststart.

    `audio` audio.build_track() tarafindan uretilmis, muzik + efektleri
    zaten karistirilmis tek parcadir. None ise sessiz kanal eklenir.
    """
    duration = probe_duration(src)

    common_v = [
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
        "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", str(cfg.fps), "-g", str(cfg.fps * 2),
        "-movflags", "+faststart",
    ]

    if audio and audio.exists():
        args = [
            "-i", str(src), "-i", str(audio),
            "-map", "0:v", "-map", "1:a", "-shortest",
            *common_v, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(dest),
        ]
        run(args, what="sesli son kodlama")
    else:
        log.warn("ses kaynagi yok (assets/music ve assets/sfx bos) -- "
                 "SESSIZ video uretiliyor, dagitim ciddi dusecek")
        args = [
            "-i", str(src),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map", "0:v", "-map", "1:a", "-shortest",
            *common_v, "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            str(dest),
        ]
        run(args, what="sessiz son kodlama")

    return dest


def ensure_min_duration(src: pathlib.Path, dest: pathlib.Path,
                        minimum: float) -> pathlib.Path:
    """Video Reels alt sinirinin altindaysa dongu yaparak uzatir.

    Uretim butcesi dolup cekim sayisi dustugunde olabiliyor. Kisa donguler
    bu formatta zaten dogal duruyor, gonderiyi tamamen kaybetmekten iyi.
    """
    secs = probe_duration(src)
    if secs >= minimum:
        shutil.copy(src, dest)
        return dest

    loops = int(minimum / max(secs, 0.1)) + 1
    log.warn(f"video {secs:.1f}sn, alt sinir {minimum:.0f}sn -- "
             f"{loops} kez donguye aliniyor")
    run(["-stream_loop", str(loops - 1), "-i", str(src),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-an", str(dest)],
        what="minimum sure icin dongu")
    return dest


def describe(path: pathlib.Path) -> str:
    out = subprocess.run(
        [_ffprobe_bin(), "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_name,width,height,r_frame_rate",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    try:
        d = json.loads(out.stdout)
        fmt = d.get("format", {})
        v = next((s for s in d.get("streams", []) if s.get("width")), {})
        mb = int(fmt.get("size", 0)) / 1_048_576
        return (f"{v.get('width')}x{v.get('height')} "
                f"{float(fmt.get('duration', 0)):.1f}s {mb:.1f}MB "
                f"{v.get('codec_name')}")
    except Exception:
        return path.name
