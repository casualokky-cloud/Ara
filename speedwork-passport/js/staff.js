/* PIC / staff scanner console — staff.html
   No real QR decoding library is vendored in this demo, so "scanning" is
   simulated: starting the camera shows a live preview for authenticity,
   and any pending scan request written by a customer tab (via
   localStorage / BroadcastChannel) is auto-detected a couple of seconds
   later, exactly like a real scan would resolve. A manual picker is also
   provided so the flow can be tested/demoed without a camera or a second
   device. See README.md. */

(() => {
  let stream = null;
  let autoDetectTimer = null;

  function q(sel, root) { return (root || document).querySelector(sel); }
  function qa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function renderIcons() {
    qa("[data-icon]").forEach(el => {
      el.innerHTML = SW.icon(el.getAttribute("data-icon"));
      el.removeAttribute("data-icon");
    });
  }

  function toast(msg) {
    const el = q("#toast");
    el.textContent = msg;
    el.classList.add("is-show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("is-show"), 2200);
  }

  function initials(name) {
    return (name || "?").trim().split(/\s+/).slice(0, 2).map(w => w[0]).join("").toUpperCase();
  }

  async function startScanning() {
    const box = q("#scanner-box");
    const btn = q("#btn-start-scan");
    if (stream) return;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      q("#scanner-video").srcObject = stream;
      box.classList.add("is-live");
      btn.textContent = "";
      btn.innerHTML = `${SW.icon("scan")} SCANNING…`;
    } catch (err) {
      // camera unavailable/denied — still enter "scanning" state so the
      // auto-detect / manual flow keeps working.
      box.classList.add("is-live");
      q("#scanner-idle").style.display = "none";
      btn.innerHTML = `${SW.icon("scan")} SCANNING… (kamera tidak tersedia)`;
    }
    armAutoDetect();
  }

  function armAutoDetect() {
    clearInterval(autoDetectTimer);
    autoDetectTimer = setInterval(() => {
      const list = SW.loadPending();
      if (list.length === 0) return;
      const req = list[0];
      SW.resolvePending(req.id);
      toast(`QR terdeteksi: ${req.name} — Stamp "${req.stampName}" berhasil diaktifkan`);
      renderAll();
    }, 2200);
  }

  function renderPending() {
    const list = SW.loadPending();
    q("#pending-count").textContent = list.length;
    q("#pending-empty").style.display = list.length ? "none" : "block";
    q("#pending-items").innerHTML = list.map(r => `
      <div class="pending-item" data-req="${r.id}">
        <div class="pending-item__avatar">${initials(r.name)}</div>
        <div>
          <div class="pending-item__name">${r.name}</div>
          <div class="pending-item__stamp">${r.gtid} · ${r.eventName || r.eventId} · Stamp: ${r.stampName}</div>
        </div>
        <button class="btn btn--pill-sm pending-item__go" data-resolve="${r.id}">Aktifkan</button>
      </div>
    `).join("");
    qa("[data-resolve]").forEach(btn => {
      btn.addEventListener("click", () => {
        const req = SW.resolvePending(btn.getAttribute("data-resolve"));
        if (req) toast(`Stamp "${req.stampName}" diaktifkan untuk ${req.name}`);
        renderAll();
      });
    });
  }

  function renderManualPickers() {
    const users = SW.loadUsers();
    const gtidSel = q("#manual-gtid");
    const current = gtidSel.value;
    const entries = Object.values(users).sort((a, b) => b.joinedAt - a.joinedAt);
    gtidSel.innerHTML = entries.length
      ? entries.map(u => `<option value="${u.gtid}">${u.name} — ${u.gtid}</option>`).join("")
      : `<option value="">(belum ada customer terdaftar)</option>`;
    if (entries.some(u => u.gtid === current)) gtidSel.value = current;

    const eventSel = q("#manual-event");
    const eventCurrent = eventSel.value;
    eventSel.innerHTML = SW.EVENTS.slice().reverse().map(ev => `<option value="${ev.id}">${ev.name}${ev.active ? " (Aktif)" : ""}</option>`).join("");
    eventSel.value = eventCurrent || SW.getActiveEvent().id;

    const stampSel = q("#manual-stamp");
    const stampCurrent = stampSel.value;
    stampSel.innerHTML = SW.STAMPS.map(s => `<option value="${s.id}">Stamp ${s.id} — ${s.name}</option>`).join("");
    if (stampCurrent) stampSel.value = stampCurrent;
  }

  function renderLog() {
    const log = SW.loadLog();
    q("#log-empty").style.display = log.length ? "none" : "block";
    q("#log-items").innerHTML = log.map(l => `
      <div class="log-item"><b>${new Date(l.ts).toLocaleTimeString("id-ID")}</b>&nbsp; ${l.text}</div>
    `).join("");
  }

  function renderAll() {
    renderPending();
    renderManualPickers();
    renderLog();
  }

  function initManualActivate() {
    q("#btn-manual-activate").addEventListener("click", () => {
      const gtid = q("#manual-gtid").value;
      const eventId = q("#manual-event").value;
      const stampId = Number(q("#manual-stamp").value);
      if (!gtid) { toast("Belum ada customer terdaftar."); return; }
      SW.cancelScan(gtid, eventId, stampId);
      SW.setStamp(gtid, eventId, stampId, true);
      toast(`Stamp ${stampId} diaktifkan untuk ${gtid}`);
      renderAll();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderIcons();
    renderAll();
    q("#btn-start-scan").addEventListener("click", startScanning);
    initManualActivate();
    SW.onSync(renderAll);
  });
})();
