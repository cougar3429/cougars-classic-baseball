"""Online 2-player check: two copies of the real game (net.html, with a stand-in for supabase-js) play each other
through the real lobby buttons: Ann hosts, Bob asks to join, Ann denies once, Bob asks again, Ann accepts.
Both then play for a while with made-up inputs at real speed over a laggy simulated network.
Passes when both phones have played, the game states they reached agree at every checked tick (fingerprints
of final states), and when Bob quits, Ann is told.

  python3 net.py [seconds_of_play] [lag_ms]
"""
import sys, threading, functools, http.server, time
from playwright.sync_api import sync_playwright
from common import BUILD

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 25
LAG = int(sys.argv[2]) if len(sys.argv) > 2 else 40

PAGE = """<!doctype html><meta charset=utf8><body style="margin:0">
<iframe id=a src="net.html" width=844 height=390></iframe><iframe id=b src="net.html" width=844 height=390></iframe>"""

# a made-up player: holds a direction for a while, taps the button now and then (runs inside each copy of the game)
DRIVE = """(seed) => { let a = seed; const r = () => { a = (a * 1103515245 + 12345) & 0x7fffffff; return a / 0x7fffffff; };
  const h = window.__ccb.human, V = { u: [0, 1], d: [0, -1], l: [-1, 0], r: [1, 0] }; let d = null;
  window.__drive = setInterval(() => { if (r() < 0.06) { const k = r(); d = k < 0.25 ? null : ['u', 'd', 'l', 'r'][Math.floor(r() * 4)]; }
    h.dir = d; h.vx = d ? V[d][0] : 0; h.vy = d ? V[d][1] : 0; if (r() < 0.05) h.btn = true; }, 16); }"""


def main():
    (BUILD / 'netpair.html').write_text(PAGE)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(BUILD)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    problems, errs = [], []
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 1700, 'height': 400})
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(f'http://127.0.0.1:{srv.server_port}/netpair.html')
        pg.wait_for_function("() => ['a','b'].every(id => document.getElementById(id).contentWindow.__ccb)")
        A = pg.frame_locator('#a'); B = pg.frame_locator('#b')
        fa = [f for f in pg.frames if f.url.endswith('net.html')]
        ann, bob = fa[0], fa[1]
        for f in (ann, bob): f.evaluate('(l) => { window.__mockLag = l; }', LAG)
        for loc, name in ((A, 'Ann'), (B, 'Bob')):
            loc.locator('#p2').click(); loc.locator('#start').click(); loc.locator('#go').click()
            loc.locator('#pname').fill(name); loc.locator('#pname').dispatch_event('change')
        A.locator('#host').click()
        B.locator('#games button', has_text='ASK TO JOIN').click(timeout=5000)
        A.locator('#reqs button', has_text='DENY').click(timeout=5000)
        B.locator('#hstat', has_text='said no').wait_for(timeout=5000)
        B.locator('#games button', has_text='ASK TO JOIN').click(timeout=5000)
        A.locator('#reqs button', has_text='ACCEPT').click(timeout=5000)
        for f in (ann, bob): f.wait_for_function('() => window.__ccb.NET.live', timeout=8000)
        names = [f.evaluate("() => document.getElementById('wl').textContent + '/' + document.getElementById('wr').textContent") for f in (ann, bob)]
        ann.evaluate(DRIVE, 11); bob.evaluate(DRIVE, 22)
        t0 = time.time()
        while time.time() - t0 < SECS: pg.wait_for_timeout(1000)
        for f in (ann, bob): f.evaluate('() => clearInterval(window.__drive)')
        pg.wait_for_timeout(1500)
        info = [f.evaluate("() => { const C = window.__ccb, R = C.RB; return { me: C.ME, t: C.S.t, half: C.S.half, score: C.S.score, over: C.S.over, rolls: R.rolls, rolled: R.rolled, hashes: R.hashes }; }") for f in (ann, bob)]
        common = sorted(set(info[0]['hashes']) & set(info[1]['hashes']), key=int)
        bad = [k for k in common if info[0]['hashes'][k] != info[1]['hashes'][k]]
        if len(common) < 20: problems.append(f'only {len(common)} ticks to compare')
        if bad: problems.append(f'the phones disagree from tick {bad[0]} ({len(bad)} of {len(common)} checked ticks)')
        if info[0]['me'] != 'you' or info[1]['me'] != 'cpu': problems.append(f"teams {info[0]['me']}/{info[1]['me']}")
        # Bob quits: Ann should be told
        B.locator('#menu').click(); B.locator('#qyes').click()
        try: A.locator('#nmp', has_text='Bob').wait_for(timeout=5000); told = A.locator('#nmp').inner_text()
        except Exception: told = None; problems.append('Ann was not told that Bob left')
        br.close()
    srv.shutdown()
    for who, i in zip(('Ann (host)', 'Bob (guest)'), info):
        print(f"{who}: tick {i['t']}, half {i['half']}, score {i['score']}, re-runs {i['rolls']} ({i['rolled']} ticks)")
    print(f'scoreboard labels Ann/Bob: {names}; checked ticks {len(common)}; Ann told: {told!r}')
    for x in problems + errs[:5]: print('   ', x)
    ok = not problems and not errs
    print('PASS' if ok else 'FAIL', '- online 2-player: lobby, deny, accept, play, agree, quit')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
