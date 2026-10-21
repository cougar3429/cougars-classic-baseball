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

Rebuilds the test pages, runs the rule checks and a 3-game soak. Exit code is non-zero if anything fails.

| Script | What it does | Typical use |
|---|---|---|
| `build_variants.py` | Builds `tests/build/hooks.html` (real game plus `window.__ccbi` internal hooks), `auto.html` (computer vs computer) and `adv.html` (exploit runner on offense) from `index.html`. Stops with a clear message if the game code no longer matches its edits. | Run after every change to `index.html` (`run_all.sh` does it). |
| `scenarios.py` | 11 scripted rule checks: forced walk, grand slam, third-out run rule, foul return, no going back past the start base, pickoff flow, foul bunt, tags, walk-off, mercy rule, catcher throwing on bunts. Prints PASS/FAIL with details. | Regression check before publishing a build. |
| `soak.py [games]` | Whole computer-vs-computer games with rule invariants checked every tick, plus a count of every call shown. | Catching rare bugs after big changes. |
| `rates.py [n] [steals\|bunts\|both]` | Your steal and bunt success rates against the computer. Version 68: steals about 42% safe, bunts about 6% hits. | Tuning difficulty. |
| `adv.py [games]` | Whole games where runners use the tricks found while testing (turn back when the ball closes in, go when they throw elsewhere). Version 68: about 0.2 to 0.5 runs per half-inning. | Checking a running exploit is closed. Edit `ADV` for a new trick. |
| `catcher_throw.py` | You as catcher throwing out a stealer after 0 to 16 ticks of delay, per pitch type. | Tuning `C_THROW`/`C_WIND`. |

## Writing a check

Add an entry to `CHECKS` in `scenarios.py`: a JS function that sets up a situation, runs ticks and returns `{ ok: true/false, ...details }`.

`T` (in `T.js`) has the helpers:

- `T.start(batFirst)` new 3-inning game, paused, at the first pitch (`true` = you bat).
- `T.run(n)`, `T.until(fn, maxTicks)` advance the simulation (60 ticks = 1 second).
- `T.press(dir)` one tick with direction (`'u' 'd' 'l' 'r'` or `null`) plus the button; `T.hold(dir)` and `T.release()`.
- `T.put([1, 3])` put runners on bases; `T.rs()` runner summary such as `"1>2@0.40,3"` (from 1 to 2, 40% of the way; one standing on 3).
- `T.toast()` the call on screen; `T.watch(n)` list of calls over n ticks.
- `T.C` is `window.__ccb` (`S`, `tick()`, `newGame(opts)`, `newRunner(base)`, `human`); `T.I` is `window.__ccbi` (internal functions: `mkBall`, `giveBall`, `batterToFirst`, `wallHit`, `commitRuns`, `runnerOut`, `takeLeads`, ...).

## Useful game internals

- `S.phase`: `ready` (before the pitch), `windup`, `pitch`, `batted` (ball in play or any live play), `result` (a call is showing), `over`.
- `S.live.kind` during `batted`: `hit`, `steal`, `wild` (wild pitch), `pick` (pickoff).
- Runners: `S.runners`, each `{ at, to, p, forced, lead, go, next, ... }`. Standing on a base when `to == null`; `lead` is the three-step lead before the pitch; `go` is a steal order; `next` is the base to keep running to.
- Field units: home `(0, -1)`, first base bag center `(60.2, 63.6)`, second `(0, 127.3)`, third `(-60.2, 63.6)`, mound `(0, 61.6)`. `proj(x, y)` maps to screen pixels.
- Speeds per tick: runner `RSPD` 0.459, fielder `FSPD` 0.32 (outfielders x1.25), throw `THROW` 1.2, catcher's steal throw `C_THROW` 1.75.
- Sides are the strings `'you'` and `'cpu'` (`batSide()`, `homeSide()`, `defenseHuman()`); see the spec doc's "2-player online: where to start" for what changes for multiplayer.

## Publishing reminders

- Bump the version label (`<small id="ver">`) with every build.
- The repository's `index.html` has no doctype/head wrapper (the first line is the `<title>` tag); keep it that way when pushing.
- Push to `main` only when the user says so.
