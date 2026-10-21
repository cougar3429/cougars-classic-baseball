"""Shared setup for the Playwright test scripts."""
from pathlib import Path
from contextlib import contextmanager
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build'
T_JS = (HERE / 'T.js').read_text()


@contextmanager
def page(variant='hooks.html', helper=True, viewport=None):
    """Open a built test page in headless Chromium. Yields (page, errors). Google Fonts may fail to load offline; that's harmless."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport=viewport or {'width': 844, 'height': 390})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto((BUILD / variant).as_uri())
        if helper:
            pg.evaluate('() => {' + T_JS + '}')
        try:
            yield pg, errs
        finally:
            b.close()
