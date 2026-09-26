# Obsidian Vault ↔ Tablet Sync: Switch to Fit, Plugin-Code Hard Limits, Mobile Zoom Fix

Follow-up session (2026-09-26) to
`docs/status/2026-09-21-obsidian-git-sync-status.md`, for
`ai-sandbox/academic-hub/academic_notes/` (its own git repo, remote
`academic-notes-vault` on GitHub, private). The 2026-09-21 doc's
architecture section (Direct Git Sync on the tablet) is now superseded —
see below — but its open restructuring proposal (moving PDFs/SVGs to
`academic_resources/`) is untouched and still pending.

## Sync architecture change: Direct Git Sync → Fit

The user switched the tablet from **Direct Git Sync** to the **Fit**
community plugin (`joshuakto/fit`), citing better reliability. Fit works
differently from both Direct Git Sync and `obsidian-git`: it syncs via
the GitHub REST API directly (no local `.git` clone/checkout), which
sidesteps the git-history-bloat crash class documented in the prior
status doc. Laptop side is unchanged (`obsidian-git`, auto-commit +
auto-push on an interval, still called "vault backup" in commit
messages).

**Fit's `.obsidian/` policy (from its own docs,
[`docs/sync-logic.md`](https://github.com/joshuakto/fit/blob/main/docs/sync-logic.md)),
load-bearing for anything touching plugin config or code going forward:**

- `.obsidian/` is excluded from sync by default. A path becomes
  *tracked* (detected) once content for it exists in the remote git
  tree, but stays *detection-only* (logged, never read or written)
  unless a root-level `.fitattributes.json` explicitly declares it
  `"format": "text"` — at which point it syncs bidirectionally as a
  whole-file replace (no field-level JSON merge yet; that's reserved
  future work).
- **Hard denylist, unconditional, cannot be overridden by
  `.fitattributes.json` even with matching remote content:** `main.js`,
  `manifest.json`, `styles.css` under **any** `.obsidian/plugins/<id>/`
  — including Fit's own. Rationale per the docs: these are
  plugin-manager-owned code assets, not preferences, and there's no
  "safe subset of fields" concept for a JS bundle. **This means Fit can
  never sync a hand-modified community plugin's code to another
  device — permanently, by design.**
- First-time sync of a newly `.fitattributes.json`-declared path can hit
  a **"tracking ADDED on both sides" clash**: if the path looks
  newly-added to both local and remote in the same sync pass, Fit
  refuses to guess and writes the *remote* version to a mirrored path
  under `_fit/` instead of the live path, leaving the live file alone.
  `_fit/<path>` is **always the remote version, never local** — resolve
  by manually copying `_fit/<path>`'s content over the live `<path>`
  (via a device file manager for anything under `.obsidian/`, since
  `_fit/` copies of hidden paths don't surface in Obsidian's own file
  explorer), then either delete the `_fit/` copy or just let the next
  sync detect the match and clear it automatically.

## Incidents / changes this session

1. **Confirmed `excalidraw-stylus-menu`'s Russian→English + Eraser fix
   (from the 2026-09-21 session) was still correct on the laptop**
   (commit `8e0b0eb` in `academic-notes-vault`) — all user-visible
   labels in English, Eraser button present and wired to
   `setActiveTool({type:"eraser"})`, source comments still Russian
   (intentional, invisible to users). Confirmed against
   `docs/status/2026-09-21-...md` line 50-55.
2. **Tablet was still running the stock (Russian, no-Eraser) build of
   that plugin.** Root cause: it's exactly the hard-denylisted file set
   above (`main.js`/`manifest.json`/`styles.css`) — Fit was never going
   to carry the laptop's modified code over, regardless of config.
   Community Plugins had installed the unmodified original on the
   tablet at some point and nothing since had touched it.
   **Fix: manual one-time copy** — downloaded the three files from
   `academic-notes-vault` on GitHub directly onto the tablet via its
   file manager, overwriting the plugin folder in place, then
   toggled the plugin off/on in Obsidian to force a reload. Confirmed
   working. **This is not an ongoing sync — any future edit to this
   plugin's code needs the same manual repeat**, or a one-off use of
   `obsidian-git`/Direct Git Sync (both still installed on the tablet)
   to pull just that folder.
3. **New: mobile zoom + undo/redo tray overlapped the tablet's OS
   gesture/home bar**, making those buttons unpressable. Fixed with a
   CSS snippet rather than touching `obsidian-excalidraw-plugin`'s
   bundled (4.8MB, minified) `main.js`/`styles.css` — snippets are the
   supported override mechanism and survive plugin updates. Added
   `.obsidian/snippets/excalidraw-mobile-zoom-offset.css`:
   ```css
   .is-mobile .excalidraw .zoom-actions,
   .is-mobile .excalidraw .undo-redo-buttons {
     --zoom-actions-lift: 2.5rem;
     transform: translateY(calc(-1 * var(--zoom-actions-lift)));
   }
   ```
   Scoped to `.is-mobile` so desktop is untouched; both trays share one
   `--zoom-actions-lift` var so they stay level. Enabled via
   `.obsidian/appearance.json`'s `enabledCssSnippets`. `2.5rem` was a
   first guess and may need tuning per-device.
4. **Wired this snippet into Fit's sync** via a new root-level
   `.fitattributes.json`:
   ```json
   { ".obsidian/snippets/excalidraw-mobile-zoom-offset.css": { "format": "text" } }
   ```
   — unlike the stylus-menu plugin's files, a CSS snippet isn't on
   Fit's hard denylist, so this path *does* sync normally once declared.
   Hit the "tracking ADDED on both sides" clash described above on the
   very first sync of this newly-declared path (expected, one-time
   friction per newly-tracked path, not a recurring issue); resolved
   by copying `_fit/`'s content over the live file on the tablet via
   file manager. Confirmed working end-to-end on tablet after
   resolution, including the follow-up edit adding
   `.undo-redo-buttons` to the same rule.
5. **Deliberately did not sync `.obsidian/appearance.json`'s
   `enabledCssSnippets` list itself** via `.fitattributes.json`, even
   though it's what toggles the snippet on. That file also carries
   theme/font-size/other display settings that may legitimately differ
   per device, and Fit's text-mode sync is a blunt whole-file replace
   with no field-level merge yet — syncing it risks clobbering
   tablet-only display prefs. Toggling the snippet on in Settings →
   Appearance is a one-time manual step per device instead.

## Still open

- Tuning `--zoom-actions-lift` (2.5rem) further if it's not quite right
  on the tablet.
- Everything under "Still open" / the restructuring proposal in
  `docs/status/2026-09-21-obsidian-git-sync-status.md` (PDF/SVG
  relocation out of `academic_notes/`) is untouched by this session.
- If the stylus-menu plugin gets edited again, repeat the manual
  copy — no sync-side fix exists for that class of file, see the hard
  denylist note above.
