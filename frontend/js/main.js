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
}

async function loadInitial() {
  try {
    const res = await fetch('/state');
    const data = await res.json();
    setState(data);
    render();
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
            type: payload.type,
            target: payload.target,
            target_voice: payload.target_voice,
            delta: payload.delta,
            obeyed: payload.obeyed,
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
