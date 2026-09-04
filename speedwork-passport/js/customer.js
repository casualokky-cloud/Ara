/* Customer app logic — index.html */

(() => {
  const NAV_ITEMS = [
    { screen: "screen-passport", icon: "passport", label: "Passport" },
    { screen: "screen-area", icon: "area", label: "Area" },
    { screen: "screen-gallery", icon: "gallery", label: "Gallery" },
    { screen: "screen-profile", icon: "id", label: "SW.ID" },
  ];

  const BRANCHES = [
    { name: "Speedwork Autocare — Kelapa Gading", addr: "Jl. Boulevard Raya Blok QJ 1, Kelapa Gading, Jakarta Utara", tag: "Booth IMOS 2026" },
    { name: "Speedwork Autocare — BSD City", addr: "Jl. Pahlawan Seribu, BSD City, Tangerang Selatan", tag: "Bengkel Mitra" },
    { name: "Speedwork Autocare — Bandung", addr: "Jl. Soekarno Hatta No. 456, Bandung", tag: "Bengkel Mitra" },
    { name: "Speedwork Autocare — Surabaya", addr: "Jl. HR Muhammad No. 88, Surabaya", tag: "Bengkel Mitra" },
  ];

  const GALLERY_ITEMS = [
    { icon: "tire", label: "Katalog Ban Terbaru" },
    { icon: "wrench", label: "Video Edukasi Servis" },
    { icon: "gamepad", label: "Keseruan Booth" },
    { icon: "trophy", label: "Galeri Pemenang" },
  ];

  let activeStampSheet = null; // stamp id currently open in the sheet
  let currentEventId = null; // which event's passport is currently open
  let qrPollTimer = null;

  function eventBadge(ev, count, total) {
    if (ev.active) return `<span class="stampitem__badge is-active">Aktif</span>`;
    if (count >= total) return `<span class="stampitem__badge is-complete">Selesai</span>`;
    return `<span class="stampitem__badge">${count}/${total}</span>`;
  }

  function q(sel, root) { return (root || document).querySelector(sel); }
  function qa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function renderIcons(root) {
    qa("[data-icon]", root || document).forEach(el => {
      const name = el.getAttribute("data-icon");
      el.innerHTML = SW.icon(name);
      el.removeAttribute("data-icon");
    });
    qa("[data-icon-color]", root || document).forEach(el => {
      const name = el.getAttribute("data-icon-color");
      el.innerHTML = SW.colorIcon(name);
      el.removeAttribute("data-icon-color");
    });
  }

  function initials(name) {
    return (name || "?").trim().split(/\s+/).slice(0, 2).map(w => w[0]).join("").toUpperCase();
  }

  function toast(msg) {
    const el = q("#toast");
    el.textContent = msg;
    el.classList.add("is-show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("is-show"), 2200);
  }

  // ---------------- navigation ----------------

  function buildBottomNavs() {
    qa("[data-nav]").forEach(nav => {
      nav.innerHTML = NAV_ITEMS.map(item => `
        <button data-go="${item.screen}">
          ${SW.icon(item.icon)}
          <span>${item.label}</span>
        </button>
      `).join("");
    });
  }

  function initGoDelegation() {
    document.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-go]");
      if (!btn) return;
      const target = btn.getAttribute("data-go");
      // any generic "Passport" nav (bottom nav, back buttons) always
      // returns to the currently-running event's passport; browsing a
      // past event happens explicitly via the history list / switcher.
      if (target === "screen-passport") openEventPassport(SW.getActiveEvent().id);
      else goTo(target);
    });
  }

  function openEventPassport(eventId) {
    currentEventId = eventId;
    goTo("screen-passport");
  }

  function goTo(screenId) {
    qa(".screen").forEach(s => s.classList.toggle("is-active", s.id === screenId));
    qa("[data-nav] button").forEach(btn => {
      btn.classList.toggle("is-active", btn.getAttribute("data-go") === screenId);
    });
    if (screenId === "screen-home") renderHome();
    if (screenId === "screen-passport") renderPassport();
    if (screenId === "screen-area") renderArea();
    if (screenId === "screen-gallery") renderGallery();
    if (screenId === "screen-profile") renderProfile();
    q(".screen__scroll", q("#" + screenId))?.scrollTo?.(0, 0);
  }

  function openOverlay(id) { q("#" + id).classList.add("is-open"); }
  function closeOverlay(id) { q("#" + id).classList.remove("is-open"); }
  function closeAllOverlays() { qa(".overlay").forEach(o => o.classList.remove("is-open")); }

  // ---------------- login ----------------

  function initLogin() {
    const check = q("#tnc-check");
    const btn = q("#btn-google");
    check.addEventListener("change", () => { btn.disabled = !check.checked; });
    q("#tnc-link").addEventListener("click", () => openOverlay("overlay-tnc"));

    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      const existing = SW.getCurrentUser();
      if (existing) { goTo("screen-home"); return; }
      let name = window.prompt("Simulasi Sign in with Google\n\nMasukkan nama kamu:", "");
      const user = SW.createUser(name);
      toast(`Selamat datang, ${user.name.split(" ")[0]}!`);
      goTo("screen-home");
    });
  }

  // ---------------- home ----------------

  function requireUser() {
    const u = SW.getCurrentUser();
    if (!u) { goTo("screen-login"); return null; }
    return u;
  }

  function renderHome() {
    const u = requireUser();
    if (!u) return;

    q("#home-avatar").textContent = initials(u.name);
    q("#home-name").textContent = u.name;
    q("#home-gtid").textContent = u.gtid;

    const total = SW.STAMPS.length;
    const activeEvent = SW.getActiveEvent();
    const done = SW.stampCount(u, activeEvent.id);
    q("#home-progress-num").textContent = `${done}/${total}`;
    q("#home-progress-fill").style.width = `${Math.round((done / total) * 100)}%`;

    q("#active-event-label").textContent = activeEvent.subtitle.toUpperCase();
    q("#active-event-title").textContent = activeEvent.name;

    q("#banner-install").classList.toggle("is-dismissed", !!u.installDismissed);
    const notifBanner = q("#banner-notif");
    notifBanner.classList.toggle("is-dismissed", !!u.notifOn);

    const markHolder = q("#passport-cover-mark");
    if (!markHolder.dataset.filled) {
      markHolder.innerHTML = markGraphic();
      markHolder.dataset.filled = "1";
    }

    const history = SW.EVENTS.filter(ev => !ev.active).slice().reverse();
    q("#event-history-list").innerHTML = history.map(ev => {
      const c = SW.stampCount(u, ev.id);
      return `
        <div class="stampitem" data-event="${ev.id}">
          <div class="stampitem__num">${SW.icon("passport")}</div>
          <div>
            <div class="stampitem__name">${ev.name}</div>
            <div class="stampitem__desc">${ev.subtitle} · ${ev.dateLabel}</div>
          </div>
          ${eventBadge(ev, c, total)}
        </div>`;
    }).join("") || `<div class="empty-hint">Belum ada riwayat event.</div>`;
    qa("[data-event]", q("#event-history-list")).forEach(el => {
      el.addEventListener("click", () => openEventPassport(el.getAttribute("data-event")));
    });
  }

  function markGraphic() {
    return `<svg viewBox="0 0 48 48" fill="none" stroke="#fff" stroke-width="2">
      <circle cx="24" cy="24" r="19" stroke-opacity=".5"/>
      <circle cx="24" cy="24" r="7" fill="#fff" fill-opacity=".95" stroke="none"/>
      <path d="M24 5v6M24 37v6M5 24h6M37 24h6" stroke-opacity=".5"/>
    </svg>`;
  }

  function initHomeHandlers() {
    q("#profile-card").addEventListener("click", () => goTo("screen-profile"));
    q("#open-passport").addEventListener("click", () => openEventPassport(SW.getActiveEvent().id));
    q("#quick-area").addEventListener("click", () => goTo("screen-area"));
    q("#quick-gallery").addEventListener("click", () => goTo("screen-gallery"));
    q("#btn-notif-bell").addEventListener("click", () => toast("Belum ada notifikasi baru"));

    q("#btn-install").addEventListener("click", () => {
      const u = SW.getCurrentUser();
      SW.updateUser(u.gtid, { installDismissed: true });
      toast("SW Passport ditambahkan ke layar utama (simulasi).");
      renderHome();
    });
    q("#btn-install-skip").addEventListener("click", () => {
      const u = SW.getCurrentUser();
      SW.updateUser(u.gtid, { installDismissed: true });
      renderHome();
    });
    q("#btn-notif").addEventListener("click", () => {
      const u = SW.getCurrentUser();
      SW.updateUser(u.gtid, { notifOn: true });
      toast("Notifikasi diaktifkan.");
      renderHome();
    });
  }

  // ---------------- passport (map + list) ----------------

  function renderPassport() {
    const u = requireUser();
    if (!u) return;
    if (!currentEventId) currentEventId = SW.getActiveEvent().id;
    const ev = SW.getEvent(currentEventId) || SW.getActiveEvent();

    q("#passport-topbar-title").textContent = ev.name;
    q("#passport-book-event").textContent = `SPEEDWORK ${ev.name.toUpperCase()} PASSPORT`;
    q("#passport-book-sub").textContent = ev.active
      ? "Ikuti alur di bawah & kumpulkan seluruh stempel"
      : `${ev.subtitle} · ${ev.dateLabel}`;

    const statusBanner = q("#event-status-banner");
    q("#passport-book").classList.toggle("is-closed", !ev.active);
    q("#passport-ribbon").style.display = ev.active ? "none" : "block";
    if (ev.active) {
      statusBanner.style.display = "none";
    } else {
      statusBanner.style.display = "flex";
      q("#event-status-text").textContent = `Event ${ev.name} sudah selesai — ini riwayat stempel kamu.`;
    }

    buildStampMap(u, ev);
    buildStampList(u, ev);
  }

  const SVG_NS = "http://www.w3.org/2000/svg";
  const MAP_SCALE = 3.8; // % position -> 0..380 viewBox units

  // Catmull-Rom -> cubic bezier, so the route reads as a winding road
  // instead of straight dashed segments between stamps.
  function smoothRoadPath(points) {
    if (points.length < 2) return "";
    let d = `M ${points[0].x} ${points[0].y} `;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i - 1] || points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = points[i + 2] || p2;
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = p1.y + (p2.y - p0.y) / 6;
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = p2.y - (p3.y - p1.y) / 6;
      d += `C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y} `;
    }
    return d;
  }

  function buildStampMap(u, ev) {
    const stamps = u.events[ev.id];
    const map = q("#stampmap");
    qa(".stampnode, .route-car, .route-flag", map).forEach(n => n.remove());
    const svg = q("#stampmap-svg");
    svg.innerHTML = "";
    svg.setAttribute("viewBox", "0 0 380 380");

    const routePoints = SW.MAP_POS.map(p => ({ x: p.x * MAP_SCALE, y: p.y * MAP_SCALE }));
    const d = smoothRoadPath(routePoints);

    const defs = document.createElementNS(SVG_NS, "defs");
    defs.innerHTML = `
      <linearGradient id="roadProgressGrad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#fed22a"/>
        <stop offset="100%" stop-color="#91c759"/>
      </linearGradient>`;
    svg.appendChild(defs);

    const roadBase = document.createElementNS(SVG_NS, "path");
    roadBase.setAttribute("class", "road-base");
    roadBase.setAttribute("d", d);
    svg.appendChild(roadBase);

    const roadProgress = document.createElementNS(SVG_NS, "path");
    roadProgress.setAttribute("class", "road-progress");
    roadProgress.setAttribute("d", d);
    svg.appendChild(roadProgress);

    const roadDash = document.createElementNS(SVG_NS, "path");
    roadDash.setAttribute("class", "road-dash");
    roadDash.setAttribute("d", d);
    svg.appendChild(roadDash);

    const doneCount = Object.values(stamps).filter(Boolean).length;
    const total = SW.STAMPS.length;
    const frac = total ? doneCount / total : 0;
    const len = roadProgress.getTotalLength();
    roadProgress.style.strokeDasharray = `${len}`;
    roadProgress.style.strokeDashoffset = `${len}`;
    requestAnimationFrame(() => {
      roadProgress.style.strokeDashoffset = `${len * (1 - frac)}`;
    });

    const nextStamp = ev.active ? SW.STAMPS.find(s => !stamps[s.id]) : null;

    SW.STAMPS.forEach((s, i) => {
      const pos = SW.MAP_POS[i];
      const done = !!stamps[s.id];
      const isNext = !done && nextStamp && nextStamp.id === s.id;
      const node = document.createElement("div");
      node.className = "stampnode" + (done ? " is-done" : "") + (isNext ? " is-next" : "");
      node.style.left = pos.x + "%";
      node.style.top = pos.y + "%";
      node.style.setProperty("--i", i);
      node.innerHTML = `
        <div class="stampnode__circle">
          ${SW.colorIcon(s.icon)}
          <div class="stampnode__check">${SW.icon("check")}</div>
        </div>
        <div class="stampnode__label">${s.id}. ${s.name}</div>
      `;
      node.addEventListener("click", () => {
        const circle = q(".stampnode__circle", node);
        circle.classList.remove("is-tapped");
        void circle.offsetWidth; // restart animation
        circle.classList.add("is-tapped");
        openStampSheet(s.id);
      });
      map.appendChild(node);

      if (s.id === total) {
        const flag = document.createElement("div");
        flag.className = "route-flag";
        flag.style.left = pos.x + "%";
        flag.style.top = pos.y + "%";
        flag.innerHTML = flagGraphic();
        map.appendChild(flag);
      }
    });

    // little car marker riding the road, parked at how far the passport
    // has progressed overall (not tied to a single stamp order).
    const carIndex = Math.max(0, Math.min(1, frac)) * len;
    const carPt = roadProgress.getPointAtLength(carIndex);
    const car = document.createElement("div");
    car.className = "route-car";
    car.style.left = (carPt.x / MAP_SCALE) + "%";
    car.style.top = (carPt.y / MAP_SCALE) + "%";
    car.innerHTML = carGraphic();
    map.appendChild(car);
  }

  function carGraphic() {
    return `<svg viewBox="0 0 32 20" width="19" height="12">
      <path d="M2 14 Q2 9 7 8 L10 4 Q11 2 14 2 L22 2 Q25 2 26 5 L28 8 Q31 8 31 12 L31 14 Q31 16 29 16 L27 16 A3 3 0 1 1 21 16 L13 16 A3 3 0 1 1 7 16 L4 16 Q2 16 2 14 Z" fill="#eb2f23" stroke="#8a1a12" stroke-width=".6"/>
      <path d="M11 5 L14 5 Q15 5 15 6.4 L15 8 L9 8 Z" fill="#bfe9f5" opacity=".85"/>
      <path d="M17 5 L22 5 Q23.5 5 24.5 7 L25.5 8 L17 8 Z" fill="#bfe9f5" opacity=".85"/>
      <circle cx="10" cy="16" r="3" fill="#1a1a1a"/><circle cx="10" cy="16" r="1.1" fill="#888"/>
      <circle cx="24" cy="16" r="3" fill="#1a1a1a"/><circle cx="24" cy="16" r="1.1" fill="#888"/>
    </svg>`;
  }

  function flagGraphic() {
    return `<svg viewBox="0 0 20 20" width="18" height="18">
      <rect x="3" y="2" width="2" height="16" rx="1" fill="#8a6a4a"/>
      <rect x="5" y="2" width="12" height="8" fill="#fff"/>
      <rect x="5" y="2" width="3" height="3" fill="#181818"/>
      <rect x="11" y="2" width="3" height="3" fill="#181818"/>
      <rect x="8" y="5" width="3" height="3" fill="#181818"/>
      <rect x="14" y="5" width="3" height="3" fill="#181818"/>
    </svg>`;
  }

  function buildStampList(u, ev) {
    const stamps = u.events[ev.id];
    const list = q("#stamplist");
    list.innerHTML = SW.STAMPS.map(s => {
      const done = !!stamps[s.id];
      return `
        <div class="stampitem${done ? " is-done" : ""}" data-stamp="${s.id}">
          <div class="stampitem__num">${s.id}</div>
          <div>
            <div class="stampitem__name">${s.name}</div>
            <div class="stampitem__desc">${s.desc}</div>
          </div>
          <div class="stampitem__status">${done ? SW.icon("check") : ""}</div>
        </div>`;
    }).join("");
    qa("[data-stamp]", list).forEach(el => {
      el.addEventListener("click", () => openStampSheet(Number(el.getAttribute("data-stamp"))));
    });
  }

  function initViewTabs() {
    q("#tab-map").addEventListener("click", () => switchView("map"));
    q("#tab-list").addEventListener("click", () => switchView("list"));
  }
  function switchView(view) {
    q("#tab-map").classList.toggle("is-active", view === "map");
    q("#tab-list").classList.toggle("is-active", view === "list");
    q(".passport-book").style.display = view === "map" ? "block" : "none";
    q("#stamplist").style.display = view === "list" ? "flex" : "none";
  }

  // ---------------- stamp detail sheet + QR ----------------

  function openStampSheet(stampId) {
    const u = requireUser();
    if (!u) return;
    const ev = SW.getEvent(currentEventId) || SW.getActiveEvent();
    const s = SW.STAMPS.find(x => x.id === stampId);
    activeStampSheet = stampId;

    q("#stampdetail-icon").innerHTML = SW.colorIcon(s.icon);
    q("#stampdetail-title").textContent = `Stamp ${s.id} — ${s.name}`;
    q("#stampdetail-desc").textContent = s.desc;

    const done = !!u.events[ev.id][stampId];
    q("#stampdetail-todo").style.display = (!done && ev.active) ? "block" : "none";
    q("#stampdetail-qr").style.display = "none";
    q("#stampdetail-done").style.display = done ? "block" : "none";
    q("#stampdetail-closed").style.display = (!done && !ev.active) ? "block" : "none";

    openOverlay("overlay-stamp");
  }

  function startQrFlow() {
    const u = SW.getCurrentUser();
    const ev = SW.getEvent(currentEventId) || SW.getActiveEvent();
    if (!u || activeStampSheet == null || !ev.active) return;
    const stampId = activeStampSheet;

    q("#stampdetail-todo").style.display = "none";
    q("#stampdetail-qr").style.display = "block";
    q("#qr-gtid").textContent = u.gtid;
    q("#qr-status-text").textContent = "Menunggu discan staff…";

    const token = `SW-PASSPORT|${ev.id}|${u.gtid}|${stampId}|${Date.now()}`;
    SW.drawFakeQr(q("#qr-canvas"), token, "#00753a");
    SW.requestScan(u.gtid, u.name, ev.id, stampId);

    clearInterval(qrPollTimer);
    qrPollTimer = setInterval(() => checkStampClaimed(u.gtid, ev.id, stampId), 700);
  }

  function checkStampClaimed(gtid, eventId, stampId) {
    const users = SW.loadUsers();
    const u = users[gtid];
    if (u && u.events[eventId] && u.events[eventId][stampId]) {
      clearInterval(qrPollTimer);
      qrPollTimer = null;
      closeOverlay("overlay-stamp");
      showSuccess(stampId);
      renderPassport();
      renderHome();
    }
  }

  function showSuccess(stampId) {
    const s = SW.STAMPS.find(x => x.id === stampId);
    q("#success-seal").innerHTML = sealGraphic(s ? s.name : "STAMP");
    q("#success-title").textContent = "Stamp berhasil diklaim!";
    q("#success-desc").textContent = s ? `${s.name} telah ditambahkan ke passport kamu.` : "";
    openOverlay("overlay-success");
  }

  function sealGraphic(label) {
    const short = (label || "").toUpperCase();
    return `<svg viewBox="0 0 120 120" fill="none">
      <circle cx="60" cy="60" r="52" stroke="#008f47" stroke-width="3" stroke-dasharray="4 5"/>
      <circle cx="60" cy="60" r="42" stroke="#00753a" stroke-width="2.5"/>
      <circle cx="60" cy="60" r="24" fill="#e7f5ea"/>
      <path d="M50 60l7 7 14-14" stroke="#008f47" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      <text x="60" y="98" text-anchor="middle" font-size="8" font-weight="700" fill="#00753a" font-family="Segoe UI, Arial">${short.length > 22 ? short.slice(0, 20) + "…" : short}</text>
      <text x="60" y="30" text-anchor="middle" font-size="7" font-weight="700" fill="#00753a" letter-spacing="2" font-family="Segoe UI, Arial">CLAIMED</text>
    </svg>`;
  }

  // ---------------- area / gallery ----------------

  function renderArea() {
    q("#branch-list").innerHTML = BRANCHES.map(b => `
      <div class="branch-card">
        <div class="branch-card__pin">${SW.colorIcon("area")}</div>
        <div>
          <div class="branch-card__name">${b.name}</div>
          <div class="branch-card__addr">${b.addr}</div>
          <span class="branch-card__tag">${b.tag}</span>
        </div>
      </div>
    `).join("");
  }

  function renderGallery() {
    q("#gallery-grid").innerHTML = GALLERY_ITEMS.map(g => `
      <div class="gallery-tile">
        ${SW.colorIcon(g.icon)}
        <span>${g.label}</span>
      </div>
    `).join("");
  }

  // ---------------- profile ----------------

  function renderProfile() {
    const u = requireUser();
    if (!u) return;
    q("#profile-avatar").textContent = initials(u.name);
    q("#profile-name").textContent = u.name;
    q("#profile-gtid").textContent = u.gtid;
    q("#profile-stamps").textContent = `${SW.stampCount(u, SW.getActiveEvent().id)}/${SW.STAMPS.length}`;
    q("#profile-since").textContent = new Date(u.joinedAt).toLocaleDateString("id-ID", { month: "short", year: "numeric" });
    SW.drawFakeQr(q("#profile-qr"), `SW-ID|${u.gtid}`, "#00753a");
  }

  function initProfileHandlers() {
    q("#btn-logout").addEventListener("click", () => {
      SW.clearCurrentGtid();
      q("#tnc-check").checked = false;
      q("#btn-google").disabled = true;
      goTo("screen-login");
    });
  }

  // ---------------- event switcher ----------------

  function initEventSwitcher() {
    q("#btn-switch-event").addEventListener("click", () => {
      const u = SW.getCurrentUser();
      if (!u) return;
      const total = SW.STAMPS.length;
      q("#event-switch-list").innerHTML = SW.EVENTS.slice().reverse().map(ev => {
        const c = SW.stampCount(u, ev.id);
        return `
          <div class="stampitem${ev.id === currentEventId ? " is-current" : ""}" data-switch-event="${ev.id}">
            <div class="stampitem__num">${SW.icon("passport")}</div>
            <div>
              <div class="stampitem__name">${ev.name}</div>
              <div class="stampitem__desc">${ev.subtitle} · ${ev.dateLabel}</div>
            </div>
            ${eventBadge(ev, c, total)}
          </div>`;
      }).join("");
      qa("[data-switch-event]", q("#event-switch-list")).forEach(el => {
        el.addEventListener("click", () => {
          closeAllOverlays();
          openEventPassport(el.getAttribute("data-switch-event"));
        });
      });
      openOverlay("overlay-events");
    });
  }

  // ---------------- global overlay/sheet handlers ----------------

  function initOverlayHandlers() {
    qa("[data-close-overlay]").forEach(btn => {
      btn.addEventListener("click", () => {
        clearInterval(qrPollTimer);
        qrPollTimer = null;
        closeAllOverlays();
      });
    });
    qa(".overlay").forEach(ov => {
      ov.addEventListener("click", (e) => {
        if (e.target === ov) { clearInterval(qrPollTimer); qrPollTimer = null; closeAllOverlays(); }
      });
    });
    q("#btn-show-qr").addEventListener("click", startQrFlow);
  }

  // ---------------- live sync across tabs ----------------

  function initSync() {
    SW.onSync(() => {
      const u = SW.getCurrentUser();
      if (!u) return;
      const activeScreen = q(".screen.is-active")?.id;
      if (activeScreen === "screen-home") renderHome();
      if (activeScreen === "screen-passport") renderPassport();
      if (activeScreen === "screen-profile") renderProfile();
      if (activeStampSheet != null && currentEventId && q("#overlay-stamp").classList.contains("is-open")) {
        checkStampClaimed(u.gtid, currentEventId, activeStampSheet);
      }
    });
  }

  // ---------------- boot ----------------

  document.addEventListener("DOMContentLoaded", () => {
    renderIcons();
    buildBottomNavs();
    initGoDelegation();
    initLogin();
    initHomeHandlers();
    initViewTabs();
    initEventSwitcher();
    initOverlayHandlers();
    initProfileHandlers();
    initSync();

    const u = SW.getCurrentUser();
    goTo(u ? "screen-home" : "screen-login");
  });
})();
