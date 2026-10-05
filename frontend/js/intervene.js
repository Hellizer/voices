import { store } from './state.js';

const TITLES = {
  request: "попросить",
  forbid: "запретить",
  support: "поддержать",
  distract: "отвлечь",
  insist: "настоять",
  leave: "уйти",
};

const VOICES = ["body", "safety", "connection", "recognition", "interest", "control"];

const VOICE_NAMES = {
  body: "тело",
  safety: "безопасность",
  connection: "связь",
  recognition: "признание",
  interest: "интерес",
  control: "контроль",
};

const ACTION_PHRASES = {
  idle: "ничего",
  eat: "ест",
  sleep: "спит",
  drink: "пьёт",
  wash: "умывается",
  go_outside: "выходит",
  move: "двигается",
  zone_out: "смотрит в стену",
  clean: "убирает",
  fix: "чинит",
  cook: "готовит",
  arrange: "раскладывает",
  save_up: "откладывает",
  throw_away: "выбрасывает",
  work: "работает",
  side_gig: "подрабатывает",
  trade: "торгует",
  invest: "вкладывает",
  borrow: "занимает",
  spend_on_self: "тратит на себя",
  write: "пишет",
  invite: "зовёт",
  help: "помогает",
  refuse: "отказывает",
  lie: "врёт",
  break_off: "разрывает",
  come_back: "возвращается",
  do: "делает",
  show: "показывает",
  stay_silent: "молчит",
  brag: "хвастается",
  humiliate: "унижает",
  revenge: "мстит",
  read: "читает",
  learn: "учится",
  try: "пробует",
  abandon: "бросает",
  collect: "собирает",
  plan: "планирует",
  forbid_self: "запрещает себе",
  ritual: "совершает ритуал",
  break_down: "ломается",
};

let currentType = null;

function fillTargets() {
  const select = document.getElementById("modal-target");
  if (!select) return;
  select.innerHTML = "";

  const voiceGroup = document.createElement("optgroup");
  voiceGroup.label = "голоса";
  for (const v of VOICES) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = VOICE_NAMES[v] || v;
    voiceGroup.appendChild(opt);
  }
  select.appendChild(voiceGroup);

  if (store.world && store.world.locations && store.location) {
    const loc = store.world.locations[store.location];
    if (loc && Array.isArray(loc.actions_available) && loc.actions_available.length) {
      const actionGroup = document.createElement("optgroup");
      actionGroup.label = "действия";
      for (const a of loc.actions_available) {
        const opt = document.createElement("option");
        opt.value = a;
        opt.textContent = ACTION_PHRASES[a] || a;
        actionGroup.appendChild(opt);
      }
      select.appendChild(actionGroup);
    }
  }
}

export function openModal(type) {
  currentType = type;
  const modal = document.getElementById("modal");
  const title = document.getElementById("modal-title");
  const intensity = document.getElementById("modal-intensity");
  const response = document.getElementById("modal-response");
  if (!modal) return;
  if (title) title.textContent = TITLES[type] || type;
  fillTargets();
  if (intensity) intensity.value = "0.2";
  if (response) response.textContent = "";
  modal.hidden = false;
}

function closeModal() {
  const modal = document.getElementById("modal");
  if (modal) modal.hidden = true;
  currentType = null;
}

async function sendIntervention() {
  if (!currentType) return;
  const select = document.getElementById("modal-target");
  const intensityEl = document.getElementById("modal-intensity");
  const response = document.getElementById("modal-response");
  const target = select ? select.value : "";
  const intensity = intensityEl ? parseFloat(intensityEl.value) : 0.2;

  if (response) response.textContent = "отправлено...";

  try {
    const res = await fetch("/intervene", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: currentType, target, intensity }),
    });
    const data = await res.json();
    if (response) response.textContent = data.message || "";
  } catch (_) {
    if (response) response.textContent = "";
  }

  setTimeout(closeModal, 1500);
}

export function initIntervene() {
  const bar = document.getElementById("intervene-bar");
  if (bar) {
    bar.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => openModal(btn.dataset.type));
    });
  }
  const cancel = document.getElementById("modal-cancel");
  if (cancel) cancel.addEventListener("click", closeModal);
  const ok = document.getElementById("modal-ok");
  if (ok) ok.addEventListener("click", sendIntervention);
}
