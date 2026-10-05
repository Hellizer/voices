import { store } from './state.js';

const VOICE_ORDER = [
  "body",
  "safety",
  "connection",
  "recognition",
  "interest",
  "control",
];

const VOICE_RGB = {
  body: "232, 180, 184",
  safety: "228, 212, 180",
  connection: "232, 168, 152",
  recognition: "212, 180, 212",
  interest: "180, 212, 196",
  control: "168, 184, 212",
};

const BUFFER_SIZE = 220;
const SUBOFFSET_INTERVAL_MS = 600000;

let canvas = null;
let ctx = null;
let buffer = [];
let running = false;
let lastPushAt = 0;
let startedAt = 0;

const VOICE_PHASE = {};

function voiceSeed(name) {
  let h = 0;
  for (let k = 0; k < name.length; k++) {
    h = (h * 31 + name.charCodeAt(k)) | 0;
  }
  return (Math.abs(h) % 1000) / 1000;
}

for (const n of VOICE_ORDER) {
  VOICE_PHASE[n] = voiceSeed(n);
}

function emptySample() {
  const s = {};
  for (const n of VOICE_ORDER) s[n] = 0.15;
  return s;
}

function resize() {
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  const w = window.innerWidth;
  const h = window.innerHeight;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

export function pushVoiceSample(sample) {
  if (!sample) return;
  buffer.unshift(sample);
  while (buffer.length > BUFFER_SIZE) buffer.pop();
  lastPushAt = performance.now();
}

export function updateWavesFromStore() {
  const voices = store.voices || {};
  const s = {};
  let any = false;
  for (const n of VOICE_ORDER) {
    const v = voices[n];
    if (v && typeof v.memory === "number") {
      s[n] = v.memory;
      any = true;
    } else {
      s[n] = 0.15;
    }
  }
  if (any) pushVoiceSample(s);
}

function loop(now) {
  if (!running) return;
  draw(now);
  requestAnimationFrame(loop);
}

function draw(now) {
  if (!ctx || !canvas) return;
  const W = window.innerWidth;
  const H = window.innerHeight;
  ctx.clearRect(0, 0, W, H);

  const rowCount = VOICE_ORDER.length;
  const rowStep = H * 0.075;
  const centerY = H * 0.5;
  const stepX = W / (BUFFER_SIZE - 1);
  const time = (now - startedAt) * 0.0004;

  const subOffset = Math.min(1, (now - lastPushAt) / SUBOFFSET_INTERVAL_MS);

  for (let i = 0; i < rowCount; i++) {
    const name = VOICE_ORDER[i];
    const baseY = centerY + (i - (rowCount - 1) / 2) * rowStep;
    const rgb = VOICE_RGB[name];
    const seed = VOICE_PHASE[name];
    const seedShift = seed * 6.283;

    const v = store.voices && store.voices[name];
    const weight = v && typeof v.weight === "number" ? v.weight : 0.15;
    const intensity = Math.max(0.1, Math.min(1, weight * 2.5));

    const alpha = 0.1 + intensity * 0.24;
    const lineWidth = 1.2 + intensity * 2.0;

    const amp = 0.6 + Math.min(2.4, weight * 3.0);

    ctx.beginPath();
    for (let j = 0; j < BUFFER_SIZE; j++) {
      const sample = buffer[j] && typeof buffer[j][name] === "number"
        ? buffer[j][name]
        : 0.15;
      const x = (j - 1 + subOffset) * stepX;

      const dy = (sample - 0.15) * rowStep * 5.0 * amp;
      const m1 = Math.sin(x * 0.003 + seedShift + time * 0.6) * rowStep * 1.3;
      const m2 = Math.sin(x * 0.009 + seedShift * 1.7 + time * 0.9) * rowStep * 0.5;
      const m3 = Math.sin(x * 0.021 + seedShift * 3.1 + time * 1.4) * rowStep * 0.15;

      const y = baseY + dy + m1 + m2 + m3;
      if (j === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }

    ctx.strokeStyle = `rgba(${rgb}, ${alpha})`;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.shadowColor = `rgba(${rgb}, ${alpha * 0.45})`;
    ctx.shadowBlur = 14;
    ctx.stroke();
    ctx.shadowBlur = 0;
  }
}

export function initWaves() {
  canvas = document.getElementById("waves");
  if (!canvas) return;
  ctx = canvas.getContext("2d");

  for (let i = 0; i < BUFFER_SIZE; i++) buffer.push(emptySample());

  resize();
  startedAt = performance.now();
  lastPushAt = performance.now();
  running = true;
  requestAnimationFrame(loop);

  window.addEventListener("resize", resize);
}
