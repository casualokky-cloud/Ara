# SW Passport — Speedwork Autocare (gamification demo)

A front-end recreation of the "GT/SW Passport Journey" deck, re-skinned in
Speedwork Autocare's green brand palette with the real Speedwork Autocare
logo, plus a working (client-side) stamp-collecting loop.

- `index.html` — the customer app: login, home, digital passport (journey
  map + checklist view), QR-to-staff flow, Area, Gallery, and the SW.ID tab.
- `staff.html` — the PIC/staff scanner console used to activate a
  customer's stamp, mirroring the "PIC Journey" screen from the deck.
- `css/style.css` — shared green theme (colors sampled from the Speedwork
  Autocare logo: dark green `#008f47`, light green `#91c759`, plus the red
  `#eb2f23`/yellow `#fed22a` dots used as small accents).
- `js/app.js` — shared data model & storage helpers.
- `js/customer.js`, `js/staff.js` — per-page UI logic.

## Running it

No build step or server-side code — just open `index.html` (and, in a
second tab, `staff.html`) in a browser. For the cross-tab live sync to
work they need to be served from the same origin, e.g.:

```bash
cd speedwork-passport
python3 -m http.server 8080
# then open http://localhost:8080/index.html and http://localhost:8080/staff.html
```

## How the demo loop works

1. On `index.html`, agree to the terms and "Sign in with Google" (a
   simulated sign-in — it just asks for a name and creates a local
   profile with a generated `SW.ID`).
2. Open the **Passport** tab and tap any stamp on the journey map (or in
   the checklist) that isn't claimed yet, then **"Tunjukkan QR ke
   Staff"**.
3. On `staff.html`, press **START SCANNING**. The request you just made
   shows up under "Menunggu Discan" and is also auto-detected a couple of
   seconds later (simulating a successful camera scan) — or resolve it
   immediately with the **Aktifkan** button, or the manual picker at the
   bottom.
4. Back on `index.html`, the QR sheet closes itself and a stamp-claimed
   confirmation appears — the passport progress bar and journey map
   update live, no page reload needed.

## What's simplified (this is a prototype, not production)

- **No backend, no real Google OAuth.** Everything lives in
  `localStorage` on the current browser and is synced across tabs with
  the `storage` event + `BroadcastChannel`. Clearing site data resets the
  demo.
- **The QR codes are visual only.** They're deterministically generated
  from a token string with real finder-pattern corners so they *look*
  like a scannable QR, but they are not a standards-compliant QR code and
  can't be decoded by a real scanner app — there was no network access
  available to vendor a QR encode/decode library for this build. The
  staff console's camera preview is real (`getUserMedia`), but "detecting"
  a QR is simulated via the shared local storage, not real computer
  vision.
- **Area / Gallery data is sample content**, not real Speedwork Autocare
  branch listings or media.
