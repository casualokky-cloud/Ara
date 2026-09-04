/* Customer app logic — index.html */

(() => {
  const NAV_ITEMS = [
    { screen: "screen-passport", icon: "passport", label: "Passport" },
    { screen: "screen-area", icon: "area", label: "Area" },
    { screen: "screen-gallery", icon: "gallery", label: "Gallery" },
    { screen: "screen-profile", icon: "id", label: "SW.ID" },
  ];

  const BRANCHES = [
    { name: "Speedwork Autocare — Kelapa Gading", addr: "Jl. Boulevard Raya Blok QJ 1, Kelapa Gading, Jakarta Utara", tag: "Booth GIIAS 2026" },
    { name: "Speedwork Autocare — BSD City", addr: "Jl. Pahlawan Seribu, BSD City, Tangerang Selatan", tag: "Bengkel Mitra" },
    { name: "Speedwork Autocare — Bandung", addr: "Jl. Soekarno Hatta No. 456, Bandung", tag: "Bengkel Mitra" },
    { name: "Speedwork Autocare — Surabaya", addr: "Jl. HR Muhammad No. 88, Surabaya", tag: "Bengkel Mitra" },
  ];

  const GALLERY_ITEMS = [
    { icon: "tire", label: "Katalog Ban Terbaru", grad: "linear-gradient(150deg,#008f47,#17a558)" },
    { icon: "wrench", label: "Video Edukasi Servis", grad: "linear-gradient(150deg,#00753a,#91c759)" },
    { icon: "gamepad", label: "Keseruan Booth", grad: "linear-gradient(150deg,#17a558,#008f47)" },
    { icon: "trophy", label: "Galeri Pemenang", grad: "linear-gradient(150deg,#eb2f23,#fed22a)" },
  ];

  let activeStampSheet = null; // stamp id currently open in the sheet
  let qrPollTimer = null;

  function q(sel, root) { return (root || document).querySelector(sel); }
  function qa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function renderIcons(root) {
    qa("[data-icon]", root || document).forEach(el => {
      const name = el.getAttribute("data-icon");
      el.innerHTML = SW.icon(name);
      el.removeAttribute("data-icon");
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
      if (btn) goTo(btn.getAttribute("data-go"));
    });
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

    const done = SW.stampCount(u);
    const total = SW.STAMPS.length;
    q("#home-progress-num").textContent = `${done}/${total}`;
    q("#home-progress-fill").style.width = `${Math.round((done / total) * 100)}%`;

    q("#banner-install").classList.toggle("is-dismissed", !!u.installDismissed);
    const notifBanner = q("#banner-notif");
    notifBanner.classList.toggle("is-dismissed", !!u.notifOn);

    const markHolder = q("#passport-cover-mark");
    if (!markHolder.dataset.filled) {
      markHolder.innerHTML = markGraphic();
      markHolder.dataset.filled = "1";
    }
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
    q("#open-passport").addEventListener("click", () => goTo("screen-passport"));
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
    buildStampMap(u);
    buildStampList(u);
  }

  function buildStampMap(u) {
    const map = q("#stampmap");
    qa(".stampnode", map).forEach(n => n.remove());
    const svg = q("#stampmap-svg");
    svg.innerHTML = "";

    // connector lines, sequential 1..N
    let path = "";
    SW.MAP_POS.forEach((p, i) => {
      const x = p.x, y = p.y;
      path += (i === 0 ? "M" : "L") + `${x} ${y} `;
    });
    const poly = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    const pts = SW.MAP_POS.map(p => `${p.x * 3.8},${p.y * 3.8}`).join(" ");
    svg.setAttribute("viewBox", "0 0 380 380");
    poly.setAttribute("points", pts);
    poly.setAttribute("fill", "none");
    poly.setAttribute("stroke", "#bfe0c9");
    poly.setAttribute("stroke-width", "3");
    poly.setAttribute("stroke-dasharray", "2 9");
    poly.setAttribute("stroke-linecap", "round");
    svg.appendChild(poly);

    SW.STAMPS.forEach((s, i) => {
      const pos = SW.MAP_POS[i];
      const done = !!u.stamps[s.id];
      const node = document.createElement("div");
      node.className = "stampnode" + (done ? " is-done" : "");
      node.style.left = pos.x + "%";
      node.style.top = pos.y + "%";
      node.innerHTML = `
        <div class="stampnode__circle">
          ${SW.icon(s.icon)}
          <div class="stampnode__check">${SW.icon("check")}</div>
        </div>
        <div class="stampnode__label">${s.id}. ${s.name}</div>
      `;
      node.addEventListener("click", () => openStampSheet(s.id));
      map.appendChild(node);
    });
  }

  function buildStampList(u) {
    const list = q("#stamplist");
    list.innerHTML = SW.STAMPS.map(s => {
      const done = !!u.stamps[s.id];
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
    const s = SW.STAMPS.find(x => x.id === stampId);
    activeStampSheet = stampId;

    q("#stampdetail-icon").innerHTML = SW.icon(s.icon);
    q("#stampdetail-title").textContent = `Stamp ${s.id} — ${s.name}`;
    q("#stampdetail-desc").textContent = s.desc;

    const done = !!u.stamps[stampId];
    q("#stampdetail-todo").style.display = done ? "none" : "block";
    q("#stampdetail-qr").style.display = "none";
    q("#stampdetail-done").style.display = done ? "block" : "none";

    openOverlay("overlay-stamp");
  }

  function startQrFlow() {
    const u = SW.getCurrentUser();
    if (!u || activeStampSheet == null) return;
    const stampId = activeStampSheet;

    q("#stampdetail-todo").style.display = "none";
    q("#stampdetail-qr").style.display = "block";
    q("#qr-gtid").textContent = u.gtid;
    q("#qr-status-text").textContent = "Menunggu discan staff…";

    const token = `SW-PASSPORT|${u.gtid}|${stampId}|${Date.now()}`;
    SW.drawFakeQr(q("#qr-canvas"), token, "#00753a");
    SW.requestScan(u.gtid, u.name, stampId);

    clearInterval(qrPollTimer);
    qrPollTimer = setInterval(() => checkStampClaimed(u.gtid, stampId), 700);
  }

  function checkStampClaimed(gtid, stampId) {
    const users = SW.loadUsers();
    const u = users[gtid];
    if (u && u.stamps[stampId]) {
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
        <div class="branch-card__pin">${SW.icon("area")}</div>
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
      <div class="gallery-tile" style="background:${g.grad}">
        ${SW.icon(g.icon)}
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
    q("#profile-stamps").textContent = `${SW.stampCount(u)}/${SW.STAMPS.length}`;
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
      if (activeStampSheet != null && q("#overlay-stamp").classList.contains("is-open")) {
        checkStampClaimed(u.gtid, activeStampSheet);
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
    initOverlayHandlers();
    initProfileHandlers();
    initSync();

    const u = SW.getCurrentUser();
    goTo(u ? "screen-home" : "screen-login");
  });
})();
