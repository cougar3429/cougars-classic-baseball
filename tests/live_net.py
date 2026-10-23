"""Online 2-player against the REAL Supabase project (needs network access to *.supabase.co and cdn.jsdelivr.net).
Two copies of the real game (build/hooks.html, which loads supabase-js from the CDN) go through the lobby, play with
made-up inputs, and must agree at every checked tick; then one quits and the other finishes against the computer.
The page is served from inside the browser so that only the outside traffic goes through the network proxy.

  python3 live_net.py [seconds_of_play]
"""
import os, sys, time
from playwright.sync_api import sync_playwright
from common import BUILD

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 20
DRIVE = open(os.path.join(os.path.dirname(__file__), 'net.py')).read().split('DRIVE = """')[1].split('"""')[0]


def serve(route):
    route.fulfill(body=(BUILD / 'hooks.html').read_bytes(), content_type='text/html')


def main():
    px = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    problems, errs = [], []
    with sync_playwright() as p:
        br = p.chromium.launch(proxy={'server': px} if px else None)
        ctx = br.new_context(viewport={'width': 844, 'height': 390}); ctx.route('https://ccb.test/**', serve)
        ann, bob = ctx.new_page(), ctx.new_page()
        for pg in (ann, bob): pg.on('pageerror', lambda e: errs.append(str(e)[:200])); pg.goto('https://ccb.test/hooks.html')
        for pg, name in ((ann, 'Test A'), (bob, 'Test B')):
            pg.click('#p2'); pg.click('#start'); pg.click('#go'); pg.fill('#pname', name); pg.dispatch_event('#pname', 'change')
        ann.wait_for_function("() => window.__ccb.NET.lobby", timeout=15000); bob.wait_for_function("() => window.__ccb.NET.lobby", timeout=15000)
        ann.wait_for_timeout(1500); ann.click('#host')
        bob.locator('#games .grow', has_text='Test A').locator('button').click(timeout=15000)
        ann.locator('#reqs button', has_text='ACCEPT').click(timeout=15000)
        t0 = time.time()
        for pg in (ann, bob): pg.wait_for_function('() => window.__ccb.NET.live', timeout=15000)
        start_s = round(time.time() - t0, 2)
        ann.evaluate(DRIVE, 5); bob.evaluate(DRIVE, 6)
        ann.wait_for_timeout(int(SECS * 1000))
        for pg in (ann, bob): pg.evaluate('() => clearInterval(window.__drive)')
        ann.wait_for_timeout(2000)
        info = [pg.evaluate("() => { const C = window.__ccb, R = C.RB; return { t: C.S.t, rolls: R.rolls, rolled: R.rolled, hashes: R.hashes, stalled: !C.NET.stepOk }; }") for pg in (ann, bob)]
        common = sorted(set(info[0]['hashes']) & set(info[1]['hashes']), key=int)
        bad = [k for k in common if info[0]['hashes'][k] != info[1]['hashes'][k]]
        if len(common) < 10: problems.append(f'only {len(common)} ticks to compare')
        if bad: problems.append(f'the phones disagree from tick {bad[0]}')
        bob.click('#menu'); bob.click('#qyes')
        try: ann.locator('#nwp', has_text='quit').wait_for(timeout=15000); ann.click('#ncpu'); quit_ok = True
        except Exception: quit_ok = False; problems.append('Test A was not told that Test B quit')
        br.close()
    for who, i in zip(('host', 'guest'), info): print(f"{who}: tick {i['t']}, re-runs {i['rolls']} ({i['rolled']} ticks)")
    print(f'game started {start_s}s after ACCEPT; checked ticks {len(common)}; quit handled: {quit_ok}')
    for x in problems + errs[:5]: print('   ', x)
    ok = not problems and not errs
    print('PASS' if ok else 'FAIL', '- online 2-player over the real Supabase project')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
