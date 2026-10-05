import { setState, applyTickEvent, addJournalEvents, markNewTrace, store } from './state.js';
import { render } from './render.js';
import { initIntervene } from './intervene.js';
import { initEnvironment } from './environment.js';
import { initJournal } from './journal.js';
import { initTraces } from './traces.js';

function initHelp() {
  const btn = document.getElementById("help-btn");
  const overlay = document.getElementById("help");
  const close = document.getElementById("help-close");
  if (!btn || !overlay) return;
  btn.addEventListener("click", () => {
    overlay.hidden = false;
  });
  if (close) {
    close.addEventListener("click", () => {
      overlay.hidden = true;
    });
  }
  overlay.addEventListener("click", (ev) => {
    if (ev.target === overlay) {
      overlay.hidden = true;
    }
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !overlay.hidden) {
      overlay.hidden = true;
    }
  });
}

function openInitOverlay() {
  const overlay = document.getElementById("init");
  const nameInput = document.getElementById("init-name");
  const femaleBtn = document.getElementById("init-female");
  const maleBtn = document.getElementById("init-male");
  const okBtn = document.getElementById("init-ok");
  const errEl = document.getElementById("init-error");
  if (!overlay || !nameInput || !okBtn) return;

  let gender = "female";
  femaleBtn.classList.add("active");
  maleBtn.classList.remove("active");

  femaleBtn.addEventListener("click", () => {
    gender = "female";
    femaleBtn.classList.add("active");
    maleBtn.classList.remove("active");
  });
  maleBtn.addEventListener("click", () => {
    gender = "male";
    maleBtn.classList.add("active");
    femaleBtn.classList.remove("active");
  });

  okBtn.addEventListener("click", async () => {
    const name = nameInput.value.trim();
    if (!name) {
      if (errEl) errEl.textContent = "нужно имя";
      return;
    }
    if (errEl) errEl.textContent = "";
    try {
      const res = await fetch("/character/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, gender }),
      });
      const data = await res.json();
      if (data.ok) {
        store.name = data.name;
        store.gender = data.gender;
        overlay.hidden = true;
        render();
      } else if (errEl) {
        errEl.textContent = "не получилось";
      }
    } catch (_) {
      if (errEl) errEl.textContent = "не получилось";
    }
  });

  overlay.hidden = false;
  nameInput.focus();
}

async function loadInitial() {
  try {
    const res = await fetch('/state');
    const data = await res.json();
    setState(data);
    render();
    if (!store.name) {
      openInitOverlay();
    }
  } catch (_) {
  }
}

async function handleTraceEvent(payload) {
  try {
    const res = await fetch('/state');
    const data = await res.json();
    setState(data);
    const ids = (store.traces || [])
      .filter((t) => t.updated_at === payload.tick)
      .map((t) => t.id);
    markNewTrace(ids);
    render();
    setTimeout(() => {
      store.newTraces = [];
      render();
    }, 2000);
  } catch (_) {
  }
}

function connectWs() {
  const ws = new WebSocket('ws://' + location.host + '/ws');
  ws.onmessage = (ev) => {
    let payload;
    try {
      payload = JSON.parse(ev.data);
    } catch (_) {
      return;
    }
    if (!payload || !payload.type) return;
    if (payload.type === 'hello') {
      return;
    }
    if (payload.type === 'tick') {
      applyTickEvent(payload);
      render();
      return;
    }
    if (payload.type === 'crisis') {
      addJournalEvents([
        { tick: payload.tick, kind: 'crisis', payload },
      ]);
      render();
      return;
    }
    if (payload.type === 'trace') {
      handleTraceEvent(payload);
      return;
    }
    if (payload.type === 'intervention_result') {
      addJournalEvents([
        {
          tick: payload.tick,
          kind: 'intervention',
          payload: {
            type: payload.intervention_type,
            target: payload.target,
            target_voice: payload.target_voice,
            delta: payload.delta,
            obeyed: payload.obeyed,
            message: payload.message,
            message_key: payload.message_key,
          },
        },
      ]);
      render();
      return;
    }
    if (payload.type === 'world_change') {
      render();
      return;
    }
  };
  ws.onclose = () => {
    setTimeout(connectWs, 3000);
  };
}

initIntervene();
initEnvironment();
initJournal();
initTraces();
initHelp();
loadInitial();
connectWs();
