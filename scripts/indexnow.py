#!/usr/bin/env python3
"""IndexNow: отправляет sitemap-URL в поисковики (Yandex, Bing и др.).
Домен задаётся переменной окружения INDEXNOW_DOMAIN (repo variables в GitHub).
Ключ — единственный .txt-файл с 32-символьным именем в public/."""
import os, sys, re, json, glob, urllib.request

domain = os.environ.get('INDEXNOW_DOMAIN', '')
if not domain:
    print('INDEXNOW_DOMAIN не задан — пропуск (сайт ещё не на своём домене)')
    sys.exit(0)

keys = [f for f in glob.glob('public/*.txt') if len(os.path.basename(f).split('.')[0]) == 32]
if not keys:
    print('Ключ IndexNow не найден')
    sys.exit(1)
key = os.path.basename(keys[0]).split('.')[0]

sm = urllib.request.urlopen(f'https://{domain}/sitemap-0.xml', timeout=30).read().decode()
urls = re.findall(r'<loc>([^<]+)</loc>', sm)
if not urls:
    print('Sitemap пуст')
    sys.exit(1)

body = json.dumps({'host': domain, 'key': key, 'urlList': urls}).encode()
req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body,
                             headers={'Content-Type': 'application/json; charset=utf-8'})
with urllib.request.urlopen(req, timeout=60) as r:
    print('IndexNow:', r.status, '| URL отправлено:', len(urls))
