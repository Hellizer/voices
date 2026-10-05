export const store = {
  tick: 0,
  location: "home",
  voices: {},
  traces: [],
  journal: [],
  world: null,
  lastAction: null,
  lastResult: null,
  newTraces: [],
};

export function setState(snapshot) {
  if (!snapshot) return;
  if (snapshot.character) {
    store.tick = snapshot.character.tick;
    store.location = snapshot.character.location;
    store.voices = snapshot.character.voices || {};
    store.traces = snapshot.character.traces || [];
    store.journal = (snapshot.character.journal || []).slice().reverse();
  }
  if (snapshot.world) {
    store.world = snapshot.world;
  }
  store.lastResult = snapshot.last_result || null;
  if (store.lastResult) {
    store.lastAction = {
      id: store.lastResult.action_id,
      group: store.lastResult.action_group,
    };
  }
}

export function applyTickEvent(payload) {
  if (!payload) return;
  store.tick = payload.tick;
  store.lastAction = {
    id: payload.action_id,
    group: payload.action_group,
  };
}

export function addJournalEvents(events) {
  if (!events || !events.length) return;
  store.journal = [...events].reverse().concat(store.journal);
}

export function markNewTrace(ids) {
  if (!ids) return;
  store.newTraces = ids.slice();
}
