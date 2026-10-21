"""Exploit hunting: whole games where your side's runners use the tricks the user found (Oct 20),
against the computer's fielding. Lower runs per half-inning and more runners thrown out = better defense.

usage: python3 tests/adv.py [games=6]
The runner policy (window.__adv): go when the defense throws somewhere else or nobody with the ball is near
the next base; turn back when the ball closes in; reverse again when they throw to the base he's going back to.
Reference (version 58 and later): about 0.5 runs per half-inning; 40 runners out over 14 games.
Edit ADV to try a new trick the user reports.
"""
import sys
from common import page

GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 6
ADV = r"""() => { window.__adv = function (S, A) {
  if (!S.live || S.live.kind !== 'hit') return;
  S.runners.forEach(function (r) {
    if (!A.alive(r) || r.trot || r.award || r.lead) return;
    var hp = S.holder ? S.F[S.holder] : null, tgt = S.thr ? S.thr.base : null;
    if (r.to == null) {
      var nx = r.at + 1; if (nx > 4 || (nx <= 3 && A.standingOn(nx, r))) return;
      var nb = A.basePos(nx);
      if ((S.thr && tgt !== nx) || (hp && A.dist2(hp.x, hp.y, nb[0], nb[1]) > 40)) A.sendRunner(r, nx);
      return;
    }
    var rp = A.rPos(r);
    if (r.to > r.at) { if ((hp && A.dist2(hp.x, hp.y, rp[0], rp[1]) < 22) || tgt === r.to) A.sendRunner(r, r.at); }
    else if (tgt === r.to && r.at <= 4) A.sendRunner(r, r.at);
  });
}; }"""

with page('adv.html', helper=False) as (pg, errs):
    pg.evaluate(ADV)
    tot = {'runs': 0, 'hits': 0, 'runnersOut': 0, 'halfInnings': 0}
    for g in range(GAMES):
        pg.evaluate("() => { window.__ccb.newGame({ innings: 3 }); window.__ccb.S.paused = true; }")
        r = pg.evaluate("""() => { const C = window.__ccb; let ro = 0, last = 0;
          for (let i = 0; i < 80000 && !C.S.over; i++) { C.tick(); const S = C.S; const o = S.runners.filter(x => x.out && !x.bat).length; if (S.phase === 'batted' && o > last) ro += o - last; last = o; }
          const S = C.S; return { runs: S.score.you + S.score.cpu, hits: S.stats.you.h + S.stats.cpu.h, ro, halves: S.half }; }""")
        tot['runs'] += r['runs']; tot['hits'] += r['hits']; tot['runnersOut'] += r['ro']; tot['halfInnings'] += r['halves']
    print(tot, 'runs per half-inning %.2f' % (tot['runs'] / max(1, tot['halfInnings'])))
    print('page errors:', errs[:5] or 'none')
