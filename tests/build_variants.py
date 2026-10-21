"""Build the test copies of the game from ../index.html into tests/build/.

  hooks.html  the real game, plus window.__ccbi exposing internal functions for scripted scenarios
  auto.html   computer vs computer on both sides (soak tests of whole games)
  adv.html    computer pitches and fields; your side's runners are driven by window.__adv (exploit hunting)

Run this after every change to index.html (run_all.sh does it for you). If a replacement no longer
matches the game code, it stops and says which one, so the edit below can be updated.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent / 'index.html'
OUT = HERE / 'build'

# internal functions the scenario scripts call through window.__ccbi
HOOKS = ['runnerOut', 'foulReturn', 'startTrot', 'commitRuns', 'endLive', 'batterToFirst', 'moveRunners',
         'settleRunners', 'snapRunners', 'resetPlay', 'mkBall', 'homeWins', 'wallHit', 'giveBall', 'takeLeads',
         'gameOver', 'afterResult']

# both sides run by the computer (version 69: the game has a switch for this, S.ai)
CPU_BOTH = [
    ("ai: g.ai || { you: false, cpu: true },", "ai: { you: true, cpu: true },"),
]
# like CPU_BOTH, but runners are driven by window.__adv(S, api) instead of the computer's running logic
ADV = CPU_BOTH + [
    ("  if (S.ai[batSide()]) cpuRunners();",
     "  if (window.__adv) window.__adv(S, { sendRunner: sendRunner, rPos: rPos, basePos: basePos, alive: alive, dist2: dist2, standingOn: standingOn });"),
]

def apply(src, pairs, name):
    for old, new in pairs:
        if src.count(old) != 1:
            raise SystemExit(f'{name}: expected exactly one match for:\n{old}\n(found {src.count(old)}). Update tests/build_variants.py to match index.html.')
        src = src.replace(old, new)
    return src


def with_hooks(src):
    names = [n for n in HOOKS if f'function {n}(' in src]
    expose = 'window.__ccbi = { ' + ', '.join(f'{n}: {n}' for n in names) + ' };\n'
    marker = 'window.__ccb = {'
    if src.count(marker) != 1:
        raise SystemExit('window.__ccb test hook not found in index.html')
    return src.replace(marker, expose + marker, 1)


def main():
    src = GAME.read_text()
    if not src.lstrip().startswith('<!doctype'):
        # the repository copy has no doctype/head wrapper; add a minimal one so the page renders the same as published
        src = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
               '<style>:root{box-sizing:border-box}body{margin:0;padding:0}[hidden]{display:none!important}</style></head><body>\n' + src + '\n</body></html>')
    OUT.mkdir(exist_ok=True)
    (OUT / 'hooks.html').write_text(with_hooks(src))
    (OUT / 'auto.html').write_text(with_hooks(apply(src, CPU_BOTH, 'auto.html')))
    (OUT / 'adv.html').write_text(with_hooks(apply(src, ADV, 'adv.html')))
    print('built', ', '.join(p.name for p in sorted(OUT.glob('*.html'))))


if __name__ == '__main__':
    main()
