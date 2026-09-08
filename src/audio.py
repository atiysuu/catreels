"""Ses katmani: muzik yatagi + kedi efektleri + ducking.

Tasarim notlari
---------------
* Efektler her kesmeye degil, dramanin UC anina konur: kanca (giris),
  donus (~%55) ve odeme (~%85). Her gecise ses koymak ucuz duruyor.
* Muzik, efekt caldigi anda sidechain ile kisilir; efekt duyulur, muzik
  geri gelir. Bu, iki sesi ayni anda tam seviyede calmaktan cok daha
  temiz bir sonuc veriyor.
* Klasorler bosken hicbir sey kirilmaz: ses varsa eklenir, yoksa sessiz
  kanal uretilir ve hat devam eder.
"""
import pathlib
import random

from . import log
from .assemble import FFmpegError, run

AUDIO_EXT = (".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac")

# Dramanin yayina degen anlari (toplam surenin orani olarak)
SFX_POSITIONS = (0.04, 0.55, 0.85)

MUSIC_LUFS = -16      # muzik yatagi, konusmasiz icerik icin makul

# Efektlerde loudnorm KULLANILMIYOR: tek gecisli loudnorm bir saniyenin
# altindaki malzemede guvenilir degil -- olcumde efektleri muzigin ALTINA
# itiyordu. Sabit kazanc da ise yaramaz, cunku kullanicinin koydugu dosyanin
# seviyesi bilinmiyor: ayni kazanc bir dosyada cukur, digerinde patlama verir.
#
# Cozum: her efektin tepe seviyesi ffmpeg ile OLCULUP gereken kazanc
# hesaplaniyor. Boylece hangi dosya konursa konsun sonuc ayni yerde cikiyor.
SFX_PEAK_TARGET = -4.0   # dBFS -- muzik yatagindan belirgin sekilde onde


def peak_dbfs(path: pathlib.Path) -> float:
    """Dosyanin tepe seviyesini dBFS olarak olcer (volumedetect)."""
    import subprocess
    from .assemble import _ffmpeg_bin
    proc = subprocess.run(
        [_ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path),
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    for line in (proc.stderr or "").splitlines():
        if "max_volume:" in line:
            try:
                return float(line.split("max_volume:")[1].split("dB")[0].strip())
            except ValueError:
                break
    return -20.0   # olculemezse makul bir varsayim


def sfx_gain_db(path: pathlib.Path) -> float:
    """Efekti hedef tepeye getirecek kazanc. Asiri yukseltmeyi sinirlar."""
    return max(-6.0, min(24.0, SFX_PEAK_TARGET - peak_dbfs(path)))


def _pick(folder: pathlib.Path, n: int = 1) -> list[pathlib.Path]:
    if not folder.exists():
        return []
    files = sorted(p for p in folder.iterdir()
                   if p.is_file() and p.suffix.lower() in AUDIO_EXT)
    if not files:
        return []
    if n >= len(files):
        return random.sample(files, len(files))
    return random.sample(files, n)


def plan(cfg, duration: float) -> dict:
    """Bu Reel icin hangi seslerin nereye konacagini belirler."""
    from .config import MUSIC, SFX

    music = _pick(MUSIC, 1)
    sfx = _pick(SFX, len(SFX_POSITIONS))
    placements = [(s, round(duration * pos, 2))
                  for s, pos in zip(sfx, SFX_POSITIONS)]
    return {"music": music[0] if music else None, "sfx": placements}


def build_track(cfg, dest: pathlib.Path, duration: float, spec: dict) -> pathlib.Path | None:
    """Karisik ses parcasini uretir. Hicbir kaynak yoksa None doner."""
    music, sfx = spec["music"], spec["sfx"]
    if not music and not sfx:
        return None

    inputs: list[str] = []
    parts: list[str] = []
    idx = 0
    fade_out_at = max(0.0, duration - 1.2)

    music_label = None
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        parts.append(
            f"[{idx}:a]atrim=duration={duration:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out_at:.2f}:d=1.2,"
            f"loudnorm=I={MUSIC_LUFS}:TP=-1.5:LRA=11,"
            f"aformat=sample_rates=48000:channel_layouts=stereo[music]"
        )
        music_label = "music"
        idx += 1

    sfx_labels = []
    for path, at in sfx:
        inputs += ["-i", str(path)]
        ms = int(at * 1000)
        parts.append(
            f"[{idx}:a]atrim=duration=3,asetpts=PTS-STARTPTS,"
            f"volume={sfx_gain_db(path):.1f}dB,alimiter=limit=0.95,"
            f"aformat=sample_rates=48000:channel_layouts=stereo,"
            f"adelay={ms}|{ms}[sfx{idx}]"
        )
        sfx_labels.append(f"[sfx{idx}]")
        idx += 1

    if sfx_labels and music_label:
        parts.append(f"{''.join(sfx_labels)}amix=inputs={len(sfx_labels)}:"
                     f"normalize=0:duration=longest[sfxmix]")
        # asplit SART: [sfxmix] hem sidechain tetikleyicisi hem de karisim
        # girdisi. Ayni etiketi iki filtreye vermek efektin karisima hic
        # girmemesine yol aciyordu -- olcumde efekt anlari muzikten 5 dB
        # DAHA SESSIZ cikiyordu.
        parts.append("[sfxmix]asplit=2[sc][sfxout]")
        # Efekt caldiginda muzigi kis, sonra geri getir.
        parts.append(f"[{music_label}][sc]sidechaincompress="
                     f"threshold=0.1:ratio=4:attack=15:release=250[ducked]")
        parts.append(f"[ducked][sfxout]amix=inputs=2:normalize=0:duration=first,"
                     f"apad,atrim=duration={duration:.3f},"
                     f"aformat=sample_rates=48000:channel_layouts=stereo[out]")
    elif music_label:
        parts.append(f"[{music_label}]apad,atrim=duration={duration:.3f}[out]")
    else:
        parts.append(f"{''.join(sfx_labels)}amix=inputs={len(sfx_labels)}:"
                     f"normalize=0:duration=longest,"
                     f"apad,atrim=duration={duration:.3f},"
                     f"aformat=sample_rates=48000:channel_layouts=stereo[out]")

    args = [*inputs, "-filter_complex", ";".join(parts), "-map", "[out]",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-t", f"{duration:.3f}", str(dest)]
    try:
        run(args, what="ses karisimi")
    except FFmpegError as exc:
        # Sidechain bazi ffmpeg derlemelerinde huysuz; duckingsiz tekrar dene.
        log.warn(f"ducking basarisiz, duz karisima dusuluyor: {str(exc)[:160]}")
        return _build_simple(dest, duration, spec)

    return dest


def _build_simple(dest: pathlib.Path, duration: float, spec: dict) -> pathlib.Path | None:
    """Ducking olmadan duz karisim -- her ffmpeg derlemesinde calisir."""
    music, sfx = spec["music"], spec["sfx"]
    inputs: list[str] = []
    parts: list[str] = []
    labels: list[str] = []
    idx = 0
    fade_out_at = max(0.0, duration - 1.2)

    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        parts.append(
            f"[{idx}:a]atrim=duration={duration:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out_at:.2f}:d=1.2,"
            f"loudnorm=I={MUSIC_LUFS}:TP=-1.5:LRA=11,"
            f"aformat=sample_rates=48000:channel_layouts=stereo[a{idx}]"
        )
        labels.append(f"[a{idx}]")
        idx += 1

    for path, at in sfx:
        inputs += ["-i", str(path)]
        ms = int(at * 1000)
        parts.append(
            f"[{idx}:a]atrim=duration=3,asetpts=PTS-STARTPTS,"
            f"volume={sfx_gain_db(path):.1f}dB,alimiter=limit=0.95,"
            f"aformat=sample_rates=48000:channel_layouts=stereo,"
            f"adelay={ms}|{ms}[a{idx}]"
        )
        labels.append(f"[a{idx}]")
        idx += 1

    if not labels:
        return None

    parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:"
                 f"duration=longest,apad,atrim=duration={duration:.3f},"
                 f"aformat=sample_rates=48000:channel_layouts=stereo[out]")
    run([*inputs, "-filter_complex", ";".join(parts), "-map", "[out]",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-t", f"{duration:.3f}", str(dest)], what="duz ses karisimi")
    return dest


def describe(spec: dict) -> str:
    bits = []
    if spec["music"]:
        bits.append(f"muzik={spec['music'].name}")
    if spec["sfx"]:
        bits.append("efekt=" + ", ".join(f"{p.name}@{t}sn" for p, t in spec["sfx"]))
    return " | ".join(bits) if bits else "ses kaynagi yok"
