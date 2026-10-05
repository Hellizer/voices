const KEY_MAP = {
  "1": { type: "teach", payload: { action_id: "learn" } },
  "2": { type: "connect", payload: { npc_id: "barista" } },
  "3": { type: "value", payload: { voice: "interest", delta: 0.1 } },
  "4": { type: "open_door", payload: { location: "park" } },
  "5": { type: "close_door", payload: { location: "park" } },
};

async function sendEnvironment(type, payload) {
  try {
    await fetch("/environment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type, payload }),
    });
  } catch (_) {
  }
}

function isEditable(el) {
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA";
}

export function initEnvironment() {
  document.addEventListener("keydown", (ev) => {
    if (isEditable(ev.target)) return;
    const entry = KEY_MAP[ev.key];
    if (!entry) return;
    sendEnvironment(entry.type, entry.payload);
  });
}
