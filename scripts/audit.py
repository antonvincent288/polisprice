#!/usr/bin/env python3
"""Живой аудит ПолисПрайс. Запуск: python scripts/audit.py [BASE_URL]
Проверяет: ключевые страницы, все внутренние ссылки и активы из sitemap-страниц,
SEO-мета, JSON-LD, sitemap-покрытие, robots. Выход: 0 — всё ок, 1 — есть проблемы.
Только stdlib. Используется в GitHub Actions после каждого деплоя."""
import sys, re, json, time, urllib.request, urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else 'https://antonvincent288.github.io/polisprice/'
UA = {'User-Agent': 'polisprice-audit/1.0'}

# 502/503/429 — транзиентные сбои CDN GitHub Pages: ретраим до 3 раз с паузой
cache = {}
def get(path):
    url = path if path.startswith('http') else BASE + path.lstrip('/')
    if url in cache:
        return cache[url]
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                cache[url] = (r.status, r.read().decode('utf-8', 'ignore'))
            return cache[url]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(2 + attempt * 2)
                continue
            try:
                cache[url] = (e.code, e.read().decode('utf-8', 'ignore'))
            except Exception:
                cache[url] = (e.code, '')
            return cache[url]
        except Exception as e:
            if attempt < 2:
                time.sleep(2 + attempt * 2)
                continue
            cache[url] = (0, str(e))
            return cache[url]
    return cache.get(url, (0, 'unreachable'))

fails = []
def check(name, cond, detail=''):
    if not cond:
        fails.append(f'{name} — {detail}')
    print(('PASS ' if cond else 'FAIL ') + name + (f' ({detail})' if detail and not cond else ''))

# 1. Ключевые страницы
KEY = ['', 'osago/kalkulyator/', 'osago/koeffitsienty/', 'osago/tarify/', 'osago/moscow/',
       'osago/regiony/', 'guides/', 'politika-konfidencialnosti/', 'oferta/', 'o-proekte/', 'kontakty/']
for p in KEY:
    code, _ = get(p)
    check(f'/{p} 200', code == 200, f'code={code}')

# 2. Сбор всех страниц из sitemap
_, sm = get('sitemap-0.xml')
urls = re.findall(r'<loc>([^<]+)</loc>', sm)
check('sitemap: ≥200 URL', len(urls) >= 200, str(len(urls)))
paths = [u.replace('https://polisprice.ru', '') for u in urls]
paths = [p.lstrip('/') for p in paths]
paths = [p if p.endswith('/') or '.' in p.split('/')[-1] else p + '/' for p in paths]

pages = {}
meta_bad, ld_bad, nan_bad = [], [], []
for p in paths:
    code, html = get(p)
    if code != 200:
        meta_bad.append((p, f'HTTP {code}'))
        continue
    pages[p] = html
    if p == '404.html':
        continue
    if not re.search(r'<title>[^<]{15,}', html): meta_bad.append((p, 'title'))
    if 'name="description"' not in html: meta_bad.append((p, 'desc'))
    if html.count('<h1') != 1: meta_bad.append((p, 'h1=' + str(html.count('<h1'))))
    if 'rel="canonical"' not in html: meta_bad.append((p, 'canonical'))
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            json.loads(m)
        except Exception:
            ld_bad.append(p)
    if 'NaN' in html or '>undefined<' in html: nan_bad.append(p)
check('SEO-мета на всех sitemap-страницах', not meta_bad, str(meta_bad[:3]))
check('JSON-LD валиден', not ld_bad, str(ld_bad[:3]))
check('нет NaN/undefined', not nan_bad, str(nan_bad[:3]))

titles = [re.search(r'<title>(.*?)</title>', h).group(1) for h in pages.values() if re.search(r'<title>(.*?)</title>', h)]
check('title уникальны', len(set(titles)) == len(titles), f'{len(set(titles))}/{len(titles)}')

# 3. Ссылки и активы (+ граф для сирот)
link_bad = []
inbound = {}
n_links = 0
for p, html in pages.items():
    for href in re.findall(r'(?:href|src)="([^"#]+)"', html):
        if href.startswith(('mailto:', 'tel:', 'javascript:')): continue
        if '://' in href: continue  # абсолютные URL (внешние и share-ссылки) — не проверяем как внутренние
        if not href.startswith('/'):
            href = '/' + p + href
        n_links += 1
        if href.rstrip('/') in ('/404', '/404.html'):
            continue
        inbound[href.strip('/')] = inbound.get(href.strip('/'), 0) + 1
        code, _ = get(href)
        if code != 200:
            link_bad.append((p, href, code))
check(f'ссылки и активы живы ({n_links})', not link_bad, str(link_bad[:4]))

# 3б. Сироты: страницы из sitemap без входящих внутренних ссылок (информационно)
orphans = [p for p in paths if p.strip('/') not in inbound and p not in ('404.html',)]
print('INFO сироты (без входящих ссылок):', len(orphans), orphans[:10])

# 4. GEO-выборка: цены совпадают с примерами форматирования
geo = [p for p in pages if p.startswith('osago-v-')]
check('GEO-страниц ≥185', len(geo) >= 185, str(len(geo)))
sample = geo[:4] + geo[len(geo)//2:len(geo)//2+4] + geo[-4:]
bad_prices = []
for p in sample:
    html = pages[p]
    if '1 399' not in html.replace('\u2009', ' ').replace('\u00a0', ' ') and '1 399' not in html:
        if '1399' not in re.sub(r'[\s\u00a0\u202f]', '', html):
            bad_prices.append(p)
check('коридор 1399–8665 на GEO-выборке', not bad_prices, str(bad_prices[:3]))

# 5. robots
code, robots = get('robots.txt')
check('robots.txt открыт', code == 200 and 'Disallow:' in robots and 'Disallow: /' not in robots, robots[:60])



# 6. CITABILITY: блочная оценка по методологии seo-suite (citability-scoring.md)
# Блок: 30 (окно 30-80 слов) + 25 (есть число) + 25 (предмет из h1 внутри абзаца). Покрытие = доля блоков >70.
def _para_stats(_html):
    body = _html.split('<main', 1)[-1]
    paras = re.findall(r'<p[^>]*>(.*?)</p>', body, re.S)
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', _html, re.S)
    h1w = set(re.sub(r'<[^>]+>', ' ', h1.group(1)).lower().split()) if h1 else set()
    good = total = win = 0
    for para in paras:
        txt = re.sub(r'<[^>]+>', ' ', para)
        words = txt.split()
        n = len(words)
        if n < 12:
            continue
        total += 1
        if 30 <= n <= 80:
            win += 1
        score = 30 if 30 <= n <= 80 else 10
        if any(ch.isdigit() for ch in txt):
            score += 25
        if h1w & {w.strip('.,;:!?«»()—') for w in words}:
            score += 25
        if score > 70:
            good += 1
    return good, total, win

print('INFO citability (доля блоков >70 из методологии seo-suite):')
for _p in sorted(paths):
    if (_p.startswith('guides/') or _p.startswith('osago-v-')) and _p.endswith('/'):
        _g, _t, _w = _para_stats(pages[_p])
        if _t:
            print(f'  {_p}: >70 {_g}/{_t} ({_g/_t:.0%}) | окно {_w}/{_t} ({_w/_t:.0%})')
_tg = sum(_para_stats(pages[p])[0] for p in paths if p.startswith('guides/') and p.endswith('/'))
_tt = sum(_para_stats(pages[p])[1] for p in paths if p.startswith('guides/') and p.endswith('/'))
_tw = sum(_para_stats(pages[p])[2] for p in paths if p.startswith('guides/') and p.endswith('/'))
print(f'  среднее по гайдам: блоков >70 {_tg/max(1,_tt):.0%} | окно 30-80 {_tw/max(1,_tt):.0%}')
_tgeo = sum(_para_stats(pages[p])[0] for p in paths if p.startswith('osago-v-') and p.endswith('/'))
_ttgeo = sum(_para_stats(pages[p])[1] for p in paths if p.startswith('osago-v-') and p.endswith('/'))
_twgeo = sum(_para_stats(pages[p])[2] for p in paths if p.startswith('osago-v-') and p.endswith('/'))
print(f'  среднее по GEO: блоков >70 {_tgeo/max(1,_ttgeo):.0%} | окно 30-80 {_twgeo/max(1,_ttgeo):.0%}')


# ===== Слой seo-skills (перенос head_check / link_graph / text_metrics, stdlib) =====
DEPRECATED_META_NAMES = {'skype_toolbar', 'msapplication-config', 'apple-mobile-web-app-capable', 'alexaverifyid', 'twitter:dnt'}
DEPRECATED_HTTP_EQUIV = {'x-ua-compatible', 'x-dns-prefetch-control', 'window-target'}
WATERMARKS = ('​', '‌', '‍', '⁠', '﻿')

def _head_stats(html):
    head = html.split('</head>', 1)[0]
    cs_ok = True
    m = re.search(r'<meta[^>]+charset', head, re.I)
    if not m:
        cs_ok = False
    elif m.start() > 1024:
        cs_ok = False
    title_ok = bool(re.search(r'<title>[^<]{3,}</title>', head))
    og_img = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', head)
    og_ok = (og_img is None) or og_img.group(1).startswith(('http://', 'https://'))
    depr = []
    for mm in re.finditer(r'<meta[^>]*>', head, re.I):
        tag = mm.group(0)
        nm = re.search(r'name="([^"]+)"', tag, re.I)
        he = re.search(r'http-equiv="([^"]+)"', tag, re.I)
        if nm and nm.group(1).lower() in DEPRECATED_META_NAMES:
            depr.append(nm.group(1))
        if he and he.group(1).lower() in DEPRECATED_HTTP_EQUIV:
            depr.append(he.group(1))
    return cs_ok, title_ok, og_ok, depr

print()
print('INFO head-check (перенос из seo-skills):')
_cs_bad, _t_bad, _og_bad, _dep_all = [], [], [], []
for _p, _h in pages.items():
    if not _p.endswith('/'):
        continue
    _cs, _ti, _og, _dp = _head_stats(_h)
    if not _cs: _cs_bad.append(_p)
    if not _ti: _t_bad.append(_p)
    if not _og: _og_bad.append(_p)
    if _dp: _dep_all.append((_p, _dp))
print(f'  charset в первых 1024 байтах: нарушений {_cs_bad and len(_cs_bad) or 0}')
print(f'  title непустой: нарушений {len(_t_bad)}')
print(f'  og:image абсолютный: нарушений {len(_og_bad)}')
print(f'  deprecated-мета: {len(_dep_all)}')
check('head: charset≤1024 и title у всех страниц', not _cs_bad and not _t_bad, f'{_cs_bad[:2]} {_t_bad[:2]}')
check('head: нет deprecated-мета', not _dep_all, str(_dep_all[:3]))

# Клик-глубина с главной (link_graph: BFS по внутренним ссылкам)
_urls = {p: re.findall(r'href="(/[^"#?]+)"', h) for p, h in pages.items() if p.endswith('/')}
_nodes = set(_urls)
_nodes = set(_urls)
_links = {p: [(u.lstrip('/') if u.lstrip('/') in _nodes else (u.lstrip('/') + '/' if u.lstrip('/') + '/' in _nodes else None)) for u in ls if u != '/'] for p, ls in _urls.items()}
_links = {p: [x for x in v if x and x != p] for p, v in _links.items()}
_home = next((p for p in _nodes if p.rstrip('/') == ''), None)
_depth = {_home: 0} if _home is not None else {}
_q = [_home] if _home is not None else []
while _q:
    cur = _q.pop(0)
    for nxt in _links.get(cur, []):
        if nxt not in _depth:
            _depth[nxt] = _depth[cur] + 1
            _q.append(nxt)
_unreach = sorted(n for n in _nodes if n not in _depth)
_deep = sorted((p, d) for p, d in _depth.items() if d > 3)
print()
print('INFO link_graph (клик-глубина с главной):')
print(f'  недостижимых страниц: {len(_unreach)}{_unreach[:5] if _unreach else ""}')
print(f'  глубже 3 кликов: {len(_deep)} — {_deep[:8]}')
check('link_graph: нет недостижимых страниц (кроме ресурсов)', not _unreach, str(_unreach[:5]))

# Аудит анкоров: точное совпадение с H1 цели = перегрев (link_graph EXACT_WARN_RATIO=0.60)
def _h1_of(p):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', pages[p], re.S)
    return re.sub(r'<[^>]+>', ' ', m.group(1)).strip() if m else ''
_anchor_edges = 0
_exact = 0
for p, ls in _urls.items():
    for m in re.finditer(r'<a[^>]*href="(/[^"#?]+)"[^>]*>(.*?)</a>', pages[p], re.S):
        _u = m.group(1).lstrip('/')
        tgt = _u if _u in _nodes else (_u + '/' if _u + '/' in _nodes else None)
        if tgt and tgt != p:
            _anchor_edges += 1
            anch = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()
            if anch and _h1_of(tgt) and anch == _h1_of(tgt):
                _exact += 1
print()
print(f'INFO anchor-audit: внутренних ссылок с текстом {_anchor_edges}, точных совпадений с H1 {_exact} ({_exact/max(1,_anchor_edges):.0%}; порог перегрева 60% при ≥10 ссылках)')
if _anchor_edges >= 10:
    check('anchor-audit: нет перегрева точных вхождений', _exact / _anchor_edges <= 0.60, f'{_exact}/{_anchor_edges}')

# Скан водяных знаков (text_metrics): нулевые ширины не должны быть в HTML
_wm_pages = [p for p, h in pages.items() if p.endswith('/') and any(w in h for w in WATERMARKS)]
check('text_metrics: нет невидимых водяных знаков', not _wm_pages, str(_wm_pages[:3]))
print()
print(f'INFO text_metrics: страниц с нулевыми символами: {len(_wm_pages)}')

# Вхлдинги без контекста (INFO-список нулевых входящих, кроме главной)
_in = {n: set() for n in _nodes}
for p, ls in _links.items():
    for t in ls:
        if t in _in:
            _in[t].add(p)
_zero_in = sorted(n for n in _nodes if n != _home and not _in.get(n))
print(f'INFO inlinks: страниц без внутренних входящих (кроме главной): {len(_zero_in)} — {_zero_in[:6]}')


# ===== Canonical-аудит (перенос методологии Habr 1104212: canonical как граф) =====
_c_missing, _c_mismatch = [], []
for _p, _h in pages.items():
    if not _p.endswith('/'):
        continue
    _m = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', _h) or re.search(r'<link[^>]+href="([^"]+)"[^>]+rel="canonical"', _h)
    if not _m:
        _c_missing.append(_p)
        continue
    _u = _m.group(1)
    if not _u.startswith('https://polisprice.ru'):
        _c_mismatch.append((_p, 'не домен: ' + _u))
        continue
    _want = 'https://polisprice.ru/' if _p in ('', '/') else 'https://polisprice.ru/' + _p
    _have = _u.rstrip('/') + '/'
    if _have != _want:
        _c_mismatch.append((_p, _u))
print()
print('INFO canonical-граф (Habr 1104212):')
print(f'  без canonical: {len(_c_missing)} — {_c_missing[:5]}')
print(f'  расхождений: {len(_c_mismatch)} — {_c_mismatch[:5]}')
check('canonical есть у всех страниц', not _c_missing, str(_c_missing[:5]))
check('canonical указывает на свой путь', not _c_mismatch, str(_c_mismatch[:5]))

# og:url + twitter-карты (share-превью; порядок атрибутов order-agnostic)
def _meta_of(_h, _key):
    for _m in re.finditer(r'<meta[^>]*>', _h):
        _tag = _m.group(0)
        _nm = re.search(r'(?:name|property)="([^"]+)"', _tag)
        _ct = re.search(r'content="([^"]*)"', _tag)
        if _nm and _nm.group(1) == _key and _ct:
            return _ct.group(1)
    return None
_t2_bad = []
for _p, _h in pages.items():
    if not _p.endswith('/'):
        continue
    _ou = _meta_of(_h, 'og:url')
    _tc = _meta_of(_h, 'twitter:card')
    if not _ou or not _ou.startswith('https://polisprice.ru'):
        _t2_bad.append((_p, 'og:url=' + str(_ou)))
    if _tc != 'summary_large_image':
        _t2_bad.append((_p, 'twitter:card=' + str(_tc)))
    if not (_meta_of(_h, 'twitter:title') and _meta_of(_h, 'twitter:description') and _meta_of(_h, 'twitter:image')):
        _t2_bad.append((_p, 'twitter:meta'))
check('head: og:url абсолютный и twitter-карты на всех страницах', not _t2_bad, str(_t2_bad[:3]))

# Выше-fold на GEO: первый абзац после h1 — прямой ответ с ценой (Perplexity-эмпирика Habr 1094484)
_geo_fold_bad = []
for _p, _h in pages.items():
    if not (_p.startswith('osago-v-') and _p.endswith('/')):
        continue
    _m = re.search(r'</h1>\s*<p[^>]*>(.*?)</p>', _h, re.S)
    if not _m:
        _geo_fold_bad.append((_p, 'нет абзаца после h1'))
        continue
    _txt = re.sub(r'<[^>]+>', ' ', _m.group(1))
    if len(_txt.split()) < 25 or '₽' not in _txt:
        _geo_fold_bad.append((_p, f'слов={len(_txt.split())}'))
check('GEO выше-fold: первый абзац ≥25 слов и с ценой', not _geo_fold_bad, str(_geo_fold_bad[:3]))


# ===== Валидатор коэффициентов (гейт на дрейф JSON) =====
import os as _os, json as _json
_cfg_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'src', 'data', 'osago_coefficients_2026.json')
_cf = _json.load(open(_cfg_path, encoding='utf-8'))
_drift = []
_kts = [x['kt'] for x in _cf['kt_full']]
if len(_kts) != 192:
    _drift.append(f'kt_full: {len(_kts)} зон вместо 192')
for _k, _v in _cf['kbm']['classes'].items():
    if not (0.46 <= _v <= 3.92):
        _drift.append(f'КБМ класс {_k} = {_v} вне коридора 0,46–3,92')
for _k, _v in _cf['km_auto']:
    if not (0.6 <= _v <= 1.6):
        _drift.append(f'КМ {_k} = {_v} вне коридора 0,6–1,6')
_kv = [v for _r in _cf['kvs_auto'] for _k, v in _r.items() if _k != 'age' and v is not None]
if _kv and (min(_kv) < 0.83 or max(_kv) > 2.27):
    _drift.append(f'КВС вне коридора 0,83–2,27 (min={min(_kv)}, max={max(_kv)})')
_ko = _cf['ko']
if _ko.get('неограниченный: физлицо') != 3.16 or _ko.get('ограниченный полис (список водителей)') != 1.0:
    _drift.append('КО изменился: ' + str(_ko))
_tb = [x for x in _cf['tb'] if x['cat'] == 'B,BE физлица/ИП'][0]
if _tb['min'] != 1399 or _tb['max'] != 8665:
    _drift.append(f'ТБ физлиц: {_tb["min"]}–{_tb["max"]} вместо 1399–8665')
print()
print('INFO валидатор коэффициентов:')
print(f'  нарушений коридоров: {len(_drift)} — {_drift[:3]}')
check('коэффициенты в коридорах Указания № 7204-У', not _drift, '; '.join(_drift[:3]))

print()
print(f'АУДИТ: {'FAILED' if fails else 'PASSED'} | провалено: {len(fails)}')
for f in fails:
    print('  -', f[:200])
sys.exit(1 if fails else 0)
