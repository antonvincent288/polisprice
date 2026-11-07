#!/usr/bin/env python3
"""Scout bot v2: ежедневная разведка решений для роста в поиске.
Источники: GitHub API, Hacker News, npm, dev.to, Google Search Central blog (RSS),
Yandex Webmaster blog (RSS). Дубли фильтруются по intel/seen.json."""
import json, os, re, urllib.request, urllib.parse, datetime, time

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTEL = os.path.join(REPO_DIR, 'intel')
SEEN = os.path.join(INTEL, 'seen.json')
UA = {'User-Agent': 'polisprice-scout/2.0', 'Accept': 'application/vnd.github+json'}

def get_raw(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'ignore')

def get_json(url, timeout=25):
    return json.loads(get_raw(url, timeout))

today = datetime.date.today().isoformat()
month_ago = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
findings = []
try:
    seen = json.load(open(SEEN, encoding='utf-8'))
except Exception:
    seen = {}
for k in ('repos', 'npm', 'hn', 'devto', 'rss'):
    seen.setdefault(k, [])
    seen[k] = seen[k][-3000:]

# --- GitHub: решения для ранжирования ---
GH_QUERIES = [
    'generative engine optimization stars:>20 pushed:>' + month_ago,
    'seo audit tool stars:>50 pushed:>' + month_ago,
    'astro seo integration stars:>5 pushed:>' + month_ago,
    'llms.txt stars:>10',
    'structured data schema.org stars:>100 pushed:>' + month_ago,
    'programmatic seo stars:>30 pushed:>' + month_ago,
    'yandex seo stars:>3 pushed:>' + month_ago,
    'search ranking factors stars:>10 pushed:>' + month_ago,
    'rich snippets structured data stars:>20',
    'internal linking tool stars:>5',
    'core web vitals tool stars:>20 pushed:>' + month_ago,
]
JUNK = re.compile(r'(hack|exploit|termux|crack|cracked|apk|\bmod\b|camera|malware|botnet|phishing|game|gaming|instagram|tiktok|youtube|download)', re.I)

def junky(name, desc):
    s = (name or '') + ' ' + (desc or '')
    return bool(JUNK.search(s))

def relevant(q_words, name, desc):
    words = {w for w in re.split(r'\W+', q.lower()) if len(w) > 3 and not w.startswith(('stars:', 'pushed:'))}
    blob = set(re.split(r'\W+', (name + ' ' + (desc or '')).lower()))
    return bool(words & blob)
for q in GH_QUERIES:
    try:
        data = get_json('https://api.github.com/search/repositories?q=' + urllib.parse.quote(q) + '&s=stars&o=desc&per_page=5')
        for it in data.get('items', []):
            fn = it['full_name']
            desc = (it.get('description') or '').strip()
            if fn in seen['repos'] or junky(fn.split('/')[-1], desc) or not relevant(q, fn.split('/')[-1], desc):
                seen['repos'].append(fn)
                continue
            seen['repos'].append(fn)
            findings.append(f"- ★{it['stargazers_count']} [{fn}]({it['html_url']}) — {desc[:120]} · GitHub")
        time.sleep(8)
    except Exception as e:
        print('GH q fail:', q[:40], e)
        time.sleep(10)

# --- Hacker News ---
HN_QUERIES = ['programmatic seo', 'generative engine optimization', 'seo automation', 'search ranking']
for q in HN_QUERIES:
    try:
        data = get_json('https://hn.algolia.com/api/v1/search?query=' + urllib.parse.quote(q) + '&tags=story&hitsPerPage=3')
        for h in data.get('hits', []):
            oid = h.get('objectID')
            if oid in seen['hn']:
                continue
            seen['hn'].append(oid)
            if (h.get('points') or 0) >= 20:
                url = h.get('url') or f"https://news.ycombinator.com/item?id={oid}"
                findings.append(f"- {h['points']} очк. [{h.get('title') or ''}]({url}) · Hacker News")
        time.sleep(4)
    except Exception as e:
        print('HN q fail:', q, e)
        time.sleep(8)

# --- npm ---
NPM_QUERIES = ['astro seo', 'seo audit', 'structured data']
for q in NPM_QUERIES:
    try:
        data = get_json('https://registry.npmjs.org/-/v1/search?text=' + urllib.parse.quote(q) + '&size=5')
        for o in data.get('objects', []):
            pkg = o['package']
            if pkg['name'] in seen['npm']:
                continue
            seen['npm'].append(pkg['name'])
            if (o.get('score', {}) or {}).get('final', 0) < 0.4:
                continue
            links = pkg.get('links', {})
            url = links.get('npm') or links.get('homepage') or 'https://www.npmjs.com/package/' + pkg['name']
            findings.append(f"- npm: [{pkg['name']}]({url}) — {(pkg.get('description') or '').strip()[:120]}")
        time.sleep(4)
    except Exception as e:
        print('npm q fail:', q, e)
        time.sleep(8)

# --- dev.to: статьи недели по seo ---
try:
    data = get_json('https://dev.to/api/articles?tag=seo&top=7&per_page=5')
    for a in data:
        if a.get('id') in seen['devto']:
            continue
        seen['devto'].append(a.get('id'))
        findings.append(f"- {a.get('positive_reactions_count', 0)}♥ [{a.get('title', '')}]({a.get('url', '')}) · dev.to")
    time.sleep(4)
except Exception as e:
    print('dev.to fail:', e)

# --- RSS-блоги: Google Search Central, Яндекс.Вебмастер ---
RSS_SOURCES = [
    ('Google Search Central', ['https://developers.google.com/search/blog/feed.xml']),
    ('Яндекс.Вебмастер', ['https://yandex.ru/blog/webmaster/rss']),
    ('Habr · SEO-хаб', ['https://habr.com/ru/rss/hubs/seo/?fl=ru']),
    ('Habr · Best', ['https://habr.com/ru/rss/best/?fl=ru']),
]
KEYWORDS = re.compile(r'(seo|geo|rank|index|schema|snippet|crawl|core web vitals|перелинков|алгорит|ранжир|индексац|сниппет|скорост|контент|нейросет|llm|ai-поиск|гпо)', re.I)
cutoff = datetime.datetime.now() - datetime.timedelta(days=14)
for src_name, urls in RSS_SOURCES:
    try:
        xml = None
        for u in urls:
            try:
                xml = get_raw(u)
                if '<item>' in xml or '<entry>' in xml:
                    break
            except Exception:
                xml = None
        if not xml:
            raise RuntimeError('нет живого URL')
        items = re.findall(r'<item>(.*?)</item>', xml, re.S)
        if not items:
            items = re.findall(r'<entry>(.*?)</entry>', xml, re.S)
        for it in items[:8]:
            title = (re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', it, re.S).group(1) if re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', it, re.S) else '').strip()
            link_m = re.search(r'<link[^>]*href="([^"]+)"', it) or re.search(r'<link>([^<]+)</link>', it)
            link = link_m.group(1).strip() if link_m else ''
            if not title or not link:
                continue
            if link in seen['rss']:
                continue
            seen['rss'].append(link)
            date_m = re.search(r'<(?:pubDate|updated|published)>([^<]+)</', it)
            if date_m:
                try:
                    from email.utils import parsedate_to_datetime
                    from datetime import timezone
                    dt = parsedate_to_datetime(date_m.group(1))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt < cutoff:
                        continue
                except Exception:
                    pass
            if KEYWORDS.search(title):
                findings.append(f"- [{title}]({link}) · {src_name}")
        time.sleep(4)
    except Exception as e:
        print(f'{src_name} fail:', e)

os.makedirs(INTEL, exist_ok=True)
json.dump(seen, open(SEEN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if findings:
    by_src = {}
    for f in findings:
        tag = f.split('·')[-1].strip() if '·' in f else 'прочее'
        by_src.setdefault(tag, []).append(f)
    block = f'## Прогон {datetime.datetime.now().strftime("%H:%M")} UTC\n\n'
    for tag, rows in by_src.items():
        block += f'### {tag}\n\n' + '\n'.join(rows[:15]) + '\n\n'
    path = os.path.join(INTEL, f'recon_{today}.md')
    # накопительный режим: не терять находки при повторных прогонах в один день
    if os.path.exists(path):
        with open(path, 'a', encoding='utf-8') as f:
            f.write('\n' + block)
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'# Разведка {today}\n\n' + block)
    print('новых находок:', len(findings), '| источников с находками:', len(by_src))
else:
    print('новых находок нет — отчёт не создавался')
print('scout v2 done')

# ===== Еженедельный свод разведки (по образцу Habr 1090870: отчёт на 200 строках Python) =====
def weekly_digest():
    import glob as _glob
    from datetime import datetime as _dt, timedelta as _td
    try:
        intel = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'intel') if not os.path.isdir('intel') else 'intel'
        if not os.path.isdir(intel):
            return
        wk_file = os.path.join(intel, 'weekly_report.md')
        since = _dt.now() - _td(days=7)
        recent = []
        for fp in sorted(_glob.glob(os.path.join(intel, 'recon_*.md'))):
            try:
                mdate = _dt.fromtimestamp(os.path.getmtime(fp))
                if mdate >= since:
                    with open(fp, encoding='utf-8') as fh:
                        recent.append((fp, fh.read()))
            except Exception:
                pass
        seen_counts = {}
        seen_path = os.path.join(intel, 'seen.json')
        if os.path.exists(seen_path):
            try:
                seen_counts = {k: len(v) if isinstance(v, (list, set, dict)) else v for k, v in json.load(open(seen_path, encoding='utf-8')).items()}
            except Exception:
                pass
        total_new = sum(body.count('- [') for _, body in recent)
        lines = [f'# Еженедельный свод разведки — {_dt.now().strftime("%Y-%m-%d")}', '',
                 f'Файлов за 7 дней: {len(recent)} | находок всего: {total_new}']
        if seen_counts:
            lines.append('Дедуп-реестр: ' + ', '.join(f'{k}: {v}' for k, v in sorted(seen_counts.items())))
        for fp, body in recent[-3:]:
            lines.append('')
            lines.append(f'## {os.path.basename(fp)}')
            lines.append(body[:1200])
        with open(wk_file, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
        print(f'[weekly] свод записан: {wk_file} ({len(recent)} файлов, {total_new} находок)')
    except Exception as _e:
        print('[weekly] ошибка (не фатально):', _e)


if __name__ == '__main__':
    pass

try:
    main()
except NameError:
    pass
weekly_digest()
