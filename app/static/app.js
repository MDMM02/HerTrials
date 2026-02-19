function toast(msg) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2200);
}

function setBusy(container, busy) {
  const buttons = container.querySelectorAll("button[data-mode]");
  buttons.forEach(b => b.disabled = busy);

  const badge = container.querySelector(".badge[data-status]");
  if (badge) {
    badge.classList.remove("ok", "wait", "err");
    badge.classList.add(busy ? "wait" : "ok");
    badge.textContent = busy ? "⏳ Generating…" : "✅ Ready";
  }
}

async function generateSummary(recordId, mode, formEl) {
  try {
    setBusy(formEl, true);

    const btn = formEl.querySelector(`button[data-mode="${mode}"]`);
    const old = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span> Generating…`;

    const res = await fetch(`/summarize/${recordId}/${mode}`, { method: "POST" });

    // Your backend returns 303 redirect. fetch follows it and ends with 200.
    if (!res.ok) throw new Error("Request failed");

    toast(`Summary ${mode.toUpperCase()} generated ✅`);
    // refresh current page to show new summary blocks
    window.location.reload();

  } catch (e) {
    console.error(e);
    toast("Error while generating summary ❌");
    const badge = formEl.querySelector(".badge[data-status]");
    if (badge) {
      badge.classList.remove("ok", "wait");
      badge.classList.add("err");
      badge.textContent = "❌ Error";
    }
  } finally {
    setBusy(formEl, false);
  }
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-mode]");
  if (!btn) return;

  e.preventDefault();
  const formEl = btn.closest("[data-record]");
  const recordId = formEl?.getAttribute("data-record");
  const mode = btn.getAttribute("data-mode");
  if (!recordId || !mode) return;

  generateSummary(recordId, mode, formEl);
});
