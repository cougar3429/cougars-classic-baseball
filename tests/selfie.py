"""Coach selfie checks (version 1.01). Needs network access to cdn.jsdelivr.net (the face check library and a sample photo).

  1. The face check on test photos: a real face passes; noise, a plain shape, a dark photo and a blurred photo fail with the right message.
  2. The camera screen end to end with Chromium's fake camera: the title screen SELFIE button opens it, SNAP checks the photo,
     USE IT saves it on the phone, the thumbnails show it, and in a 1-player game your team's HUD portrait is your selfie
     (happy when you score, mad when the computer scores) while the computer keeps the cartoon coach.
     With the fake camera's test pattern (no face) the check says no face was found.
  3. Happy and mad are really changed from the photo (not copies), and mad is redder.

  python3 selfie.py
The 2-player exchange (each phone gets the other's selfie) is checked in net.py.
"""
import subprocess, sys, tempfile, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
from common import BUILD

SAMPLE = 'https://cdn.jsdelivr.net/gh/vladmandic/face-api@master/demo/sample6.jpg'

# builds test photos in the page from a sample photo (four people; cropped around one face), returns data URLs
MAKE = """async (url) => {
  const im = new Image(); im.crossOrigin = 'anonymous'; im.src = url; await im.decode();
  const mk = (fn) => { const c = document.createElement('canvas'); c.width = 640; c.height = 480; const g = c.getContext('2d'); fn(g); return c; };
  const sx = 765 - 450, sy = 560 - 337;   // in a 1920-wide copy of the photo
  const s = im.naturalWidth / 1920;
  const real = (g) => g.drawImage(im, sx * s, sy * s, 900 * s, 675 * s, 0, 0, 640, 480);
  const out = {};
  out.real = mk(real);
  out.dark = mk((g) => { real(g); g.fillStyle = 'rgba(0,0,0,0.75)'; g.fillRect(0, 0, 640, 480); });
  out.blur = mk((g) => { g.filter = 'blur(3px)'; real(g); });
  out.noise = mk((g) => { const d = g.createImageData(640, 480); for (let i = 0; i < d.data.length; i++) d.data[i] = i % 4 === 3 ? 255 : Math.random() * 255; g.putImageData(d, 0, 0); });
  out.blob = mk((g) => { g.fillStyle = '#c96'; g.fillRect(0, 0, 640, 480); g.fillStyle = '#333'; g.beginPath(); g.ellipse(320, 240, 90, 120, 0, 0, 7); g.fill(); });
  window.__pics = out;
  return out.real.toDataURL('image/png');
}"""

CHECK = """async () => { const r = {}; for (const k of Object.keys(window.__pics)) { const x = await window.__ccb.checkFace(window.__pics[k]); r[k] = x.ok ? { ok: true, blur: Math.round(x.blur), light: Math.round(x.light), bytes: x.selfie.img.length } : { ok: false, msg: x.msg }; } return r; }"""


def main():
    problems, errs = [], []
    work = Path(tempfile.mkdtemp())
    with sync_playwright() as p:
        # 1. the face check on test photos
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 844, 'height': 390})
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto((BUILD / 'hooks.html').as_uri())
        png = pg.evaluate(MAKE, SAMPLE)
        r = pg.evaluate(CHECK)
        print('face check:', r)
        if not r['real']['ok']: problems.append(f"a real face failed the check: {r['real']}")
        for k, want in (('noise', 'No face'), ('blob', 'No face'), ('dark', 'dark'), ('blur', 'blurry')):
            if r[k]['ok'] or want not in r[k]['msg']: problems.append(f'{k}: expected "{want}", got {r[k]}')
        if r['real'].get('bytes', 99999) > 20000: problems.append(f"selfie too big to send: {r['real']['bytes']} characters")
        br.close()

        # a video file of the test photo for Chromium's fake camera
        import base64
        (work / 'face.png').write_bytes(base64.b64decode(png.split(',', 1)[1]))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-loop', '1', '-i', str(work / 'face.png'), '-t', '2', '-r', '15', '-pix_fmt', 'yuv420p', str(work / 'face.y4m')], check=True)

        # 2. the camera screen, end to end
        for video, expect in ((work / 'face.y4m', 'ok'), (None, 'none')):
            args = ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] + ([f'--use-file-for-fake-video-capture={video}'] if video else [])
            br = p.chromium.launch(args=args)
            ctx = br.new_context(viewport={'width': 844, 'height': 390})
            ctx.grant_permissions(['camera'])
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            # served over http://localhost so the camera is allowed (a secure context)
            import threading, functools, http.server
            class Q(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *a): pass
            srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=str(BUILD)))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            pg.goto(f'http://localhost:{srv.server_port}/hooks.html')
            pg.locator('#self1').click()
            pg.wait_for_function("() => !document.getElementById('snap').disabled && document.getElementById('camv').videoWidth > 0", timeout=15000)
            pg.locator('#snap').click()
            pg.wait_for_function("() => !document.getElementById('camuse').hidden || document.getElementById('camp').classList.contains('bad')", timeout=60000)
            msg = pg.locator('#camp').inner_text()
            if expect == 'none':
                print('fake test pattern:', msg)
                if 'No face' not in msg: problems.append(f'test pattern: expected "No face", got "{msg}"')
                if pg.locator('#retake').is_hidden(): problems.append('test pattern: no RETAKE button')
            else:
                print('fake camera face:', msg)
                if pg.locator('#camuse').is_hidden(): problems.append(f'face photo: USE IT not offered ("{msg}")')
                else:
                    if pg.locator('#cammoods img').count() != 3: problems.append('face photo: no happy/mad previews')
                    pg.screenshot(path=str(BUILD / 'selfie_cam.png'))
                    pg.locator('#camuse').click()
                    st = pg.evaluate("() => ({ saved: !!localStorage.getItem('ccb-selfie'), cam: document.getElementById('cam').hidden, thumbs: [...document.querySelectorAll('.sthumb img')].length })")
                    if not (st['saved'] and st['cam'] and st['thumbs'] == 2): problems.append(f'after USE IT: {st}')
                    # 1-player game: your portrait is the selfie, the computer's is the cartoon coach
                    pg.locator('#start').click(); pg.locator('#go').click()
                    pg.wait_for_function('() => window.__ccb.S && window.__ccb.S.phase')
                    q = """() => { const S = window.__ccb.S, me = window.__ccb.ME, bat = S.half % 2 === 0 ? S.vis : (S.vis === 'you' ? 'cpu' : 'you');
                        const el = id => document.getElementById(id); const mine = bat === me ? el('fl') : el('fr'), cpu = bat === me ? el('fr') : el('fl');
                        return { mine: mine.querySelector('img') ? mine.querySelector('img').src.slice(0, 40) : 'coach', cpu: cpu.querySelector('svg') ? 'coach' : 'img' }; }"""
                    pg.wait_for_timeout(500)
                    hud = pg.evaluate(q); print('HUD:', hud)
                    if not hud['mine'].startswith('data:image/jpeg') or hud['cpu'] != 'coach': problems.append(f'HUD portraits: {hud}')
                    pg.screenshot(path=str(BUILD / 'selfie_hud.png'))
                    # the moods are made and differ from the photo; mad is redder
                    m = pg.evaluate("""async () => { const f = window.__ccb.selfie; for (let i = 0; i < 50 && !f.moods; i++) await new Promise(r => setTimeout(r, 50));
                        const px = async (u) => { const im = new Image(); im.src = u; await im.decode(); const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d'); g.drawImage(im, 0, 0); return g.getImageData(0, 0, 128, 128).data; };
                        const n = await px(f.moods.neutral), h = await px(f.moods.happy), a = await px(f.moods.mad); let dh = 0, red = 0;
                        for (let i = 0; i < n.length; i += 4) { dh += Math.abs(n[i] - h[i]) + Math.abs(n[i + 1] - h[i + 1]); red += (a[i] - a[i + 2]) - (n[i] - n[i + 2]); }
                        return { happyDiff: Math.round(dh / (128 * 128)), madRedder: Math.round(red / (128 * 128)) }; }""")
                    print('moods:', m)
                    if m['happyDiff'] < 2 or m['madRedder'] < 5: problems.append(f'moods look unchanged: {m}')
                    # NO SELFIE goes back to the coach
                    pg.locator('#menu').click(); pg.locator('#qyes').click(); pg.locator('#self1').click(); pg.locator('#camno').click()
                    st = pg.evaluate("() => ({ saved: !!localStorage.getItem('ccb-selfie'), thumbs: document.querySelectorAll('.sthumb svg').length })")
                    if st['saved'] or st['thumbs'] != 2: problems.append(f'after NO SELFIE: {st}')
            srv.shutdown(); br.close()
    if errs: problems.append('page errors: ' + '; '.join(errs[:3]))
    for x in problems: print('FAIL -', x)
    print('PASS - selfies: face check, camera screen, save, HUD, moods, no selfie' if not problems else f'{len(problems)} problem(s)')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
