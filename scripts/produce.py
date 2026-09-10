"""Elle uretim: verilen klip sayisiyla tek bir Reel uretir, yayinlamaz.

  python scripts/produce.py --clips 2 --theme aldatma --name reel-8sn

Gunluk otomasyondan farki: temayi ve uzunlugu sen seciyorsun, cikti da
out/<name>.mp4 olarak sabit bir ada yaziliyor. Yayin akisina dokunmaz.
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import assemble, audio, config, ideas, log  # noqa: E402
from src.main import produce_video  # noqa: E402
from src.pollinations import Pollinations  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", type=int, default=2, help="kac AI video klibi (her biri 4sn)")
    ap.add_argument("--situation", default=None, help="belirli bir sitcom durumu (bos = rastgele)")
    ap.add_argument("--episode", type=int, default=1, help="bolum numarasi")
    ap.add_argument("--name", default="reel", help="cikti dosya adi (uzantisiz)")
    args = ap.parse_args()

    cfg = config.load()
    cfg.video_clips = args.clips

    from src.backends import ai_video
    cost = ai_video.estimate_cost(cfg, args.clips)
    log.info(f"{args.clips} klip x {cfg.video_clip_seconds}sn = "
             f"{args.clips * cfg.video_clip_seconds}sn, tahmini ${cost:.2f}")

    if args.situation:
        ideas.SITUATIONS = [args.situation]

    client = Pollinations(cfg)

    log.group("Konsept")
    idea = ideas.generate(client, cfg, [], episode=args.episode)
    print(f"  bolum    : {idea['episode']} -- {', '.join(idea['cast'])}")
    print(f"  kanca    : {idea['hook']}")
    print(f"  karakter : {idea['character'][:110]}")
    for i, s in enumerate(idea["shots"], 1):
        print(f"  vurus {i}  : {s['action'][:100]}")
    print(f"  aciklama : {idea['caption']}")

    workdir = config.OUT / f"_prod_{args.name}"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "idea.json").write_text(
        json.dumps(idea, ensure_ascii=False, indent=2), encoding="utf-8")

    log.group("Video")
    joined = produce_video(client, cfg, idea, workdir)
    source_audio = assemble.extract_audio(joined, workdir / "source_audio.m4a")
    if source_audio:
        log.info("modelin urettigi ses korunuyor")

    log.group("Kurgu")
    padded = assemble.ensure_min_duration(joined, workdir / "padded.mp4", 6.0)
    hooked = assemble.overlay_hook(padded, workdir / "hooked.mp4", cfg, idea["hook"])
    dur = assemble.probe_duration(hooked)
    spec = audio.plan(cfg, dur, source_audio=source_audio)
    log.info(f"ses: {audio.describe(spec)}")
    track = audio.build_track(cfg, workdir / "audio.m4a", dur, spec)

    final = config.OUT / f"{args.name}.mp4"
    assemble.finalize(hooked, final, cfg, track)
    (config.OUT / f"{args.name}.txt").write_text(
        f"{idea['caption']}\n\n{' '.join(idea['hashtags'])}", encoding="utf-8")

    log.info(f"HAZIR: {final.name} -- {assemble.describe(final)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
