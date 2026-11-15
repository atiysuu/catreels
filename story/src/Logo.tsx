// KULE profil logosu. Instagram daireye kirpar ve ~110px gosterir:
// her sey merkez dairenin icinde, tek siluet + tek sicak nokta.
import React from "react";
import {AbsoluteFill} from "remotion";
import {loadFont} from "@remotion/google-fonts/Inter";
import {C} from "./kit";

const {fontFamily} = loadFont("normal", {weights: ["800"], subsets: ["latin", "latin-ext"]});

const S = 1080;
const cx = S / 2;

const TowerMark: React.FC<{base: number; top: number; w: number}> = ({base, top, w}) => {
  const tw = w * 0.82;
  const merl = 5;
  const mw = tw / (merl * 2 - 1);
  const winY = top + (base - top) * 0.13;
  return (
    <g>
      <circle cx={cx} cy={winY + 26} r={150} fill="url(#lg-glow)" />
      <path d={`M${cx - w / 2} ${base} L${cx - tw / 2} ${top} L${cx + tw / 2} ${top} L${cx + w / 2} ${base}Z`} fill={C.ink} />
      {Array.from({length: merl}, (_, i) => (
        <rect key={i} x={cx - tw / 2 + i * mw * 2} y={top - 34} width={mw} height={36} fill={C.ink} />
      ))}
      <rect x={cx - 15} y={winY} width={30} height={54} rx={15} fill={C.amber} />
      <path d={`M${cx - 20} ${base} L${cx - 20} ${base - 46} Q${cx} ${base - 72} ${cx + 20} ${base - 46} L${cx + 20} ${base}Z`} fill="#000" />
    </g>
  );
};

export const Logo: React.FC<{variant: "mark" | "word" | "ring"}> = ({variant}) => {
  const word = variant === "word";
  const base = word ? 760 : 820;
  const top = word ? 250 : 250;
  return (
    <AbsoluteFill style={{background: "#05070d"}}>
      <svg viewBox={`0 0 ${S} ${S}`} width={S} height={S}>
        <defs>
          <radialGradient id="lg-sky" cx="50%" cy="36%" r="62%">
            <stop offset="0" stopColor="#33415d" />
            <stop offset="0.55" stopColor="#141c2c" />
            <stop offset="1" stopColor="#05070d" />
          </radialGradient>
          <radialGradient id="lg-glow">
            <stop offset="0" stopColor={C.amber} stopOpacity="0.75" />
            <stop offset="0.4" stopColor={C.amber} stopOpacity="0.18" />
            <stop offset="1" stopColor={C.amber} stopOpacity="0" />
          </radialGradient>
          <linearGradient id="lg-fog" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#8b97ae" stopOpacity="0" />
            <stop offset="0.5" stopColor="#8b97ae" stopOpacity="0.55" />
            <stop offset="1" stopColor="#8b97ae" stopOpacity="0" />
          </linearGradient>
          <filter id="lg-blur"><feGaussianBlur stdDeviation={22} /></filter>
        </defs>
        <rect width={S} height={S} fill="url(#lg-sky)" />
        <path d={`M0 ${base + 10} C260 ${base - 50} 420 ${base - 30} ${cx} ${base - 6} C700 ${base - 40} 860 ${base - 60} ${S} ${base + 4} L${S} ${S} L0 ${S}Z`} fill="#0b101a" />
        <TowerMark base={base + 6} top={top} w={190} />
        <rect x={0} y={base - 60} width={S} height={140} fill="url(#lg-fog)" filter="url(#lg-blur)" />
        {word && (
          <text x={cx} y={905} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={118}
            letterSpacing={38} fill="#e9edf4">
            {/* harf araligi sonda da bosluk birakir; ortalamak icin yarisi kadar kaydir */}
            <tspan dx={19}>KULE</tspan>
          </text>
        )}
        {variant === "ring" && (
          <g>
            {Array.from({length: 40}, (_, i) => {
              const a = (i / 40) * Math.PI * 2 - Math.PI / 2;
              const r0 = 430;
              const r1 = 470;
              const lit = i === 0;
              return (
                <line key={i} x1={cx + r0 * Math.cos(a)} y1={cx + r0 * Math.sin(a)}
                  x2={cx + r1 * Math.cos(a)} y2={cx + r1 * Math.sin(a)}
                  stroke={lit ? C.amber : "#55617a"} strokeWidth={lit ? 16 : 9} strokeLinecap="round" />
              );
            })}
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};
