"""Two-phone rollback check: two copies of the game play each other through a fake network.

Three copies of the game run side by side in one browser page (each in its own frame):
  host   plays team 'you' with the rollback engine (RB): its own input applies after RB.DELAY ticks,
         the opponent's is guessed until it arrives, and a wrong guess re-runs the game from that tick
  guest  plays team 'cpu' the same way
  truth  gets both players' inputs at once, with no lag
Messages between host and guest arrive after a random lag, so they also arrive out of order.
At the end all three must hold exactly the same game.

  python3 rollback.py [games] [max_lag_ticks] [max_ticks]
"""
import json, sys, threading, functools, http.server
from playwright.sync_api import sync_playwright
from common import BUILD

GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 3
LAG = int(sys.argv[2]) if len(sys.argv) > 2 else 8
MAXT = int(sys.argv[3]) if len(sys.argv) > 3 else 60 * 60 * 12

DRIVER = r"""<!doctype html><meta charset=utf8><body>
<iframe id=truth src="hooks.html" width=844 height=390></iframe>
<iframe id=host src="hooks.html" width=844 height=390></iframe>
<iframe id=guest src="hooks.html" width=844 height=390></iframe>
<script>
function rng(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const VEC = { u: [0, 16], d: [0, -16], l: [-16, 0], r: [16, 0] };
/* a made-up player: holds a direction for a while, taps the button now and then. Precomputed, so it does not
   depend on the game (the truth copy and the phones see the same inputs). */
function player(seed, n, delay) {
  const r = rng(seed), out = []; let d = null;
  for (let t = 0; t <= n + delay + 2; t++) {
    if (t <= delay) { out.push({ d: null, b: 0, x: 0, y: 0 }); continue; }
    if (r() < 0.05) { const k = r(); d = k < 0.2 ? null : k < 0.4 ? 'u' : k < 0.6 ? 'd' : k < 0.8 ? 'l' : 'r'; }
    const v = d ? VEC[d] : [0, 0];
    out.push({ d, b: r() < 0.06 ? 1 : 0, x: v[0], y: v[1] });
  }
  return out;
}
const un = p => ({ dir: p.d, btn: !!p.b, vx: p.x / 16, vy: p.y / 16 });
function setup(w, seed, me, delay) {
  const C = w.__ccb; C.newGame({ innings: 3, mercy: 10, batFirst: true, seed, ai: { you: false, cpu: false }, me: me || 'you', vis: 'you' });
  C.S.paused = true; if (me) C.RB.start(me, delay); return C;
}
window.runGame = function (seed, lag, maxT, delay) {
  const T = setup(truth.contentWindow, seed, null), A = setup(host.contentWindow, seed, 'you', delay), B = setup(guest.contentWindow, seed, 'cpu', delay);
  const inA = player(seed * 7 + 1, maxT, delay), inB = player(seed * 7 + 2, maxT, delay), net = rng(seed * 7 + 3);
  /* truth first: play until the game ends (or maxT), then the phones play exactly as many ticks */
  let n = 0; while (!T.S.over && n < maxT) { n++; T.tick({ you: un(inA[n]), cpu: un(inB[n]) }); }
  const want = JSON.stringify(T.S);
  const q = [], P = [{ C: A, inp: inA, to: 1 }, { C: B, inp: inB, to: 0 }];
  let step = 0, stalls = 0;
  while ((A.S.t < n || B.S.t < n) && step < n * 4) {
    step++;
    P.forEach((p, i) => {
      for (let j = q.length - 1; j >= 0; j--) if (q[j].to === i && q[j].at <= step) { p.C.RB.recv(q[j].m.t, q[j].m.i); q.splice(j, 1); }
      if (p.C.S.t >= n) { p.C.RB.fix(); return; }
      const m = p.C.RB.step(un(p.inp[p.C.S.t + 1 + delay]));
      if (m) q.push({ to: p.to, at: step + Math.floor(net() * (lag + 1)), m }); else stalls++;
    });
  }
  q.forEach(x => P[x.to].C.RB.recv(x.m.t, x.m.i)); A.RB.fix(); B.RB.fix();
  const S = T.S, st = S.stats;
  return { want, host: JSON.stringify(A.S), guest: JSON.stringify(B.S), ticks: n, over: S.over, half: S.half, score: S.score,
    hits: st.you.h + st.cpu.h, ks: st.you.k + st.cpu.k, walks: st.you.bb + st.cpu.bb, stalls,
    rolls: [A.RB.rolls, B.RB.rolls], rolled: [A.RB.rolled, B.RB.rolled] };
};
</script>"""


def first_diff(a, b, path='S'):
    if type(a) != type(b): return f'{path}: {a!r} vs {b!r}'
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: return f'{path}.{k}: only on one side'
            d = first_diff(a[k], b[k], f'{path}.{k}')
            if d: return d
    elif isinstance(a, list):
        if len(a) != len(b): return f'{path}: length {len(a)} vs {len(b)}'
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f'{path}[{i}]')
            if d: return d
    elif a != b: return f'{path}: {a!r} vs {b!r}'
    return None


def main():
    (BUILD / 'rollback.html').write_text(DRIVER)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    handler = functools.partial(Quiet, directory=str(BUILD))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    fails = 0
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(f'http://127.0.0.1:{srv.server_port}/rollback.html')
        pg.wait_for_function("() => ['truth','host','guest'].every(id => document.getElementById(id).contentWindow.__ccb)")
        for g in range(GAMES):
            r = pg.evaluate('([s, l, m]) => runGame(s, l, m, 1)', [1000 + g, LAG, MAXT])
            # the last call's wording is from each phone's own point of view ('YOU PITCH' / 'YOU ARE UP'), so it is left out
            game = lambda js: {k: v for k, v in json.loads(js).items() if k != 'lastToast'}
            w = game(r['want'])
            problems = [f'{who} differs from the no-lag game at {d}' for who in ('host', 'guest')
                        if (d := first_diff(w, game(r[who])))]
            ok = not problems and not errs
            fails += 0 if ok else 1
            secs = r['ticks'] / 60
            print(('PASS' if ok else 'FAIL') + f" - game {g}: {r['ticks']} ticks ({secs / 60:.1f} min of play), "
                  f"{'finished' if r['over'] else 'stopped'} in half {r['half']}, score {r['score']}, "
                  f"{r['hits']} hits, {r['ks']} strikeouts, {r['walks']} walks; lag 0-{LAG} ticks; "
                  f"re-runs host {r['rolls'][0]} ({r['rolled'][0]} ticks), guest {r['rolls'][1]} ({r['rolled'][1]} ticks); waits {r['stalls']}")
            for x in problems + errs: print('   ', x)
            errs.clear()
        br.close()
    srv.shutdown()
    print(f'{GAMES - fails}/{GAMES} passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
