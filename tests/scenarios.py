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

'a runner standing on a base never goes back on a command (runner who reached third stays; the runner on first goes to second)': r'''() => { T.start(true); const S = T.C.S; T.put([1, 3]); S.runners.forEach(r => { r.lead = false; r.to = null; }); T.I.snapRunners();
  const r3 = S.runners.find(r => r.at === 3), r1 = S.runners.find(r => r.at === 1); r3.snap = 2;
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(40, 60); T.I.giveBall('3B'); S.gatherT = 9999;
  T.press('u'); return { ok: r3.at === 3 && r3.to == null && r1.to === 2, third: r3.at + '>' + r3.to, first: r1.at + '>' + r1.to }; }''',
'runner never goes back past the base he started on': r"""() => { T.start(true); const S = T.C.S; T.put([2]); const r = S.runners[0]; r.lead = false; r.to = null; T.I.snapRunners();
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(-100, 150); T.I.giveBall('LF'); S.F.LF.x = -100; S.F.LF.y = 150; S.gatherT = 9999;
  T.press('r'); return { ok: T.rs() === '2', runnersAfterSendingToFirst: T.rs() }; }""",

'pickoff: a runner who broke and went back to his base is no stolen base; the toast shows no old second line': r'''() => { T.start(true); const S = T.C.S; T.put([2]); T.run(80);
  const r = S.runners[0]; T.press('l'); T.I.callPick(); const broke = r.to === 3; T.run(3); T.press('u'); const back = r.to === 2;
  S.lastToast = { text: 'STRIKE 1', sub: 'Out of reach', end: S.t + 1, big: false }; document.getElementById('ts').textContent = 'Out of reach'; document.getElementById('ts').hidden = false;
  let stole = false; for (let i = 0; i < 300 && S.pick; i++) { T.C.tick(); if (S.pick) T.I.pickSettled(); if (S.lastToast && S.lastToast.text === 'STOLEN BASE') stole = true; }
  T.until(() => r.to == null, 300); const ts = document.getElementById('ts'); ts.hidden = true;
  /* the live site has no wrapper page: switch off the test page's own [hidden] rule (it hid the bug) */
  const wrap = [...document.styleSheets].find(x => [...x.cssRules].some(c => c.cssText.includes('!important') && c.selectorText === '[hidden]')); if (wrap) wrap.disabled = true;
  const subShows = getComputedStyle(ts).display !== 'none'; if (wrap) wrap.disabled = false;
  return { ok: broke && back && !stole && r.at === 2 && !subShows, broke, wentBack: back, stolenBaseCalled: stole, base: r.at, oldSubStillShows: subShows }; }''',
'a sliding runner cannot stop or turn around': r'''() => { T.start(true); const S = T.C.S; T.put([2]); const r = S.runners[0]; r.lead = false; r.to = 3; r.p = 0.85; r.slide = 20; T.I.snapRunners();
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(40, 60); T.I.giveBall('3B'); S.gatherT = 9999;
  T.press('u'); return { ok: r.at === 2 && r.to === 3, runner: r.at + '>' + r.to }; }''',
'pickoff: one tap steps off (runners dive back), tap again goes back on the rubber': r"""() => { T.start(false); const S = T.C.S; T.put([1, 2]); T.run(80); const leads = T.rs();
  T.press(null); const pick = S.pick; T.run(70); const back = T.rs(); T.press(null);
  return { ok: pick && back === '1,2' && !S.pick, leads, steppedOffWithOneTap: pick, afterCall: back, backOnRubber: !S.pick }; }""",

'pickoff: a direction after stepping off throws at once, even to an empty base': r"""() => { const res = {};
  for (const [dir, base] of [['r', 1], ['l', 3]]) { T.start(false); const S = T.C.S; T.put([1]); T.run(80);
    T.press(null); T.run(2); T.hold(dir); let n = 0; while (!S.thr && n < 60) { T.C.tick(); n++; } T.release(); res[base] = { ticksToRelease: n, throwTo: S.thr && S.thr.base }; }
  return { ok: res[1].throwTo === 1 && res[3].throwTo === 3 && res[1].ticksToRelease <= 14 && res[3].ticksToRelease <= 14, res }; }""",

'pickoff: a direction already held when he steps off does not throw': r"""() => { T.start(false); const S = T.C.S; T.put([1]); T.run(80);
  T.hold('r'); T.C.human.btn = true; T.C.tick(); T.C.human.btn = false; const off = S.pick; T.run(30); const threw = !!S.thr || S.phase !== 'ready'; T.release();
  return { ok: off === false || !threw, steppedOff: off, threw }; }""",

'bunt stance: up/down move him, left/right aim, other presses do nothing, down + button goes back to hitting': r'''() => { T.start(true); const S = T.C.S; S.runners = [];
  T.press('d'); const inBunt = !!(S.sw && S.sw.type === 'bunt'); const y0 = S.bOff.y, x0 = S.bOff.x;
  T.hold('u'); T.run(10); const movedUp = S.bOff.y > y0; T.hold('l'); T.run(5); const aimL = S.sw && S.sw.aim === 'l', xSame = S.bOff.x === x0; T.release(); T.C.tick();
  T.press(null); T.press('u'); T.press('l'); T.press('r'); const stillBunt = !!(S.sw && S.sw.type === 'bunt');
  T.press('d'); T.run(3); const out = !S.sw; T.press('d'); const back = !!(S.sw && S.sw.type === 'bunt');
  return { ok: inBunt && movedUp && aimL && xSame && stillBunt && out && back, inBunt, movedUp, aimLeft: aimL, sidewaysDidNotMove: xSame, otherPressesIgnored: stillBunt, downButtonLeft: out, downButtonSquaresAgain: back }; }''',
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
'runner sent to an occupied base stays put; the computer takes the out at first': r"""() => { const res = [];
  for (const [ang, ev] of [[-6, 1.4], [-12, 1.4], [0, 1.7]]) { T.start(true); const S = T.C.S; T.put([2, 3]); T.hit(ang, ev); let sent = false, first = null, moved = false;
    for (let i = 0; i < 900 && S.phase === 'batted'; i++) { if (!sent && S.holder) { T.press('l'); sent = true; const r2 = S.runners.find(r => !r.bat && r.at === 2); moved = !!(r2 && r2.to === 3); } else T.C.tick(); if (S.thr && first == null) first = S.thr.base; }
    res.push({ ang, runnerWent: moved, firstThrow: first, batterOut: S.batR.out }); }
  return { ok: res.every(r => !r.runnerWent && r.firstThrow === 1 && r.batterOut), plays: res }; }""",

'a stranded runner (stopped short of an occupied base) is never thrown at there; the computer gets him after the out at first': r"""() => { const res = [];
  for (const [ang, ev] of [[-6, 1.4], [-12, 1.4], [0, 1.7]]) { T.start(true); const S = T.C.S; T.put([2, 3]); T.hit(ang, ev);
    const r2 = S.runners.find(r => !r.bat && r.at === 2); r2.to = 3; r2.p = 0.1; let first = null;
    for (let i = 0; i < 900 && S.phase === 'batted'; i++) { T.C.tick(); if (S.thr && first == null) first = S.thr.base; }
    res.push({ ang, firstThrow: first, batterOut: S.batR.out, outs: S.playOuts }); }
  return { ok: res.every(r => r.firstThrow !== 3 && r.batterOut && r.outs === 2), plays: res }; }""",

'runners on 1st and 2nd: sending the trailing runner back to first leaves the runner on 2nd alone': r"""() => { T.start(true); const S = T.C.S; T.put([1, 2]);
  S.phase = 'batted'; S.live = { kind: 'steal', still: 0 }; S.bb = T.I.mkBall(0, -21); T.I.giveBall('C'); S.playT = 0;   /* a steal play: no batter-runner */
  const a = S.runners.find(r => r.at === 1), b = S.runners.find(r => r.at === 2); [a, b].forEach(r => { r.lead = false; r.go = false; }); a.to = 2; a.p = 0.4; b.to = null;
  T.press('r'); return { ok: a.to === 1 && b.to == null && b.at === 2, trailing: T.rs() }; }""",

'live play, runners on 1st and 2nd: second is ignored while occupied; after third, up calls the lead runner back (he always obeys)': r"""() => { T.start(true); const S = T.C.S; T.put([1, 2]); T.hit(0, 0.2);
  const a = S.runners.find(r => !r.bat && r.at === 1), b = S.runners.find(r => !r.bat && r.at === 2); [a, b].forEach(r => { r.forced = false; r.to = null; r.p = 0; });
  T.press('u'); const ignored = a.to == null && b.to == null; T.press('l'); const leadWent = b.to === 3; T.press('u');
  const leadBack = b.to === 2 || (b.to == null && b.at === 2);
  return { ok: ignored && leadWent && leadBack && a.to == null && a.at === 1, secondFirstIgnored: ignored, runners: T.rs() }; }""",

'Case A: lead runner halfway to third, batter on first: up brings the lead runner back and the batter stays': r"""() => { T.start(true); const S = T.C.S; T.put([2]); T.hit(-10, 0.25);
  const lead = S.runners.find(r => !r.bat && r.at === 2); T.until(() => S.batR.to == null && S.batR.at === 1, 400); T.press('l'); T.until(() => lead.to === 3 && lead.p >= 0.45, 400);
  T.press('u'); return { ok: lead.to === 2 && S.batR.to == null, lead: lead.at + '>' + lead.to, batter: S.batR.at + '>' + S.batR.to }; }""",



'Case B: a forced lead runner can turn back but stays forced; whoever reaches second first gets it, and the other is forced out': r"""() => { const res = [];
  for (const [ev, at] of [[0.6, 0.3], [1.0, 0.3], [0.6, 0.7], [1.0, 0.7]]) { T.start(true); const S = T.C.S; T.put([1, 2]); T.hit(-10, ev);
    const lead = S.runners.find(r => !r.bat && r.at === 2), mid = S.runners.find(r => !r.bat && r.at === 1); T.until(() => lead.to === 3 && lead.p >= at, 400);
    T.press('u'); const forced = lead.forced && lead.fb === 3; let first = null;
    for (let i = 0; i < 3000 && S.phase === 'batted'; i++) { T.C.tick(); if (!first) { if (lead.to == null && lead.at === 2) first = 'lead'; else if (mid.to == null && mid.at === 2) first = 'trailing'; } }
    res.push({ ev, at, stillForced: forced, first, lead: lead.out ? lead.how : 'safe at ' + lead.at, trailing: mid.out ? mid.how : 'safe at ' + mid.at }); }
  const ok = res.every(r => r.stillForced && (r.first === 'lead' ? r.lead === 'safe at 2' && /Forced out at second/.test(r.trailing) : r.trailing === 'safe at 2' && /Forced out at third/.test(r.lead)));
  return { ok, plays: res }; }""",

'a fielder with the ball touching the force base puts out a forced runner who turned back': r"""() => { T.start(false); const S = T.C.S; T.put([1, 2]); T.hit(-10, 0.6);
  const lead = S.runners.find(r => !r.bat && r.at === 2); T.until(() => lead.to === 3 && lead.p >= 0.4, 400);
  lead.at = 3; lead.to = 2; lead.p = 1 - lead.p;
  S.bb = T.I.mkBall(-60.2, 63.6); T.I.giveBall('3B'); S.F['3B'].x = -60.2; S.F['3B'].y = 63.6; T.C.tick();
  return { ok: lead.out && /Forced out at third/.test(lead.how), how: lead.how }; }""",

'the play clock never ends a play while a runner is off a base': r"""() => { let a = 99; const rn = () => { a = (a * 1103515245 + 12345) & 0x7fffffff; return a / 0x7fffffff; };
  const bad = []; let plays = 0;
  for (let k = 0; k < 40; k++) { T.start(rn() < 0.5); const S = T.C.S; T.put([[1], [2], [1, 2], [1, 3], [2, 3], [1, 2, 3]][Math.floor(rn() * 6)]); T.hit(Math.floor(rn() * 80) - 40, 0.6 + rn() * 1.2); plays++;
    for (let i = 0; i < 4000 && S.phase === 'batted'; i++) {
      const off = S.runners.some(r => !r.out && !r.scored && r.to != null && !r.lead && !r.trot), outs = S.outs;
      if (rn() < 0.02) T.press(['u', 'l', 'r', 'd'][Math.floor(rn() * 4)]); else T.C.tick();
      if (S.phase !== 'batted' && off && S.outs < 3 && !S.over && S.outs === outs && S.runners.some(r => !r.out && !r.scored)) bad.push({ k, i, toast: T.toast() }); } }
  return { ok: bad.length === 0, plays, endedWithRunnerOff: bad.slice(0, 3) }; }""",

'the catcher throws the ball back to the pitcher after a pitch that is not hit': r"""() => { let saw = 0, ready = false, call = '';
  for (let k = 0; k < 12 && !saw; k++) { T.start(true); const S = T.C.S; S.runners = [];   /* you bat and never swing: the computer's pitch is caught */
    for (let i = 0; i < 600 && S.phase !== 'result' && S.phase !== 'batted'; i++) T.C.tick();
    if (S.phase !== 'result' || !S.ret) continue; call = T.toast();
    for (let i = 0; i < 300 && S.phase === 'result'; i++) { if (S.ret && S.ret.t >= 0 && S.ret.t < 46) saw++; T.C.tick(); } ready = S.phase === 'ready'; }
  return { ok: saw > 20 && ready, ticksInFlight: saw, call }; }""",

'SAFE call when a runner beats a close throw': r"""() => { T.start(true); const S = T.C.S; S.runners = []; T.hit(0, 0.2); const b = S.batR; b.p = 0.985; S.F['1B'].x = 60.2; S.F['1B'].y = 63.6;
  S.bb = T.I.mkBall(30, 70); T.I.giveBall('2B'); S.F['2B'].x = 30; S.F['2B'].y = 70; S.thr = { player: '1B', x: 50, y: 66, sx: 30, sy: 70, tx: 60.2, ty: 63.6, base: 1, d0: 31, peak: 8, sp: 1.2 }; S.holder = null; S.thrFrom = '2B';
  const calls = T.watch(80); return { ok: calls.some(c => / SAFE /.test(c)), calls }; }""",

'a runner standing on a base is drawn in front of a fielder on the bag': r"""() => { document.getElementById('title').hidden = true; T.start(true); const S = T.C.S; T.put([2]); const r = S.runners[0]; r.lead = false; r.to = null;
  S.phase = 'result'; S.rt = 999; S.wasLive = true; S.bb = T.I.mkBall(0, 125.9); S.holder = '2B'; S.F['2B'].x = 0.4; S.F['2B'].y = 125.9; document.getElementById('toast').classList.remove('on');
  return new Promise(done => requestAnimationFrame(() => requestAnimationFrame(() => {
    const cv = document.getElementById('cv'), k = cv.width / 844, d = cv.getContext('2d').getImageData(Math.round(420 * k), Math.round(146 * k), Math.max(1, Math.round(4 * k)), Math.max(1, Math.round(3 * k))).data;
    let rr = 0, bl = 0; for (let i = 0; i < d.length; i += 4) { rr += d[i]; bl += d[i + 2]; }
    S.rt = 1; done({ ok: rr > bl, red: rr, blue: bl }); }))); }""",
'holding runners: the quickest pickoff to any base is caught on the bag, from anywhere on the rubber': r"""() => { const res = [];
  for (const base of [1, 2, 3]) for (const slide of [-6, 0, 6]) { T.start(false); const S = T.C.S; T.put([base]); S.pOff = slide; S.F.P.x = slide; T.I.resetPlay(); T.I.takeLeads();
    const id = { 1: '1B', 2: '2B', 3: '3B' }[base], b = { 1: [60.2, 63.6], 2: [0, 127.3], 3: [-60.2, 63.6] }[base];
    T.press(null); T.hold({ 1: 'r', 2: 'u', 3: 'l' }[base]); T.C.tick(); T.release();
    let n = 0; while ((S.thr || S.queued != null || S.windT > 0) && n < 200) { T.C.tick(); n++; }
    const f = S.F[id]; res.push({ base, slide, caughtBy: S.holder, offBag: S.holder ? +Math.hypot(f.x - b[0], f.y - b[1]).toFixed(2) : null }); }
  return { ok: res.every(r => r.caughtBy === { 1: '1B', 2: '2B', 3: '3B' }[r.base] && r.offBag < 1.5), plays: res }; }""",
'W A S D type into the name box but still steer in the game; Game Setup has a Back button': r"""() => {
  const box = document.getElementById('pname'), ev = (el, code) => { const e = new KeyboardEvent('keydown', { code, key: code.slice(-1).toLowerCase(), bubbles: true, cancelable: true }); el.dispatchEvent(e); document.dispatchEvent(new KeyboardEvent('keyup', { code, bubbles: true })); return e.defaultPrevented; };
  const blockedInBox = ['KeyW', 'KeyA', 'KeyS', 'KeyD'].filter(c => ev(box, c));
  const steersInGame = ev(document.body, 'KeyA');
  const back = !!document.getElementById('sback');
  return { ok: blockedInBox.length === 0 && steersInGame && back, blockedInBox, steersInGame, setupBack: back }; }""",
'runners on 1st and 2nd: two runners are never sent to the same base (before, during and after the pitch)': r"""() => {
  const run = (seq) => { T.start(true); const S = T.C.S; T.put([1, 2]); T.I.takeLeads(); T.run(40);
    for (const step of seq) { if (step === 'windup') T.until(() => S.phase === 'windup', 400);
      else if (step === 'stealplay') { S.runners.forEach(r => { r.lead = false; r.go = false; }); const a = S.runners.find(r => r.at === 1), b = S.runners.find(r => r.at === 2); a.to = null; b.to = 3; b.p = 0.3; S.phase = 'batted'; S.live = { kind: 'steal', still: 0 }; S.bb = T.I.mkBall(0, -21); T.I.giveBall('C'); }
      else T.press(step); }
    const a = S.runners.find(r => r.snap === 1 || r.at === 1 && !r.bat), b = S.runners.find(r => r !== a && !r.bat);
    const dest = r => r.lead ? (r.go ? r.to : r.at) : (r.to == null ? r.at : r.to);
    return { a: dest(a), b: dest(b) }; };
  const cases = { upBeforePitch: run(['u']), thirdThenUp: run(['l', 'u', 'windup']), upInWindup: run(['windup', 'u']), upOnStealPlay: run(['stealplay', 'u']) };
  const ok = Object.values(cases).every(c => c.a !== c.b) && cases.thirdThenUp.a === 2 && cases.thirdThenUp.b === 3 && cases.upOnStealPlay.a === 1 && cases.upOnStealPlay.b === 2; /* live play: up calls the lead runner back (version 84) */
  return { ok, cases }; }""",
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
