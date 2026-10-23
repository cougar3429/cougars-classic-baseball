# Tests for Cougar's Classic Baseball

Headless browser tests for `index.html`. None of this is served as part of the game; GitHub Pages only links `index.html`.

## Setup

- Python 3 with Playwright: `pip install playwright` (add `--break-system-packages` if pip asks).
- Chromium: already installed in Claude's cloud workspace (do **not** run `playwright install` there). On your own machine, run `playwright install chromium` once.
- Google Fonts fail to load offline; that's harmless, the game falls back to system fonts.

## Run

```
./tests/run_all.sh
```

Rebuilds the test pages, runs the rule checks, a 3-game soak, a 2-game two-phone rollback check and a 15-second online 2-player check. Exit code is non-zero if anything fails.

| Script | What it does | Typical use |
|---|---|---|
| `build_variants.py` | Builds `tests/build/hooks.html` (real game plus `window.__ccbi` internal hooks), `auto.html` (computer vs computer) and `adv.html` (exploit runner on offense) from `index.html`. Stops with a clear message if the game code no longer matches its edits. | Run after every change to `index.html` (`run_all.sh` does it). |
| `scenarios.py` | 25 scripted rule checks: forced walk, grand slam, third-out run rule, foul return, no going back past the start base, pickoff flow (one tap steps off, a new direction throws at once), foul bunt, tags, walk-off, mercy rule, catcher on bunts, force at home and first, timed throws, wild pitches only out of reach, double plays, runners sent to occupied bases, stranded runners, run commands blocked by a runner in the way, the throw back to the pitcher, SAFE calls, runner drawn on a bag. Prints PASS/FAIL with details. | Regression check before publishing a build. |
| `soak.py [games]` | Whole computer-vs-computer games with rule invariants checked every tick, plus a count of every call shown. | Catching rare bugs after big changes. |
| `rates.py [n] [steals\|bunts\|both]` | Your steal and bunt success rates against the computer. Version 73: steals about 50% safe, bunts about 10-12% hits. | Tuning difficulty. |
| `rollback.py [games] [max_lag] [max_ticks]` | Two-phone check: a host and a guest copy of the game play each other through the rollback engine (`RB`) with a fake network (random lag, out of order); a third copy gets both players' inputs with no lag. All three must end with exactly the same game. Serves `build/` on a local port so the three copies can share one page. | After any change to the game logic: catches anything that makes the phones disagree. |
| `net.py [seconds] [lag_ms]` | Online 2-player: two copies of the real game (`build/net.html`, with `mock_supabase.js` standing in for supabase-js) go through the real lobby buttons (host, ask, deny, ask again, accept), play at real speed over a laggy simulated network, and must agree at every checked tick; then one phone's connection drops for 6 s (the other must offer WAIT FOR RECONNECT / FINISH VS CPU / QUIT GAME, and play must pick up by itself when it is back, with lost moves resent); then one quits and the other finishes against the computer. | After any change to the lobby, the network code or the game logic. |
| `live_net.py [seconds]` | The same online game against the REAL Supabase project (needs network access to the project and cdn.jsdelivr.net; not part of run_all.sh). | Before pushing a change to the online code. |
| `adv.py [games]` | Whole games where runners use the tricks found while testing (turn back when the ball closes in, go when they throw elsewhere). Version 73: about 0.3 to 0.45 runs per half-inning. | Checking a running exploit is closed. Edit `ADV` for a new trick. |
| `catcher_throw.py` | You as catcher throwing out a stealer after 0 to 16 ticks of delay, per pitch type. | Tuning `C_THROW`/`C_WIND`. |

## Writing a check

Add an entry to `CHECKS` in `scenarios.py`: a JS function that sets up a situation, runs ticks and returns `{ ok: true/false, ...details }`.

`T` (in `T.js`) has the helpers:

- `T.start(batFirst)` new 3-inning game, paused, at the first pitch (`true` = you bat).
- `T.run(n)`, `T.until(fn, maxTicks)` advance the simulation (60 ticks = 1 second).
- `T.press(dir)` one tick with direction (`'u' 'd' 'l' 'r'` or `null`) plus the button; `T.hold(dir)` and `T.release()`.
- `T.put([1, 3])` put runners on bases; `T.rs()` runner summary such as `"1>2@0.40,3"` (from 1 to 2, 40% of the way; one standing on 3).
- `T.hit(angle, speed)` a ground ball set up exactly as contact does (0 = up the middle, + = toward third).
- `T.toast()` the call on screen; `T.watch(n)` list of calls over n ticks.
- `T.C` is `window.__ccb` (`S`, `tick(inputs)`, `newGame(opts)`, `newRunner(base)`, `human`, plus `save()`, `load(copy)`, `syncView()`, `quiet(on)`, `RB`, `packIn`); `T.I` is `window.__ccbi` (internal functions: `mkBall`, `giveBall`, `batterToFirst`, `wallHit`, `commitRuns`, `runnerOut`, `takeLeads`, ...).

## Useful game internals

- `S.phase`: `ready` (before the pitch), `windup`, `pitch`, `batted` (ball in play or any live play), `result` (a call is showing), `over`.
- `S.live.kind` during `batted`: `hit`, `steal`, `wild` (wild pitch), `pick` (pickoff).
- Runners: `S.runners`, each `{ at, to, p, forced, lead, go, next, ... }`. Standing on a base when `to == null`; `lead` is the three-step lead before the pitch; `go` is a steal order; `next` is the base to keep running to.
- Field units: home `(0, -1)`, first base bag center `(60.2, 63.6)`, second `(0, 127.3)`, third `(-60.2, 63.6)`, mound `(0, 61.6)`. `proj(x, y)` maps to screen pixels.
- Speeds per tick: runner `RSPD` 0.459, fielder `FSPD` 0.32 (outfielders x1.25), throw `THROW` 1.2, catcher's steal throw `C_THROW` 1.75.
- Teams are the strings `'you'` and `'cpu'`: you and the computer in 1-player, the host and the guest in 2-player. `S.ai` says which teams the computer plays (`{ you: false, cpu: true }` in 1-player; `auto.html` sets both true). `ME` is the team this phone controls (screen text and local input only).
- `tick(inputs)` takes `{ you: input, cpu: input }` for human teams; with no argument it reads this phone's controls for `ME`. Input: `{ dir, btn, vx, vy }`.
- Random numbers: `rnd()`, state in `S.seed` (a number). `newGame` takes `seed`, `ai`, `me` and `vis` (who bats first) alongside the usual options.
- Rollback: `save()` / `load()` copy the whole game (`S` is plain data, about 1.2 KB). While `QUIET` is on (re-running ticks), sounds and screen updates are skipped; `syncView()` redraws from `S` afterwards.

## Online play

- The game loads supabase-js 2.117.3 from cdn.jsdelivr.net only when 2 PLAYER is picked, and talks to the Supabase project in `SB_URL` with the publishable key. Realtime only (Presence on `ccb-lobby`, Broadcast on `ccb-g-<room>`); no database tables.
- The Claude artifact viewer blocks connections to Supabase, so online play works only on the live GitHub Pages site. Claude's cloud workspace can't reach Supabase either, so tests use `mock_supabase.js`.

## Publishing reminders

- Bump the version label (`<small id="ver">`) with every build.
- The repository's `index.html` has no doctype/head wrapper (the first line is the `<title>` tag); keep it that way when pushing.
- Push to `main` only when the user says so.
