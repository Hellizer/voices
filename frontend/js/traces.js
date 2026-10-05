export function initTraces() {
  const el = document.getElementById("traces");
  if (!el) return;
  el.addEventListener("click", (ev) => {
    const target = ev.target.closest(".trace");
    if (!target) return;
    const id = target.dataset.id || "";
    const type = target.dataset.type || "";
    alert(id + " / " + type);
  });
}
