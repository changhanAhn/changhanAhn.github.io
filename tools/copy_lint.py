# -*- coding: utf-8 -*-
"""Fail when site copy uses slogan-style or promotional phrasing.

The lab site is written in plain, textbook-style sentences (user instruction
2026-10-21). This scans the visible copy of every page and script under
04_LabSite (data-ko/data-en attributes and quoted sentence strings in scripts)
and exits 1 on any hit. Run `--selftest` to confirm the rules still catch the
phrases that were removed on 2026-10-21.
"""
import glob
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

RULES = [
    # parallel slogans: "하나의 X, 다섯 개의 Y" / "One X, five Y"
    ('parallel slogan', re.compile(r'하나의\s*[^,]{1,12},\s*(<em>)?\s*[^,]{0,6}(개|갈래|가지)의')),
    ('parallel slogan', re.compile(r'\bOne [a-z]+, (<em>)?(two|three|four|five|six|seven) ', re.I)),
    # clipped twin sentences: "AI는 맞는 곳에만. 경계는 증거로."
    ('clipped pair', re.compile(r'^[^.]{2,16}\.\s+[^.]{2,16}\.$')),
    # promotional or AI-typical wording
    ('promo wording', re.compile(r'그대로 보입니다|한눈에|살아 있는|여정|혁신|강력한|게임 체인저|꾸민 숫자|지금까지의 기록|누가 할지|맞는 곳에만|경계는 증거로')),
    ('promo wording', re.compile(r'as it happens|The line, proven|Watch the lab|game[- ]changer|cutting[- ]edge|state[- ]of[- ]the[- ]art|world[- ]class', re.I)),
    # claims the internal canon forbids
    ('forbidden claim', re.compile(r'세계\s*최초|100\s*%|0\s*%\s*(불량|결함)|완벽|최고의|world.?s first', re.I)),
    # rejected items are not listed on the public site
    ('rejection listed', re.compile(r'탈락|게재 불가|Not selected|Rejected')),
    # Japanese and Chinese equivalents (added 2026-10-22 with the ja/zh pages)
    ('promo wording', re.compile(r'一目で|一目了然|革新的|革命的|画期的|最先端|最前沿|強力な|强大的|旅路|颠覆')),
    ('forbidden claim', re.compile(r'世界初|業界初|世界首创|全球首创|全球领先|完璧|完美|最高の|最好的|100\s*[%％]')),
    ('rejection listed', re.compile(r'落選|不採択|不採用|落选|未入选|未获资助|拒稿')),
]

ATTR = re.compile(r'data-(?:ko|en|ja|zh)="([^"]*)"')
JSSTR = re.compile(r"'((?:[^'\\]|\\.){4,})'")
HANGUL = re.compile(r'[\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff]')


def visible_strings(text):
    for m in ATTR.finditer(text):
        yield m.start(), m.group(1)
    for m in JSSTR.finditer(text):
        s = m.group(1)
        # sentence-like strings only: Korean text, or English with spaces and no CSS/markup syntax
        if HANGUL.search(s) or (' ' in s and not re.search(r'[{};:<>=]|px|rgba|#[0-9a-f]{3}', s)):
            yield m.start(), s


def check(text):
    hits = []
    for pos, s in visible_strings(text):
        s = re.sub(r'<[^>]+>', '', s)
        for label, rx in RULES:
            m = rx.search(s)
            if m:
                hits.append((pos, label, m.group(0)))
    return hits


def selftest():
    bad = ['data-ko="하나의 코어, <em>다섯 개의 연구 트랙</em>"', 'data-en="One core, <em>five research tracks</em>"',
           'data-ko="AI는 맞는 곳에만. 경계는 증거로."', 'data-en="Watch the lab work, <em>as it happens</em>"',
           'data-ko="연구실이 일하는 모습이 <em>그대로</em> 보입니다"', "L.T('꾸민 숫자는 없습니다.','x')",
           'data-ko="한국전력 사외공모<small>탈락</small>"', 'data-ko="세계 최초 100% 안전"']
    bad += ['data-ja="世界初の革新的な手法"', 'data-zh="全球首创，一目了然"', 'data-ja="一次審査で落選"', 'data-zh="100%安全"']
    good = ['data-ko="연구 분야와 <em>공통 판단 기준</em>"', 'data-ja="研究分野と<em>共通の判断基準</em>"', 'data-zh="研究方向与<em>共同判断标准</em>"', 'style="width:100%"', "background:linear-gradient(90deg,#b9a37a var(--p,50%),x 100%)"]
    missed = [b for b in bad if not check(b)]
    false = [g for g in good if check(g)]
    print('selftest missed:', missed, 'false positives:', false)
    return 1 if missed or false else 0


def main():
    if '--selftest' in sys.argv:
        return selftest()
    files = glob.glob(os.path.join(ROOT, '*.html')) + glob.glob(os.path.join(ROOT, 'assets', '*.js'))
    files = [f for f in sorted(files) if not os.path.basename(f).startswith('_')]
    total = 0
    sys.path.insert(0, os.path.dirname(__file__))
    from i18n_src import T
    for i, row in enumerate(T):
        for s_ in row[1:]:
            for pos, label, frag in check('data-ja="%s"' % s_.replace('"', "'")):
                total += 1
                print(f'tools/i18n_src.py entry {i}: {label}: {frag[:60]}')
    for path in files:
        text = open(path, encoding='utf-8').read()
        for pos, label, frag in check(text):
            total += 1
            print(f'{os.path.relpath(path, ROOT)}:{text.count(chr(10), 0, pos) + 1}: {label}: {frag[:60]}')
    print(f'copy_lint: {total} hit(s) in {len(files)} file(s)')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
