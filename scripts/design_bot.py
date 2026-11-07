#!/usr/bin/env python3
"""Design Bot: визуальный контроль вёрстки и типографики.
Скриншоты 7 ключевых страниц (Playwright/Chromium, 1280px, full-page) и
попиксельное сравнение с бейзлайнами visual-baseline/*.png.
Порог: >3% изменённых пикселей = FAIL. Первая пара создаёт бейзлайны (exit 0)."""
import os, sys, io
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

BASE = os.environ.get('DESIGN_BASE', 'https://antonvincent288.github.io/polisprice/')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLDIR = os.path.join(HERE, 'visual-baseline')
PAGES = [
    ('home', ''),
    ('moscow', 'osago/moscow/'),
    ('kalkulyator', 'osago/kalkulyator/'),
    ('guides-hub', 'guides/'),
    ('regiony-hub', 'osago/regiony/'),
    ('guide', 'guides/kak-schitaetsya-osago/'),
    ('geo-kazan', 'osago-v-kazan/'),
]
THRESHOLD = 3.0

def pct_diff(a_bytes, b_bytes):
    ia = Image.open(io.BytesIO(a_bytes)).convert('RGB')
    ib = Image.open(io.BytesIO(b_bytes)).convert('RGB')
    if ia.size != ib.size:
        return 100.0
    diff = ImageChops.difference(ia, ib).convert('L')
    changed = sum(diff.histogram()[8:])
    return 100.0 * changed / (ia.size[0] * ia.size[1])

results, created = [], []
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    for name, path in PAGES:
        try:
            page.goto(BASE + path, wait_until='load', timeout=60000)
            page.wait_for_timeout(1200)
            page.screenshot(path=f'/tmp/{name}.png', full_page=True)
        except Exception as e:
            print(f'{name}: SCREENSHOT FAIL {e}')
            results.append((name, 100.0))
            continue
        with open(f'/tmp/{name}.png', 'rb') as f:
            shot = f.read()
        os.makedirs(BLDIR, exist_ok=True)
        bl = os.path.join(BLDIR, f'{name}.png')
        if not os.path.exists(bl):
            with open(bl, 'wb') as f:
                f.write(shot)
            created.append(name)
        else:
            with open(bl, 'rb') as f:
                d = pct_diff(f.read(), shot)
            results.append((name, round(d, 2)))
    browser.close()

if created:
    print('бейзлайны созданы:', ', '.join(created))
print('сравнение с бейзлайном:')
for name, d in results:
    print(f'  {name}: {d}%')
bad = [r for r in results if r[1] > THRESHOLD]
if bad:
    print(f'FAIL: вёрстка изменилась: {", ".join(n for n, _ in bad)} (> {THRESHOLD}%)')
    sys.exit(1)
print('DESIGN OK')
