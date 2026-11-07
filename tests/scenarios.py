"""Scripted rule checks on the real game (with internal hooks). Each prints PASS or FAIL with details.

usage: python3 tests/scenarios.py
Add a check by writing a JS function that returns { ok: bool, ...details } and calling check().
T (tests/T.js) has helpers: T.start(batFirst), T.run(n), T.until(fn, n), T.press(dir), T.hold(dir), T.release(),
T.put([bases]), T.rs() (runner summary like '1>2@0.40,3'), T.toast(), T.watch(n). T.I exposes internal functions.
"""
import json, sys
from common import page

CHECKS = {
'bat break (version 1.48): every strikeout the batter stays in the box and breaks his bat (over the knee or slammed down), with one snap sound; gone for the next batter': r"""() => { const C = window.__ccb, res = { kinds: {}, snaps: 0, ks: 0, drawn: 0 };
  for (let g = 0; g < 12; g++) { T.start(true); const S = C.S; S.seed = 300 + g; T.until(() => S.phase === 'ready', 600); S.s = 2; S.b = 0; S.runners = [];
    const s0 = C.sfxCount.snap || 0; T.until(() => S.brk || S.outs > 0 || S.b > 0, 1200); /* you never swing: a called strike three, or a ball */
    if (!S.brk) continue; res.ks++; res.kinds[S.brk.kind] = (res.kinds[S.brk.kind] || 0) + 1; if (T.I.brkOn && T.I.brkOn()) res.drawn++;
    T.until(() => S.phase !== 'result', 400); res.snaps += (C.sfxCount.snap || 0) - s0; if (S.brk) res.left = true; }
  return { ok: res.ks >= 4 && res.snaps === res.ks && !res.left && res.drawn === res.ks && Object.keys(res.kinds).length === 2, res }; }""",
'catcher steal throw (version 1.47): the catcher throws to second 5% slower (1.75 to 1.6625); to third unchanged': r"""() => { const res = {};
  for (const [base, bases] of [[2, [1]], [3, [2]]]) { T.start(true); const S = T.C.S; T.until(() => S.phase === 'ready', 600); T.put(bases); T.I.takeLeads();
    S.runners.forEach(r => { if (!r.bat) r.go = true; }); S.cpuP = { slide: 0, delay: 10, type: 'slow', sign: 1, target: 0, pick: 0 }; S.pt = 0;
    let sp = null; for (let i = 0; i < 600 && sp == null; i++) { T.C.tick(); if (S.thr && S.thr.sp && S.thrFrom === 'C') sp = +S.thr.sp.toFixed(4); if (S.phase === 'result' || S.phase === 'ready' && i > 300) break; }
    res[base] = sp; }
  return { ok: res[2] === 1.6625 && res[3] === 1.75, res }; }""",
'catcher on the plate (version 1.46): with a play at home he stands centered on the plate, as high as he can while still on it; you can still switch to him': r"""() => { const res = {};
  T.start(false); let S = T.C.S; T.put([1, 2, 3]); T.hit(0, 1.0); T.until(() => S.holder, 400); S.ctl = S.holder; T.press('d'); let at = null;
  for (let i = 0; i < 300; i++) { const had = !!S.thr; T.C.tick(); if (had && !S.thr && !at) at = [+S.F.C.x.toFixed(2), +S.F.C.y.toFixed(2)]; if (S.phase !== 'batted') break; }
  const third = S.runners.find(r => r.fb === 4); res.forced = { catcherAt: at, out: third && third.out, how: third && third.how };
  T.start(false); S = T.C.S; T.put([3]); T.hit(-20, 2.0); const r3 = S.runners.find(r => r.at === 3); r3.to = 4; r3.p = 0; T.until(() => Math.abs(S.F.C.y - 2.3) < 0.05 || !r3.to || r3.scored || r3.out, 300); res.runnerComing = [+S.F.C.x.toFixed(2), +S.F.C.y.toFixed(2)];
  T.start(false); S = T.C.S; T.put([1, 2, 3]); T.hit(0, 1.0); T.run(15); T.press('d'); res.switchTo = S.ctl;
  const onPlate = p => p && Math.abs(p[0]) < 0.05 && Math.abs(p[1] - 2.3) < 0.05 && Math.hypot(p[0], p[1] + 1) < 3.5;
  return { ok: onPlate(res.forced.catcherAt) && res.forced.out && onPlate(res.runnerComing) && res.switchTo === 'C', res }; }""",
'no pickoff with the bases empty (version 1.44): the pitcher\'s button alone shakes off the sign instead; with a runner on it still steps off': r"""() => { const res = {};
  T.start(false); let S = T.C.S; T.until(() => S.phase === 'ready', 600); S.runners = []; T.run(5); T.press(null); res.empty = { pick: S.pick, shook: S.t - S.shake < 5, phase: S.phase };
  T.run(60); res.after = { pick: S.pick, phase: S.phase };
  T.start(false); S = T.C.S; T.until(() => S.phase === 'ready', 600); T.put([1]); T.I.takeLeads(); T.run(5); T.press(null); res.runner = { pick: S.pick };
  return { ok: !res.empty.pick && res.empty.shook && res.empty.phase === 'ready' && !res.after.pick && res.runner.pick, res }; }""",
'outfielder plays the carom (version 1.42): on a ball to the wall in the gap, the computer outfielder runs diagonally toward where it will come off the wall, not straight out to the wall first': r"""() => {
  T.start(false); const S = T.C.S; S.seed = 111; T.hit(12, 2.4); S.ctl = 'P'; let who = null, p0 = null, pw = null;
  for (let i = 0; i < 400 && !S.holder && !(S.bb && S.bb.gone); i++) { T.C.tick(); if (S.cpuChase && !who) { who = S.cpuChase; p0 = [S.F[who].x, S.F[who].y]; } if (S.bb.wall && !pw && who) pw = [S.F[who].x, S.F[who].y]; }
  if (!pw) return { ok: false, why: 'never reached the wall', who };
  const dx = Math.abs(pw[0] - p0[0]), dy = Math.abs(pw[1] - p0[1]);
  return { ok: who === 'CF' && dx > dy, who, sideways: +dx.toFixed(1), outward: +dy.toFixed(1), fielded: S.holder }; }""",
'steal home and the bunt (version 1.41): before the wind-up, down + button orders the runner on third to steal home (no bunt); once the wind-up starts it only bunts': r"""() => { const res = {};
  T.start(true); let S = T.C.S; T.until(() => S.phase === 'ready', 600); T.put([3]); T.I.takeLeads(); S.cpuP = { slide: 0, delay: 40, type: 'fast', sign: 1, target: 0, pick: 0 }; S.pt = 0; T.run(10);
  T.press('d'); let r = S.runners.find(x => !x.bat); res.ready = { go: r.go, squared: !!S.sw };
  T.until(() => S.phase === 'pitch', 300); T.run(2); res.onPitch = { at: r.at, to: r.to, lead: r.lead };
  T.start(true); S = T.C.S; T.until(() => S.phase === 'ready', 600); T.put([3]); T.I.takeLeads(); S.cpuP = { slide: 0, delay: 5, type: 'fast', sign: 1, target: 0, pick: 0 }; S.pt = 0;
  T.until(() => S.phase === 'windup', 300); T.press('d'); r = S.runners.find(x => !x.bat); res.windup = { bunt: !!(S.sw && S.sw.type === 'bunt'), lead: r.lead, to: r.to, go: r.go };
  return { ok: res.ready.go && !res.ready.squared && res.onPitch.to === 4 && !res.onPitch.lead && res.windup.bunt && res.windup.lead && !res.windup.go, res }; }""",
'off the wall (version 1.40): the ball comes off the wall 5.3% faster, so it rolls 10% farther': r"""() => { const res = {};
  for (const sp of [0.9, 1.5, 2.2]) { T.start(true); const S = T.C.S; S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 199); S.bb.wall = true; S.bb.v = sp; S.spd = { ev: 3, wall: null }; T.I.batterToFirst(false);
    T.I.wallHit(200); let v = S.bb.v, d = 0; const v0 = v; while (v > 0) { v = v * 0.997 - 0.004; if (v < 0) v = 0; d += v; }
    let w = Math.max(0.3, Math.min(0.6, v0 / 1.053)), d0 = 0; while (w > 0) { w = w * 0.997 - 0.004; if (w < 0) w = 0; d0 += w; } res[sp] = +(d / d0).toFixed(3); }
  return { ok: Object.values(res).every(x => x > 1.09 && x < 1.11), farther: res }; }""",
'air horn tap (version 1.39): the home player\'s tap after a play good for the home team plays the air horn, never the crowd cheer, so a cheer already playing is not cut off': r"""async () => {
  const C = window.__ccb; T.start(false); const S = T.C.S; S.phase = 'result'; S.rt = 200; S.goodSide = S.vis === 'you' ? 'cpu' : 'you'; S.hr = null; S.fan = {};
  const c0 = Object.assign({}, C.sfxCount); T.press(null); await new Promise(r => setTimeout(r, 150)); T.run(35); T.press(null); await new Promise(r => setTimeout(r, 150));
  const d = k => (C.sfxCount[k] || 0) - (c0[k] || 0);
  return { ok: S.fan.you && S.fan.you.k === 'horn' && d('tap_horn') === 2 && d('tap_cheer') === 0, kind: S.fan.you && S.fan.you.k, horns: d('tap_horn'), cheerTaps: d('tap_cheer') }; }""",
'move controls from the in-game menu (version 1.38): MOVE CONTROLS on the Quit screen, drag, DONE goes back to it; the game stays paused (1-player)': r"""() => {
  const $ = id => document.getElementById(id), k = () => $('stage').getBoundingClientRect().width / 844;
  const fire = (el, type, x, y) => el.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true, pointerId: 9, clientX: x, clientY: y, isPrimary: true }));
  localStorage.removeItem('ccb-ctl'); $('ctlreset').click(); T.start(true); const S = T.C.S; S.paused = false;
  $('menu').hidden = false; $('menu').click(); const paused = S.paused, quitShown = !$('quit').hidden;
  $('qmove').click(); const editing = !$('ctledit').hidden && $('quit').hidden;
  const b = $('btn').getBoundingClientRect(), x = b.left + b.width / 2, y = b.top + b.height / 2; fire($('btn'), 'pointerdown', x, y); fire(document, 'pointermove', x - 50 * k(), y); fire(document, 'pointerup', x - 50 * k(), y);
  const moved = JSON.parse(localStorage.getItem('ccb-ctl') || '{}'); $('ctldone').click(); const back = !$('quit').hidden && $('ctledit').hidden && $('setup').hidden;
  const stillPaused = S.paused; $('qno').click(); $('ctlreset').click(); $('menu').hidden = true;
  return { ok: paused && quitShown && editing && moved.btn && moved.btn[0] === 680 && back && stillPaused, paused, quitShown, editing, moved, back, stillPaused }; }""",
'computer pickoff timing (version 1.37): he steps off at his pitch moment, not right away, so a steal can be called first; the runner then goes': r"""() => {
  T.start(true); const S = T.C.S; T.until(() => S.phase === 'ready', 600); T.put([1]); S.runners.forEach(r => { r.lead = false; r.to = null; }); T.I.takeLeads();
  S.cpuP = { slide: 0, delay: 60, type: 'fast', sign: 1, target: 0, pick: 1 }; S.pt = 0;
  T.run(30); const offEarly = S.pick; T.press('u'); const r = S.runners.find(x => !x.bat); const ordered = r.go;
  let n = 0; while (!S.pick && n < 100) { T.C.tick(); n++; } const at = S.pt; T.run(3);
  const going = { at: r.at, to: r.to, lead: r.lead }; let q = 0; for (let i = 0; i < 60 && !q; i++) { T.C.tick(); q = S.pickQ || (S.thr && S.thr.base) || 0; }
  return { ok: !offEarly && ordered && at >= 60 && going.at === 1 && going.to === 2 && !going.lead && q === 2, offEarly, ordered, steppedOffAt: at, going, throwTo: q }; }""",
'steal order click (version 1.35): only the batting player\'s phone hears it, never the defense\'s': r"""() => { const C = window.__ccb, res = {};
  for (const me of ['you', 'cpu']) {
    C.newGame({ seed: 5, ai: { you: false, cpu: false }, me, vis: 'you' }); const S = C.S; S.paused = true; T.until(() => S.phase === 'ready', 400); T.put([1]); T.I.takeLeads();
    const n0 = C.sfxCount.click || 0, NOI = { dir: null, btn: false, vx: 0, vy: 0 };
    C.tick({ you: { dir: 'u', btn: true, vx: 0, vy: 1 }, cpu: NOI }); const r = S.runners.find(x => !x.bat);
    res[me === 'you' ? 'battingPhone' : 'fieldingPhone'] = { clicks: (C.sfxCount.click || 0) - n0, ordered: r.go };
  }
  C.newGame({ seed: 5 }); return { ok: res.battingPhone.clicks === 1 && res.fieldingPhone.clicks === 0 && res.battingPhone.ordered && res.fieldingPhone.ordered, res }; }""",
'play at the plate first (versions 1.35, 1.36): on a bunt, a runner coming home (not forced) gets a try at the plate, or a tag on the line when that is sooner, whenever there is a play; with none, the throw goes to first': r"""() => { const res = {};
  const play = (ang, ev, p0) => { T.start(true); const S = T.C.S; S.seed = 9; T.put([3]); T.hit(ang, ev); S.bb.bunt = true; const r = S.runners.find(x => x.at === 3); r.to = 4; r.p = p0;
    let who = null, first = null; for (let i = 0; i < 400; i++) { T.C.tick(); if (S.holder && !who) who = S.holder; if (who && first == null && (S.thr || S.cpuRunTo === 4 || r.out)) first = S.thr ? 'throw ' + S.thr.base : S.cpuRunTo === 4 ? 'runs to the plate' : 'tag'; if (S.phase === 'result') break; }
    return { who, first, runner: r.out ? 'out' : r.scored ? 'scored' : 'r' + r.at }; };
  res.closeCatcher = play(-30, 0.4, 0.25);   /* before version 1.35 he threw to first and the run scored */
  res.closeCatcher2 = play(-40, 0.35, 0.35);
  res.noPlay = play(0, 0.5, 0.6);            /* the runner is nearly home: no play there, so first */
  /* version 1.36: when it is sooner, he tags the runner on the line instead of going to the plate */
  { T.start(true); const S = T.C.S; S.seed = 9; T.put([3]); T.hit(-30, 0.45, 0); S.bb.bunt = true; const r = S.runners.find(x => x.at === 3); r.to = 4; r.p = 0.05; let ranPlate = false, outAt = null;
    for (let i = 0; i < 400; i++) { T.C.tick(); if (S.cpuRunTo === 4) ranPlate = true; if (r.out && outAt == null) { const c = S.F.C; outAt = +Math.hypot(c.x, c.y + 1).toFixed(1); } if (S.phase === 'result') break; }
    res.tagOnLine = { out: r.out, ranToPlate: ranPlate, feetFromPlate: outAt }; }
  return { ok: res.closeCatcher.who === 'C' && res.closeCatcher.first !== 'throw 1' && res.closeCatcher2.first !== 'throw 1' && res.noPlay.first === 'throw 1' && res.noPlay.runner === 'scored' && res.tagOnLine.out && !res.tagOnLine.ranToPlate && res.tagOnLine.feetFromPlate > 8, res }; }""",
'bobble chances (version 1.34): over 80% speed 20%; 75-80% 10%; over 50% to 75% 5%; 50% or less never': r"""() => {
  const I = window.__ccbi; let lo = 0, hi = 50; for (let i = 0; i < 80; i++) { const m = (lo + hi) / 2; if (I.bobbleP(m) === 0.2) hi = m; else lo = m; } const max = hi / 0.8; /* the fastest hit, from the 80% line */
  const at = {}; for (const pc of [30, 49.99, 51, 60, 74, 74.9, 75, 78, 79.99, 81, 100]) at[pc] = I.bobbleP(max * pc / 100);
  return { ok: at[30] === 0 && at[49.99] === 0 && at[51] === 0.05 && at[60] === 0.05 && at[74] === 0.05 && at[74.9] === 0.05 && at[75] === 0.1 && at[78] === 0.1 && at[79.99] === 0.1 && at[81] === 0.2 && at[100] === 0.2, at }; }""",
'moving the controls (version 1.32): MOVE on Game Setup, drag the D pad and the button, saved on the phone, RESET puts them back; dragging does not steer or swing': r"""() => {
  const $ = id => document.getElementById(id), st = () => $('stage').getBoundingClientRect(), k = () => st().width / 844;
  const at = el => { const r = el.getBoundingClientRect(), s = st(); return [Math.round((r.left - s.left) / k()), Math.round((r.top - s.top) / k())]; };
  const fire = (el, type, x, y) => el.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true, pointerId: 7, clientX: x, clientY: y, isPrimary: true }));
  const drag = (el, ddx, ddy) => { const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2; fire(el, 'pointerdown', x, y); fire(document, 'pointermove', x + ddx * k(), y + ddy * k()); fire(document, 'pointerup', x + ddx * k(), y + ddy * k()); };
  localStorage.removeItem('ccb-ctl'); $('ctlreset').click();
  const pad0 = at($('dpad')), btn0 = at($('btn'));
  $('setup').hidden = false; $('ctlmove').click(); const editing = !$('ctledit').hidden && $('setup').hidden;
  const C = window.__ccb, sw0 = C.S ? 0 : 0;
  drag($('dpad'), 0, 30); drag($('btn'), -100, -40); drag($('dpad'), 0, 500); /* the last one is held at the bottom edge */
  const pad1 = at($('dpad')), btn1 = at($('btn')), lit = $('dpad').querySelectorAll('.arm.on').length, saved = JSON.parse(localStorage.getItem('ccb-ctl'));
  $('ctldone').click(); const back = !$('setup').hidden && $('ctledit').hidden;
  $('ctlreset').click(); const pad2 = at($('dpad')), btn2 = at($('btn')), cleared = localStorage.getItem('ccb-ctl'); $('setup').hidden = true;
  return { ok: editing && pad1[1] === 390 - 136 && pad1[0] === pad0[0] && btn1[0] === btn0[0] - 100 && btn1[1] === btn0[1] - 40 && lit === 0 && saved && saved.pad[1] === 254 && back
    && pad2.join() === pad0.join() && btn2.join() === btn0.join() && cleared === null, pad0, pad1, btn0, btn1, saved, pad2, btn2 }; }""",
'speed readout (version 1.31): right of home plate, background at least 50% see-through': r"""() => {
  const e = document.getElementById('spd'), was = e.hidden; e.hidden = false; const r = e.getBoundingClientRect(), stage = document.getElementById('cv').getBoundingClientRect();
  const k = stage.width / 844, left = (r.left - stage.left) / k, alpha = parseFloat((getComputedStyle(e).backgroundColor.match(/[\d.]+\)$/) || ['1'])[0]); e.hidden = was;
  return { ok: left > 422 + 30 && alpha <= 0.5, left: Math.round(left), homePlateX: 422, alpha }; }""",
'coin flip, 1-player (version 1.30): BAT FIRST by default; you call it; the winner picks; no pick in 5 s makes the winner home; the computer picks at random; a rematch is switched by default with COIN FLIP offered (1.43)': r"""async () => {
  const C = window.__ccb, $ = id => document.getElementById(id), wait = ms => new Promise(r => setTimeout(r, ms));
  const until = async (fn, ms) => { const t = performance.now(); while (performance.now() - t < ms) { if (fn()) return true; await wait(20); } return false; };
  const keep = Object.assign({}, C.FLIPT); Object.assign(C.FLIPT, { wait: 600, spin: 200, show: 100, go: 100, cpu: 100 });
  const rand = Math.random, res = {};
  $('start').click(); res.newGame = { bat: $('bf').getAttribute('aria-pressed'), flipOffered: !$('cf').hidden };
  const coin0 = C.sfxCount.coin || 0;
  const run = async (r, call, pick) => {
    $('start').click(); $('cf').click(); Math.random = () => r; const S0 = C.S; $('go').click();
    const o = { callShown: !$('flip').hidden && !$('flcall').hidden };
    $(call === 'H' ? 'fheads' : 'ftails').click();
    await until(() => !$('flpick').hidden || C.FLIP.F && C.FLIP.F.step === 'go', 3000);
    o.pickShown = !$('flpick').hidden;
    if (pick) $(pick === 'bat' ? 'fbat' : 'fpitch').click();
    await until(() => C.FLIP.F && C.FLIP.F.step === 'go', 3000); o.said = $('flp').textContent;
    await until(() => C.S !== S0 && $('flip').hidden, 3000); Math.random = rand;
    o.vis = C.S && C.S !== S0 ? C.S.vis : 'no game'; return o; };
  res.youWinBat = await run(0.2, 'H', 'bat');       /* coin heads, you called heads: you win and bat first */
  res.youWinPitch = await run(0.2, 'H', 'pitch');   /* you pitch first */
  res.youWinNoPick = await run(0.2, 'H', null);     /* no pick: you are home */
  res.cpuWinsA = await run(0.2, 'T', null);         /* coin heads, you called tails: the computer wins and picks (random 0.2 = bat first) */
  res.cpuWinsB = await run(0.7, 'H', null);         /* coin tails: the computer wins and picks (random 0.7 = pitch first) */
  res.coinSounds = (C.sfxCount.coin || 0) - coin0;
  /* 1-player rematch: switched, no coin flip offered */
  const lastVis = C.S.vis; C.S.over = true; $('final').hidden = false; $('again').click();
  res.rematch = { lastVis, bat: $('bf').getAttribute('aria-pressed'), pitch: $('pf').getAttribute('aria-pressed'), flipOffered: !$('cf').hidden, setup: !$('setup').hidden };
  $('setup').hidden = true; Object.assign(C.FLIPT, keep);
  const ok = res.newGame.bat === 'true' && res.newGame.flipOffered
    && res.youWinBat.callShown && res.youWinBat.pickShown && res.youWinBat.vis === 'you'
    && res.youWinPitch.vis === 'cpu' && res.youWinNoPick.vis === 'cpu' && /Time's up/.test(res.youWinNoPick.said)
    && !res.cpuWinsA.pickShown && res.cpuWinsA.vis === 'cpu' && /computer wins the toss and chooses to BAT FIRST/.test(res.cpuWinsA.said)
    && res.cpuWinsB.vis === 'you' && /PITCH FIRST/.test(res.cpuWinsB.said) && res.coinSounds === 5
    && res.rematch.flipOffered === true && res.rematch.setup && res.rematch.bat === String(lastVis === 'cpu');
  return { ok, res }; }""",

'coin flip, 2-player host (version 1.30): waits for a selfie; a random caller; no call in 5 s is called for him; no pick in 5 s makes the winner home; the other phone can call and pick': r"""async () => {
  const C = window.__ccb, I = window.__ccbi, N = C.NET, $ = id => document.getElementById(id), wait = ms => new Promise(r => setTimeout(r, ms));
  const until = async (fn, ms) => { const t = performance.now(); while (performance.now() - t < ms) { if (fn()) return true; await wait(20); } return false; };
  const keep = Object.assign({}, C.FLIPT); Object.assign(C.FLIPT, { wait: 600, spin: 200, show: 100, go: 99999 });
  const rand = Math.random, sent = [], res = {}; N.role = 'host'; N.oppName = 'Bob'; N.ch = { send: m => sent.push(m) };
  /* run 1: Bob (random 0.7 makes him the caller; the coin lands tails) doesn't call or pick */
  Math.random = () => 0.7; I.flipStart(true); await wait(200);
  res.before = [C.FLIP.F.step, $('flp').textContent];
  I.flipOpp({ cam: true }); await wait(200); res.selfie = [C.FLIP.F.step, $('flp').textContent];
  I.flipOpp({ cam: false }); await wait(200); const F = C.FLIP.F; res.call = [F.step, F.caller, $('flp').textContent, $('flcall').hidden];
  await until(() => F.step === 'spin', 2000); res.auto = [F.call, F.auto, $('flp').textContent];
  await until(() => F.step === 'pick', 2000); res.pick = [F.winner, $('flp').textContent, $('flpick').hidden];
  await until(() => F.step === 'go', 2000); res.noPick = [F.pick, F.auto2, $('flp').textContent];
  res.sent = sent.filter(m => m.event === 'fl').length; I.flipStop();
  /* run 2: random 0.2 makes Ann (the host) the caller; Ann doesn't call; then the coin (heads) */
  Math.random = () => 0.2; I.flipStart(true); I.flipOpp({ cam: false }); await wait(200); const G = C.FLIP.F;
  res.hostCalls = [G.caller, $('flcall').hidden]; $('ftails').click(); await until(() => G.step === 'pick', 2000);
  res.bobWins = [G.call, G.coin, G.winner, $('flp').textContent];
  I.flipOpp({ cam: false, pick: { n: G.n, v: 'bat' } }); await wait(200); res.bobPicks = [G.step, G.pick, $('flp').textContent];
  I.flipStop(); Math.random = rand; N.ch = null; N.role = null; Object.assign(C.FLIPT, keep);
  const ok = res.before[0] === 'wait' && res.selfie[0] === 'wait' && /Bob to finish a selfie/.test(res.selfie[1]) && res.call[0] === 'call' && res.call[1] === 'cpu' && /Bob is calling/.test(res.call[2]) && res.call[3]
    && res.auto[0] === 'T' && res.auto[1] && /TAILS was called for Bob/.test(res.auto[2]) && res.pick[0] === 'cpu' && res.pick[2]
    && res.noPick[0] === 'pitch' && res.noPick[1] && /Bob is the home team. You bat first/.test(res.noPick[2]) && res.sent >= 4
    && res.hostCalls[0] === 'you' && !res.hostCalls[1] && res.bobWins[2] === 'cpu' && res.bobPicks[0] === 'go' && res.bobPicks[1] === 'bat' && /You pitch first/.test(res.bobPicks[2]);
  return { ok, res }; }""",

'run on contact (version 1.29): every runner runs on contact at any number of outs': r"""() => { const res = {};
  for (const [name, bases, outs] of [['2 outs, runner on 2nd', [2], 2], ['2 outs, runners on 2nd and 3rd', [2, 3], 2], ['2 outs, runners on 1st and 3rd', [1, 3], 2], ['1 out, runner on 2nd', [2], 1], ['0 outs, runners on 2nd and 3rd', [2, 3], 0]]) {
    let S = null, got = false;
    for (let tries = 0; tries < 30 && !got; tries++) { /* retry until a pitch is put in play (some swings miss or go foul) */
      T.start(true); S = T.C.S; S.seed = 4000 + tries * 13; S.cpuP = { slide: 0, delay: 99999, type: 'fast', sign: 1, target: 0, pick: 0 }; T.until(() => S.phase === 'ready', 600);
      T.put(bases); S.outs = outs; T.I.takeLeads(); T.run(30); S.cpuP = null; /* runners take their leads; now the computer pitches */
      T.until(() => S.phase === 'pitch' && S.ball.fy <= 6, 900); T.press(null); T.until(() => (S.sw && S.sw.hit) || S.phase !== 'pitch', 40);
      got = !!(S.sw && S.sw.hit && S.bb && !S.bb.foul);
    }
    if (!got) { res[name] = 'no fair contact'; continue; }
    res[name] = S.runners.filter(r => !r.bat && !r.out).map(r => (r.to > r.at ? 'runs ' : r.to == null ? 'stays ' : 'back ') + r.at + '>' + r.to).join(', ');
  }
  const runs = k => res[k] && !/back|stays/.test(res[k]) && res[k] !== 'no fair contact';
  return { ok: Object.keys(res).every(runs), res }; }""",

'home run chance (version 1.25): no +25 bonus under 55% speed at the fence; +10 near the lines still applies': r"""() => { const res = {};
  for (const [name, frac, x] of [['50% center', 0.50, 0], ['54% center', 0.54, 0], ['55% center', 0.55, 0], ['70% center', 0.70, 0], ['50% near line', 0.50, 150]]) {
    T.start(true); const S = T.C.S; S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; const y = x ? 115 : 200, d = Math.hypot(x, y);
    S.bb = T.I.mkBall(x, y); S.bb.wall = false; S.bb.v = frac * 4; S.spd = { ev: 3, wall: null }; T.I.batterToFirst(false); T.I.wallHit(d);
    res[name] = Math.round(S.spd.wall.ch);
  }
  return { ok: res['50% center'] === 50 && res['54% center'] === 54 && res['55% center'] === 80 && res['70% center'] === 95 && res['50% near line'] === 60, res }; }""",

'throw speeds (versions 1.24, 1.28, 1.40, 1.47): outfield throws to second 5% slower, center fielder another 15%; outfield throws home 12% then 15% faster; others unchanged': r"""() => {
  const time = (id, base) => { T.start(true); const S = T.C.S; T.hit(0, 1); const p = S.F[id]; S.bb.x = p.x; S.bb.y = p.y; T.I.giveBall(id); S.gatherT = 0;
    S.thr = null; const tx = base === 2 ? 0 : base === 4 ? 0 : 60.2, ty = base === 2 ? 127.3 : base === 4 ? -1 : 63.6; ['1B', '2B'].forEach(f => { S.F[f].x = 200; S.F[f].y = 200; });
    S.queued = null; S.animStart = null; S.quick = true; T.I.giveBall(id); S.gatherT = 0; S.windT = 1; S.queued = base; let n = 0;
    for (; n < 400; n++) { T.C.tick(); if (S.thr && S.thr.sp) return +(S.thr.sp).toFixed(3); } return null; };
  const cf2 = time('CF', 2), cf1 = time('CF', 1), lf2 = time('LF', 2), lf4 = time('LF', 4), rf4 = time('RF', 4), cf4 = time('CF', 4);
  return { ok: Math.abs(cf2 - 0.969) < 0.01 && Math.abs(cf1 - 0.96) < 0.01 && Math.abs(lf2 - 1.14) < 0.01 && Math.abs(lf4 - 1.5456) < 0.01 && Math.abs(cf4 - 1.5456) < 0.01 && Math.abs(rf4 - 1.3915) < 0.01, cf2, cf1, lf2, lf4, cf4, rf4 }; }""",

'uncaught third strike (version 1.23): swing-and-miss strike three past the catcher, the batter may run if first is empty or there are two outs': r"""() => { const res = {};
  for (const [name, bases, outs, want] of [['bases empty, 0 outs', [], 0, 'runs'], ['runner on first, 1 out', [1], 1, 'out'], ['runner on first, 2 outs', [1], 2, 'runs'], ['runner on second, 0 outs', [2], 0, 'runs']]) {
    T.start(false); const S = T.C.S; T.until(() => S.phase === 'ready', 600); if (bases.length) { T.put(bases); S.runners.forEach(r => { r.lead = false; r.to = null; }); }
    S.outs = outs; S.s = 2; const k0 = S.stats[S.vis].k; T.I.snapRunners();
    S.phase = 'pitch'; S.ball = { fx: 12, fy: -18, sp: 1.2, lv: 0.6, crossed: true, crossFx: 9 }; S.sw = { t: 20, type: 'normal', hit: false, miss: true, ct: 6, len: 16 }; S.cat = { up: false, upT: 0 };
    T.I.wildPitch();
    const runs = !!(S.batR && S.batR.to === 1 && S.live && S.live.kind === 'wild');
    res[name] = { got: runs ? 'runs' : 'out', want, outs: S.outs, k: S.stats[S.vis].k - k0, forcedAhead: S.runners.filter(r => !r.bat && r.forced).map(r => r.fb) };
  }
  /* a full play: bases empty, the batter runs, nobody touches the ball; he is safe at first */
  T.start(false); let S = T.C.S; T.until(() => S.phase === 'ready', 600); S.s = 2; S.phase = 'pitch'; S.ball = { fx: 12, fy: -18, sp: 1.2, lv: 0.6, crossed: true, crossFx: 9 }; S.sw = { t: 20, type: 'normal', hit: false, miss: true, ct: 6, len: 16 }; S.cat = { up: false, upT: 0 };
  T.I.wildPitch(); T.until(() => S.phase !== 'batted', 1500); res.play = { call: T.toast(), onFirst: S.runners.some(r => !r.out && r.at === 1 && r.to == null) || T.toast().startsWith('SAFE') };
  const ok = Object.keys(res).filter(k => k !== 'play').every(k => res[k].got === res[k].want && res[k].k === 1 && res[k].outs === (res[k].want === 'out' ? (k.includes('1 out') ? 2 : 1) : (k.includes('2 outs') ? 2 : 0)));
  return { ok: ok && res.play.call.startsWith('SAFE AT FIRST'), res }; }""",

'wild pitch with the bases empty (version 1.22): no chase; the call shows and the next pitch comes by itself; with a runner on it stays live': r"""() => { const res = {};
  for (const [name, bases, s0, b0] of [['empty, ball', [], 0, 0], ['empty, two strikes', [], 2, 0], ['runner on first', [1], 0, 0], ['runner on first stealing', [1], 0, 0], ['empty, ball four', [], 0, 3]]) {
    T.start(false); const S = T.C.S; T.until(() => S.phase === 'ready', 600); if (bases.length) { T.put(bases); T.I.takeLeads(); S.runners.forEach(r => { r.go = name.includes('stealing'); }); } S.s = s0; S.b = b0;
    T.hold('r'); T.press('r'); T.until(() => S.phase === 'pitch', 200); S.cpuB = { decided: true }; /* you pitch a curve and curve it hard toward first; the batter takes it */
    T.until(() => { T.C.human.dir = 'r'; T.C.human.vx = 1; return S.phase !== 'pitch'; }, 600); T.release();
    const kind = S.live && S.live.kind, phase = S.phase, toast = T.toast(); let back = T.until(() => S.phase === 'ready', 600);
    res[name] = { phase, live: kind || null, toast, readyAfterTicks: back };
  }
  const e = ['empty, ball', 'empty, two strikes'].every(k => res[k].phase === 'result' && res[k].readyAfterTicks >= 0 && /Wild pitch/.test(res[k].toast));
  return { ok: e && res['runner on first'].live === 'wild' && res['runner on first stealing'].live === 'wild' && res['empty, ball four'].live === 'wild', res }; }""",

'lead runner priority (version 1.19): runner going 2nd to 3rd, batter going to 1st; up + button sends only the lead runner back to 2nd': r"""() => { T.start(true); const S = T.C.S; T.put([2]); const a = S.runners[0]; a.lead = false; a.to = 3; a.p = 0.3; T.I.snapRunners();
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(-40, 120); S.bb.v = 0.5; T.I.batterToFirst(false); const b = S.batR; b.p = 0.3; b.forced = false; a.forced = false;
  T.press('u'); const res = { lead: [a.at, a.to], batter: [b.at, b.to, b.next] };
  return { ok: a.to === 2 && b.to === 1 && !b.next, res }; }""",

'after the game (version 1.18): home win cheers, visitor win boos; winner fanfare; final-screen taps: winner Yeah, loser Boo': r"""() => { const res = [], el = id => document.getElementById(id);
  for (const [youBatFirst, youWin] of [[true, true], [true, false], [false, true], [false, false]]) {
    T.start(youBatFirst); const S = T.C.S; const c0 = Object.assign({}, window.__ccb.sfxCount);
    S.score.you = youWin ? 3 : 1; S.score.cpu = youWin ? 1 : 3; T.I.endGame();
    const c1 = window.__ccb.sfxCount, d = k => (c1[k] || 0) - (c0[k] || 0);
    const youHome = !youBatFirst, homeWon = youHome === youWin;
    window.__ccb.endTap(); const c2 = window.__ccb.sfxCount;
    res.push({ youBatFirst, youWin, cheer: d('cheer'), boo: d('boo'), fanfare: d('fanfare'), tapYeah: (c2.endYeah || 0) - (c0.endYeah || 0), tapBoo: (c2.endBoo || 0) - (c0.endBoo || 0), btnUp: el('btn').classList.contains('fin') || true,
      ok: d('cheer') === (homeWon ? 1 : 0) && d('boo') === (homeWon ? 0 : 1) && d('fanfare') === (youWin ? 1 : 0) });
    el('final').hidden = true;
  }
  return { ok: res.every(r => r.ok), res }; }""",

'1-player rematch (version 1.16): REMATCH opens Game Setup with home and away switched; PLAY BALL starts it that way': r"""() => { const el = id => document.getElementById(id), res = [];
  for (const firstBat of [true, false]) {
    T.start(firstBat); T.C.S.paused = false; T.I.endGame(); const label = el('again').textContent; el('again').click();
    const picked = el('pf').getAttribute('aria-pressed') === 'true' ? 'pitch first' : 'bat first'; el('go').click(); const S = T.C.S;
    res.push({ firstBat, label, picked, nowVis: S.vis }); el('menu').click(); el('qyes').click();
  }
  return { ok: res.every(r => r.label === 'REMATCH' && r.picked === (r.firstBat ? 'pitch first' : 'bat first') && r.nowVis === (r.firstBat ? 'cpu' : 'you')), res }; }""",

'cheer and boo taps (versions 1.17, 1.33): after a run or an out, while the call shows; good for home: home air horn (version 1.39), visitor a single "Boo!" (never the crowd); good for visitors: home boos, visitor "Yeah!"; the last thing decides': r"""() => { const res = {};
  /* the table: you are the visitor (bat first) or home (pitch first); the last thing was good for one team */
  for (const [youBatFirst, good, want] of [[true, 'cpu', 'boo1'], [true, 'you', 'yeah'], [false, 'you', 'horn'], [false, 'cpu', 'boo']]) {
    T.start(youBatFirst); const S = T.C.S; S.phase = 'result'; S.rt = 100; S.goodSide = good; S.hr = null; S.fan = {}; T.press(null);
    res[(youBatFirst ? 'visitor' : 'home') + ', good for ' + (good === S.vis ? 'visitors' : 'home')] = [want, S.fan.you && S.fan.you.k];
  }
  /* a run crossing makes it good for the batting team; an out after it on the same play flips it (the last thing decides) */
  T.start(true); let S = T.C.S; T.put([3]); S.runners.forEach(r => { r.lead = false; r.to = null; }); T.I.snapRunners(); S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 160); T.I.batterToFirst(false);
  const r3 = S.runners.find(r => r.at === 3); r3.to = 4; r3.p = 0.95; T.until(() => r3.scored, 60); const afterRun = S.goodSide;
  T.I.giveBall('1B'); S.F['1B'].x = 60.2; S.F['1B'].y = 63.6; S.ctl = '1B'; T.until(() => S.outs > 0, 30); const afterOut = S.goodSide; /* the first baseman with the ball on the bag forces the batter out */
  res.lastThing = [afterRun, afterOut];
  /* never during live play */
  T.start(true); S = T.C.S; S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 60); S.goodSide = 'cpu'; S.fan = {}; T.press(null); res.live = S.fan.you ? 'tapped' : 'none';
  /* the half-second limit, after a real strikeout */
  T.start(true); S = T.C.S; S.seed = 11; T.until(() => S.phase === 'ready', 600); S.s = 2; S.cpuP = null; T.until(() => S.outs > 0, 3000); T.until(() => S.phase === 'result', 300);
  T.run(2); T.press(null); const t1 = S.fan.you && S.fan.you.t; T.run(5); T.press(null); const t2 = S.fan.you.t; T.run(35); T.press(null); res.limit = [t1 != null && t2 === t1, S.fan.you.t > t1, S.fan.you.k];
  const table = Object.keys(res).filter(k => k.includes('good for')).every(k => res[k][0] === res[k][1]);
  return { ok: table && res.lastThing[0] === 'you' && res.lastThing[1] === 'cpu' && res.live === 'none' && res.limit[0] && res.limit[1] && res.limit[2] === 'boo1', res }; }""",

'menu and volume (version 1.15): a tap on either button reaches it, even while both portraits are doubled': r"""() => { T.start(true); const S = T.C.S; document.getElementById('menu').hidden = false; const ttl = document.getElementById('title'), was = ttl.hidden; ttl.hidden = true;
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 200); S.bb.wall = false; S.bb.v = 4; T.I.batterToFirst(false); T.I.wallHit(200); T.C.view();
  const hit = (id) => { const b = document.getElementById(id).getBoundingClientRect(), e = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2); return !!e && document.getElementById(id).contains(e); };
  const big = ['pl', 'pr'].every(id => document.getElementById(id).classList.contains('big'));
  const res = { ok: big && hit('menu') && hit('mute'), big, menu: hit('menu'), mute: hit('mute') }; ttl.hidden = was; return res; }""",

'foul line (version 1.14): a grounder rolling along the line past first or third is fair; one clearly off it is foul': r"""() => { const res = [];
  for (const side of [1, -1]) for (const [d, want] of [[0, 'fair'], [2.5, 'fair'], [4.5, 'fair'], [7, 'foul']]) {
    T.start(false); const S = T.C.S; S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.sw = null;
    S.bb = { bunt: false, x: side * (20 + d), y: 20, ux: side * 0.70711, uy: 0.70711, v: 1.4, ev: 1.4, dist: 0, h: 0, hPeak: 0, foul: false, wall: false, t: 40, gone: false, touched: false };
    T.I.batterToFirst(false); ['1B', '3B', 'P', 'C', 'RF', 'LF', '2B', 'CF'].forEach(id => { S.F[id].x = 0; S.F[id].y = 200; });
    let got = 'fair'; for (let k = 0; k < 120; k++) { T.C.tick(); if (S.bb && S.bb.foul) { got = 'foul'; break; } if (S.bb && S.bb.fairLocked) break; }
    res.push([side > 0 ? 'first' : 'third', d, want, got]);
  } return { ok: res.every(x => x[2] === x[3]), res }; }""",

'bases loaded bunt (version 1.14): the catcher covers home and never chases; the computer gets the force at home': r"""() => { const bad = []; let cpuHomeOuts = 0, n = 0;
  for (const youBat of [true, false]) for (const ang of [-30, 0, 30]) for (const ev of [0.4, 0.7]) {
    T.start(youBat); const S = T.C.S; T.until(() => S.phase === 'ready', 600); T.put([1, 2, 3]); S.runners.forEach(r => { r.lead = false; r.to = null; }); T.I.snapRunners();
    T.hit(ang, ev); S.bb.bunt = true; n++; let homeOut = false;
    for (let k = 0; k < 400 && S.phase === 'batted'; k++) { if (S.cpuChase === 'C' && S.runners.some(r => !r.out && !r.scored && r.forced && r.fb === 4)) { bad.push([youBat, ang, ev, 'catcher chased']); break; }
      const r3 = S.runners.find(r => r.fb === 4); if (r3 && r3.out) homeOut = true; T.C.tick(); }
    if (youBat && homeOut) cpuHomeOuts++;
  }
  return { ok: !bad.length && cpuHomeOuts === 6, cases: n, cpuHomeOuts, bad }; }""",

'contact swing speed (version 1.14): 1.80 to 2.81 off the bat; power unchanged': r"""() => { let cmin = 9, cmax = 0, pmin = 9, pmax = 0, n = 0;
  for (let i = 0; i < 160; i++) { T.start(true); const S = T.C.S; S.seed = 7000 + i; S.cpuP = null; const power = i % 2 === 1;
    T.until(() => S.phase === 'pitch' && S.ball.fy <= 20 - (i % 20), 900); if (S.phase !== 'pitch') continue; T.press(power ? 'u' : null);
    for (let k = 0; k < 40 && !S.bb; k++) T.C.tick(); if (!S.bb || S.bb.foul) continue; n++; const e = S.bb.ev;
    if (power) { pmin = Math.min(pmin, e); pmax = Math.max(pmax, e); } else { cmin = Math.min(cmin, e); cmax = Math.max(cmax, e); } }
  return { ok: cmin >= 1.8 && cmax <= 2.81 && pmin < 1.4 && pmax > 3, n, contact: [cmin.toFixed(2), cmax.toFixed(2)], power: [pmin.toFixed(2), pmax.toFixed(2)] }; }""",

'pickoff cover (version 1.13): the quickest pickoff to any base is caught on the bag, runner on that base or not (with someone on), from anywhere on the rubber': r"""() => {
  const BAG = { 1: [60.2, 63.6], 2: [0, 127.3], 3: [-60.2, 63.6] }, ID = { 1: '1B', 2: '2B', 3: '3B' }, DIR = { 1: 'r', 2: 'u', 3: 'l' }, bad = []; let n = 0;
  for (const base of [1, 2, 3]) for (const bases of [[1], [2], [3], [1, 2, 3]]) for (const off of [-6, 0, 6]) { /* bases empty: no pickoff since version 1.44 */
    T.start(false); const S = T.C.S; T.until(() => S.phase === 'ready', 600); T.put(bases); T.I.takeLeads(); S.pOff = off; S.F.P.x = off; T.run(120);
    const bag = BAG[base], id = ID[base]; T.press(null); T.press(DIR[base]); let got = null, thrown = false; n++;
    for (let k = 0; k < 300; k++) { T.C.tick(); if (S.thr) thrown = true; if (!thrown) continue;
      if (S.holder && S.holder !== 'P') { got = S.holder === id ? Math.hypot(S.F[id].x - bag[0], S.F[id].y - bag[1]) : S.holder; break; }
      if (!S.thr && !S.holder && S.bb && S.bb.v > 0) { got = 'rolled'; break; } }
    if (!(typeof got === 'number' && got <= 1.5)) bad.push([base, bases, off, got]);
  }
  return { ok: !bad.length, cases: n, bad }; }""",

'run scores sound (version 1.12): the ta-da plays when a runner crosses the plate, not on a home run trot': r"""() => {
  T.start(true); let S = T.C.S, played = []; const C = T.C; window.__sfxLog = played;
  T.put([3]); S.runners.forEach(r => { r.lead = false; r.to = null; }); T.I.snapRunners(); S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 160); T.I.batterToFirst(false);
  const r3 = S.runners.find(r => r.at === 3); r3.to = 4; r3.p = 0.9; const before = (window.__ccb.sfxCount || {}).tada || 0;
  T.run(120); const afterRun = (window.__ccb.sfxCount || {}).tada || 0;
  T.start(true); S = T.C.S; T.put([1, 2, 3]); S.runners.forEach(r => { r.lead = false; r.to = null; }); S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 200); S.bb.wall = false; S.bb.v = 4; T.I.batterToFirst(false);
  const b2 = (window.__ccb.sfxCount || {}).tada || 0; T.I.wallHit(200); T.run(400); const afterHr = (window.__ccb.sfxCount || {}).tada || 0;
  return { ok: afterRun - before >= 1 && afterHr === b2, runTadas: afterRun - before, hrTadas: afterHr - b2, score: S.score }; }""",

'recorded sounds (versions 1.07, 1.49): the crowd cheer (5 s), the Yeah yell and the bat crack (0.3 s) decode and play': r"""async () => {
  window.__ccb.clips(); let c = []; for (let i = 0; i < 60 && c.length < 2; i++) { await new Promise(r => setTimeout(r, 50)); c = window.__ccb.clips(); }
  const m = Object.fromEntries(c); return { ok: m.cheer > 4.9 && m.cheer < 5.2 && m.yeah > 0.3 && m.yeah < 0.8 && m.bat > 0.25 && m.bat < 0.4, clips: m }; }""",

'swing label (version 1.05): CONTACT or POWER shows after the batter swings, nothing for a bunt': r"""() => {
  const el = document.getElementById('swl'), seen = [];
  for (const [dir, want] of [[null, 'CONTACT'], ['u', 'POWER'], ['d', null]]) {
    T.start(true); const S = T.C.S; S.cpuP = null; el.hidden = true; T.until(() => S.phase === 'pitch' && S.ball.fy < 25, 800);
    T.press(dir); T.C.view();
    seen.push([want, el.hidden ? null : el.textContent]);
  }
  return { ok: seen.every(([w, g]) => w === g), seen }; }""",

'home run celebration (version 1.04): the hitting team portrait grows, flashes and has confetti; taps yell, at most one per half second': r"""() => {
  T.start(true); const S = T.C.S, el = id => document.getElementById(id);
  S.phase = 'batted'; S.live = { kind: 'hit', still: 0 }; S.bb = T.I.mkBall(0, 200); S.bb.wall = false; S.bb.v = 4; T.I.batterToFirst(false); T.I.wallHit(200);
  if (!S.hr || S.hr.side !== 'you') return { ok: false, why: 'no celebration', hr: S.hr };
  T.run(2); T.press(null); const y1 = S.yell && S.yell.t; T.run(5); T.press(null); const y2 = S.yell && S.yell.t; T.run(35); T.press(null); const y3 = S.yell && S.yell.t;
  return { ok: !!y1 && y2 === y1 && y3 > y1 && S.yell.k >= 0 && S.yell.k <= 2 && S.hr.end - S.hr.t0 >= 300, y1, y2, y3, k: S.yell.k, len: S.hr.end - S.hr.t0 }; }""",

'bobble (versions 1.05, 1.34): about 20% of grounders still over 80% speed at the fielder pop loose about 2 feet, with no call; slower ones 10% or less': r"""() => {
  let hard = 0, bob = 0, soft = 0, softBob = 0, minRoll = 99, maxRoll = 0, called = false;
  for (let i = 0; i < 400; i++) {
    T.start(false); const S = T.C.S; S.seed = 1000 + i; const fast = i % 2 === 0; T.hit(0, fast ? 4 : 2.2);
    for (let k = 0; k < 120 && !S.holder && !S.bob; k++) T.C.tick();
    if (S.bob && fast) { const x0 = S.bb.x, y0 = S.bb.y; called = called || T.toast().includes('BOBBLE'); for (let k = 0; k < 60 && S.bb.v > 0; k++) { S.bb.v = S.bb.v * 0.997 - 0.004; if (S.bb.v < 0) S.bb.v = 0; S.bb.x += S.bb.ux * S.bb.v; S.bb.y += S.bb.uy * S.bb.v; }
      const d = Math.hypot(S.bb.x - x0, S.bb.y - y0); minRoll = Math.min(minRoll, d); maxRoll = Math.max(maxRoll, d); }
    if (fast) { hard++; if (S.bob) bob++; } else { soft++; if (S.bob) softBob++; }
  }
  const rate = bob / hard; return { ok: rate > 0.13 && rate < 0.28 && softBob / soft <= 0.1 && maxRoll < 3.2 && minRoll > 1.2 && !called, hard, bob, rate: rate.toFixed(3), soft, softBob, roll: [minRoll.toFixed(2), maxRoll.toFixed(2)], called }; }""",

'portraits (version 1.03): an out makes the batting team mad with smoke and the fielders happy for 5 s; a run reaction is not cut short': r"""() => { T.start(true); const S = T.C.S, el = id => document.getElementById(id);
  T.until(() => S.phase === 'ready', 600); S.b = 0; S.s = 2; S.cpuP = null;
  T.until(() => S.outs > 0, 3000); if (!S.outs) return { ok: false, why: 'no out' };
  const out = { faces: JSON.stringify(S.faces), smokeBat: !el('sml').hidden, smokeField: !el('smr').hidden };
  T.run(305); const later = JSON.stringify(S.faces);
  /* a run's reaction is not cut short by an out on the same play */
  T.I.commitRuns && (S.playRuns = 1, T.I.commitRuns()); const run = JSON.stringify(S.faces); S.outs++; T.C.tick(); const kept = JSON.stringify(S.faces) === run && S.faceKind === 'run';
  return { ok: out.faces === '{"cpu":"happy","you":"mad"}' && out.smokeBat && !out.smokeField && later === 'null' && run === '{"you":"happy","cpu":"mad"}' && kept, out, later, run, kept }; }""",

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

'pickoff: a runner who broke and went back to his base is no stolen base; the toast shows no old second line': r'''() => { T.start(true); const S = T.C.S; S.cpuP = { slide: 0, delay: 99999, type: 'fast', sign: 1, target: 0, pick: 0 }; /* the computer pitcher waits (he could start his delivery before the test is set) */ T.put([2]); T.run(80);
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

'bunt stance: up/down move him, left/right aim, other presses do nothing, down + button goes back to hitting; not before the wind-up (version 1.41)': r'''() => { T.start(true); const S = T.C.S; S.runners = [];
  T.press('d'); const notInReady = !S.sw; S.cpuP = { slide: 0, delay: 5, type: 'fast', sign: 1, target: 0, pick: 0 }; T.until(() => S.phase === 'windup', 300); S.wlen = 99999;
  T.press('d'); const inBunt = !!(S.sw && S.sw.type === 'bunt'); const y0 = S.bOff.y, x0 = S.bOff.x;
  T.hold('u'); T.run(10); const movedUp = S.bOff.y > y0; T.hold('l'); T.run(5); const aimL = S.sw && S.sw.aim === 'l', xSame = S.bOff.x === x0; T.release(); T.C.tick();
  T.press(null); T.press('u'); T.press('l'); T.press('r'); const stillBunt = !!(S.sw && S.sw.type === 'bunt');
  T.press('d'); T.run(3); const out = !S.sw; T.press('d'); const back = !!(S.sw && S.sw.type === 'bunt');
  return { ok: notInReady && inBunt && movedUp && aimL && xSame && stillBunt && out && back, notInReady, inBunt, movedUp, aimLeft: aimL, sidewaysDidNotMove: xSame, otherPressesIgnored: stillBunt, downButtonLeft: out, downButtonSquaresAgain: back }; }''',
'bunt fielded fully in foul ground is foul (65 degrees; version 1.14 calls a ball still on the line fair)': r"""() => { T.start(true); const S = T.C.S; S.runners = []; const a = 65 * Math.PI / 180;
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
    T.until(() => S.phase === 'ready', 200); T.until(() => S.phase === 'windup', 300); T.press('d'); for (let i = 0; i < 400 && ['ready', 'windup', 'pitch'].includes(S.phase); i++) T.C.tick();
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
  /* the computer pitcher sometimes calls a pickoff in the first 40 ticks (random), which sends the runners back; start over when he does */
  const run = (seq) => { let S; for (let k = 0; k < 20; k++) { T.start(true); S = T.C.S; T.put([1, 2]); T.I.takeLeads(); S.cpuP = { slide: 0, delay: 60, type: 'fast', sign: 1, target: 0, pick: 0 }; T.run(40); if (!S.pick) break; } /* no pickoff (since 1.37 it can come later than 40 ticks) */
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
