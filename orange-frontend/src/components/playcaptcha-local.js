import { useState, useMemo, useRef, useEffect } from 'react';
import { useReducedMotion, MotionConfig, motion, AnimatePresence } from 'motion/react';
import { jsx, jsxs, Fragment } from 'react/jsx-runtime';

// src/ClawCaptcha.tsx

// src/toys.ts
var TOY_META = {
  duck: { label: "黄色小鸭", accent: "#E8A33D" },
  bear: { label: "泰迪熊", accent: "#C98A4B" },
  panda: { label: "熊猫", accent: "#52525B" },
  bunny: { label: "小兔子", accent: "#E58AB0" },
  dino: { label: "小恐龙", accent: "#5CA86A" },
  penguin: { label: "企鹅", accent: "#3F4854" },
  fox: { label: "狐狸", accent: "#DD7A3D" },
  frog: { label: "青蛙", accent: "#69A85C" },
  whale: { label: "鲸鱼", accent: "#5A93C9" },
  cat: { label: "小猫", accent: "#B08D57" },
  puppy: { label: "小狗", accent: "#A1785A" },
  unicorn: { label: "独角兽", accent: "#B287D8" }
};

// src/clawArt.ts
var CLAW_PIVOT = { x: 20.6, y: 22.7 };
var CLAW_BODY = [{ "fill": "#666D85", "d": "M20.031,24.324c0.086,2.939,0.263,5.874,0.531,8.802c0.016,0.175,0.073,0.395,0.247,0.42\r\n		c0.218,0.03,0.311-0.267,0.318-0.487c0.104-2.988,0.207-5.975,0.311-8.963C21.048,24.142,20.657,24.188,20.031,24.324z" }, { "fill": "#3D4459", "d": "M20.222,11.816c0.023,2.291,0.046,4.583,0.069,6.874c0.356,0.036,0.717,0.036,1.073,0\r\n		c-0.01-2.339-0.019-4.679-0.028-7.018C20.987,11.656,20.636,11.679,20.222,11.816z" }, { "fill": "#666D85", "d": "M18.924,10.588c0.013,0.395,0.025,0.789,0.038,1.184c0.003,0.101,0.009,0.209,0.073,0.288\r\n		c0.084,0.103,0.234,0.116,0.367,0.12c1.017,0.034,2.044,0.068,3.047-0.106c0.054-0.009,0.111-0.021,0.15-0.059\r\n		c0.047-0.047,0.054-0.12,0.058-0.187c0.022-0.45,0.009-0.901-0.039-1.349c-0.004-0.04-0.011-0.083-0.04-0.11\r\n		c-0.031-0.03-0.079-0.031-0.122-0.031C21.186,10.343,19.916,10.39,18.924,10.588z" }, { "fill": "#DE2121", "d": "M18.282,9.052c-0.062,0-0.13,0.002-0.179,0.04c-0.059,0.045-0.074,0.126-0.084,0.199\r\n		c-0.055,0.411-0.06,0.83-0.015,1.242c0.008,0.074,0.02,0.153,0.071,0.208c0.066,0.07,0.172,0.077,0.268,0.079\r\n		c1.573,0.031,3.146,0.006,4.717-0.076c0.064-0.003,0.132-0.008,0.185-0.045c0.096-0.066,0.102-0.204,0.098-0.321\r\n		c-0.015-0.438-0.031-0.875-0.046-1.313c-0.001-0.039-0.004-0.081-0.031-0.109c-0.029-0.03-0.076-0.032-0.119-0.032\r\n		C22.905,8.925,19.701,9.046,18.282,9.052z" }, { "fill": "#666D85", "d": "M19.815,20.079c-0.001-0.526-0.003-1.052-0.004-1.577c0-0.036,0-0.074,0.017-0.105\r\n		c0.033-0.061,0.112-0.077,0.18-0.085c0.483-0.058,0.97-0.086,1.456-0.083c0.099,0.001,0.21,0.008,0.274,0.083\r\n		c0.053,0.062,0.055,0.151,0.055,0.233c0,0.475-0.001,0.95-0.001,1.425C21.155,19.978,20.517,19.972,19.815,20.079z" }, { "fill": "#B4B9C4", "d": "M19.458,20.771c-0.269,0.791-0.539,1.583-0.808,2.374c-0.016,0.048-0.033,0.098-0.022,0.147\r\n		c0.01,0.047,0.045,0.085,0.077,0.121l0.799,0.87c0.083,0.091,0.169,0.184,0.28,0.238c0.134,0.066,0.289,0.068,0.438,0.069\r\n		c0.471,0.003,0.942,0.006,1.413,0.01c0.048,0,0.098,0,0.141-0.021c0.052-0.026,0.085-0.078,0.115-0.127\r\n		c0.244-0.399,0.487-0.797,0.731-1.196c0.047-0.078,0.096-0.159,0.106-0.249c0.011-0.101-0.027-0.199-0.065-0.293\r\n		c-0.231-0.58-0.463-1.159-0.695-1.739c-0.029-0.072-0.061-0.149-0.124-0.194c-0.074-0.053-0.172-0.051-0.262-0.047\r\n		C20.836,20.765,20.09,20.808,19.458,20.771z" }, { "fill": "#3D4459", "d": "M21.101,22.267c-0.117-0.169-0.332-0.237-0.531-0.186c-0.182,0.047-0.359,0.12-0.459,0.274\r\n		c-0.076,0.116-0.095,0.259-0.101,0.397c-0.004,0.095-0.002,0.192,0.034,0.28c0.061,0.149,0.214,0.245,0.372,0.274\r\n		c0.254,0.047,0.53-0.066,0.678-0.278c0.147-0.212,0.158-0.51,0.025-0.732C21.114,22.286,21.107,22.276,21.101,22.267z" }, { "fill": "#DE2121", "d": "M22.585,19.777c-1.368-0.115-2.751-0.055-4.105,0.179c-0.127,0.022-0.272,0.059-0.327,0.176\r\n		c-0.028,0.06-0.025,0.129-0.022,0.195c0.009,0.173,0.017,0.345,0.026,0.518c0.003,0.058,0.007,0.118,0.037,0.167\r\n		c0.053,0.084,0.164,0.106,0.262,0.118c1.395,0.173,2.808,0.083,4.21-0.007c0.351-0.023,0.703-0.045,1.047-0.121\r\n		c0.053-0.012,0.109-0.026,0.145-0.066c0.044-0.048,0.049-0.119,0.05-0.184c0.003-0.209-0.01-0.418-0.039-0.625\r\n		c-0.01-0.07-0.025-0.145-0.076-0.193c-0.048-0.045-0.118-0.055-0.183-0.064C23.273,19.826,22.935,19.806,22.585,19.777z" }, { "fill": "#851313", "d": "M20.275,21.326c-0.53,0-1.06-0.021-1.589-0.064c-0.113-0.009-0.267-0.021-0.391-0.104\r\n			c-0.281-0.187-0.251-0.584-0.204-0.866c0.007-0.041,0.046-0.068,0.086-0.061c0.041,0.007,0.068,0.045,0.062,0.086\r\n			c-0.064,0.383-0.02,0.611,0.139,0.716c0.085,0.056,0.195,0.069,0.32,0.079c1.626,0.13,3.266,0.058,4.875-0.214\r\n			c0.041-0.007,0.079,0.021,0.086,0.061c0.007,0.041-0.021,0.08-0.061,0.087C22.501,21.233,21.388,21.326,20.275,21.326z" }, { "fill": "#1F2229", "d": "M20.376,17.8c-0.04,0-0.074-0.032-0.075-0.073l-0.152-5.054c-0.001-0.041,0.031-0.076,0.073-0.077\r\n			c0.042,0,0.076,0.031,0.077,0.073l0.152,5.054c0.001,0.042-0.031,0.076-0.073,0.077C20.377,17.8,20.376,17.8,20.376,17.8z" }, { "fill": "#851313", "d": "M17.993,10.472c-0.041,0-0.075-0.033-0.075-0.075l-0.001-0.949c0-0.109,0-0.258,0.087-0.372\r\n			c0.126-0.164,0.364-0.165,0.492-0.166l4.541-0.022c0.088-0.001,0.179,0.004,0.25,0.068c0.089,0.081,0.087,0.211,0.086,0.282\r\n			l-0.018,1.146c-0.001,0.042-0.033,0.074-0.076,0.074c-0.042-0.001-0.075-0.035-0.074-0.076l0.018-1.146\r\n			c0.001-0.064-0.001-0.136-0.037-0.168c-0.031-0.028-0.087-0.03-0.148-0.03l-4.541,0.022c-0.141,0.001-0.298,0.01-0.374,0.108\r\n			c-0.052,0.068-0.056,0.167-0.056,0.28l0.001,0.949C18.068,10.438,18.035,10.472,17.993,10.472\r\n			C17.993,10.472,17.993,10.472,17.993,10.472z" }];
var CLAW_ARM_L = [{ "fill": "#808596", "d": "M18.965,20.803c-1.243,0.927-2.486,1.854-3.729,2.781c-0.176,0.131-0.363,0.279-0.417,0.491\r\n		c-0.049,0.192,0.023,0.391,0.089,0.577c0.681,1.927,0.824,3.999,1.323,5.981c0.055,0.217,0.118,0.441,0.261,0.613\r\n		c0.142,0.17,0.348,0.272,0.542,0.38c0.641,0.359,1.208,0.848,1.658,1.429c0.141,0.182,0.283,0.383,0.499,0.463\r\n		c0.216,0.08,0.52-0.043,0.533-0.249c-0.459-0.883-1.167-1.635-2.02-2.147c-0.152-0.091-0.313-0.179-0.413-0.325\r\n		c-0.081-0.119-0.113-0.263-0.142-0.404c-0.348-1.641-0.697-3.281-1.045-4.922c-0.102-0.478,0.135-0.964,0.574-1.178\r\n		c0.616-0.3,1.225-0.615,1.827-0.943c0.325-0.177,0.656-0.367,0.882-0.66c0.274-0.355,0.358-0.817,0.433-1.259\r\n		c0.029-0.17,0.057-0.35-0.007-0.51c-0.096-0.238-0.378-0.358-0.635-0.345C18.921,20.591,18.683,20.709,18.965,20.803z" }, { "fill": "#3D4459", "d": "M19.335,32.718c-0.024,0-0.047-0.011-0.062-0.032c-0.347-0.498-0.802-0.934-1.314-1.26\r\n			c-0.033-0.021-0.067-0.042-0.101-0.063c-0.213-0.132-0.432-0.268-0.574-0.485c-0.11-0.169-0.158-0.367-0.2-0.543\r\n			c-0.391-1.627-0.752-3.283-1.073-4.922c-0.032-0.163-0.076-0.387,0.009-0.583c0.093-0.216,0.315-0.338,0.477-0.427l1.805-0.99\r\n			c0.036-0.02,0.082-0.007,0.102,0.03c0.02,0.036,0.007,0.082-0.03,0.102l-1.805,0.99c-0.185,0.102-0.344,0.199-0.412,0.355\r\n			c-0.061,0.141-0.036,0.307,0.001,0.494c0.321,1.638,0.681,3.292,1.072,4.916c0.039,0.163,0.084,0.349,0.18,0.496\r\n			c0.123,0.188,0.328,0.316,0.527,0.439c0.034,0.021,0.068,0.042,0.102,0.064c0.529,0.336,0.998,0.786,1.357,1.3\r\n			c0.024,0.034,0.015,0.081-0.019,0.104C19.365,32.714,19.35,32.718,19.335,32.718z" }];
var CLAW_ARM_R = [{ "fill": "#808596", "d": "M22.64,20.803c1.243,0.927,2.486,1.854,3.729,2.781c0.176,0.131,0.363,0.279,0.417,0.491\r\n		c0.049,0.192-0.023,0.391-0.089,0.577c-0.681,1.927-0.824,3.999-1.323,5.981c-0.055,0.217-0.118,0.441-0.261,0.613\r\n		c-0.142,0.17-0.348,0.272-0.542,0.38c-0.641,0.359-1.208,0.848-1.658,1.429c-0.141,0.182-0.284,0.383-0.499,0.463\r\n		c-0.216,0.08-0.52-0.043-0.533-0.249c0.459-0.883,1.167-1.635,2.02-2.147c0.152-0.091,0.313-0.179,0.413-0.325\r\n		c0.081-0.119,0.113-0.263,0.142-0.404c0.348-1.641,0.697-3.281,1.045-4.922c0.101-0.478-0.135-0.964-0.574-1.178\r\n		c-0.616-0.3-1.225-0.615-1.827-0.943c-0.324-0.177-0.656-0.367-0.882-0.66c-0.274-0.355-0.358-0.817-0.433-1.259\r\n		c-0.029-0.17-0.057-0.35,0.007-0.51c0.096-0.238,0.378-0.358,0.635-0.345C22.684,20.591,22.922,20.709,22.64,20.803z" }, { "fill": "#3D4459", "d": "M24.41,30.372c-0.007,0-0.014-0.001-0.021-0.003c-0.04-0.012-0.063-0.053-0.051-0.093\r\n			c0.464-1.586,0.83-3.218,1.089-4.85c0.007-0.041,0.045-0.069,0.086-0.062c0.041,0.007,0.069,0.045,0.062,0.086\r\n			c-0.26,1.639-0.627,3.277-1.093,4.868C24.472,30.351,24.442,30.372,24.41,30.372z" }, { "fill": "#3D4459", "d": "M22.613,33.409c-0.017,0-0.034-0.006-0.048-0.017c-0.032-0.027-0.036-0.074-0.009-0.106\r\n			c0.565-0.675,1.234-1.247,1.99-1.698l0.055-0.033c0.18-0.107,0.365-0.217,0.488-0.377c0.142-0.186,0.197-0.436,0.244-0.656\r\n			l1.14-5.256c0.009-0.04,0.049-0.066,0.089-0.057c0.041,0.009,0.066,0.049,0.057,0.089l-1.14,5.256\r\n			c-0.051,0.236-0.109,0.503-0.272,0.715c-0.141,0.184-0.339,0.301-0.531,0.415l-0.055,0.032c-0.741,0.443-1.398,1.003-1.952,1.666\r\n			C22.656,33.399,22.635,33.409,22.613,33.409z" }];
var GW = 380;
var GH = 320;
var RAIL_Y = 14;
var HOME_Y = 64;
var DROP_Y = 198;
var CLAW_MIN = 46;
var CLAW_MAX = 334;
var COIL_LEN = 50;
var GRAB_RADIUS = 38;
var GRIP_OFFSET = 46;
var TRAY = { cx: 232, cy: GH + 56, min: 150, max: 320 };
var TOY_SET = [
  { toy: "duck", w: 96 },
  { toy: "bear", w: 92 },
  { toy: "panda", w: 86 },
  { toy: "bunny", w: 78 },
  { toy: "dino", w: 92 },
  { toy: "penguin", w: 84 },
  { toy: "fox", w: 80 },
  { toy: "frog", w: 76 },
  { toy: "whale", w: 90 },
  { toy: "cat", w: 74 },
  { toy: "puppy", w: 72 },
  { toy: "unicorn", w: 82 }
];
var rand = (a, b) => a + Math.random() * (b - a);
var CONFETTI = [
  { dx: -44, dy: -54, dr: -150, c: "#34c759", d: 0 },
  { dx: -30, dy: -66, dr: 120, c: "#ffd60a", d: 0.05 },
  { dx: -14, dy: -76, dr: -80, c: "#5cd679", d: 0.02 },
  { dx: 2, dy: -80, dr: 60, c: "#5a93c9", d: 0.07 },
  { dx: 16, dy: -74, dr: -130, c: "#ffb340", d: 0.03 },
  { dx: 30, dy: -64, dr: 100, c: "#a8e6b8", d: 0.06 },
  { dx: 44, dy: -52, dr: -110, c: "#34c759", d: 0.01 },
  { dx: -54, dy: -36, dr: 90, c: "#e58ab0", d: 0.09 },
  { dx: 54, dy: -34, dr: -70, c: "#5a93c9", d: 0.08 }
];
var easeInQuad = (p) => p * p;
var easeOutCubic = (p) => 1 - Math.pow(1 - p, 3);
var easeInOutCubic = (p) => p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
var clamp01 = (p) => Math.min(1, Math.max(0, p));
var T = {
  antic: 0.16,
  // tiny upward anticipation before the dive
  down: 0.78,
  // cable pays out, accelerating
  dwell1: 0.18,
  // momentum carries the claw a touch past the stop, then settles
  close: 0.45,
  // fingers close, decelerating
  dwell2: 0.26,
  // grip settles before the lift
  load: 0.24,
  // the cable takes the toy's weight: a visible strain dip
  up: 0.95,
  // slow ease-in-out retract
  open: 0.4
  // fingers release over the tray
};
var ANTIC_RISE = 8;
var DROP_G = 1150;
var ENTRANCE_G = 1500;
var shuffle = (arr) => {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};
function scatterPile(target) {
  const order = shuffle(TOY_SET);
  const rest = order.filter((t) => t.toy !== target);
  const tgt = order.find((t) => t.toy === target);
  const nB = 8;
  const nTop = order.length - nB;
  const bottomIdx = 2 + Math.floor(Math.random() * 4);
  const slots = new Array(order.length);
  let r = 0;
  const frontW = [];
  const frontToy = [];
  for (let i = 0; i < nB; i++) {
    const isTarget = i === bottomIdx;
    const t = isTarget ? tgt : rest[r++];
    frontToy.push(t);
    frontW.push(t.w * (isTarget ? rand(1, 1.05) : rand(0.76, 0.86)));
  }
  const xs = [0];
  for (let i = 1; i < nB; i++) {
    xs.push(xs[i - 1] + (frontW[i - 1] + frontW[i]) / 2 * rand(0.62, 0.68));
  }
  const span = xs[nB - 1];
  const fit = Math.min(1, (GW - 80) / span);
  for (let i = 0; i < nB; i++) frontW[i] *= fit;
  const offset = (GW - span * fit) / 2;
  const centers = [];
  for (let i = 0; i < nB; i++) {
    const cx = offset + xs[i] * fit + rand(-3, 3);
    centers.push(cx);
    const isTarget = i === bottomIdx;
    slots[i] = {
      toy: frontToy[i].toy,
      w: frontW[i],
      x: Math.min(GW - 26, Math.max(26, cx)),
      b: rand(0, 2),
      // planted on the floor, not hovering over it
      z: isTarget ? 4 : 2,
      // target drawn in front of its neighbours
      rot: rand(-7, 7),
      dropFrom: -rand(340, 440),
      delay: i * 0.05 + rand(0, 0.1)
    };
  }
  const gaps = [];
  for (let g = 0; g < nB - 1; g++) {
    if (g === bottomIdx - 1 || g === bottomIdx) continue;
    gaps.push(g);
  }
  const useGaps = shuffle(gaps).slice(0, nTop);
  let ti = 0;
  for (const g of useGaps) {
    const t = rest[r++];
    const cx = (centers[g] + centers[g + 1]) / 2 + rand(-3, 3);
    slots[nB + ti] = {
      toy: t.toy,
      w: t.w * rand(0.7, 0.8),
      x: Math.min(GW - 26, Math.max(26, cx)),
      b: rand(6, 16),
      // low: peeking over shoulders, base out of sight
      z: 1,
      // BEHIND the floor row
      rot: rand(-8, 8),
      dropFrom: -rand(360, 470),
      delay: 0.45 + ti * 0.08 + rand(0, 0.1)
      // settle in after the floor row
    };
    ti++;
  }
  const tip = slots[nB + Math.floor(Math.random() * nTop)];
  tip.rot = rand(10, 16) * (Math.random() < 0.5 ? -1 : 1);
  return slots;
}
function ClawCaptcha({
  target: targetProp,
  onVerify,
  title = "Verify you\u2019re human",
  assetBase = "/toys/",
  className
}) {
  const reduce = useReducedMotion();
  const [autoTarget] = useState(() => TOY_SET[Math.floor(Math.random() * TOY_SET.length)].toy);
  const target = targetProp ?? autoTarget;
  const [phase, setPhase] = useState("idle");
  const [infoOpen, setInfoOpen] = useState(false);
  const [verified, setVerified] = useState(false);
  const [message, setMessage] = useState(null);
  const [overTray, setOverTray] = useState(false);
  const [trayMode, setTrayMode] = useState("");
  const pile = useMemo(() => scatterPile(target), [target]);
  const rigEl = useRef(null);
  const clawEl = useRef(null);
  const coilEl = useRef(null);
  const fingerL = useRef(null);
  const fingerR = useRef(null);
  const carriedEl = useRef(null);
  const stickEl = useRef(null);
  const trolleyEl = useRef(null);
  const shadowEl = useRef(null);
  const machineEl = useRef(null);
  const trayEl = useRef(null);
  const pileEls = useRef([]);
  const dir = useRef(0);
  const phaseRef = useRef("idle");
  const onVerifyRef = useRef(onVerify);
  onVerifyRef.current = onVerify;
  const sim = useRef({
    x: GW / 2,
    y: HOME_Y,
    vx: 0,
    drive: 0,
    // smoothed steering input (eases abrupt key/stick changes)
    sway: 0,
    swayV: 0,
    breeze: 0,
    // sub-degree ambient sway so the rig never freezes solid
    close: 0,
    carried: -1,
    carry: { x: 0, y: 0 },
    // scripted-sequence bookkeeping
    stage: "",
    st: 0,
    // seconds inside the current stage
    depthY: DROP_Y,
    // how far the cable pays out THIS grab (reaches the toy's head)
    fallV: 0,
    stretch: 0,
    // 0..~0.09 vertical stretch while falling fast (squash-and-stretch)
    xrot: 0,
    // extra rotation on the carried toy (pickup tilt / dangle lag / impact)
    swallow: 0,
    // 0..1 shrink+fade as a WRONG toy is dismissed off the lid
    released: false,
    // the claw has let go this drop (one-shot)
    mouthY: 353
    // the hatch rim line in machine space — measured at release time
  });
  const softRef = useRef(null);
  if (softRef.current === null) {
    softRef.current = pile.map((s) => ({
      dx: 0,
      dy: 0,
      rot: 0,
      sq: 0,
      vdx: 0,
      vdy: 0,
      vrot: 0,
      vsq: 0,
      ey: s.dropFrom,
      evy: 0,
      delay: s.delay,
      landed: false
    }));
  }
  const setPhaseBoth = (p) => {
    phaseRef.current = p;
    setPhase(p);
  };
  const api = useRef({ setPhaseBoth, setMessage, setVerified, setOverTray, setTrayMode });
  api.current = { setPhaseBoth, setMessage, setVerified, setOverTray, setTrayMode };
  const targetIdx = useMemo(() => pile.findIndex((p) => p.toy === target), [pile, target]);
  useEffect(() => {
    const s = sim.current;
    const soft = softRef.current;
    let raf = 0;
    let wasOverTray = false;
    let prevNow = 0;
    const speedMul = reduce ? 2.4 : 1;
    if (reduce) {
      soft.forEach((b) => {
        b.ey = 0;
        b.landed = true;
      });
    }
    const toyCenter = (i) => {
      const p = pile[i];
      return { x: p.x, y: GH - p.b - p.w / 2 * 0.92 };
    };
    const ripple = (x, power, except = -1) => {
      pile.forEach((p, i) => {
        if (i === except || i === s.carried) return;
        const d = Math.abs(p.x - x);
        if (d < 80) {
          const f = (1 - d / 80) * power;
          const side = p.x < x ? -1 : 1;
          const b = soft[i];
          b.vdx += side * f * 1.6;
          b.vdy -= f * 1.1;
          b.vrot += side * f * 2;
          b.vsq += f * 0.02;
        }
      });
    };
    const pend = () => {
      const len = Math.max(2, s.y - RAIL_Y);
      const rad = reduce ? 0 : (s.sway + s.breeze) * Math.PI / 180;
      return { ex: s.x + Math.sin(rad) * len, ey: RAIL_Y + Math.cos(rad) * len };
    };
    const gripY = (ey) => ey + GRIP_OFFSET + (s.carried >= 0 ? pile[s.carried].w : 80) / 2;
    const candidateAt = (x) => {
      let best = -1;
      let bestScore = -Infinity;
      pile.forEach((q, i) => {
        const d = Math.abs(q.x - x);
        if (d < GRAB_RADIUS) {
          const score = q.z * 100 - d;
          if (score > bestScore) {
            bestScore = score;
            best = i;
          }
        }
      });
      return best;
    };
    const render = () => {
      const sway = reduce ? 0 : s.sway + s.breeze;
      const len = Math.max(2, s.y - RAIL_Y);
      if (trolleyEl.current) trolleyEl.current.style.transform = `translateX(${(s.x - 14).toFixed(2)}px)`;
      if (shadowEl.current) {
        const rad = sway * Math.PI / 180;
        const ex = s.x + Math.sin(rad) * len;
        const bottomY = s.carried >= 0 ? s.carry.y + pile[s.carried].w / 2 : s.y + 58;
        const t2 = clamp01(1 - (GH - bottomY) / 210);
        shadowEl.current.style.transform = `translateX(${(ex - 45).toFixed(2)}px) scaleX(${(1.25 - 0.5 * t2).toFixed(3)})`;
        shadowEl.current.style.opacity = (0.1 + 0.3 * t2).toFixed(3);
      }
      if (rigEl.current) {
        const totalH = len + 70;
        rigEl.current.setAttribute("viewBox", `0 0 36 ${totalH.toFixed(1)}`);
        rigEl.current.setAttribute("height", totalH.toFixed(1));
        rigEl.current.style.transform = `translateX(${s.x.toFixed(2)}px) rotate(${sway.toFixed(2)}deg)`;
      }
      coilEl.current?.setAttribute("transform", `translate(9 0) scale(1 ${(len / 100).toFixed(4)})`);
      clawEl.current?.setAttribute("transform", `translate(18 ${len.toFixed(2)}) scale(2.5) translate(-20.6 -8.9)`);
      const pinch = 15 * s.close;
      fingerL.current?.setAttribute("transform", `rotate(${pinch.toFixed(2)} ${CLAW_PIVOT.x} ${CLAW_PIVOT.y})`);
      fingerR.current?.setAttribute("transform", `rotate(${(-pinch).toFixed(2)} ${CLAW_PIVOT.x} ${CLAW_PIVOT.y})`);
      for (let i = 0; i < pile.length; i++) {
        const el = pileEls.current[i];
        if (!el) continue;
        const b = soft[i];
        el.style.transform = `translate(${b.dx.toFixed(2)}px, ${(b.dy + b.ey).toFixed(2)}px) rotate(${(pile[i].rot + b.rot).toFixed(2)}deg) scale(${(1 - b.sq * 0.6).toFixed(3)}, ${(1 + b.sq).toFixed(3)})`;
      }
      if (s.carried >= 0 && carriedEl.current) {
        const w = pile[s.carried].w;
        const sc = 1 - s.swallow * 0.78;
        const sx = (sc * (1 - s.stretch * 0.55)).toFixed(3);
        const sy = (sc * (1 + s.stretch)).toFixed(3);
        carriedEl.current.style.transform = `translate(${s.carry.x - w / 2}px, ${s.carry.y - w / 2}px) rotate(${(sway + s.xrot).toFixed(2)}deg) scale(${sx}, ${sy})`;
        if (s.swallow > 0) carriedEl.current.style.opacity = (1 - s.swallow).toFixed(2);
      }
    };
    const stageP = (dur, dt) => {
      s.st += dt;
      return clamp01(s.st / dur);
    };
    const nextStage = (st) => {
      s.stage = st;
      s.st = 0;
    };
    const step = (now) => {
      const dtRaw = prevNow ? Math.min(0.04, Math.max(4e-3, (now - prevNow) / 1e3)) : 1 / 60;
      prevNow = now;
      const dt = dtRaw * speedMul;
      const f = dt * 60;
      const ph = phaseRef.current;
      const a = api.current;
      if (!reduce) {
        const lean = ph === "idle" || ph === "carry" ? -s.vx * 0.042 : 0;
        s.swayV += (lean - s.sway) * 0.05 * f;
        s.swayV *= Math.pow(0.93, f);
        s.sway += s.swayV * f;
        s.breeze = Math.sin(now / 1500) * 0.45 + Math.sin(now / 521) * 0.12;
      }
      for (let i = 0; i < soft.length; i++) {
        const b = soft[i];
        if (!b.landed) {
          if (b.delay > 0) {
            b.delay -= dt;
          } else {
            b.evy += ENTRANCE_G * dt;
            b.ey += b.evy * dt;
            if (b.ey >= 0) {
              b.ey = 0;
              b.landed = true;
              b.vsq += Math.min(0.055, b.evy * 6e-5);
              b.vrot += rand(-0.8, 0.8);
              ripple(pile[i].x, Math.min(0.22, b.evy * 2e-4), i);
            }
          }
        }
        b.vdx += -b.dx * 0.055 * f;
        b.vdy += -b.dy * 0.055 * f;
        b.vrot += -b.rot * 0.05 * f;
        b.vsq += -b.sq * 0.13 * f;
        const damp = Math.pow(0.9, f);
        b.vdx *= damp;
        b.vdy *= damp;
        b.vrot *= Math.pow(0.91, f);
        b.vsq *= Math.pow(0.84, f);
        b.dx += b.vdx * f;
        b.dy += b.vdy * f;
        b.rot += b.vrot * f;
        b.sq += b.vsq * f;
      }
      if (ph === "idle" || ph === "carry") {
        s.drive += (dir.current - s.drive) * (1 - Math.exp(-13 * dt));
        s.vx += s.drive * 720 * dt;
        s.vx *= Math.exp(-5.5 * dt);
        s.x = Math.min(CLAW_MAX, Math.max(CLAW_MIN, s.x + s.vx * dt));
        if (ph === "carry") {
          s.xrot += (s.sway * 0.5 - s.xrot) * (1 - Math.exp(-6 * dt));
          const { ex, ey } = pend();
          s.carry.x = ex;
          s.carry.y = gripY(ey);
          const over = s.x >= TRAY.min && s.x <= TRAY.max;
          if (over !== wasOverTray) {
            wasOverTray = over;
            a.setOverTray(over);
          }
        }
      } else if (ph === "seq") {
        if (s.stage === "antic") {
          const p = stageP(T.antic, dt);
          s.y = HOME_Y - ANTIC_RISE * easeOutCubic(p);
          s.close = -0.55 * easeOutCubic(p);
          if (p >= 1) {
            const cand = candidateAt(s.x);
            if (cand >= 0) {
              const c = toyCenter(cand);
              s.depthY = Math.min(GH - 46, Math.max(HOME_Y + 50, c.y - GRIP_OFFSET - pile[cand].w / 2));
            } else {
              s.depthY = DROP_Y;
            }
            nextStage("down");
          }
        } else if (s.stage === "down") {
          const p = stageP(T.down, dt);
          s.y = HOME_Y - ANTIC_RISE + (s.depthY - HOME_Y + ANTIC_RISE) * easeInQuad(p);
          if (s.y > 130 && !reduce) {
            pile.forEach((q, i) => {
              const d = Math.abs(q.x - s.x);
              if (d < 56) {
                const push = (1 - d / 56) * 7 * dt;
                const side = q.x < s.x ? -1 : 1;
                soft[i].vdx += side * push;
                soft[i].vsq += push * 0.012;
              }
            });
          }
          if (p >= 1) nextStage("dwell1");
        } else if (s.stage === "dwell1") {
          const p = stageP(T.dwell1, dt);
          s.y = s.depthY + (reduce ? 0 : 3.5 * Math.sin(Math.PI * p));
          if (p >= 1) {
            s.y = s.depthY;
            nextStage("close");
          }
        } else if (s.stage === "close") {
          const p = stageP(T.close, dt);
          s.close = -0.55 + 1.55 * easeOutCubic(p);
          if (p >= 1) {
            const best = candidateAt(s.x);
            s.carried = best;
            if (best >= 0) {
              s.carry = { ...toyCenter(best) };
              s.xrot = pile[best].rot + soft[best].rot;
              const el = pileEls.current[best];
              if (el) el.style.visibility = "hidden";
              ripple(pile[best].x, 0.35, best);
              if (carriedEl.current) {
                carriedEl.current.src = el?.src ?? carriedEl.current.src;
                carriedEl.current.style.width = `${pile[best].w}px`;
                carriedEl.current.style.visibility = "visible";
                carriedEl.current.style.opacity = "";
              }
            } else {
              ripple(s.x, 0.2);
            }
            nextStage("dwell2");
          }
        } else if (s.stage === "dwell2") {
          if (stageP(T.dwell2, dt) >= 1) nextStage(s.carried >= 0 && !reduce ? "load" : "up");
          if (s.carried >= 0) {
            s.xrot += -s.xrot * (1 - Math.exp(-3.5 * dt));
            const { ex, ey } = pend();
            s.carry.x = ex;
            s.carry.y = gripY(ey);
          }
        } else if (s.stage === "load") {
          const p = stageP(T.load, dt);
          const bell = Math.sin(Math.PI * p);
          s.y = s.depthY + 6 * bell;
          s.close = 1 + 0.12 * bell;
          s.xrot += -s.xrot * (1 - Math.exp(-3.5 * dt));
          const { ex, ey } = pend();
          s.carry.x = ex;
          s.carry.y = gripY(ey);
          if (p >= 1) {
            s.y = s.depthY;
            nextStage("up");
          }
        } else if (s.stage === "up") {
          const p = stageP(T.up, dt);
          s.y = s.depthY + (HOME_Y - s.depthY) * easeInOutCubic(p);
          if (s.carried >= 0) {
            s.xrot += -s.xrot * (1 - Math.exp(-3.5 * dt));
            const { ex, ey } = pend();
            s.carry.x = ex;
            s.carry.y = gripY(ey);
          }
          if (p >= 1) {
            if (s.carried >= 0) {
              a.setPhaseBoth("carry");
              a.setMessage(null);
            } else {
              a.setPhaseBoth("idle");
              a.setMessage("什么都没抓到，再试一次");
            }
          }
        }
      } else if (ph === "toTray") {
        const right = s.carried === targetIdx;
        if (s.stage === "open") {
          const p = stageP(T.open, dt);
          s.close = 1 - easeOutCubic(p);
          if (s.st > 0.12 && !s.released) {
            s.released = true;
            if (right) {
              a.setTrayMode("open");
              if (reduce) {
                if (carriedEl.current) carriedEl.current.style.visibility = "hidden";
                s.carried = -1;
                a.setOverTray(false);
                a.setTrayMode("win");
                nextStage("beat");
                a.setPhaseBoth("celebrate");
              } else {
                const m = machineEl.current?.getBoundingClientRect();
                const tr = trayEl.current?.getBoundingClientRect();
                if (m && tr) s.mouthY = tr.top - m.top + 2;
                s.fallV = 30;
              }
            } else {
              s.fallV = 40;
            }
          }
        }
        if (right && s.released && s.carried >= 0) {
          s.fallV = Math.min(s.fallV + DROP_G * dt, 460);
          s.carry.y += s.fallV * dt;
          s.carry.x += (TRAY.cx - s.carry.x) * (1 - Math.exp(-2.2 * dt));
          s.xrot += -s.xrot * (1 - Math.exp(-4 * dt));
          s.stretch = Math.abs(s.fallV) / 460 * 0.09;
          const w = pile[s.carried].w;
          const sunk = s.carry.y + w / 2 - s.mouthY;
          if (sunk > 0 && carriedEl.current) {
            carriedEl.current.style.clipPath = `inset(0 0 ${sunk.toFixed(1)}px 0)`;
            carriedEl.current.style.filter = `brightness(${Math.max(0.4, 1 - sunk / w * 0.75).toFixed(3)})`;
          }
          if (sunk >= w + 4) {
            if (carriedEl.current) {
              carriedEl.current.style.visibility = "hidden";
              carriedEl.current.style.clipPath = "";
              carriedEl.current.style.filter = "";
            }
            s.carried = -1;
            a.setOverTray(false);
            a.setTrayMode("win");
            nextStage("beat");
            a.setPhaseBoth("celebrate");
          }
        }
        if (!right && s.fallV !== 0) {
          s.fallV = Math.min(s.fallV + DROP_G * dt, 360);
          s.carry.y += s.fallV * dt;
          s.carry.x += (TRAY.cx - s.carry.x) * (1 - Math.exp(-4 * dt));
          s.xrot += -s.xrot * (1 - Math.exp(-3 * dt));
          s.stretch = Math.abs(s.fallV) / 460 * 0.09;
          if (s.fallV > 0 && s.carry.y >= TRAY.cy) {
            if (s.fallV > 200) {
              s.carry.y = TRAY.cy;
              s.fallV = -s.fallV * 0.28;
              s.xrot += rand(-7, 7);
            } else {
              s.carry.y = TRAY.cy;
              s.fallV = 0;
              s.stretch = 0;
              a.setOverTray(false);
              a.setTrayMode("no");
              a.setMessage(
                `这是${TOY_META[pile[s.carried].toy].label}！请找${TOY_META[target].label}。`
              );
              nextStage("beat");
              a.setPhaseBoth("deny");
            }
          }
        }
      } else if (ph === "celebrate") {
        if (s.stage === "beat") {
          if (stageP(0.28, dt) >= 1) {
            nextStage("shine");
            api.current.setVerified(true);
            onVerifyRef.current?.();
          }
        } else if (s.stage === "shine") {
          if (stageP(0.7, dt) >= 1) api.current.setPhaseBoth("done");
        }
      } else if (ph === "deny") {
        if (s.stage === "beat") {
          const p = stageP(0.46, dt);
          s.swallow = easeOutCubic(p);
          s.carry.y -= 46 * dt;
          if (p >= 1) {
            const idx = s.carried;
            api.current.setTrayMode("");
            const el = pileEls.current[idx];
            if (el) el.style.visibility = "";
            if (carriedEl.current) {
              carriedEl.current.style.visibility = "hidden";
              carriedEl.current.style.opacity = "";
              carriedEl.current.style.clipPath = "";
              carriedEl.current.style.filter = "";
            }
            s.swallow = 0;
            const b = soft[idx];
            b.vsq += 0.05;
            b.vrot += rand(-1, 1);
            ripple(pile[idx].x, 0.25, idx);
            s.carried = -1;
            a.setPhaseBoth("idle");
          }
        }
      }
      render();
      raf = requestAnimationFrame(step);
    };
    render();
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [reduce, targetIdx, target, pile]);
  const action = () => {
    const s = sim.current;
    if (verified) return;
    if (phaseRef.current === "idle") {
      setMessage(null);
      s.close = 0;
      s.stage = "antic";
      s.st = 0;
      setPhaseBoth("seq");
    } else if (phaseRef.current === "carry") {
      if (s.x >= TRAY.min && s.x <= TRAY.max) {
        if (carriedEl.current) {
          carriedEl.current.style.visibility = "visible";
          carriedEl.current.style.opacity = "";
          carriedEl.current.style.clipPath = "";
          carriedEl.current.style.filter = "";
        }
        s.stage = "open";
        s.st = 0;
        s.fallV = 0;
        s.swallow = 0;
        s.stretch = 0;
        s.released = false;
        setOverTray(false);
        setPhaseBoth("toTray");
      } else {
        setMessage("先把玩具移到投放区上方");
      }
    }
  };
  const stickDrag = useRef(null);
  const onStickDown = (e) => {
    if (verified) return;
    e.target.setPointerCapture(e.pointerId);
    stickDrag.current = { id: e.pointerId, startX: e.clientX };
    if (stickEl.current) stickEl.current.style.transition = "none";
  };
  const onStickMove = (e) => {
    const d = stickDrag.current;
    if (!d || e.pointerId !== d.id) return;
    const dx = Math.max(-26, Math.min(26, e.clientX - d.startX));
    dir.current = dx / 26;
    if (stickEl.current) stickEl.current.style.transform = `rotate(${(dx * 1.05).toFixed(1)}deg)`;
  };
  const onStickUp = (e) => {
    if (stickDrag.current?.id !== e.pointerId) return;
    stickDrag.current = null;
    dir.current = 0;
    if (stickEl.current) {
      stickEl.current.style.transition = "transform 0.25s cubic-bezier(0.2, 1.6, 0.4, 1)";
      stickEl.current.style.transform = "";
    }
  };
  const onKeyDown = (e) => {
    if (infoOpen) {
      if (e.key === "Escape") setInfoOpen(false);
      return;
    }
    if (verified) return;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      dir.current = -1;
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      dir.current = 1;
    } else if ((e.key === " " || e.key === "Enter") && !e.repeat) {
      e.preventDefault();
      action();
    }
  };
  const onKeyUp = (e) => {
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") dir.current = 0;
  };
  const t = TOY_META[target];
  const busy = phase !== "idle" && phase !== "carry";
  const stepNo = verified || phase === "carry" || phase === "toTray" || phase === "celebrate" ? 3 : phase === "seq" ? 2 : 1;
  const carried = sim.current.carried;
  const carriedW = carried >= 0 ? pile[carried].w : 80;
  return (
    // app-wide reduced-motion safety net: under prefers-reduced-motion, Motion
    // drops transform/position animation and keeps opacity — meaningful state
    // still reads, nothing slides.
    /* @__PURE__ */ jsx(MotionConfig, { reducedMotion: "user", children: /* @__PURE__ */ jsxs(
      motion.div,
      {
        className: className ? `clawcap ${className}` : "clawcap",
        role: "group",
        "aria-label": "抓娃娃人机验证",
        tabIndex: 0,
        onKeyDown,
        onKeyUp,
        initial: reduce ? false : { opacity: 0, y: 16, scale: 0.985 },
        animate: { opacity: 1, y: 0, scale: 1 },
        transition: { duration: 0.55, ease: [0.2, 0.8, 0.2, 1] },
        children: [
          /* @__PURE__ */ jsxs("header", { className: "clawcap-top", children: [
            /* @__PURE__ */ jsx(
              motion.span,
              {
                className: verified ? "clawcap-shield clawcap-shield--ok" : "clawcap-shield",
                "aria-hidden": "true",
                initial: verified ? { scale: 0.55 } : false,
                animate: { scale: 1 },
                transition: { type: "spring", stiffness: 420, damping: 20 },
                children: /* @__PURE__ */ jsxs("svg", { viewBox: "0 0 20 20", width: "14", height: "14", children: [
                  /* @__PURE__ */ jsx(
                    "path",
                    {
                      d: "M10 2.2 4 4.6v4.6c0 4 2.6 6.7 6 8.2 3.4-1.5 6-4.2 6-8.2V4.6Z",
                      fill: "none",
                      stroke: "currentColor",
                      strokeWidth: "1.5",
                      strokeLinejoin: "round"
                    }
                  ),
                  verified && /* @__PURE__ */ jsx("path", { d: "m7 9.8 2.2 2.2L13.4 7.6", fill: "none", stroke: "currentColor", strokeWidth: "1.7", strokeLinecap: "round", strokeLinejoin: "round" })
                ] })
              },
              verified ? "ok" : "idle"
            ),
            /* @__PURE__ */ jsx(
              "button",
              {
                type: "button",
                className: "clawcap-help",
                "aria-label": "关于抓娃娃验证",
                "aria-haspopup": "dialog",
                onClick: () => setInfoOpen(true),
                children: /* @__PURE__ */ jsxs("svg", { viewBox: "0 0 20 20", width: "14", height: "14", "aria-hidden": "true", children: [
                  /* @__PURE__ */ jsx("circle", { cx: "10", cy: "10", r: "7.4", fill: "none", stroke: "currentColor", strokeWidth: "1.4" }),
                  /* @__PURE__ */ jsx("path", { d: "M8 8.2c.2-1.2 1-1.9 2.1-1.9 1.2 0 2 .8 2 1.8 0 1.6-2.1 1.7-2.1 3.2", fill: "none", stroke: "currentColor", strokeWidth: "1.4", strokeLinecap: "round" }),
                  /* @__PURE__ */ jsx("circle", { cx: "10", cy: "13.9", r: "0.9", fill: "currentColor" })
                ] })
              }
            )
          ] }),
          /* @__PURE__ */ jsx(AnimatePresence, { children: infoOpen && /* @__PURE__ */ jsx(
            motion.div,
            {
              className: "clawcap-info",
              role: "dialog",
              "aria-modal": "true",
              "aria-label": "关于抓娃娃验证",
              onClick: () => setInfoOpen(false),
              initial: { opacity: 0 },
              animate: { opacity: 1 },
              exit: { opacity: 0 },
              transition: { duration: 0.18 },
              children: /* @__PURE__ */ jsxs(
                motion.div,
                {
                  className: "clawcap-info-card",
                  onClick: (e) => e.stopPropagation(),
                  initial: reduce ? false : { opacity: 0, scale: 0.92, y: 10 },
                  animate: { opacity: 1, scale: 1, y: 0 },
                  exit: { opacity: 0, scale: 0.97, transition: { duration: 0.13, ease: "easeOut" } },
                  transition: { type: "spring", stiffness: 360, damping: 28 },
                  children: [
                    /* @__PURE__ */ jsx(
                      "button",
                      {
                        type: "button",
                        className: "clawcap-info-x",
                        "aria-label": "关闭",
                        onClick: () => setInfoOpen(false),
                        children: /* @__PURE__ */ jsx("svg", { viewBox: "0 0 20 20", width: "14", height: "14", "aria-hidden": "true", children: /* @__PURE__ */ jsx("path", { d: "M5 5l10 10M15 5 5 15", fill: "none", stroke: "currentColor", strokeWidth: "1.7", strokeLinecap: "round" }) })
                      }
                    ),
                    /* @__PURE__ */ jsxs("div", { className: "clawcap-info-head", children: [
                      /* @__PURE__ */ jsx("span", { className: "clawcap-info-tile", children: /* @__PURE__ */ jsx("img", { src: "/playcaptcha.svg", alt: "", "aria-hidden": "true" }) }),
                      /* @__PURE__ */ jsxs("h4", { className: "clawcap-info-title", children: [
                        "抓娃娃验证 ",
                        /* @__PURE__ */ jsx("span", { className: "clawcap-info-ver", children: "v1" })
                      ] }),
                      /* @__PURE__ */ jsx("p", { className: "clawcap-info-tag", children: "抓住指定的玩具，证明你是真人。" })
                    ] }),
                    /* @__PURE__ */ jsx("ol", { className: "clawcap-info-list", children: [
                      ["移动", /* @__PURE__ */ jsxs(Fragment, { children: [
                        "把爪子对准目标玩具 \u2014 拖动摇杆或按 ",
                        /* @__PURE__ */ jsx("kbd", { children: "\u2190" }),
                        " ",
                        /* @__PURE__ */ jsx("kbd", { children: "\u2192" })
                      ] })],
                      ["抓取", /* @__PURE__ */ jsxs(Fragment, { children: [
                        "按下后爪子会下探、夹住并提起 \u2014 点击红色按钮或按 ",
                        /* @__PURE__ */ jsx("kbd", { children: "空格" })
                      ] })],
                      ["投放", /* @__PURE__ */ jsx(Fragment, { children: "把它送到投放口再松手；抓错了会自动放回堆积区" })]
                    ].map(([label, desc], i) => /* @__PURE__ */ jsxs("li", { children: [
                      /* @__PURE__ */ jsx("span", { className: "clawcap-info-n", children: i + 1 }),
                      /* @__PURE__ */ jsxs("span", { children: [
                        /* @__PURE__ */ jsx("strong", { children: label }),
                        /* @__PURE__ */ jsx("span", { className: "clawcap-info-d", children: desc })
                      ] })
                    ] }, label)) }),
                    /* @__PURE__ */ jsx("button", { type: "button", className: "clawcap-info-done", onClick: () => setInfoOpen(false), children: "知道了" })
                  ]
                }
              )
            }
          ) }),
          /* @__PURE__ */ jsx("h3", { className: "clawcap-title", children: /* @__PURE__ */ jsx(AnimatePresence, { mode: "wait", initial: false, children: /* @__PURE__ */ jsx(
            motion.span,
            {
              style: { display: "inline-block" },
              initial: { opacity: 0, y: 5 },
              animate: { opacity: 1, y: 0 },
              exit: { opacity: 0, y: -5 },
              transition: { duration: 0.24, ease: "easeOut" },
              children: verified ? "Verified" : title
            },
            verified ? "verified" : "title"
          ) }) }),
          /* @__PURE__ */ jsx("p", { className: "clawcap-sub", "aria-live": "polite", children: /* @__PURE__ */ jsx(AnimatePresence, { mode: "wait", initial: false, children: /* @__PURE__ */ jsx(
            motion.span,
            {
              style: { display: "inline-block" },
              initial: { opacity: 0, y: 4 },
              animate: { opacity: 1, y: 0 },
              exit: { opacity: 0, y: -4 },
              transition: { duration: 0.2, ease: "easeOut" },
              children: verified ? "验证通过，干得漂亮。" : message ? message : /* @__PURE__ */ jsxs(Fragment, { children: [
                "用爪子抓起",
                " ",
                /* @__PURE__ */ jsxs("em", { style: { color: t.accent }, children: [
                  /* @__PURE__ */ jsx("img", { className: "clawcap-sub-toy", src: `${assetBase}${target}.png`, alt: "", draggable: false }),
                  t.label
                ] })
              ] })
            },
            verified ? "done" : message ?? "challenge"
          ) }) }),
          /* @__PURE__ */ jsxs("ol", { className: "clawcap-steps", "aria-hidden": "true", children: [
            /* @__PURE__ */ jsx("span", { className: "clawcap-steps-pill", style: { transform: `translateX(${(stepNo - 1) * 100}%)` } }),
            ["移动", "抓取", "投放"].map((label, i) => /* @__PURE__ */ jsxs("li", { className: stepNo === i + 1 ? "is-active" : void 0, children: [
              /* @__PURE__ */ jsx("span", { className: "clawcap-step-n", children: i + 1 }),
              " ",
              label
            ] }, label))
          ] }),
          /* @__PURE__ */ jsxs("div", { ref: machineEl, className: "clawcap-machine", children: [
            /* @__PURE__ */ jsxs("div", { className: "clawcap-case", children: [
              /* @__PURE__ */ jsxs("div", { className: verified ? "clawcap-glass clawcap-glass--dim" : "clawcap-glass", children: [
                /* @__PURE__ */ jsx("div", { className: "cc-rail" }),
                /* @__PURE__ */ jsx("div", { ref: trolleyEl, className: "cc-trolley", "aria-hidden": "true" }),
                /* @__PURE__ */ jsx("div", { ref: shadowEl, className: "cc-claw-shadow", "aria-hidden": "true" }),
                pile.map((p, i) => /* @__PURE__ */ jsx(
                  "img",
                  {
                    ref: (el) => {
                      pileEls.current[i] = el;
                    },
                    className: "cc-toy",
                    src: `${assetBase}${p.toy}.png`,
                    alt: "",
                    draggable: false,
                    style: {
                      left: p.x - p.w / 2,
                      bottom: p.b,
                      width: p.w,
                      zIndex: p.z,
                      transform: `translateY(${p.dropFrom}px)`,
                      transformOrigin: "50% 100%"
                    }
                  },
                  p.toy
                )),
                /* @__PURE__ */ jsx("div", { className: "cc-pile-shadow" }),
                /* @__PURE__ */ jsxs("svg", { ref: rigEl, className: "cc-rig", width: "36", height: COIL_LEN + 70, viewBox: `0 0 36 ${COIL_LEN + 70}`, "aria-hidden": "true", children: [
                  /* @__PURE__ */ jsx("g", { ref: coilEl, transform: `translate(9 0) scale(1 ${COIL_LEN / 100})`, children: /* @__PURE__ */ jsx(
                    "path",
                    {
                      d: "M9 0 L9 5 C 15 7.5 15 9.5 9 12 C 3 14.5 3 16.5 9 19 C 15 21.5 15 23.5 9 26 C 3 28.5 3 30.5 9 33 C 15 35.5 15 37.5 9 40 C 3 42.5 3 44.5 9 47 C 15 49.5 15 51.5 9 54 C 3 56.5 3 58.5 9 61 C 15 63.5 15 65.5 9 68 C 3 70.5 3 72.5 9 75 C 15 77.5 15 79.5 9 82 C 3 84.5 3 86.5 9 89 C 15 91.5 15 93.5 9 95 L 9 100",
                      fill: "none",
                      stroke: "#9A9FA8",
                      strokeWidth: "2.2",
                      strokeLinecap: "round",
                      strokeLinejoin: "round",
                      vectorEffect: "non-scaling-stroke"
                    }
                  ) }),
                  /* @__PURE__ */ jsxs("g", { ref: clawEl, transform: `translate(18 ${COIL_LEN}) scale(2.5) translate(-20.6 -8.9)`, children: [
                    /* @__PURE__ */ jsx("g", { ref: fingerL, children: CLAW_ARM_L.map((p, i) => /* @__PURE__ */ jsx("path", { fill: p.fill, d: p.d }, i)) }),
                    /* @__PURE__ */ jsx("g", { ref: fingerR, children: CLAW_ARM_R.map((p, i) => /* @__PURE__ */ jsx("path", { fill: p.fill, d: p.d }, i)) }),
                    CLAW_BODY.map((p, i) => /* @__PURE__ */ jsx("path", { fill: p.fill, d: p.d }, i))
                  ] })
                ] }),
                /* @__PURE__ */ jsx("div", { className: "cc-glass-shine" })
              ] }),
              /* @__PURE__ */ jsxs("div", { className: "clawcap-panel", children: [
                /* @__PURE__ */ jsxs(
                  "div",
                  {
                    className: "cc-joy",
                    role: "slider",
                    "aria-label": "移动爪子",
                    "aria-valuemin": 0,
                    "aria-valuemax": 100,
                    "aria-valuenow": Math.round((sim.current.x - CLAW_MIN) / (CLAW_MAX - CLAW_MIN) * 100),
                    onPointerDown: onStickDown,
                    onPointerMove: onStickMove,
                    onPointerUp: onStickUp,
                    onPointerCancel: onStickUp,
                    children: [
                      /* @__PURE__ */ jsx("div", { className: "cc-joy-base" }),
                      /* @__PURE__ */ jsxs("div", { ref: stickEl, className: "cc-joy-stick", children: [
                        /* @__PURE__ */ jsx("div", { className: "cc-joy-shaft" }),
                        /* @__PURE__ */ jsx("div", { className: "cc-joy-ball" })
                      ] })
                    ]
                  }
                ),
                /* @__PURE__ */ jsxs(
                  "div",
                  {
                    ref: trayEl,
                    className: "cc-tray" + (trayMode === "open" ? " cc-tray--open" : trayMode === "win" ? " cc-tray--win" : trayMode === "no" ? " cc-tray--no" : overTray ? " cc-tray--hot" : ""),
                    children: [
                      /* @__PURE__ */ jsxs("span", { className: "cc-tray-hatch", "aria-hidden": "true", children: [
                        /* @__PURE__ */ jsx("span", { className: "cc-tray-mouth" }),
                        /* @__PURE__ */ jsx("span", { className: "cc-tray-door cc-tray-door--l" }),
                        /* @__PURE__ */ jsx("span", { className: "cc-tray-door cc-tray-door--r" }),
                        /* @__PURE__ */ jsx("span", { className: "cc-tray-skin" })
                      ] }),
                      trayMode === "win" && !reduce && /* @__PURE__ */ jsx("span", { className: "cc-confetti", "aria-hidden": "true", children: CONFETTI.map((p, i) => /* @__PURE__ */ jsx(
                        "i",
                        {
                          style: {
                            background: p.c,
                            animationDelay: `${p.d}s`,
                            "--dx": `${p.dx}px`,
                            "--dy": `${p.dy}px`,
                            "--dr": `${p.dr}deg`
                          }
                        },
                        i
                      )) }),
                      /* @__PURE__ */ jsxs("span", { className: "cc-tray-label", children: [
                        trayMode === "win" ? (
                          // a clean check — the catch is in
                          /* @__PURE__ */ jsx("svg", { viewBox: "0 0 16 16", width: "14", height: "14", "aria-hidden": "true", children: /* @__PURE__ */ jsx("path", { d: "m3.6 8.6 2.9 2.9 6-6.8", fill: "none", stroke: "currentColor", strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" }) })
                        ) : trayMode === "no" ? (
                          // try-again loop — it goes back to the pile
                          /* @__PURE__ */ jsxs("svg", { viewBox: "0 0 16 16", width: "14", height: "14", "aria-hidden": "true", children: [
                            /* @__PURE__ */ jsx("path", { d: "M13.2 8A5.2 5.2 0 1 1 11.6 4.25", fill: "none", stroke: "currentColor", strokeWidth: "1.6", strokeLinecap: "round" }),
                            /* @__PURE__ */ jsx("path", { d: "M11.7 1.5v2.9h2.9", fill: "none", stroke: "currentColor", strokeWidth: "1.6", strokeLinecap: "round", strokeLinejoin: "round" })
                          ] })
                        ) : (
                          // a toy over the parted slot — this is where the catch goes in
                          /* @__PURE__ */ jsxs("svg", { viewBox: "0 0 16 16", width: "14", height: "14", "aria-hidden": "true", children: [
                            /* @__PURE__ */ jsx("circle", { cx: "8", cy: "4.9", r: "2.7", fill: "none", stroke: "currentColor", strokeWidth: "1.5" }),
                            /* @__PURE__ */ jsx("path", { d: "M2.4 12.1h3.7M9.9 12.1h3.7", fill: "none", stroke: "currentColor", strokeWidth: "1.5", strokeLinecap: "round" })
                          ] })
                        ),
                        /* @__PURE__ */ jsx("span", { children: trayMode === "win" ? "抓到了！" : trayMode === "no" ? "抓错了玩具" : overTray ? "松手！" : "放到这里" })
                      ] })
                    ]
                  }
                ),
                /* @__PURE__ */ jsx(
                  "button",
                  {
                    type: "button",
                    className: phase === "carry" && overTray ? "cc-action cc-action--ready" : "cc-action",
                    onClick: action,
                    disabled: busy || verified,
                    "aria-label": phase === "carry" ? "放下玩具" : "抓取",
                    children: /* @__PURE__ */ jsx(AnimatePresence, { mode: "wait", initial: false, children: /* @__PURE__ */ jsx(
                      motion.span,
                      {
                        style: { display: "inline-block" },
                        initial: { opacity: 0, y: 6 },
                        animate: { opacity: 1, y: 0 },
                        exit: { opacity: 0, y: -6 },
                        transition: { duration: 0.16, ease: "easeOut" },
                        children: phase === "carry" ? "投放" : "抓取"
                      },
                      phase === "carry" ? "drop" : "grab"
                    ) })
                  }
                )
              ] })
            ] }),
            /* @__PURE__ */ jsx(
              "img",
              {
                ref: carriedEl,
                className: "cc-carried",
                src: carried >= 0 ? `${assetBase}${pile[carried].toy}.png` : `${assetBase}${target}.png`,
                alt: "",
                draggable: false,
                style: {
                  width: carriedW,
                  visibility: carried >= 0 && phase !== "idle" ? "visible" : "hidden"
                }
              }
            )
          ] }),
          /* @__PURE__ */ jsx("p", { className: "clawcap-hint", children: "拖动摇杆或按 \u2190 \u2192 移动 \xB7 空格键抓取 / 投放" })
        ]
      }
    ) })
  );
}

export { ClawCaptcha, TOY_META };
