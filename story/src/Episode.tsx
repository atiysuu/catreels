import React from "react";
import {AbsoluteFill, Audio, Easing, Sequence, interpolate, staticFile, useCurrentFrame} from "remotion";
import {loadFont} from "@remotion/google-fonts/Inter";
import {Grain, fadeEdges, prog} from "./kit";
import {SCENES} from "./scenes";

// latin-ext: ğ, ş, ı, İ icin sart.
const {fontFamily} = loadFont("normal", {weights: ["500", "700", "800"], subsets: ["latin", "latin-ext"]});

export type EpisodeData = {
  fps: number; frames: number; series: string; episode: number; day: number; daysTotal: number;
  audio: string;
  shots: {scene: string; from: number; dur: number}[];
  subs: {from: number; to: number; text: string}[];
  steps: number[];
  titleUntil: number;
  card: {question: string; a: string; b: string; hint: string; from: number};
};

const shadow = "0 3px 14px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.9)";

const Shot: React.FC<{dur: number; children: React.ReactNode}> = ({dur, children}) => {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{opacity: fadeEdges(f, dur, 7)}}>{children}</AbsoluteFill>;
};

const Subs: React.FC<{d: EpisodeData}> = ({d}) => {
  const f = useCurrentFrame();
  const s = d.subs.find((x) => f >= x.from && f < x.to);
  if (!s) return null;
  const k = prog(f, s.from, s.from + 5, Easing.out(Easing.quad));
  return (
    <AbsoluteFill style={{justifyContent: "flex-end", alignItems: "center", paddingBottom: 430}}>
      <div style={{
        fontFamily, fontWeight: 800, fontSize: 60, color: "#fff", textAlign: "center", maxWidth: 900,
        lineHeight: 1.2, textShadow: shadow, opacity: k, transform: `translateY(${(1 - k) * 10}px)`,
        background: "rgba(0,0,0,0.42)", padding: "10px 26px", borderRadius: 16,
      }}>{s.text}</div>
    </AbsoluteFill>
  );
};

const Title: React.FC<{d: EpisodeData}> = ({d}) => {
  const f = useCurrentFrame();
  const inn = prog(f, 6, 22, Easing.out(Easing.cubic));
  const showTitle = f < d.titleUntil;
  const out = 1 - prog(f, d.titleUntil - 10, d.titleUntil, Easing.linear);
  const corner = prog(f, d.titleUntil, d.titleUntil + 12, Easing.linear) * (1 - prog(f, d.card.from - 8, d.card.from, Easing.linear));
  return (
    <>
      {showTitle && (
        <AbsoluteFill style={{alignItems: "center", paddingTop: 190, opacity: inn * out}}>
          <div style={{fontFamily, fontWeight: 700, fontSize: 34, letterSpacing: 12, color: "#cfd6e2", textShadow: shadow}}>
            {d.series} · BÖLÜM {d.episode}
          </div>
          <div style={{fontFamily, fontWeight: 800, fontSize: 96, letterSpacing: 6, color: "#fff", marginTop: 14, textShadow: shadow}}>
            GÜN {d.day} / {d.daysTotal}
          </div>
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{alignItems: "flex-start", padding: "120px 0 0 64px", opacity: corner * 0.85}}>
        <div style={{fontFamily, fontWeight: 700, fontSize: 30, letterSpacing: 6, color: "#e6ebf3", textShadow: shadow}}>
          {d.series} · GÜN {d.day}/{d.daysTotal}
        </div>
      </AbsoluteFill>
    </>
  );
};

const Option: React.FC<{letter: string; text: string; k: number}> = ({letter, text, k}) => (
  <div style={{
    display: "flex", alignItems: "center", gap: 26, width: 860, padding: "26px 34px", borderRadius: 22,
    background: "rgba(8,11,18,0.72)", border: "2px solid rgba(255,255,255,0.18)",
    opacity: k, transform: `translateY(${(1 - k) * 24}px)`,
  }}>
    <div style={{
      width: 74, height: 74, borderRadius: 37, background: "#f2a541", color: "#0b0f17",
      display: "flex", alignItems: "center", justifyContent: "center", fontFamily, fontWeight: 800, fontSize: 44,
    }}>{letter}</div>
    <div style={{fontFamily, fontWeight: 700, fontSize: 46, color: "#fff"}}>{text}</div>
  </div>
);

const Card: React.FC<{d: EpisodeData}> = ({d}) => {
  const f = useCurrentFrame();
  const c = d.card;
  if (f < c.from) return null;
  const k = (o: number) => prog(f, c.from + o, c.from + o + 12, Easing.out(Easing.cubic));
  return (
    <AbsoluteFill style={{
      background: `rgba(0,0,0,${0.5 * k(0)})`, alignItems: "center", justifyContent: "center", gap: 30, paddingBottom: 260,
    }}>
      <div style={{fontFamily, fontWeight: 800, fontSize: 80, letterSpacing: 4, color: "#fff", textShadow: shadow, opacity: k(0), marginBottom: 20}}>
        {c.question}
      </div>
      <Option letter="A" text={c.a} k={k(10)} />
      <Option letter="B" text={c.b} k={k(20)} />
      <div style={{fontFamily, fontWeight: 500, fontSize: 34, color: "#c9d1de", textShadow: shadow, opacity: k(32), marginTop: 18}}>
        {c.hint}
      </div>
    </AbsoluteFill>
  );
};

export const Episode: React.FC<{d: EpisodeData}> = ({d}) => {
  const f = useCurrentFrame();
  const fadeOut = interpolate(f, [d.frames - 20, d.frames], [1, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  return (
    <AbsoluteFill style={{background: "#000"}}>
      <AbsoluteFill style={{opacity: fadeOut}}>
        {d.shots.map((s, i) => {
          const S = SCENES[s.scene];
          return (
            <Sequence key={i} from={s.from} durationInFrames={s.dur}>
              <Shot dur={s.dur}><S dur={s.dur} from={s.from} steps={d.steps} /></Shot>
            </Sequence>
          );
        })}
        <Grain />
        <Subs d={d} />
        <Title d={d} />
        <Card d={d} />
      </AbsoluteFill>
      <Audio src={staticFile(d.audio)} />
    </AbsoluteFill>
  );
};
