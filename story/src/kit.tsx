// Ortak cizim parcalari: tuval, sis, gren, vinyet, tas duvar, siluet.
import React from "react";
import {AbsoluteFill, Easing, interpolate, random, useCurrentFrame} from "remotion";

export const W = 1080;
export const H = 1920;

// Tek palet: gece mavisi + soguk sis + tek sicak vurgu (mum / pencere).
export const C = {
  night: "#070a12",
  deep: "#0d1320",
  slate: "#1a2334",
  steel: "#2b3649",
  mist: "#7d8aa3",
  pale: "#c9d3e3",
  amber: "#f2a541",
  ink: "#04060a",
};

const clamp = {extrapolateLeft: "clamp", extrapolateRight: "clamp"} as const;

export const prog = (f: number, a: number, b: number, ease = Easing.inOut(Easing.cubic)) =>
  interpolate(f, [a, b], [0, 1], {...clamp, easing: ease});

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export const mixHex = (a: string, b: string, t: number) => {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return "#" + pa.map((v, i) => Math.round(lerp(v, pb[i], t)).toString(16).padStart(2, "0")).join("");
};

// Mum alevi: iki farkli frekansin carpimi duzensiz ama yumusak titreme verir.
export const flicker = (f: number, seed = 0) =>
  0.82 + 0.1 * Math.sin(f * 0.71 + seed) + 0.08 * Math.sin(f * 1.93 + seed * 2.1);

export const Svg: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
  <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{position: "absolute", inset: 0, ...style}}>
    {children}
  </svg>
);

// Kamera: verilen merkez etrafinda olcek + kayma.
export const Cam: React.FC<{cx?: number; cy?: number; s: number; dx?: number; dy?: number; children: React.ReactNode}> = ({
  cx = W / 2, cy = H / 2, s, dx = 0, dy = 0, children,
}) => <g transform={`translate(${cx + dx} ${cy + dy}) scale(${s}) translate(${-cx} ${-cy})`}>{children}</g>;

export const Fog: React.FC<{
  id: string; y: number; h: number; speed: number; opacity: number; color?: string; blur?: number; count?: number;
}> = ({id, y, h, speed, opacity, color = "#8a96ad", blur = 40, count = 7}) => {
  const f = useCurrentFrame();
  const blobs = Array.from({length: count}, (_, i) => ({
    x: random(`${id}x${i}`) * 1700 - 300,
    w: 260 + random(`${id}w${i}`) * 380,
    dy: (random(`${id}y${i}`) - 0.5) * h * 0.7,
    o: 0.45 + random(`${id}o${i}`) * 0.55,
  }));
  return (
    <>
      <defs>
        <filter id={id} x="-50%" y="-80%" width="200%" height="260%">
          <feGaussianBlur stdDeviation={blur} />
        </filter>
      </defs>
      <g filter={`url(#${id})`} opacity={opacity}>
        {blobs.map((b, i) => {
          const x = (((b.x + f * speed * (0.6 + i * 0.12)) % 1900) + 1900) % 1900 - 400;
          return <ellipse key={i} cx={x} cy={y + b.dy} rx={b.w} ry={h / 2} fill={color} opacity={b.o} />;
        })}
      </g>
    </>
  );
};

export const Grain: React.FC<{amount?: number}> = ({amount = 0.11}) => {
  const f = useCurrentFrame();
  return (
    <Svg style={{mixBlendMode: "overlay", opacity: amount}}>
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={f % 17} stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width={W} height={H} filter="url(#grain)" />
    </Svg>
  );
};

export const Vignette: React.FC<{strength?: number}> = ({strength = 0.8}) => (
  <AbsoluteFill
    style={{background: `radial-gradient(ellipse 75% 60% at 50% 48%, rgba(0,0,0,0) 40%, rgba(0,0,0,${strength}) 100%)`}}
  />
);

// Tas duvar: satir satir, sasirtmali bloklar. Deterministik (random seed'li).
export const Stones: React.FC<{
  id: string; x?: number; y?: number; w?: number; h?: number; rowH?: number; base: string; line: string;
}> = ({id, x = 0, y = 0, w = W, h = H, rowH = 64, base, line}) => {
  const rows = Math.ceil(h / rowH);
  const blocks: React.ReactNode[] = [];
  for (let r = 0; r < rows; r++) {
    let bx = x - random(`${id}r${r}`) * 120;
    let k = 0;
    while (bx < x + w) {
      const bw = 100 + random(`${id}${r}-${k}`) * 90;
      const shade = random(`${id}s${r}-${k}`);
      blocks.push(
        <rect key={`${r}-${k}`} x={bx + 3} y={y + r * rowH + 3} width={bw - 6} height={rowH - 6} rx={6}
          fill={shade > 0.5 ? "#ffffff" : "#000000"} opacity={Math.abs(shade - 0.5) * 0.14} />,
      );
      blocks.push(
        <rect key={`l${r}-${k}`} x={bx} y={y + r * rowH} width={bw} height={rowH} fill="none"
          stroke={line} strokeWidth={4} opacity={0.75} />,
      );
      bx += bw;
      k++;
    }
  }
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} fill={base} />
      {blocks}
    </g>
  );
};

// Arkadan gorunen yuruyen adam (ayak tabani orijinde, ~180px boy).
export const Walker: React.FC<{x: number; y: number; s: number; phase: number}> = ({x, y, s, phase}) => {
  const a = Math.sin(phase) * 16;
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} fill={C.ink}>
      <ellipse cx={0} cy={2} rx={34} ry={7} fill="#000" opacity={0.35} />
      <rect x={-13} y={-84} width={12} height={84} rx={5} transform={`rotate(${a} -7 -84)`} />
      <rect x={1} y={-84} width={12} height={84} rx={5} transform={`rotate(${-a} 7 -84)`} />
      <path d="M-27 -152 Q-33 -112 -22 -78 L22 -78 Q33 -112 27 -152 Q0 -164 -27 -152Z" />
      <rect x={24} y={-150} width={10} height={64} rx={5} transform={`rotate(${-a * 0.4} 29 -150)`} />
      <rect x={22} y={-96} width={30} height={26} rx={4} transform={`rotate(${-a * 0.4} 29 -150)`} />
      <circle cx={0} cy={-171} r={16} />
    </g>
  );
};

export const fadeEdges = (f: number, dur: number, n = 8) =>
  Math.min(prog(f, 0, n, Easing.linear), 1 - prog(f, dur - n, dur, Easing.linear));
