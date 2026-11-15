"""Bolum sesini hazirlar ve Remotion icin zaman cizelgesini yazar.

Kullanim:
    python story/tools/prep.py ep01 --vo out/story/kule/ep01/vo

Girdi : story/episodes/<ep>.json + <vo>/<key>.wav (Fish Audio ciktilari)
Cikti : story/public/<ep>/mix.wav  (VO + ambiyans + efekt, tek parca)
        story/src/data/<ep>.json   (sahne/altyazi zamanlari)
"""
import argparse
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
FPS = 30
TEMPO = 1.05      # varsayilan; --tempo ile degisir
GAP = 0.30        # cumleler arasi nefes
TAIL = 2.4        # secim karti son ekranda kalsin


def run(args, cwd):
    subprocess.run(args, check=True, cwd=cwd)


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def chunks(text, maxc=26):
    """Altyaziyi ekrana sigacak kisa parcalara boler; cumle sonunda keser."""
    cur, out = "", []
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > maxc:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
        if w.endswith((".", "?", ":")) and len(cur) > 8:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("--vo", required=True)
    ap.add_argument("--tempo", type=float, default=TEMPO)
    ap.add_argument("--gap", type=float, default=GAP)
    a = ap.parse_args()

    ep = json.loads((ROOT / "episodes" / f"{a.ep}.json").read_text(encoding="utf-8"))
    vo_dir = pathlib.Path(a.vo).resolve()
    work = ROOT / "out" / a.ep
    work.mkdir(parents=True, exist_ok=True)
    pub = ROOT / "public" / a.ep
    pub.mkdir(parents=True, exist_ok=True)

    trim = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
            "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
            f"atempo={a.tempo},aresample=48000")
    segs, t = [], 0.0
    for s in ep["segments"]:
        dst = work / f"vo{s['key']}.wav"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(vo_dir / f"{s['key']}.wav"),
             "-af", trim, "-ac", "1", str(dst)], work)
        d = dur(dst)
        segs.append({**s, "start": t, "vo": d})
        t += d + a.gap
    total = t - a.gap + TAIL
    for x, y in zip(segs, segs[1:]):
        x["len"] = y["start"] - x["start"]
    segs[-1]["len"] = total - segs[-1]["start"]

    # altyazi parcalari: sure, karakter sayisina orantili
    subs = []
    for s in segs:
        parts = chunks(s["text"])
        n = sum(len(p) for p in parts)
        t0 = s["start"]
        for p in parts:
            d = s["vo"] * len(p) / n
            subs.append({"from": round(t0 * FPS), "to": round((t0 + d) * FPS), "text": p})
            t0 += d

    # --- ses: VO + ruzgar + dron + ayak sesi + anahtar vurusu -------------
    inputs, filt, labels = [], [], []
    for i, s in enumerate(segs):
        inputs += ["-i", f"vo{s['key']}.wav"]
        ms = int(s["start"] * 1000)
        filt.append(f"[{i}]adelay={ms}|{ms},apad[v{i}]")
        labels.append(f"[v{i}]")
    filt.append(f"{''.join(labels)}amix=inputs={len(segs)}:normalize=0,atrim=0:{total:.3f},"
                "loudnorm=I=-15:TP=-1.5:LRA=7[vo]")
    filt.append(f"anoisesrc=c=brown:r=48000:a=0.5:d={total:.3f},lowpass=f=420,highpass=f=40,"
                "tremolo=f=0.15:d=0.6,volume=0.22[wind]")
    filt.append(f"sine=f=55:r=48000:d={total:.3f},volume=0.05[drone]")
    fx = ["[wind]", "[drone]"]

    # ayak sesi: tas merdivende yavas, agir adimlar (kisa alcak gurultu darbeleri)
    steps = []
    for s in segs:
        if s.get("footsteps"):
            k, st = 0, s["start"] + 0.2
            while st < s["start"] + s["len"] - 0.4:
                steps.append(st)
                st += 1.05 if k % 2 else 0.95
                k += 1
    for j, st in enumerate(steps):
        filt.append(f"anoisesrc=c=brown:r=48000:a=0.9:d=0.22,lowpass=f=260,"
                    f"afade=t=out:st=0.02:d=0.2,volume=0.8,adelay={int(st * 1000)},apad[st{j}]")
        fx.append(f"[st{j}]")
    for j, s in enumerate(segs):
        if "hit_at" in s:
            ht = s["start"] + s["vo"] * s["hit_at"]
            filt.append("sine=f=48:r=48000:d=2.5,afade=t=out:st=0:d=2.5,volume=0.9,"
                        f"adelay={int(ht * 1000)},apad[hit{j}]")
            fx.append(f"[hit{j}]")
    filt.append(f"{''.join(fx)}amix=inputs={len(fx)}:normalize=0,atrim=0:{total:.3f},"
                f"afade=t=in:d=1.5,afade=t=out:st={total - 1.5:.3f}:d=1.5[bed]")
    filt.append("[vo]asplit[vo1][vo2]")
    filt.append("[bed][vo1]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400[bedd]")
    filt.append("[vo2][bedd]amix=inputs=2:normalize=0,alimiter=limit=0.89[aout]")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt),
         "-map", "[aout]", "-c:a", "pcm_s16le", str(pub / "mix.wav")], work)

    # --- Remotion zaman cizelgesi ----------------------------------------
    shots = []
    for s in segs:
        f0 = round(s["start"] * FPS)
        L = round(s["len"] * FPS)
        acc = 0
        for i, (name, frac) in enumerate(s["shots"]):
            n = L - acc if i == len(s["shots"]) - 1 else round(L * frac)
            shots.append({"scene": name, "from": f0 + acc, "dur": n})
            acc += n
    last = segs[-1]
    data = {
        "fps": FPS,
        "frames": round(total * FPS),
        "series": ep["series"], "episode": ep["episode"],
        "day": ep["day"], "daysTotal": ep["days_total"],
        "audio": f"{a.ep}/mix.wav",
        "shots": shots,
        "subs": subs,
        "steps": [round(x * FPS) for x in steps],
        "titleUntil": round((segs[0]["vo"] + 0.3) * FPS),
        "card": {**ep["choices"],
                 "from": round((last["start"] + last["vo"] * last.get("card_at", 0.2)) * FPS)},
    }
    (ROOT / "src" / "data").mkdir(exist_ok=True)
    (ROOT / "src" / "data" / f"{a.ep}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{a.ep}: {total:.2f} sn, {len(shots)} sahne, {len(subs)} altyazi, {len(steps)} adim")


if __name__ == "__main__":
    main()
