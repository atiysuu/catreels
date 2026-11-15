// KULE sahneleri. Hepsi elle cizilmis SVG; yapay zeka uretimi gorsel yok.
// Her sahne kendi Sequence'i icinde calisir: useCurrentFrame() sahnenin 0'indan sayar.
import React from "react";
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from "remotion";
import {C, Cam, Fog, H, Stones, Svg, Vignette, W, Walker, flicker, lerp, mixHex, prog} from "./kit";

export type SceneProps = {dur: number; from: number; steps: number[]};

// ------------------------------------------------------------------ 1. kule
const bez = (t: number, p: number[][]) => {
  const u = 1 - t;
  return [0, 1].map((k) =>
    u * u * u * p[0][k] + 3 * u * u * t * p[1][k] + 3 * u * t * t * p[2][k] + t * t * t * p[3][k]);
};
const PATH = [[380, 1920], [600, 1700], [640, 1500], [540, 1318]];

export const Tower: React.FC<SceneProps> = ({dur}) => {
  const f = useCurrentFrame();
  const walk = prog(f, 0, dur, Easing.linear);
  const t = lerp(0.18, 0.62, walk);
  const [mx, my] = bez(t, PATH);
  const ms = lerp(0.95, 0.38, t);
  const fl = flicker(f);

  // patika: merkez egrisinden iki yana, yukari dogru daralan seritler
  const left: string[] = [];
  const right: string[] = [];
  for (let i = 0; i <= 30; i++) {
    const tt = i / 30;
    const [x, y] = bez(tt, PATH);
    const w = lerp(120, 10, Math.pow(tt, 0.8));
    left.push(`${x - w},${y}`);
    right.unshift(`${x + w},${y}`);
  }
  const towerPath = "M428 1318 L452 338 L628 338 L652 1318 Z";
  const rows: React.ReactNode[] = [];
  for (let y = 360, r = 0; y < 1318; y += 36, r++) {
    rows.push(<line key={`h${r}`} x1={400} x2={680} y1={y} y2={y} stroke="#0a0e16" strokeWidth={3} opacity={0.6} />);
    for (let x = 420 + (r % 2) * 26; x < 680; x += 52) {
      rows.push(<line key={`v${r}-${x}`} x1={x} x2={x} y1={y} y2={y + 36} stroke="#0a0e16" strokeWidth={3} opacity={0.45} />);
    }
  }

  return (
    <AbsoluteFill style={{background: C.night}}>
      <Svg>
        <defs>
          <linearGradient id="t-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0b101d" />
            <stop offset="0.5" stopColor="#25314a" />
            <stop offset="0.7" stopColor="#4f5c78" />
          </linearGradient>
          <linearGradient id="t-tw" x1="0" x2="1">
            <stop offset="0" stopColor="#141b29" />
            <stop offset="0.32" stopColor="#3b475e" />
            <stop offset="1" stopColor="#0f1521" />
          </linearGradient>
          <radialGradient id="t-glow">
            <stop offset="0" stopColor={C.amber} stopOpacity="0.9" />
            <stop offset="1" stopColor={C.amber} stopOpacity="0" />
          </radialGradient>
          <clipPath id="t-clip"><path d={towerPath} /></clipPath>
        </defs>
        <Cam s={lerp(1, 1.08, prog(f, 0, dur, Easing.linear))} cy={1150}>
          <rect width={W} height={H} fill="url(#t-sky)" />
          <Fog id="t-c1" y={260} h={160} speed={0.35} opacity={0.35} color="#3a4660" />
          <path d="M0 1250 C200 1150 380 1180 540 1225 C720 1170 900 1120 1080 1195 L1080 1920 L0 1920Z" fill="#202a3d" />
          <Fog id="t-f1" y={1240} h={150} speed={0.6} opacity={0.55} color="#7f8ba3" />
          <path d="M0 1410 C250 1310 420 1296 540 1306 C700 1296 900 1336 1080 1430 L1080 1920 L0 1920Z" fill="#111723" />
          <path d={towerPath} fill="url(#t-tw)" />
          <g clipPath="url(#t-clip)">{rows}</g>
          <rect x={442} y={308} width={196} height={36} fill="#161d2b" />
          {[0, 1, 2, 3, 4].map((i) => (
            <rect key={i} x={442 + i * 43} y={278} width={26} height={34} fill="#161d2b" />
          ))}
          <circle cx={540} cy={445} r={130} fill="url(#t-glow)" opacity={0.4 * fl} />
          <rect x={527} y={420} width={26} height={50} rx={13} fill={C.amber} opacity={0.75 + 0.25 * fl} />
          <path d="M512 1318 L512 1250 Q540 1212 568 1250 L568 1318Z" fill="#05070c" />
          <polygon points={[...left, ...right].join(" ")} fill="#3a4458" opacity={0.75} />
          <Walker x={mx} y={my} s={ms} phase={f * 0.28} />
          <Fog id="t-f2" y={1640} h={260} speed={0.9} opacity={0.42} color="#6f7b93" />
        </Cam>
      </Svg>
      <Vignette />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 2. kapi kilitlenir
export const Door: React.FC<SceneProps> = ({dur}) => {
  const f = useCurrentFrame();
  const lock = prog(f, dur * 0.12, dur * 0.2, Easing.out(Easing.cubic));
  const shake = f > dur * 0.2 ? Math.exp(-(f - dur * 0.2) / 4) * 7 * Math.sin(f * 2.3) : 0;
  const walkAway = prog(f, dur * 0.35, dur * 0.95, Easing.in(Easing.quad));
  const feetX = lerp(500, 1000, walkAway);
  const feetO = 1 - prog(f, dur * 0.8, dur * 0.95, Easing.linear);
  const planks = [360, 420, 480, 540, 600, 660, 720];
  return (
    <AbsoluteFill style={{background: C.night}}>
      <Svg>
        <defs>
          <linearGradient id="d-wood" x1="0" x2="1">
            <stop offset="0" stopColor="#1d1712" />
            <stop offset="0.5" stopColor="#2e251c" />
            <stop offset="1" stopColor="#17120e" />
          </linearGradient>
          <linearGradient id="d-spill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#cfd8e8" stopOpacity="0.5" />
            <stop offset="1" stopColor="#cfd8e8" stopOpacity="0" />
          </linearGradient>
          <clipPath id="d-door"><path d="M300 1480 L300 560 Q540 340 780 560 L780 1480Z" /></clipPath>
        </defs>
        <Cam s={lerp(1.02, 1.1, prog(f, 0, dur, Easing.linear))} dx={shake} cy={1000}>
          <Stones id="d-wall" base="#161d29" line="#0a0e15" />
          <rect x={0} y={1486} width={W} height={434} fill="#0a0e16" />
          <path d="M270 1486 L270 560 Q540 300 810 560 L810 1486" fill="none" stroke="#252e3e" strokeWidth={44} />
          <path d="M300 1480 L300 560 Q540 340 780 560 L780 1480Z" fill="url(#d-wood)" />
          <g clipPath="url(#d-door)">
            {planks.map((x) => <line key={x} x1={x} x2={x} y1={300} y2={1480} stroke="#0c0907" strokeWidth={5} />)}
            {[640, 1300].map((y) => (
              <g key={y}>
                <rect x={300} y={y} width={480} height={34} fill="#0f1217" />
                {[330, 450, 630, 750].map((x) => <circle key={x} cx={x} cy={y + 17} r={7} fill="#2a2f38" />)}
              </g>
            ))}
          </g>
          {/* kilit kutusu ve surgu */}
          <rect x={676} y={950} width={78} height={120} rx={6} fill="#1b1f27" stroke="#2c323d" strokeWidth={3} />
          <circle cx={715} cy={995} r={9} fill="#05070a" />
          <rect x={712} y={995} width={6} height={22} fill="#05070a" />
          <rect x={lerp(700, 790, lock)} y={1030} width={90} height={20} rx={4} fill="#3a404b" />
          {/* kapi alti isik ve disaridan gecen ayaklar */}
          <rect x={300} y={1476} width={480} height={10} fill="#d7e0ee" />
          <polygon points="300,1486 780,1486 930,1920 150,1920" fill="url(#d-spill)" opacity={0.6} />
          <g opacity={feetO}>
            {[0, 90].map((o) => (
              <g key={o}>
                <rect x={feetX + o - 380} y={1474} width={58} height={14} fill="#06080c" />
                <polygon points={`${feetX + o - 380},1486 ${feetX + o - 322},1486 ${feetX + o - 290},1920 ${feetX + o - 430},1920`} fill="#06080c" opacity={0.55} />
              </g>
            ))}
          </g>
        </Cam>
      </Svg>
      <Vignette strength={0.85} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 3. oda
const Candle: React.FC<{x: number; y: number; f: number; s?: number; glow?: number}> = ({x, y, f, s = 1, glow = 420}) => {
  const fl = flicker(f, x);
  return (
    <g>
      <circle cx={x} cy={y - 70 * s} r={glow} fill="url(#candle-glow)" opacity={0.42 * fl} />
      <g transform={`translate(${x} ${y}) scale(${s})`}>
        <rect x={-11} y={-56} width={22} height={56} rx={3} fill="#d9cdb2" />
        <path d="M-11 -56 Q0 -50 11 -56" fill="none" stroke="#efe5cc" strokeWidth={3} />
        <line x1={0} y1={-56} x2={0} y2={-64} stroke="#111" strokeWidth={2} />
        <path d={`M0 ${-92 * fl} Q10 -70 0 -60 Q-10 -70 0 ${-92 * fl}Z`} fill="#ffd27a" />
        <path d={`M0 ${-80 * fl} Q4 -68 0 -63 Q-4 -68 0 ${-80 * fl}Z`} fill="#fff4d6" />
      </g>
    </g>
  );
};

const CandleDefs = () => (
  <radialGradient id="candle-glow">
    <stop offset="0" stopColor={C.amber} stopOpacity="0.55" />
    <stop offset="0.5" stopColor={C.amber} stopOpacity="0.12" />
    <stop offset="1" stopColor={C.amber} stopOpacity="0" />
  </radialGradient>
);

export const Room: React.FC<SceneProps> = ({dur}) => {
  const f = useCurrentFrame();
  const p = prog(f, 0, dur, Easing.inOut(Easing.sin));
  return (
    <AbsoluteFill style={{background: C.night}}>
      <Svg>
        <defs>
          <CandleDefs />
          <linearGradient id="r-win" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#a4b0c6" />
            <stop offset="1" stopColor="#56627b" />
          </linearGradient>
          <filter id="r-blur"><feGaussianBlur stdDeviation={18} /></filter>
          <clipPath id="r-winclip"><path d="M498 690 L498 430 Q540 370 582 430 L582 690Z" /></clipPath>
        </defs>
        <Cam s={1.1} dx={lerp(-40, 40, p)} cy={1100}>
          <Stones id="r-wall" base="#151c28" line="#090c13" rowH={58} />
          <path d="M0 1390 Q540 1330 1080 1390 L1080 1920 L0 1920Z" fill="#0c1018" />
          {[1450, 1540, 1660, 1810].map((y) => (
            <path key={y} d={`M0 ${y} Q540 ${y - 50} 1080 ${y}`} fill="none" stroke="#06080d" strokeWidth={4} />
          ))}
          {/* pencere ve isik huzmesi */}
          <path d="M498 690 L498 430 Q540 370 582 430 L582 690Z" fill="url(#r-win)" />
          <g clipPath="url(#r-winclip)">
            <Fog id="r-out" y={560} h={90} speed={0.5} opacity={0.6} color="#d6deea" blur={14} count={4} />
          </g>
          <path d="M488 700 L488 425 Q540 355 592 425 L592 700" fill="none" stroke="#273043" strokeWidth={18} />
          <polygon points="498,690 582,690 820,1560 300,1560" fill="#aab6cb" opacity={0.08} filter="url(#r-blur)" />
          {/* karyola */}
          <g>
            <rect x={110} y={1330} width={430} height={60} rx={14} fill="#2a3346" />
            <path d="M140 1330 Q300 1300 520 1336 L520 1376 L140 1376Z" fill="#3a4559" />
            <rect x={100} y={1386} width={450} height={12} fill="#11151d" />
            {[110, 530].map((x) => <rect key={x} x={x} y={1260} width={12} height={230} fill="#11151d" />)}
            <rect x={110} y={1262} width={10} height={12} fill="#11151d" />
          </g>
          {/* konserveler */}
          {[[700, 1500], [752, 1500], [804, 1500], [726, 1440], [778, 1440]].map(([x, y], i) => (
            <g key={i}>
              <rect x={x} y={y - 58} width={46} height={58} fill="#4a5468" />
              <rect x={x} y={y - 42} width={46} height={20} fill="#2f3644" />
              <ellipse cx={x + 23} cy={y - 58} rx={23} ry={7} fill="#79839b" />
            </g>
          ))}
          {/* su bidonlari */}
          {[880, 960].map((x) => (
            <g key={x}>
              <rect x={x} y={1390} width={70} height={115} rx={14} fill="#7d93b0" opacity={0.35} />
              <rect x={x + 26} y={1376} width={18} height={16} fill="#3a4a63" />
              <rect x={x + 6} y={1440} width={58} height={60} rx={10} fill="#9fb4cf" opacity={0.25} />
            </g>
          ))}
          <Candle x={620} y={1500} f={f} />
        </Cam>
      </Svg>
      <Vignette strength={0.85} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 4. merdiven (ayak sesleri)
// Merdivenin basindan asagi, karanliga bakis. Dikis cizgileri tek kacis noktasina gider.
const VY = 860;      // basamaklarin bittigi (en uzak) yukseklik
const XL = 470;      // uzak aciklik sol kenari
const XR = 610;      // uzak aciklik sag kenari
const seamL = (y: number) => XL - (XL - 110) * (y - VY) / (H - VY);
const seamR = (y: number) => XR + (970 - XR) * (y - VY) / (H - VY);

export const Stairs: React.FC<SceneProps> = ({dur, from, steps}) => {
  const f = useCurrentFrame();
  const g = f + from;
  let shake = 0;
  for (const st of steps) {
    if (g >= st && g < st + 14) shake += Math.exp(-(g - st) / 3.5) * 9;
  }
  const treads: React.ReactNode[] = [];
  const n = 16;
  for (let i = n - 1; i >= 0; i--) {
    const y0 = VY + (H - VY) * Math.pow(0.8, i);
    const y1 = VY + (H - VY) * Math.pow(0.8, i + 1);
    const light = Math.max(0, 1 - i / 7);
    treads.push(
      <g key={i}>
        <polygon points={`${seamL(y1)},${y1} ${seamR(y1)},${y1} ${seamR(y0)},${y0} ${seamL(y0)},${y0}`}
          fill={mixHex("#06080d", "#4b4538", light)} />
        <line x1={seamL(y1)} x2={seamR(y1)} y1={y1} y2={y1} stroke="#020305" strokeWidth={Math.max(2, 14 * Math.pow(0.8, i))} />
      </g>,
    );
  }
  const wallLines: React.ReactNode[] = [];
  for (let k = 0; k <= 12; k++) {
    const y = k * 165;
    const ty = 640 + (y / H) * 220;
    wallLines.push(<line key={`l${k}`} x1={0} y1={y} x2={XL} y2={ty} stroke="#06080d" strokeWidth={4} />);
    wallLines.push(<line key={`r${k}`} x1={W} y1={y} x2={XR} y2={ty} stroke="#06080d" strokeWidth={4} />);
  }
  for (let i = 0; i < 9; i++) {
    const y = VY + (H - VY) * Math.pow(0.8, i);
    const top = 640 - (640 * (y - VY)) / (H - VY);
    wallLines.push(<line key={`vl${i}`} x1={seamL(y)} x2={seamL(y)} y1={top} y2={y} stroke="#06080d" strokeWidth={4} />);
    wallLines.push(<line key={`vr${i}`} x1={seamR(y)} x2={seamR(y)} y1={top} y2={y} stroke="#06080d" strokeWidth={4} />);
  }
  return (
    <AbsoluteFill style={{background: "#000"}}>
      <Svg>
        <defs>
          <radialGradient id="s-dark" cx="50%" cy="39%" r="34%">
            <stop offset="0" stopColor="#000" stopOpacity="1" />
            <stop offset="0.55" stopColor="#000" stopOpacity="0.85" />
            <stop offset="1" stopColor="#000" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="s-warm" cx="50%" cy="100%" r="75%">
            <stop offset="0" stopColor={C.amber} stopOpacity="0.38" />
            <stop offset="1" stopColor={C.amber} stopOpacity="0" />
          </radialGradient>
          <clipPath id="s-walls">
            <polygon points={`0,0 ${XL},640 ${XL},${VY} 110,${H} 0,${H}`} />
            <polygon points={`${W},0 ${XR},640 ${XR},${VY} 970,${H} ${W},${H}`} />
          </clipPath>
        </defs>
        <Cam s={lerp(1, 1.16, prog(f, 0, dur, Easing.linear))} dy={shake * 0.6} dx={shake * 0.3} cy={760}>
          <polygon points={`0,0 ${W},0 ${XR},640 ${XL},640`} fill="#07090f" />
          <polygon points={`0,0 ${XL},640 ${XL},${VY} 110,${H} 0,${H}`} fill="#1a2130" />
          <polygon points={`${W},0 ${XR},640 ${XR},${VY} 970,${H} ${W},${H}`} fill="#151b28" />
          <g clipPath="url(#s-walls)">{wallLines}</g>
          <rect x={XL} y={640} width={XR - XL} height={VY - 640} fill="#000" />
          {treads}
          <rect width={W} height={H} fill="url(#s-dark)" />
        </Cam>
        <rect width={W} height={H} fill="url(#s-warm)" opacity={flicker(f)} />
      </Svg>
      <Vignette strength={0.9} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 5. kapinin altindan not
export const Note: React.FC<SceneProps> = ({dur}) => {
  const f = useCurrentFrame();
  const feet = prog(f, 0, 10, Easing.linear);
  const slide = prog(f, dur * 0.3, dur * 0.42, Easing.out(Easing.cubic));
  const py = lerp(1110, 1360, slide);
  const fl = 0.92 + 0.08 * Math.sin(f * 0.4);
  const tiles: React.ReactNode[] = [];
  const vy = 300;
  for (let i = -8; i <= 8; i++) {
    tiles.push(<line key={`r${i}`} x1={540 + i * 70} y1={1162} x2={540 + i * 70 + (i * 70) * (1920 - 1162) / (1162 - vy)} y2={1920} stroke="#05070b" strokeWidth={4} />);
  }
  [1230, 1330, 1480, 1700].forEach((y) => tiles.push(<line key={`h${y}`} x1={0} x2={W} y1={y} y2={y} stroke="#05070b" strokeWidth={4} />));
  return (
    <AbsoluteFill style={{background: C.night}}>
      <Svg>
        <defs>
          <linearGradient id="n-spill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#dfe6f1" stopOpacity="0.55" />
            <stop offset="1" stopColor="#dfe6f1" stopOpacity="0" />
          </linearGradient>
          <clipPath id="n-floor"><rect x={0} y={1162} width={W} height={800} /></clipPath>
        </defs>
        <Cam s={lerp(1, 1.14, prog(f, 0, dur, Easing.linear))} cy={1300}>
          <rect width={W} height={1162} fill="#1a140f" />
          {[160, 260, 360, 460, 560, 660, 760, 860, 960].map((x) => (
            <line key={x} x1={x} x2={x} y1={0} y2={1150} stroke="#0b0806" strokeWidth={6} />
          ))}
          <rect x={0} y={880} width={W} height={46} fill="#0e1116" />
          <rect x={0} y={1162} width={W} height={758} fill="#0b0f17" />
          {tiles}
          <rect x={60} y={1150} width={960} height={12} fill="#e4eaf4" opacity={fl} />
          <polygon points="60,1162 1020,1162 1180,1920 -100,1920" fill="url(#n-spill)" opacity={0.3 * fl} />
          <g opacity={feet}>
            {[420, 590].map((x) => (
              <g key={x}>
                <rect x={x} y={1148} width={72} height={16} fill="#05070a" />
                <polygon points={`${x},1162 ${x + 72},1162 ${x + 120},1920 ${x - 60},1920`} fill="#05070a" opacity={0.6} />
              </g>
            ))}
          </g>
          <g clipPath="url(#n-floor)">
            <g transform={`translate(${lerp(560, 500, slide)} ${py}) rotate(${lerp(0, -9, slide)})`}>
              <polygon points="-120,-70 120,-76 128,74 -116,80" fill="#d8d0bd" />
              <line x1={-118} y1={4} x2={124} y2={-2} stroke="#a79f8c" strokeWidth={3} />
              <polygon points="-120,-70 120,-76 124,-2 -118,4" fill="#ece5d3" opacity={0.6} />
            </g>
          </g>
        </Cam>
      </Svg>
      <Vignette strength={0.85} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 6a. pencereden asagi: paltolu adam
export const WindowDown: React.FC<SceneProps> = ({dur}) => {
  const f = useCurrentFrame();
  const z = lerp(1, 1.42, prog(f, 0, dur, Easing.inOut(Easing.quad)));
  const eyes = prog(f, dur * 0.55, dur * 0.75, Easing.linear);
  const mx = 540;
  const my = 1180;
  return (
    <AbsoluteFill style={{background: "#000"}}>
      <Svg>
        <defs>
          <radialGradient id="w-ground" cx="50%" cy="58%" r="55%">
            <stop offset="0" stopColor="#6c7891" />
            <stop offset="0.45" stopColor="#2b3447" />
            <stop offset="1" stopColor="#0c1019" />
          </radialGradient>
          <clipPath id="w-open"><path d="M300 1660 L300 520 Q540 190 780 520 L780 1660Z" /></clipPath>
        </defs>
        <Cam s={z} cx={mx} cy={my}>
          <Stones id="w-wall" base="#0d121b" line="#05070c" rowH={70} />
          <g clipPath="url(#w-open)">
            <rect x={300} y={190} width={480} height={1480} fill="url(#w-ground)" />
            <Fog id="w-f1" y={900} h={260} speed={0.7} opacity={0.5} color="#9aa6bc" />
            {/* adam: yukaridan, bize bakiyor */}
            <g transform={`translate(${mx} ${my}) scale(1.6) translate(${-mx} ${-my})`}>
            <ellipse cx={mx + 60} cy={my + 150} rx={40} ry={170} fill="#05070b" opacity={0.45} transform={`rotate(-18 ${mx} ${my})`} />
            <path d={`M${mx - 52} ${my + 10} Q${mx - 64} ${my + 110} ${mx - 30} ${my + 160} L${mx + 30} ${my + 160} Q${mx + 64} ${my + 110} ${mx + 52} ${my + 10} Q${mx} ${my - 18} ${mx - 52} ${my + 10}Z`} fill="#06080d" />
            <ellipse cx={mx} cy={my - 4} rx={26} ry={20} fill="#6f7686" opacity={0.55} />
            <ellipse cx={mx} cy={my - 30} rx={58} ry={34} fill="#05070b" />
            <ellipse cx={mx} cy={my - 40} rx={32} ry={22} fill="#0b0e15" />
            <g opacity={eyes}>
              <circle cx={mx - 9} cy={my + 2} r={2.6} fill="#e8eef8" />
              <circle cx={mx + 9} cy={my + 2} r={2.6} fill="#e8eef8" />
            </g>
            </g>
            <Fog id="w-f2" y={1480} h={260} speed={1.0} opacity={0.3} color="#7b879f" />
          </g>
          <path d="M300 1660 L300 520 Q540 190 780 520 L780 1660" fill="none" stroke="#1c2433" strokeWidth={26} />
          <rect x={250} y={1640} width={580} height={70} fill="#1d2534" />
          <rect x={250} y={1640} width={580} height={8} fill="#38435a" />
        </Cam>
      </Svg>
      <Vignette strength={0.9} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 6b. eldivenli el ve anahtar
export const KeyHand: React.FC<SceneProps> = ({dur}) => {
  const f = useCurrentFrame();
  const rise = prog(f, 0, dur * 0.35, Easing.out(Easing.cubic));
  const sway = Math.sin(f * 0.08) * 6;
  const glint = interpolate(f, [dur * 0.45, dur * 0.55, dur * 0.7], [0, 1, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  return (
    <AbsoluteFill style={{background: C.night}}>
      <Svg>
        <defs>
          <linearGradient id="k-bg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#080b13" />
            <stop offset="1" stopColor="#1d2637" />
          </linearGradient>
          <radialGradient id="k-lamp">
            <stop offset="0" stopColor={C.amber} stopOpacity="0.5" />
            <stop offset="1" stopColor={C.amber} stopOpacity="0" />
          </radialGradient>
          <linearGradient id="k-iron" x1="0" x2="1">
            <stop offset="0" stopColor="#2a2e36" />
            <stop offset="0.45" stopColor="#7c838f" />
            <stop offset="1" stopColor="#23262d" />
          </linearGradient>
        </defs>
        <rect width={W} height={H} fill="url(#k-bg)" />
        <rect x={850} y={430} width={8} height={1500} fill="#0b0e15" />
        <circle cx={854} cy={430} r={160} fill="url(#k-lamp)" opacity={flicker(f)} />
        <Fog id="k-f" y={900} h={400} speed={0.8} opacity={0.4} color="#56627b" />
        <g transform={`translate(${sway} ${lerp(260, 0, rise)}) rotate(${sway * 0.3} 540 1300)`}>
          {/* anahtar: yumruk halkadan tutuyor, sap yukari, disler tepede */}
          <circle cx={540} cy={1190} r={84} fill="none" stroke="url(#k-iron)" strokeWidth={30} />
          <rect x={518} y={850} width={44} height={330} rx={6} fill="url(#k-iron)" />
          <rect x={506} y={1080} width={68} height={18} rx={4} fill="url(#k-iron)" />
          <rect x={506} y={1110} width={68} height={18} rx={4} fill="url(#k-iron)" />
          <path d="M562 856 L660 856 L660 900 L630 900 L630 924 L660 924 L660 976 L604 976 L604 952 L562 952Z" fill="url(#k-iron)" />
          <rect x={530} y={850} width={8} height={330} fill="#c9ced8" opacity={0.35} />
          {/* eldivenli yumruk */}
          <rect x={400} y={1170} width={300} height={260} rx={110} fill={C.ink} />
          <path d="M410 1240 Q380 1300 430 1360 Q500 1380 560 1330" fill="none" stroke="#141a26" strokeWidth={10} />
          {[1250, 1300, 1350].map((y) => (
            <path key={y} d={`M560 ${y} Q640 ${y - 10} 690 ${y + 10}`} fill="none" stroke="#141a26" strokeWidth={6} />
          ))}
          <path d="M404 1240 Q396 1200 440 1176" fill="none" stroke="#4d5a72" strokeWidth={4} />
          <rect x={430} y={1400} width={250} height={600} fill="#0a0d14" />
          <path d="M430 1400 L430 2000" stroke="#3f4a60" strokeWidth={4} />
          <g opacity={glint} transform={`translate(648 870) scale(${0.6 + glint * 0.6})`}>
            <path d="M0 -60 L8 -8 L60 0 L8 8 L0 60 L-8 8 L-60 0 L-8 -8Z" fill="#f4f7fc" />
          </g>
        </g>
      </Svg>
      <Vignette strength={0.85} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 7. karar: oda, kapi, sandalye
export const Choice: React.FC<SceneProps> = ({dur}) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: C.night}}>
      <Svg>
        <defs><CandleDefs /></defs>
        <Cam s={lerp(1.0, 1.08, prog(f, 0, dur, Easing.linear))} cy={1200}>
          <Stones id="c-wall" base="#141a26" line="#080b12" rowH={60} />
          <path d="M0 1520 Q540 1470 1080 1520 L1080 1920 L0 1920Z" fill="#0b0f17" />
          <path d="M350 1520 L350 860 Q540 660 730 860 L730 1520" fill="none" stroke="#232c3c" strokeWidth={34} />
          <path d="M370 1520 L370 870 Q540 690 710 870 L710 1520Z" fill="#1c160f" />
          {[430, 490, 550, 610, 670].map((x) => <line key={x} x1={x} x2={x} y1={720} y2={1520} stroke="#0b0806" strokeWidth={5} />)}
          <rect x={370} y={1514} width={340} height={8} fill="#cfd8e6" opacity={0.55} />
          {/* sandalye */}
          <g fill="#07090e">
            <rect x={470} y={1380} width={14} height={300} />
            <rect x={600} y={1380} width={14} height={300} />
            {[1420, 1470, 1520].map((y) => <rect key={y} x={470} y={y} width={144} height={12} />)}
            <path d="M440 1600 L640 1600 L660 1640 L420 1640Z" />
            <rect x={428} y={1640} width={14} height={160} />
            <rect x={640} y={1640} width={14} height={160} />
          </g>
          <rect x={150} y={1450} width={160} height={14} fill="#2a2119" />
          <rect x={170} y={1464} width={12} height={200} fill="#1a140f" />
          <rect x={280} y={1464} width={12} height={200} fill="#1a140f" />
          <Candle x={230} y={1450} f={f} s={0.9} glow={380} />
        </Cam>
      </Svg>
      <Vignette strength={0.85} />
    </AbsoluteFill>
  );
};

export const SCENES: Record<string, React.FC<SceneProps>> = {
  tower: Tower, door: Door, room: Room, stairs: Stairs, note: Note, window: WindowDown, key: KeyHand, choice: Choice,
};

