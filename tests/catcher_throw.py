"""Steal-throw calibration: you are the catcher; a runner steals second from his lead.
Throws to second after a delay of 0-16 ticks (60 ticks = 1 s) for each pitch type.

usage: python3 tests/catcher_throw.py
Target (version 68, C_THROW = 1.75): normal-speed pitch (l) out with a quick throw, safe after about 12 ticks;
fast pitch (d) out even after a delay; slow pitch (u) always safe.
"""
from common import page

JS = r"""([dir, delay]) => {
  T.start(false); const S = T.C.S; S.runners = []; T.C.newRunner(1); T.I.takeLeads(); const r = S.runners[0]; r.go = true; T.run(40);
  T.press(dir);
  for (let i = 0; i < 400 && (S.phase === 'windup' || S.phase === 'pitch'); i++) { if (S.phase === 'pitch') S.cpuB = { decided: true }; T.C.tick(); }
  if (!S.live || S.live.kind !== 'steal') return 'no steal: ' + T.toast();
  T.run(delay); T.press('u');
  let res = null; for (let i = 0; i < 400 && !res; i++) { T.C.tick(); if (r.out) res = 'OUT'; else if (r.to == null && r.at === 2) res = 'SAFE'; }
  return res; }"""

with page() as (pg, errs):
    for d, name in [('d', 'fast'), ('l', 'normal'), ('u', 'slow')]:
        print(f'{name:6s}', [(delay, pg.evaluate(JS, [d, delay])) for delay in [0, 4, 8, 12, 16]])
    print('page errors:', errs[:5] or 'none')
