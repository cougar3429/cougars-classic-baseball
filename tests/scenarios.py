"""Scripted rule checks on the real game (with internal hooks). Each prints PASS or FAIL with details.

usage: python3 tests/scenarios.py
Add a check by writing a JS function that returns { ok: bool, ...details } and calling check().
T (tests/T.js) has helpers: T.start(batFirst), T.run(n), T.until(fn, n), T.press(dir), T.hold(dir), T.release(),
T.put([bases]), T.rs() (runner summary like '1>2@0.40,3'), T.toast(), T.watch(n). T.I exposes internal functions.
"""
import json, sys
from common import page

CHECKS = {
'bases-loaded walk forces in a run': r"""() => { T.start(true); const S = T.C.S;
  for (let k = 0; k < 40; k++) { T.until(() => S.phase === 'ready', 800); T.put([1, 2, 3]); S.b = 3; S.s = 0; S.cpuP = null;
    T.until(() => S.phase === 'result', 800); if (T.toast().startsWith('WALK')) { const before = S.score.you; T.until(() => S.phase === 'ready', 400); return { ok: S.score.you === before + 1, toast: T.toast(), runners: T.rs() }; } }
  return { ok: false, why: 'no walk in 40 tries' }; }""",

'grand slam: 4 runs and the GRAND SLAM call': r"""() => { T.start(true); const S = T.C.S; T.put([1, 2, 3]); S.runners.forEach(r => { r.lead = false; r.to = null; });
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 200); S.bb.wall = false; S.bb.v = 4; S.spd = { ev: 4, wall: null }; T.I.batterToFirst(false);
  const before = S.score.you; T.I.wallHit(200); const toast = T.toast(); return { ok: S.score.you === before + 4 && toast.startsWith('GRAND SLAM'), toast, runs: S.score.you - before }; }""",

'third out on a force wipes the run; on a tag it counts': r"""() => {
  T.start(true); let S = T.C.S; T.put([3]); S.runners.forEach(r => { r.lead = false; r.to = null; }); S.outs = 2; T.I.snapRunners(); S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 60); T.I.batterToFirst(false);
  let r3 = S.runners.find(r => r.at === 3); r3.to = 4; r3.p = 0.999; S.playRuns = 0; T.I.moveRunners(); T.I.runnerOut(S.batR, 'Forced out at first', true); const afterForce = S.score.you;
  T.start(true); S = T.C.S; T.put([3, 1]); S.runners.forEach(r => { r.lead = false; r.to = null; }); S.outs = 2; T.I.snapRunners(); S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 60);
  r3 = S.runners.find(r => r.at === 3); r3.to = 4; r3.p = 0.999; S.playRuns = 0; T.I.moveRunners(); const r1 = S.runners.find(r => r.at === 1); r1.to = 2; r1.p = 0.5; T.I.runnerOut(r1, 'Tagged out', false);
  return { ok: afterForce === 0 && S.score.you === 1, runsAfterForceOut: afterForce, runsAfterTagOut: S.score.you }; }""",

'foul ball sends a stealing runner back': r"""() => { T.start(true); const S = T.C.S; T.put([1]); const r = S.runners[0]; r.lead = false; r.to = null; T.I.snapRunners();
  r.to = 2; r.p = 0.4; T.I.foulReturn(); for (let i = 0; i < 300; i++) T.I.moveRunners(); return { ok: T.rs() === '1', runners: T.rs() }; }""",

'runner never goes back past the base he started on': r"""() => { T.start(true); const S = T.C.S; T.put([2]); const r = S.runners[0]; r.lead = false; r.to = null; T.I.snapRunners();
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(-100, 150); T.I.giveBall('LF'); S.F.LF.x = -100; S.F.LF.y = 150; S.gatherT = 9999;
  T.press('r'); return { ok: T.rs() === '2', runnersAfterSendingToFirst: T.rs() }; }""",

'pickoff: set, call (runners dive back), call off': r"""() => { T.start(false); const S = T.C.S; T.put([1, 2]); T.run(80); const leads = T.rs();
  T.press(null); const set = S.lock; T.press(null); const pick = S.pick; T.run(70); const back = T.rs(); T.press(null);
  return { ok: set && pick && back === '1,2' && !S.pick, leads, afterCall: back, calledOff: !S.pick }; }""",

'bunt fielded fully in foul ground is foul': r"""() => { T.start(true); const S = T.C.S; S.runners = []; const a = 50 * Math.PI / 180;
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.abOver = true; S.batterGone = true; S.playT = 0;
  S.bb = { bunt: true, x: 0, y: 1, ux: -Math.sin(a), uy: Math.cos(a), v: 0.45, ev: 0.45, dist: 0, h: 0, hPeak: 0, foul: false, wall: false, t: 0, gone: false };
  T.I.batterToFirst(false); for (let i = 0; i < 400 && S.phase === 'batted'; i++) T.C.tick(); return { ok: T.toast().startsWith('FOUL'), call: T.toast() }; }""",

'tag counts when the fielder runs into the runner': r"""() => { T.start(false); const S = T.C.S; T.put([1]); const r = S.runners[0]; r.lead = false; r.to = 2; r.p = 0.45; r.forced = true; r.fb = 2;
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(20, 100); T.I.giveBall('2B'); S.F['2B'].x = 20; S.F['2B'].y = 100; S.playT = 30;
  const pos = () => { const a = [60.2, 63.6], b = [0, 127.3]; return [a[0] + (b[0] - a[0]) * r.p, a[1] + (b[1] - a[1]) * r.p]; };
  for (let i = 0; i < 200 && !r.out && r.to != null; i++) { const q = pos(), f = S.F['2B']; T.C.human.vx = Math.sign(q[0] - f.x); T.C.human.vy = Math.sign(q[1] - f.y); T.C.human.dir = 'u'; T.C.tick(); }
  T.release(); return { ok: r.out, result: r.out ? r.how : 'safe' }; }""",

'walk-off ends the game': r"""() => { const C = T.C; C.newGame({ innings: 9, batFirst: true }); const S = C.S; S.paused = true; S.half = 17; S.vis = 'you'; S.score = { you: 2, cpu: 2 };
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.playRuns = 1; T.I.commitRuns(); T.run(300);
  return { ok: C.S.over && document.getElementById('fh').textContent === 'CPU Wins', final: document.getElementById('fh').textContent }; }""",

'mercy rule (10 runs) ends the game in the bottom half': r"""() => { const C = T.C; C.newGame({ innings: 9, batFirst: true, mercy: 10 }); const S = C.S; S.paused = true; S.half = 1; S.score = { you: 0, cpu: 9 };
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.playRuns = 1; T.I.commitRuns(); T.run(300);
  return { ok: C.S.over && /mercy/i.test(document.getElementById('fsub').textContent), sub: document.getElementById('fsub').textContent }; }""",

'computer catcher throws on a bunt with a runner on (gets an out most of the time)': r"""() => { let outs = 0, n = 0;
  for (let k = 0; k < 80 && n < 15; k++) { T.start(true); const S = T.C.S; S.runners = []; T.C.newRunner(1); T.I.takeLeads(); S.runners[0].go = false;
    T.until(() => S.phase === 'ready', 200); T.run(10); T.press('d'); for (let i = 0; i < 400 && ['ready', 'windup', 'pitch'].includes(S.phase); i++) T.C.tick();
    if (!S.bb || !S.bb.bunt || S.bb.foul) continue; for (let i = 0; i < 700 && S.phase === 'batted'; i++) T.C.tick(); n++; if (S.runners.some(r => r.out) || (S.batR && S.batR.out)) outs++; }
  return { ok: n > 0 && outs / n >= 0.6, bunts: n, withAnOut: outs }; }""",
'you throw home on a bases-loaded ground ball: force out at home (any infielder)': r"""() => { const res = [];
  for (const ang of [-25, -8, 0, 25, 40]) { T.start(false); const S = T.C.S; T.put([1, 2, 3]); const third = S.runners.find(r => r.at === 3); T.hit(ang, 1.5);
    T.until(() => S.holder, 400); const who = S.holder; T.press('d'); T.until(() => S.phase !== 'batted', 400); res.push(who + ':' + (third.out && /home/.test(third.how) ? 'out' : 'safe')); }
  return { ok: res.every(x => x.endsWith('out')), plays: res }; }""",

'you throw to first on a ground ball: the first baseman takes it on the bag': r"""() => { const res = [];
  for (const ang of [-8, 0, 25, 40]) { T.start(false); const S = T.C.S; S.runners = []; T.hit(ang, 1.5);
    T.until(() => S.holder, 400); const who = S.holder; T.press('r'); T.until(() => S.phase !== 'batted', 400); res.push(who + ':' + (S.batR.out ? S.batR.how : 'safe')); }
  return { ok: res.every(x => /Forced out at first/.test(x)), plays: res }; }""",

'timed throw: the pitcher holds his throw to second until the cover man will be there, and he takes it on the bag': r"""() => { T.start(false); const S = T.C.S; T.put([1]); T.hit(0, 1.2);
  T.until(() => S.holder === 'P', 400); T.press('u'); let held = 0; for (let i = 0; i < 200 && !S.thr && S.holder; i++) { if (S.thrWait > 0) held++; T.C.tick(); }
  const runner = S.runners.find(r => !r.bat); T.until(() => !S.thr, 300); const f = S.F['2B'], off = Math.hypot(f.x, f.y - 127.3);
  T.until(() => S.phase !== 'batted' || runner.out, 400);
  return { ok: held > 0 && runner.out && /second baseman/.test(runner.how) && off < 1, heldTicks: held, distanceFromBag: +off.toFixed(2), runner: runner.out ? runner.how : 'safe' }; }""",

'a pitch the catcher can reach is never a wild pitch (the screen-edge walls never decide a play)': r"""() => { let a = 77; const r = () => { a = (a * 1103515245 + 12345) & 0x7fffffff; return a / 0x7fffffff; };
  let n = 0, wild = 0, inReach = 0;
  for (let k = 0; k < 200; k++) { T.start(false); const S = T.C.S; S.runners = []; T.hold(['u', 'd', 'l', 'r'][Math.floor(r() * 4)]); T.press(T.C.human.dir);
    const curve = r() < 0.6 ? (r() < 0.5 ? 'l' : 'r') : null, hold = Math.floor(r() * 40), start = Math.floor(r() * 20); let i = 0;
    while (['windup', 'pitch'].includes(S.phase) && i < 600) { if (S.phase === 'pitch') { i++; if (curve && i > start && i < start + hold) T.hold(curve); else T.release(); } T.C.tick(); }
    T.release(); n++; if (S.live && S.live.kind === 'wild') { wild++; if (Math.abs(S.bb.x - S.F.C.x) <= 7) inReach++; } }
  return { ok: inReach === 0, pitches: n, wildPitches: wild, wildButCatcherCouldReach: inReach }; }""",

'computer goes for the double play (turns one on the right side, tries on the left)': r"""() => { const run = ang => { T.start(true); const S = T.C.S; T.put([1]); T.hit(ang, 1.5); let tried = false;
    for (let i = 0; i < 900 && S.phase === 'batted'; i++) { T.C.tick(); if (S.playOuts === 1 && S.thr && S.thr.base === 1) tried = true; } return { outs: S.playOuts, tried }; };
  const right = run(-10), left = run(30);
  return { ok: right.outs === 2 && left.tried, right, left }; }""",
'runner sent to an occupied base: the computer takes the out at first, then gets the stranded runner': r"""() => { const res = [];
  for (const [ang, ev] of [[-6, 1.4], [-12, 1.4], [0, 1.7], [-25, 1.4]]) { T.start(true); const S = T.C.S; T.put([2, 3]); T.hit(ang, ev); let sent = false, first = null;
    for (let i = 0; i < 900 && S.phase === 'batted'; i++) { if (!sent && S.holder) { T.press('l'); sent = true; } else T.C.tick(); if (S.thr && first == null) first = S.thr.base; }
    res.push({ ang, firstThrow: first, batterOut: S.batR.out, outs: S.playOuts }); }
  return { ok: res.every(r => r.firstThrow !== 3 && r.batterOut && r.outs === 2), plays: res }; }""",

'a runner standing on a base is drawn in front of a fielder on the bag': r"""() => { document.getElementById('title').hidden = true; T.start(true); const S = T.C.S; T.put([2]); const r = S.runners[0]; r.lead = false; r.to = null;
  S.phase = 'result'; S.rt = 999; S.wasLive = true; S.bb = T.I.mkBall(0, 125.9); S.holder = '2B'; S.F['2B'].x = 0.4; S.F['2B'].y = 125.9; document.getElementById('toast').classList.remove('on');
  return new Promise(done => requestAnimationFrame(() => requestAnimationFrame(() => {
    const cv = document.getElementById('cv'), k = cv.width / 844, d = cv.getContext('2d').getImageData(Math.round(420 * k), Math.round(146 * k), Math.max(1, Math.round(4 * k)), Math.max(1, Math.round(3 * k))).data;
    let rr = 0, bl = 0; for (let i = 0; i < d.length; i += 4) { rr += d[i]; bl += d[i + 2]; }
    S.rt = 1; done({ ok: rr > bl, red: rr, blue: bl }); }))); }""",
}

failed = 0
with page() as (pg, errs):
    for name, js in CHECKS.items():
        try:
            r = pg.evaluate(js)
        except Exception as e:
            r = {'ok': False, 'error': str(e)[:300]}
        ok = r.pop('ok', False)
        failed += not ok
        print('PASS' if ok else 'FAIL', '-', name, json.dumps(r))
    print('page errors:', errs[:5] or 'none')
print(f'{len(CHECKS) - failed}/{len(CHECKS)} passed')
sys.exit(1 if failed else 0)
