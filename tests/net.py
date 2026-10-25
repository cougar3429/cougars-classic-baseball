"""Online 2-player check: two copies of the real game (net.html, with a stand-in for supabase-js) play each other
through the real lobby buttons: Ann hosts, Bob asks to join, Ann denies once, Bob asks again, Ann accepts.
Both then play for a while with made-up inputs at real speed over a laggy simulated network.
Ann has a coach selfie and Bob has none: Bob's HUD must show Ann's selfie for her team and Ann's must show the cartoon coach for Bob's.
Passes when both phones have played and their game states agree at every checked tick (fingerprints of final
states); when Bob's connection drops for 6 s, Ann is offered the choices and play picks up by itself when he is back
(lost moves are resent); and when Bob quits, Ann can finish the game against the computer.

  python3 net.py [seconds_of_play] [lag_ms]
"""
import sys, threading, functools, http.server, time
from playwright.sync_api import sync_playwright
from common import BUILD

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 25
LAG = int(sys.argv[2]) if len(sys.argv) > 2 else 40

PAGE = """<!doctype html><meta charset=utf8><body style="margin:0">
<iframe id=a src="net.html" width=844 height=390></iframe><iframe id=b src="net.html" width=844 height=390></iframe>"""

# a stand-in selfie (a plain 128 px JPEG with made-up face landmarks); the real face check is tested in selfie.py
FAKE_SELFIE = """() => { const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  g.fillStyle = '#d9a37a'; g.fillRect(0, 0, 128, 128); g.fillStyle = '#333'; g.fillRect(40, 50, 10, 6); g.fillRect(78, 50, 10, 6); g.fillRect(48, 90, 32, 6);
  const p = (x, y) => [x / 128, y / 128];
  window.__ccb.setSelfie({ img: c.toDataURL('image/jpeg', 0.8), lm: { ml: p(48, 92), mr: p(80, 92), mt: p(64, 89), mb: p(64, 97), b1o: p(36, 42), b1m: p(44, 40), b1i: p(52, 42),
    b2i: p(76, 42), b2m: p(84, 40), b2o: p(92, 42), e1: p(45, 53), e2: p(83, 53) } }); return !!window.__ccb.selfie; }"""
# which HUD portrait shows a team: { mine, theirs } as 'img' (a selfie) or 'coach'
HUD_FACES = """() => { const C = window.__ccb, S = C.S, bat = S.half % 2 === 0 ? S.vis : (S.vis === 'you' ? 'cpu' : 'you'), el = id => document.getElementById(id);
  const kind = e => e.querySelector('img') ? 'img' : 'coach', mine = bat === C.ME ? el('fl') : el('fr'), theirs = bat === C.ME ? el('fr') : el('fl');
  return { mine: kind(mine), theirs: kind(theirs), tries: C.NET.faceTries || 0, acked: !!C.NET.faceAcked }; }"""

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
        # lag readout: on by default; tapping the version number turns it off and on again (version 1.10)
        lab = lambda f: f.evaluate("() => document.getElementById('ver').textContent")
        lagver = [lab(ann)]; A.locator('#ver').click(); lagver.append(lab(ann)); A.locator('#ver').click(); lagver.append(lab(ann))
        if not (lagver[0].endswith('LAG ON') and not lagver[1].endswith('LAG ON') and lagver[2].endswith('LAG ON')): problems.append(f'lag readout label: {lagver}')
        for loc, name in ((A, 'Ann'), (B, 'Bob')):
            loc.locator('#p2').click(); loc.locator('#start').click(); loc.locator('#go').click()
            loc.locator('#pname').fill(name); loc.locator('#pname').dispatch_event('change')
        early_host = [f.evaluate("() => [document.getElementById('host').textContent, document.getElementById('host').disabled, !!window.__ccb.NET.lobbyReady]") for f in (ann, bob)]
        for t in early_host:
            if not t[2] and (t[0] != 'CONNECTING…' or not t[1]): problems.append(f'HOST A GAME before the lobby connected: {t}')
        for f in (ann, bob): f.wait_for_function('() => window.__ccb.NET.lobbyReady', timeout=8000) # HOST A GAME shows CONNECTING… until the lobby is connected
        if A.locator('#host').inner_text() != 'HOST A GAME' or A.locator('#host').is_disabled(): problems.append('HOST A GAME not ready after connecting')
        if not ann.evaluate(FAKE_SELFIE): problems.append("couldn't give Ann a selfie")
        A.locator('#host').click()
        B.locator('#games button', has_text='ASK TO JOIN').click(timeout=5000)
        A.locator('#reqs button', has_text='DENY').click(timeout=5000)
        B.locator('#hstat', has_text='said no').wait_for(timeout=5000)
        B.locator('#games button', has_text='ASK TO JOIN').click(timeout=5000)
        A.locator('#reqs button', has_text='ACCEPT').click(timeout=5000)
        for f in (ann, bob): f.wait_for_function('() => window.__ccb.NET.live', timeout=8000)
        faces = None
        try:
            bob.wait_for_function('() => !!window.__ccb.NET.oppFace', timeout=6000); ann.wait_for_function('() => window.__ccb.NET.faceAcked', timeout=6000)
            faces = [f.evaluate(HUD_FACES) for f in (ann, bob)]
            if faces[0]['mine'] != 'img' or faces[0]['theirs'] != 'coach' or faces[1]['mine'] != 'coach' or faces[1]['theirs'] != 'img': problems.append(f'selfies in the HUD (Ann, Bob): {faces}')
            if faces[0]['tries'] > 3 or faces[1]['tries'] != 0: problems.append(f"selfie messages sent: Ann {faces[0]['tries']}, Bob {faces[1]['tries']}")
        except Exception: problems.append("Bob never got Ann's selfie")
        names = [f.evaluate("() => document.getElementById('wl').textContent + '/' + document.getElementById('wr').textContent") for f in (ann, bob)]
        ann.evaluate(DRIVE, 11); bob.evaluate(DRIVE, 22)
        t0 = time.time()
        while time.time() - t0 < SECS: pg.wait_for_timeout(1000)
        lag = ann.evaluate("() => { const b = document.getElementById('lagbox'); return b.hidden ? null : b.textContent; }")
        import re as _re
        if not lag or not _re.search(r'DELAY \d+ ms', lag) or not _re.search(r'PING  \d+ ms', lag) or 'FIXES' not in lag or 'FRAME' not in lag: problems.append(f'lag readout: {lag!r}')
        for f in (ann, bob): f.evaluate('() => clearInterval(window.__drive)')
        pg.wait_for_timeout(1500)
        info = [f.evaluate("() => { const C = window.__ccb, R = C.RB; return { me: C.ME, t: C.S.t, half: C.S.half, score: C.S.score, over: C.S.over, rolls: R.rolls, rolled: R.rolled, hashes: R.hashes }; }") for f in (ann, bob)]
        common = sorted(set(info[0]['hashes']) & set(info[1]['hashes']), key=int)
        bad = [k for k in common if info[0]['hashes'][k] != info[1]['hashes'][k]]
        if len(common) < 20: problems.append(f'only {len(common)} ticks to compare')
        if bad: problems.append(f'the phones disagree from tick {bad[0]} ({len(bad)} of {len(common)} checked ticks)')
        if info[0]['me'] != 'you' or info[1]['me'] != 'cpu': problems.append(f"teams {info[0]['me']}/{info[1]['me']}")
        # game over: REMATCH and MAIN MENU on both; Ann asks, Bob accepts, a new game starts with home and away swapped and the phones agree;
        # then the next game ends, Bob asks, Ann declines and Bob is told
        rm = {}
        vis0 = ann.evaluate('() => window.__ccb.S.vis')
        for f in (ann, bob): f.evaluate('() => window.__ccbi.endGame()')
        rm['buttons'] = [A.locator('#again').inner_text(), A.locator('#fmenu').is_visible(), B.locator('#again').inner_text()]
        if rm['buttons'] != ['REMATCH', True, 'REMATCH']: problems.append(f"game over buttons {rm['buttons']}")
        A.locator('#again').click()
        try: B.locator('#racc').wait_for(state='visible', timeout=5000); rm['asked'] = B.locator('#frm').inner_text()
        except Exception: problems.append('Bob was not asked for the rematch')
        B.locator('#racc').click()
        try:
            for f in (ann, bob): f.wait_for_function('() => window.__ccb.S && !window.__ccb.S.over && window.__ccb.NET.gn === 1', timeout=5000)
        except Exception: problems.append('the rematch did not start on both phones')
        rm['vis'] = [vis0] + [f.evaluate('() => window.__ccb.S.vis') for f in (ann, bob)]
        if not (rm['vis'][1] == rm['vis'][2] != vis0): problems.append(f"home and away not swapped: {rm['vis']}")
        ann.evaluate(DRIVE, 55); bob.evaluate(DRIVE, 66); pg.wait_for_timeout(5000)
        for f in (ann, bob): f.evaluate('() => clearInterval(window.__drive)')
        pg.wait_for_timeout(1500)
        info3 = [f.evaluate("() => ({ t: window.__ccb.S.t, hashes: window.__ccb.RB.hashes })") for f in (ann, bob)]
        common3 = sorted(set(info3[0]['hashes']) & set(info3[1]['hashes']), key=int)
        bad3 = [k for k in common3 if info3[0]['hashes'][k] != info3[1]['hashes'][k]]
        if len(common3) < 5 or bad3: problems.append(f'rematch game: {len(common3)} checked ticks, disagree at {bad3[:1]}')
        rm['checked'] = len(common3)
        for f in (ann, bob): f.evaluate('() => window.__ccbi.endGame()')
        B.locator('#again').click(); A.locator('#rdec').click(timeout=5000)
        try: B.locator('#frm', has_text='said no').wait_for(timeout=5000); rm['declined'] = B.locator('#frm').inner_text()
        except Exception: problems.append('Bob was not told Ann said no')
        # Ann changes her mind: she can still ask, and Bob accepts (a third game, so the rest of the test has a live game)
        A.locator('#again').click(); B.locator('#racc').click(timeout=5000)
        for f in (ann, bob): f.wait_for_function('() => window.__ccb.S && !window.__ccb.S.over && window.__ccb.NET.gn === 2', timeout=5000)
        # Bob's connection drops for 6 s (everything he sends or receives is lost): Ann gets the choices and waits; when Bob is back, lost moves are resent and play picks up
        bob.evaluate('() => { window.__mockDrop = true; }')
        try: A.locator('#netwait').wait_for(state='visible', timeout=8000); shown = A.locator('#nwh').inner_text()
        except Exception: shown = None; problems.append('Ann did not get the choices when Bob dropped out')
        if shown: A.locator('#nwait').click()
        pg.wait_for_timeout(3000)
        bob.evaluate('() => { window.__mockDrop = false; }')
        try: A.locator('#netwait').wait_for(state='hidden', timeout=10000); healed = True
        except Exception: healed = False; problems.append('play did not pick up after Bob came back')
        t_before = [f.evaluate('() => window.__ccb.S.t') for f in (ann, bob)]
        ann.evaluate(DRIVE, 33); bob.evaluate(DRIVE, 44); pg.wait_for_timeout(5000)
        for f in (ann, bob): f.evaluate('() => clearInterval(window.__drive)')
        pg.wait_for_timeout(1500)
        info2 = [f.evaluate("() => ({ t: window.__ccb.S.t, hashes: window.__ccb.RB.hashes })") for f in (ann, bob)]
        common2 = sorted(set(info2[0]['hashes']) & set(info2[1]['hashes']), key=int)
        bad2 = [k for k in common2 if info2[0]['hashes'][k] != info2[1]['hashes'][k]]
        if bad2: problems.append(f'after the dropout the phones disagree from tick {bad2[0]}')
        if not all(b > a + 100 for a, b in zip(t_before, [i['t'] for i in info2])): problems.append('play did not continue after the dropout')
        # the wait has a time limit (30 s in the game, 3 s here): when it runs out Ann sees Disconnected with only FINISH VS CPU and QUIT GAME;
        # if Bob comes back anyway, play still picks up by itself
        ann.evaluate('() => { window.__ccb.NET.WAIT_MS = 3000; }')
        bob.evaluate('() => { window.__mockDrop = true; }')
        gone = None
        try:
            A.locator('#netwait').wait_for(state='visible', timeout=8000); A.locator('#nwait').click()
            A.locator('#nwh', has_text='Disconnected').wait_for(timeout=7000); gone = A.locator('#nwp').inner_text()
            if not A.locator('#nwait').is_hidden(): problems.append('WAIT FOR RECONNECT still offered after the time limit')
        except Exception: problems.append('the wait did not time out into Disconnected')
        bob.evaluate('() => { window.__mockDrop = false; }')
        try: A.locator('#netwait').wait_for(state='hidden', timeout=10000); back_after = True
        except Exception: back_after = False; problems.append('play did not pick up when Bob came back after the time limit')
        # Bob quits: Ann gets the choices without WAIT, picks FINISH VS CPU, and her game goes on against the computer
        B.locator('#menu').click(); B.locator('#qyes').click()
        try: A.locator('#nwp', has_text='quit').wait_for(timeout=5000); told = A.locator('#nwp').inner_text()
        except Exception: told = None; problems.append('Ann was not told that Bob quit')
        wait_hidden = A.locator('#nwait').is_hidden()
        if not wait_hidden: problems.append('WAIT FOR RECONNECT was offered after Bob quit')
        A.locator('#ncpu').click()
        t_cpu = ann.evaluate('() => window.__ccb.S.t'); pg.wait_for_timeout(3000)
        cpu = ann.evaluate("() => ({ t: window.__ccb.S.t, ai: window.__ccb.S.ai, label: document.getElementById('wl').textContent + '/' + document.getElementById('wr').textContent })")
        if not (cpu['ai']['cpu'] and cpu['t'] > t_cpu + 100): problems.append(f'finish vs CPU did not take over: {cpu}')
        br.close()
    srv.shutdown()
    for who, i in zip(('Ann (host)', 'Bob (guest)'), info):
        print(f"{who}: tick {i['t']}, half {i['half']}, score {i['score']}, re-runs {i['rolls']} ({i['rolled']} ticks)")
    print(f'scoreboard labels Ann/Bob: {names}; checked ticks {len(common)}')
    print(f'dropout: choices shown as {shown!r}, play picked up: {healed}, checked ticks after: {len(common2)}')
    print(f'time limit: {gone!r}; picked up when Bob came back: {back_after}')
    print(f'quit: Ann told {told!r}; after FINISH VS CPU: {cpu}')
    print(f'rematch: {rm}')
    print(f'selfies (Ann has one, Bob none): {faces}')
    print('lag readout (Ann):', (lag or '').replace(chr(10), ' | '))
    print(f'host button right after opening the lobby: {early_host}')
    for x in problems + errs[:5]: print('   ', x)
    ok = not problems and not errs
    print('PASS' if ok else 'FAIL', '- online 2-player: lobby, deny, accept, play, agree, selfies, lag readout, rematch (accept, swap, agree, decline), dropout and reconnect, wait time limit, quit, finish vs CPU')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
