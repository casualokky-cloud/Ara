/* Speedwork Autocare — SW Passport
   Shared data model + storage helpers used by both index.html (customer)
   and staff.html (PIC scanner console).

   Persistence note: this is a front-end only demo. "Users" and "pending
   scan requests" live in localStorage on the current browser, synced live
   across tabs with the storage event + BroadcastChannel. Open index.html
   and staff.html side by side in two tabs of the same browser to see the
   full loop (customer opens QR -> staff activates -> customer sees the
   stamp land in real time). There is no real server, real Google sign-in,
   or real QR camera decoding behind this — see README.md. */

const SW = (() => {
  const LS_USERS = "sw_users";
  const LS_CURRENT = "sw_current_gtid";
  const LS_PENDING = "sw_pending_scans";
  const LS_LOG = "sw_scan_log";

  const channel = ("BroadcastChannel" in window) ? new BroadcastChannel("sw-passport") : null;

  const STAMPS = [
    { id: 1, name: "Daftar SW Passport", desc: "Selesaikan pendaftaran akun & lengkapi profil kamu.", icon: "user" },
    { id: 2, name: "Konsultasi Servis", desc: "Konsultasi kondisi ban & kendaraan bersama tim teknisi.", icon: "wrench" },
    { id: 3, name: "Main di Booth Interaktif", desc: "Coba booth simulasi & edukasi di lokasi event.", icon: "gamepad" },
    { id: 4, name: "Follow & Share", desc: "Follow akun sosial media Speedwork lalu share event ini.", icon: "share" },
    { id: 5, name: "Isi Survey", desc: "Bantu isi survey kepuasan layanan Speedwork Autocare.", icon: "clipboard" },
    { id: 6, name: "Daftar Partner App", desc: "Daftarkan akun kamu di aplikasi mitra Speedwork.", icon: "apps" },
    { id: 7, name: "Mini Games", desc: "Mainkan mini games berhadiah di booth Speedwork.", icon: "game" },
    { id: 8, name: "Servis Paket Hemat", desc: "Selesaikan transaksi servis paket half-set di bengkel.", icon: "tire" },
    { id: 9, name: "Servis Paket Lengkap", desc: "Selesaikan transaksi servis paket full-set di bengkel.", icon: "trophy" },
  ];

  // layout positions (percent) for the journey-map view, echoing the
  // scattered stamp-map look from the reference deck.
  const MAP_POS = [
    { x: 16, y: 14 }, { x: 58, y: 10 }, { x: 86, y: 30 },
    { x: 30, y: 38 }, { x: 66, y: 46 }, { x: 12, y: 62 },
    { x: 48, y: 66 }, { x: 82, y: 74 }, { x: 34, y: 90 },
  ];

  const NAMES = ["Dian Anggraeni", "Wandi Kafri", "Rizky Pratama", "Sarah Amelia", "Budi Santoso", "Putri Lestari"];

  function uid() {
    return Math.random().toString(36).slice(2, 8).toUpperCase();
  }

  function genGtid() {
    return "SW.ID-" + Math.floor(10000000 + Math.random() * 89999999);
  }

  function loadUsers() {
    try { return JSON.parse(localStorage.getItem(LS_USERS)) || {}; }
    catch (e) { return {}; }
  }
  function saveUsers(users) {
    localStorage.setItem(LS_USERS, JSON.stringify(users));
    broadcast({ type: "users" });
  }

  function getCurrentGtid() {
    return localStorage.getItem(LS_CURRENT);
  }
  function setCurrentGtid(gtid) {
    localStorage.setItem(LS_CURRENT, gtid);
  }
  function clearCurrentGtid() {
    localStorage.removeItem(LS_CURRENT);
  }

  function getCurrentUser() {
    const gtid = getCurrentGtid();
    if (!gtid) return null;
    const users = loadUsers();
    return users[gtid] || null;
  }

  function createUser(name) {
    const users = loadUsers();
    const gtid = genGtid();
    const stamps = {};
    STAMPS.forEach(s => stamps[s.id] = false);
    users[gtid] = {
      gtid,
      name: name && name.trim() ? name.trim() : NAMES[Math.floor(Math.random() * NAMES.length)],
      joinedAt: Date.now(),
      stamps,
      installDismissed: false,
      notifOn: false,
    };
    saveUsers(users);
    setCurrentGtid(gtid);
    return users[gtid];
  }

  function updateUser(gtid, patch) {
    const users = loadUsers();
    if (!users[gtid]) return null;
    users[gtid] = Object.assign({}, users[gtid], patch);
    saveUsers(users);
    return users[gtid];
  }

  function setStamp(gtid, stampId, done) {
    const users = loadUsers();
    if (!users[gtid]) return null;
    users[gtid].stamps[stampId] = done;
    saveUsers(users);
    appendLog(`Stamp ${stampId} (${stampName(stampId)}) diaktifkan untuk ${users[gtid].name}`);
    return users[gtid];
  }

  function stampName(id) {
    const s = STAMPS.find(x => x.id === Number(id));
    return s ? s.name : "Stamp";
  }

  function stampCount(user) {
    if (!user) return 0;
    return Object.values(user.stamps).filter(Boolean).length;
  }

  // ---- pending scan requests (customer -> staff) ----

  function loadPending() {
    try { return JSON.parse(localStorage.getItem(LS_PENDING)) || []; }
    catch (e) { return []; }
  }
  function savePending(list) {
    localStorage.setItem(LS_PENDING, JSON.stringify(list));
    broadcast({ type: "pending" });
  }

  function requestScan(gtid, name, stampId) {
    const list = loadPending().filter(p => !(p.gtid === gtid && p.stampId === stampId));
    const req = { id: uid(), gtid, name, stampId, stampName: stampName(stampId), ts: Date.now() };
    list.push(req);
    savePending(list);
    return req;
  }

  function cancelScan(gtid, stampId) {
    savePending(loadPending().filter(p => !(p.gtid === gtid && p.stampId === stampId)));
  }

  function resolvePending(reqId) {
    const list = loadPending();
    const req = list.find(r => r.id === reqId);
    if (!req) return null;
    savePending(list.filter(r => r.id !== reqId));
    setStamp(req.gtid, req.stampId, true);
    return req;
  }

  function appendLog(text) {
    let log = [];
    try { log = JSON.parse(localStorage.getItem(LS_LOG)) || []; } catch (e) {}
    log.unshift({ text, ts: Date.now() });
    log = log.slice(0, 30);
    localStorage.setItem(LS_LOG, JSON.stringify(log));
    broadcast({ type: "log" });
  }
  function loadLog() {
    try { return JSON.parse(localStorage.getItem(LS_LOG)) || []; }
    catch (e) { return []; }
  }

  function broadcast(msg) {
    if (channel) channel.postMessage(msg);
  }
  function onSync(cb) {
    window.addEventListener("storage", () => cb());
    if (channel) channel.onmessage = () => cb();
  }

  // ---- fake-but-authentic-looking QR renderer (visual only) ----
  // Deterministic module grid seeded from the token string, drawn with
  // real QR-style finder patterns in the three corners. Not a scannable
  // standard QR — see README.md.

  function seededRand(seed) {
    let h = 1779033703 ^ seed.length;
    for (let i = 0; i < seed.length; i++) {
      h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
      h = (h << 13) | (h >>> 19);
    }
    return function () {
      h = Math.imul(h ^ (h >>> 16), 2246822507);
      h = Math.imul(h ^ (h >>> 13), 3266489909);
      h ^= h >>> 16;
      return (h >>> 0) / 4294967296;
    };
  }

  function drawFakeQr(canvas, token, color) {
    const N = 25;
    const cell = 8;
    canvas.width = N * cell;
    canvas.height = N * cell;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = color || "#00753a";

    const rand = seededRand(token);
    const grid = [];
    for (let y = 0; y < N; y++) {
      grid.push([]);
      for (let x = 0; x < N; x++) grid[y].push(rand() > 0.55 ? 1 : 0);
    }

    function finder(gx, gy) {
      for (let y = 0; y < 7; y++) {
        for (let x = 0; x < 7; x++) {
          const border = x === 0 || x === 6 || y === 0 || y === 6;
          const core = x >= 2 && x <= 4 && y >= 2 && y <= 4;
          grid[gy + y][gx + x] = (border || core) ? 1 : 0;
        }
      }
    }
    finder(0, 0);
    finder(N - 7, 0);
    finder(0, N - 7);

    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        if (grid[y][x]) ctx.fillRect(x * cell, y * cell, cell - 1, cell - 1);
      }
    }
  }

  // ---- inline icon set (stroke-style, currentColor) ----

  const ICONS = {
    user: '<circle cx="12" cy="8" r="3.4"/><path d="M5 20c1.6-4 4.2-6 7-6s5.4 2 7 6"/>',
    wrench: '<path d="M14.7 6.3a4 4 0 0 1-5 5L4 17l3 3 5.7-5.7a4 4 0 0 1 5-5l-2.6 2.6-2-2 2.6-2.6z"/>',
    gamepad: '<rect x="3" y="8" width="18" height="9" rx="4"/><path d="M8 11v3M6.5 12.5h3M15.5 12h.01M18 10.5h.01"/>',
    share: '<circle cx="6" cy="12" r="2.4"/><circle cx="18" cy="6" r="2.4"/><circle cx="18" cy="18" r="2.4"/><path d="M8.2 10.8 15.8 7.2M8.2 13.2l7.6 3.6"/>',
    clipboard: '<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3h6v1"/><path d="M9 11h6M9 15h6"/>',
    apps: '<rect x="4" y="4" width="6" height="6" rx="1.5"/><rect x="14" y="4" width="6" height="6" rx="1.5"/><rect x="4" y="14" width="6" height="6" rx="1.5"/><rect x="14" y="14" width="6" height="6" rx="1.5"/>',
    game: '<rect x="3" y="8" width="18" height="9" rx="4"/><path d="M8 11v3M6.5 12.5h3M15.5 12h.01M18 10.5h.01"/>',
    tire: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 4v3M12 17v3M4 12h3M17 12h3"/>',
    trophy: '<path d="M7 4h10v4a5 5 0 0 1-10 0V4z"/><path d="M7 6H4a3 3 0 0 0 3 5M17 6h3a3 3 0 0 1-3 5"/><path d="M10 17h4M12 13v4M9 20h6"/>',
    passport: '<rect x="5" y="3" width="14" height="18" rx="2"/><circle cx="12" cy="10" r="3"/><path d="M8 17h8"/>',
    area: '<path d="M12 21s7-6.3 7-11.5A7 7 0 0 0 5 9.5C5 14.7 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.4"/>',
    gallery: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.7"/><path d="M21 16l-5.5-5.5L6 19"/>',
    id: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="12" r="2.2"/><path d="M6 16.2c.6-1.6 1.6-2.3 2.5-2.3s1.9.7 2.5 2.3M14 9.5h5M14 13h5M14 16h3"/>',
    chevron: '<path d="M9 6l6 6-6 6"/>',
    back: '<path d="M15 6l-6 6 6 6"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    bell: '<path d="M6 9a6 6 0 0 1 12 0v5l1.5 3h-15L6 14V9z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    download: '<path d="M12 4v11m0 0-4-4m4 4 4-4"/><path d="M5 19h14"/>',
    close: '<path d="M6 6l12 12M18 6 6 18"/>',
    scan: '<path d="M4 7V5a1 1 0 0 1 1-1h2M4 17v2a1 1 0 0 0 1 1h2M20 7V5a1 1 0 0 0-1-1h-2M20 17v2a1 1 0 0 1-1 1h-2"/><path d="M4 12h16"/>',
    camera: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7l1.4-2.4A2 2 0 0 1 11.1 3.6h1.8a2 2 0 0 1 1.7 1L16 7"/><circle cx="12" cy="13.5" r="3.4"/>',
  };

  function icon(name, cls) {
    return `<svg class="ic ${cls || ""}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;
  }

  return {
    STAMPS, MAP_POS,
    loadUsers, saveUsers, getCurrentGtid, setCurrentGtid, clearCurrentGtid, getCurrentUser,
    createUser, updateUser, setStamp, stampName, stampCount,
    loadPending, savePending, requestScan, cancelScan, resolvePending,
    appendLog, loadLog, onSync, drawFakeQr, icon,
  };
})();
