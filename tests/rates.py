"""Success rates against the computer's defense: your steals of second and your bunts.

usage: python3 tests/rates.py [attempts=60] [steals|bunts|both]
Steals: a runner on first ordered to steal from his lead; results by pitch type (fast/curve/slow).
Bunts: square around, aim left/right/straight in turn; counts outs, hits and fouls.
Reference (version 73, 200 attempts each): steals about 50% safe (fast pitches always out, curves about 50-60%, slow always safe);
bunts about 10-12% hits with no runner on (counted by whether the batter is put out; earlier versions read the call text and showed about 6%).
"""
import json, sys
from common import page

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
WHAT = sys.argv[2] if len(sys.argv) > 2 else 'both'

STEALS = r"""(N) => { const t = {}; let n = 0;
  for (let k = 0; k < N * 3 && n < N; k++) { T.start(true); const S = T.C.S; S.runners = []; T.C.newRunner(1); T.I.takeLeads();
    T.run(30); T.press('u');
    T.until(() => S.phase === 'windup', 400); const ty = S.cpuP && S.cpuP.type;
    for (let i = 0; i < 400 && (S.phase === 'windup' || S.phase === 'pitch'); i++) { if (S.phase === 'pitch') S.cpuB = { decided: true }; T.C.tick(); }
    if (!S.live || S.live.kind !== 'steal') continue; n++;
    const r = S.runners.find(x => !x.bat); let res = null; for (let i = 0; i < 600 && !res; i++) { T.C.tick(); if (r.out) res = 'out'; else if (r.to == null && r.at === 2) res = 'safe'; }
    const key = ty + ':' + res; t[key] = (t[key] || 0) + 1; }
  return t; }"""

BUNTS = r"""(N) => { const t = { out: 0, hit: 0, foul: 0 }; let n = 0;
  for (let k = 0; k < N * 4 && n < N; k++) { T.start(true); const S = T.C.S; S.runners = [];
    T.until(() => S.phase === 'ready', 200); T.run(10); T.press('d'); const aim = ['l', 'r', null][k % 3]; if (aim) T.hold(aim);
    for (let i = 0; i < 400 && ['ready', 'windup', 'pitch'].includes(S.phase); i++) T.C.tick();
    T.release(); if (!S.bb || !S.bb.bunt) continue;
    const b = S.batR; for (let i = 0; i < 700 && S.phase === 'batted'; i++) T.C.tick();
    n++; if (!b || S.bb.foul || /FOUL|STRIKEOUT/.test(T.toast())) t.foul++; else if (b.out) t.out++; else t.hit++; }   /* by the real outcome, not the call text (version 73) */
  t.hitPercentOfFair = Math.round(100 * t.hit / Math.max(1, t.out + t.hit)); return t; }"""

with page() as (pg, errs):
    if WHAT in ('steals', 'both'): print('steals:', json.dumps(pg.evaluate(STEALS, N)))
    if WHAT in ('bunts', 'both'): print('bunts:', json.dumps(pg.evaluate(BUNTS, N)))
    print('page errors:', errs[:5] or 'none')
