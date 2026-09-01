"""ÜCRETSIZ yol: flux gorselleri + ffmpeg hareketi.

Kedinin ayni kedi kalmasi icin tum karelerde tek bir seed sabitlenir ve
karakter tarifi hic degistirilmez; sadece poz cumlesi degisir. Boylece
model ayni kompozisyonu koruyup yalnizca hareketi guncelliyor.
"""
import pathlib
import time

from .. import assemble, ideas, log
from ..pollinations import PollinationsError, new_seed

# Reels'in alt siniri 5 saniye; bu kadar cekim her zaman tamamlanmali.
MIN_USABLE_SHOTS = 3

# Ayni cekim icindeki ara kareler: kompozisyonu bozmadan hareketi ilerletir.
MICRO_STEPS = [
    "",
    " The pose continues one small step further, tail swung to the other side,"
    " subtle motion blur on the paws.",
    " The motion reaches its peak, body weight shifted forward, fur in motion.",
]


def produce(client, cfg, idea: dict, workdir: pathlib.Path) -> pathlib.Path:
    seed = new_seed(cfg)
    log.info(f"ucretsiz yol: seed={seed}, {len(idea['shots'])} cekim x "
             f"{cfg.keyframes_per_shot} kare")

    frames_dir = workdir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Anonim erisimde servis cozunurlugu kisitliyor; yine de buyuk isteyip
    # montajda lanczos + unsharp ile toparliyoruz.
    req_w, req_h = 768, 1344

    # Gozetimsiz calisiyoruz: tek bir yavas istek tum is akisini zaman asimina
    # surukleyebilir. Butce dolunca elimizdekiyle yetinip videoyu tamamlariz --
    # kisa bir Reel, hic Reel olmamasindan iyidir.
    deadline = time.time() + cfg.max_gen_minutes * 60

    clips: list[pathlib.Path] = []
    last_good: pathlib.Path | None = None

    for i, shot in enumerate(idea["shots"]):
        if time.time() > deadline and len(clips) >= MIN_USABLE_SHOTS:
            log.warn(f"uretim butcesi ({cfg.max_gen_minutes}dk) doldu; "
                     f"{len(clips)} cekimle tamamlaniyor")
            break

        frames: list[pathlib.Path] = []
        for k in range(max(1, cfg.keyframes_per_shot)):
            # Butce dolduysa bu cekimin ek karelerini atla, ilkiyle yetin.
            if k > 0 and time.time() > deadline:
                break
            dest = frames_dir / f"s{i:02d}_k{k}.jpg"
            prompt = ideas.shot_prompt(idea, shot) + MICRO_STEPS[k % len(MICRO_STEPS)]
            try:
                client.image(prompt, dest, seed=seed, width=req_w, height=req_h)
                frames.append(dest)
                last_good = dest
                log.info(f"  kare {i:02d}/{k} hazir ({dest.stat().st_size // 1024}KB)")
            except PollinationsError as exc:
                log.warn(f"  kare {i:02d}/{k} uretilemedi: {exc}")
                if last_good is not None:
                    frames.append(last_good)

        if not frames:
            log.warn(f"cekim {i} tamamen bos, atlaniyor")
            continue

        clip = assemble.build_shot_clip(
            frames, workdir / f"clip{i:02d}.mp4", cfg,
            seconds=cfg.shot_seconds, index=i,
        )
        clips.append(clip)

    if not clips:
        raise RuntimeError("hicbir cekim uretilemedi -- Pollinations erisilemiyor olabilir")

    return assemble.join_clips(clips, workdir / "joined.mp4", cfg)
