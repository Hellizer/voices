import { store } from './state.js';

const VOICE_NAMES = {
  body: "тело",
  safety: "безопасность",
  connection: "связь",
  recognition: "признание",
  interest: "интерес",
  control: "контроль",
};

const TRACE_TYPE_NAMES = {
  habit: "привычка",
  threshold: "порог",
  scar: "шрам",
  self_narrative: "самоназвание",
  debt: "долг",
  attachment: "привязанность",
  project: "проект",
  ritual: "ритуал",
  missed_window: "упущенное",
  reputation: "репутация",
};

function traceLabel(t) {
  const key = t.key || "";
  if (key.startsWith("voice_high:")) {
    const name = key.slice("voice_high:".length);
    return `${VOICE_NAMES[name] || name} — выше порога`;
  }
  if (key.startsWith("voice_low:")) {
    const name = key.slice("voice_low:".length);
    return `${VOICE_NAMES[name] || name} — замолкает`;
  }
  if (key.startsWith("action:")) {
    const aid = key.slice("action:".length);
    return ACTION_PHRASES[aid] || aid;
  }
  if (key.startsWith("after:")) {
    const name = key.slice("after:".length);
    return `после ${VOICE_NAMES[name] || name}`;
  }
  if (key.startsWith("crisis:")) {
    const body = key.slice("crisis:".length);
    const parts = body.split("_vs_");
    if (parts.length === 2) {
      const a = VOICE_NAMES[parts[0]] || parts[0];
      const b = VOICE_NAMES[parts[1]] || parts[1];
      return `${a} против ${b}`;
    }
    return body;
  }
  if (key.startsWith("shift:")) {
    return `сдвиг ${key.slice("shift:".length)}`;
  }
  if (key.startsWith("w_") || key.startsWith("w-")) {
    return "упущенное окно";
  }
  if (ACTION_PHRASES[key]) {
    return ACTION_PHRASES[key];
  }
  return key;
}

const EVENT_KIND_NAMES = {
  tick: "такт",
  action: "действие",
  trace: "след",
  crisis: "кризис",
  intervention: "вмешательство",
  world: "мир",
  presence: "присутствие",
};

const INTERVENTION_TITLES = {
  request: "попросить",
  forbid: "запретить",
  support: "поддержать",
  distract: "отвлечь",
  insist: "настоять",
  leave: "уйти",
};

const MESSAGES_M = {
  heard: "он услышал",
  ignored: "он проигнорировал",
  wrong: "он ответил не то, что ты просил",
};

const MESSAGES_F = {
  heard: "она услышала",
  ignored: "она проигнорировала",
  wrong: "она ответила не то, что ты просила",
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

const LOCATION_PHRASES = {
  home: "дом",
  street: "улица",
  cafe: "кафе",
  work_place: "работа",
  gym: "спортзал",
  park: "парк",
  shop: "магазин",
  nowhere: "нигде",
};

const VOICE_ORDER = [
  "body",
  "safety",
  "connection",
  "recognition",
  "interest",
  "control",
];

let currentFilter = "all";
let scheduled = false;

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderScene() {
  const el = document.getElementById("scene");
  if (!el) return;
  const actionId = store.lastAction ? store.lastAction.id : null;
  const phrase = actionId ? (ACTION_PHRASES[actionId] || actionId) : "тишина";
  const place = LOCATION_PHRASES[store.location] || store.location || "";

  const name = store.name || "";
  const selfName = store.selfName || "";
  let nameHtml = "";
  if (name && selfName) {
    nameHtml = `<div class="name"><span class="given">${escapeHtml(name)}</span> <span class="self">${escapeHtml(selfName)}</span></div>`;
  } else if (name) {
    nameHtml = `<div class="name"><span class="given">${escapeHtml(name)}</span></div>`;
  } else if (selfName) {
    nameHtml = `<div class="name"><span class="self">${escapeHtml(selfName)}</span></div>`;
  }

  const tick = store.tick || 0;
  const day = Math.floor((tick - 1) / 24) + 1;
  const hour = ((tick - 1) % 24 + 24) % 24;
  const timeStr = `день ${day} · ${String(hour).padStart(2, "0")}:00`;

  el.innerHTML =
    nameHtml +
    `<div class="time">${timeStr}</div>` +
    `<div class="line">${phrase}</div>` +
    `<div class="place">${place}</div>`;

  const tickEl = document.getElementById("tick-top");
  if (tickEl) {
    tickEl.textContent = `такт ${tick}`;
  }
}

function renderVoices() {
  const el = document.getElementById("voices");
  if (!el) return;
  let html = "";
  for (const name of VOICE_ORDER) {
    const v = store.voices[name];
    const weight = v ? v.weight : 0;
    const height = Math.round(weight * 100);
    const pulse = weight > 0.35 ? " pulse" : "";
    html +=
      `<div class="voice${pulse}" data-name="${name}">` +
      `<span class="name">${VOICE_NAMES[name] || name}</span>` +
      `<div class="bar"><i style="width: ${height}%"></i></div>` +
      `</div>`;
  }
  el.innerHTML = html;
}

function renderTraces() {
  const el = document.getElementById("traces");
  if (!el) return;
  const traces = (store.traces || []).slice();
  traces.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
  const newSet = new Set(store.newTraces || []);
  let html = "";
  for (const t of traces) {
    const isNew = newSet.has(t.id) ? " new" : "";
    html +=
      `<div class="trace${isNew}" data-id="${t.id}" data-type="${t.type}">` +
      `<span class="type">${TRACE_TYPE_NAMES[t.type] || t.type}</span>` +
      `<span class="text">${traceLabel(t)}</span>` +
      `</div>`;
  }
  el.innerHTML = html;
}

function eventKind(e) {
  return EVENT_KIND_NAMES[e.kind] || e.kind;
}

function eventText(e) {
  const p = e.payload || {};
  if (e.kind === "action") {
    const aid = p.action_id || "";
    return ACTION_PHRASES[aid] || aid;
  }
  if (e.kind === "crisis") {
    const muts = p.mutations || [];
    if (muts.length) {
      return muts.map((m) => `${m.kind} → ${m.key}`).join(", ");
    }
    return "";
  }
  if (e.kind === "intervention") {
    const title = INTERVENTION_TITLES[p.type] || p.type || "";
    const base = `${title} → ${p.target || ""}`;
    const mk = p.message_key;
    if (!mk) return base;
    const table = store.gender === "male" ? MESSAGES_M : MESSAGES_F;
    const msg = table[mk] || "";
    return msg ? `${base} — ${msg}` : base;
  }
  let text = "";
  try {
    text = JSON.stringify(p);
  } catch (_) {
    text = "";
  }
  if (text.length > 80) text = text.slice(0, 80);
  return text;
}

function matchesFilter(e) {
  if (currentFilter === "all") return true;
  if (currentFilter === "actions") return e.kind === "action";
  if (currentFilter === "traces") return e.kind === "trace";
  if (currentFilter === "crisis") return e.kind === "crisis";
  return true;
}

function renderJournal() {
  const filtersEl = document.querySelector("#journal .filters");
  const listEl = document.querySelector("#journal .list");
  if (!filtersEl || !listEl) return;

  filtersEl.innerHTML =
    `<button data-filter="all" class="${currentFilter === "all" ? "active" : ""}">все</button>` +
    `<button data-filter="actions" class="${currentFilter === "actions" ? "active" : ""}">действия</button>` +
    `<button data-filter="traces" class="${currentFilter === "traces" ? "active" : ""}">следы</button>` +
    `<button data-filter="crisis" class="${currentFilter === "crisis" ? "active" : ""}">кризисы</button>`;

  const filtered = store.journal.filter(matchesFilter);

  let listHtml;
  if (!filtered.length) {
    listHtml = `<div class="empty">пока ничего</div>`;
  } else {
    const groups = new Map();
    for (const e of filtered) {
      if (!groups.has(e.tick)) groups.set(e.tick, []);
      groups.get(e.tick).push(e);
    }
    const ticks = Array.from(groups.keys()).sort((a, b) => b - a);
    listHtml = "";
    for (const tick of ticks) {
      listHtml += `<div class="group">`;
      for (const e of groups.get(tick)) {
        listHtml +=
          `<div class="event">` +
          `<span class="tick">${tick}</span>` +
          `<span class="text">${eventText(e)}</span>` +
          `</div>`;
      }
      listHtml += `</div>`;
    }
  }

  listEl.innerHTML = listHtml;

  filtersEl.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentFilter = btn.dataset.filter;
      renderJournal();
    });
  });
}

export function render() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => {
    scheduled = false;
    renderScene();
    renderVoices();
    renderTraces();
    renderJournal();
  });
}
