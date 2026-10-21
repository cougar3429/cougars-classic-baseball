"""Soak test: whole computer-vs-computer games, checking rule invariants every tick.

usage: python3 tests/soak.py [games=6]
Prints each game's score and any broken invariant, then a count of every call shown on screen
(plus * counters for double plays, pickoff throws, steal attempts and stretch pitches).
"""
import json, sys
from common import page

GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 6
JS = r"""
(maxTicks) => {
  const C = window.__ccb, ev = {}, bad = [];
  let lastT = '', ticks = 0;
  while (ticks < maxTicks && !C.S.over) {
    C.tick(); ticks++;
    const S = C.S;
    const tt = document.getElementById('tt').textContent, on = document.getElementById('toast').classList.contains('on');
    const sub = document.getElementById('ts').hidden ? '' : document.getElementById('ts').textContent, key = tt + '|' + sub;
    if (on && key !== lastT) { lastT = key; const k = tt.replace(/[0-9]+/g, '#'); ev[k] = (ev[k] || 0) + 1; }
    const alive = S.runners.filter(r => !r.out && !r.scored), st = {};
    for (const r of alive) {
      if (r.to == null && r.at >= 1 && r.at <= 3) { if (st[r.at]) bad.push('two runners standing on base ' + r.at + ' (phase ' + S.phase + ')'); st[r.at] = 1; }
      if (!isFinite(r.p) || r.p < 0 || r.p > 1) bad.push('runner progress out of range: ' + r.p);
    }
    if (S.phase === 'ready' && !S.pick && alive.some(r => r.to != null && !r.lead)) bad.push('runner moving between pitches');
    if (S.phase === 'ready' && alive.length > 3) bad.push('4 runners between pitches');
    if (S.outs > 3) bad.push('more than 3 outs');
    for (const id in S.F) if (!isFinite(S.F[id].x) || !isFinite(S.F[id].y)) bad.push('fielder position not a number: ' + id);
    if (S.playOuts >= 2 && !S.__dp) { S.__dp = 1; ev['*DOUBLE PLAY'] = (ev['*DOUBLE PLAY'] || 0) + 1; } if (S.phase === 'windup') S.__dp = 0;
    if (S.phase === 'batted' && S.live && S.live.kind === 'pick' && !S.__pk) { S.__pk = 1; ev['*PICKOFF THROW'] = (ev['*PICKOFF THROW'] || 0) + 1; } if (S.phase === 'ready') S.__pk = 0;
    if (S.phase === 'windup' && S.wt === 1 && S.runners.some(r => r.to != null && !r.lead)) ev['*STEAL ATTEMPT'] = (ev['*STEAL ATTEMPT'] || 0) + 1;
    if (S.phase === 'windup' && S.wt === 1 && S.stretch) ev['*STRETCH PITCH'] = (ev['*STRETCH PITCH'] || 0) + 1;
    if (bad.length > 20) break;
  }
  return { ticks, over: C.S.over, score: C.S.score, ev, bad: [...new Set(bad)].slice(0, 20) };
}
"""

with page('auto.html', helper=False) as (pg, errs):
    tot, failed = {}, False
    for g in range(GAMES):
        pg.evaluate("() => { window.__ccb.newGame({ innings: 3 }); window.__ccb.S.paused = true; document.getElementById('title').hidden = true; }")
        r = pg.evaluate(JS, 60 * 60 * 40)
        for k, v in r['ev'].items(): tot[k] = tot.get(k, 0) + v
        failed = failed or bool(r['bad']) or not r['over']
        print('game', g, 'finished' if r['over'] else 'DID NOT FINISH', 'score', r['score'], 'problems', r['bad'] or 'none')
    print(json.dumps(dict(sorted(tot.items(), key=lambda kv: -kv[1])), indent=0))
    print('page errors:', errs[:5] or 'none')
    sys.exit(1 if failed or errs else 0)
