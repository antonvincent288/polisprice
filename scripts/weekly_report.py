#!/usr/bin/env python3
"""Недельная сводка ПолисПрайс (Guardian Bot). Запуск: python scripts/weekly_report.py [--save PATH]
Лёгкий срез живого сайта: sitemap, гайды, GEO, цитируемость, ИИ-краулеры в robots, RSS. Только stdlib."""
import sys, re, urllib.request, datetime

BASE = 'https://antonvincent288.github.io/polisprice/'
def get(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': 'polisprice-weekly/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore')

out = [f'# Недельная сводка ПолисПрайс — {datetime.date.today().isoformat()}', '']
sm = get('sitemap-0.xml')
urls = re.findall(r'<loc>([^<]+)</loc>', sm)
guides = [u for u in urls if '/guides/' in u and not u.rstrip('/').endswith('/guides')]
geo = [u for u in urls if '/osago-v-' in u]
out.append(f'- Страниц в sitemap: {len(urls)}')
out.append(f'- Гайды: {len(guides)} | GEO-страниц: {len(geo)}')
rss = get('rss.xml')
out.append(f'- Гайдов в RSS: {rss.count("<item>")}')
rb = get('robots.txt')
ai_ua = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User',
         'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'CCBot', 'Bytespider', 'YandexBot', 'Bingbot']
allowed = [ua for ua in ai_ua if re.search(rf'User-agent: {re.escape(ua)}\s*\nAllow: /', rb)]
out.append(f'- ИИ-краулеров разрешено: {len(allowed)}/{len(ai_ua)}')
lf = get('llms-full.txt')
out.append(f'- llms-full.txt: {len(lf)} байт, разделов гайдов: {lf.count("## ") - 4}')
sample = [u.replace('https://polisprice.ru/', '') for u in (guides[:4] + geo[:6] + geo[-4:])]
win = tot = 0
for p in sample:
    try:
        h = get(p)
    except Exception:
        continue
    body = h.split('<main', 1)[-1]
    for para in re.findall(r'<p[^>]*>(.*?)</p>', body, re.S):
        txt = re.sub(r'<[^>]+>', ' ', para)
        n = len(txt.split())
        if n < 12:
            continue
        tot += 1
        if 30 <= n <= 80:
            win += 1
out.append(f'- Окно 30–80 слов (выборка {len(sample)} стр.): {win}/{tot} ({(win / max(1, tot)):.0%})')
code = urllib.request.urlopen(urllib.request.Request(BASE, headers={'User-Agent': 'w'}), timeout=30).status
out.append(f'- Главная: HTTP {code}')
report = chr(10).join(out) + chr(10)
if '--save' in sys.argv:
    open(sys.argv[sys.argv.index('--save') + 1], 'w', encoding='utf-8').write(report)
print(report)