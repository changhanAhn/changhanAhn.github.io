# -*- coding: utf-8 -*-
"""Load every lab page in every language and fail on clipped or untranslated text.

Each page is opened with ?lang=<code> at three screen sizes. Checks:
  overflow  - a visible element ends below 720 px or right of 1280 px on the canvas
  clip      - text in a box with hidden overflow runs past its padding edge, by more
              than the same box does in Korean (Korean and English were checked by eye)
  miss      - a Japanese or Chinese string fell back to English (LAB.miss)
The map page is also checked with each research area opened, and the MAIA page
with each preset task loaded.

  py -3 tools/check_pages.py            all pages, all languages, three sizes
  py -3 tools/check_pages.py --quick    one size (1536x793)
  py -3 tools/check_pages.py --keys     print every missing Korean key as JSON
"""
import functools
import http.server
import json
import os
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PAGES = ['index', 'map', 'maia', 'record', 'grants', 'open', 'data']
LANGS = ['ko', 'en', 'ja', 'zh']
SIZES = [(1366, 768), (1536, 793), (1920, 1080)]

PROBE = """() => {
  const p = document.getElementById('page'), pr = p.getBoundingClientRect(), k = pr.height / 720;
  const over = [], clip = {};
  const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\\s+/).join('.') : '');
  const path = e => { const a = []; for (let x = e; x && x !== p; x = x.parentElement) a.unshift(name(x)); return a.join('>'); };
  p.querySelectorAll('*').forEach(e => {
    if (e.closest('.top') || getComputedStyle(e).visibility === 'hidden') return;
    const r = e.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const b = (r.bottom - pr.top) / k, rt = (r.right - pr.left) / k;
    if (b > 721 || rt > 1281) over.push([path(e), Math.round(b), Math.round(rt)]);
    const cs = getComputedStyle(e);
    if (!(e instanceof SVGElement) && /hidden|clip/.test(cs.overflow + cs.overflowX + cs.overflowY)) {
      // text may run into the padding; it is hidden only past the padding edge
      const dy = Math.round(e.scrollHeight - e.clientHeight - parseFloat(cs.paddingBottom)),
            dx = Math.round(e.scrollWidth - e.clientWidth - parseFloat(cs.paddingRight));
      if (dy > 0 || dx > 0) clip[path(e)] = [dy, dx];
    }
  });
  return {over, clip, miss: [...window.LAB.miss.entries()]};
}"""


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=ROOT)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def states(page, name):
    """Yield (label, None) after each interaction worth measuring."""
    yield 'load'
    if name == 'map':
        for i in range(5):
            page.locator('text.pname').nth(i).click()
            page.wait_for_timeout(250)
            yield 'area%d' % (i + 1)
    if name == 'maia':
        buttons = page.locator('#pr button')
        for i in range(buttons.count()):
            buttons.nth(i).click()
            page.wait_for_timeout(250)
            yield 'preset%d' % (i + 1)


def main():
    quick, keys = '--quick' in sys.argv, '--keys' in sys.argv
    sizes = [SIZES[1]] if (quick or keys) else SIZES
    langs = ['ja', 'zh'] if keys else LANGS
    srv = serve()
    base = 'http://127.0.0.1:%d/' % srv.server_address[1]
    fails, missing = [], {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for w, h in sizes:
            ctx = browser.new_context(viewport={'width': w, 'height': h})
            page = ctx.new_page()
            for name in PAGES:
                baseline = {}
                for lang in langs:
                    page.goto('%s%s.html?lang=%s' % (base, name, lang))
                    page.evaluate('document.fonts.ready')
                    page.wait_for_timeout(1500)
                    for state in states(page, name):
                        r = page.evaluate(PROBE)
                        tag = '%dx%d %s %s %s' % (w, h, name, lang, state)
                        for k_, en in r['miss']:
                            missing.setdefault(lang, {})[k_] = en
                        if keys:
                            continue
                        if lang == 'ko':
                            baseline[state] = r['clip']
                        for path, b, rt in r['over']:
                            fails.append('%s overflow %s bottom=%d right=%d' % (tag, path, b, rt))
                        base_clip = baseline.get(state, {})
                        for path, (dy, dx) in r['clip'].items():
                            by, bx = base_clip.get(path, [0, 0])
                            if dy > by + 2 or dx > bx + 2:
                                fails.append('%s clip %s +%dpx down +%dpx across' % (tag, path, dy - by, dx - bx))
                        if lang in ('ja', 'zh') and r['miss']:
                            fails.append('%s miss %d string(s)' % (tag, len(r['miss'])))
            ctx.close()
        browser.close()
    srv.shutdown()
    if keys:
        print(json.dumps(missing, ensure_ascii=False, indent=1))
        return 0
    for f in sorted(set(fails)):
        print(f)
    print('check_pages: %d failure(s), %d page(s) x %d language(s) x %d size(s)'
          % (len(set(fails)), len(PAGES), len(langs), len(sizes)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
