#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка сайта argument-law.ru — перед переобходом и после каждой выкладки.

Две разные проверки, и нужны обе (Игорь, 24.09.2026): сверка с репозиторием подтверждает, что на сервере то же, что в git,
но не то, что в git правильно.

1. По рабочей копии (всегда):
   - парность тегов: каждый открытый section, div, main, header, footer, nav, article, aside, ul, ol, table, form, figure,
     details, a, span, button, h1–h6, script, style закрыт, и закрыт по порядку (24.09 у четырёх страниц первый экран
     не был закрыт — нижние блоки оказывались внутри него);
   - заголовок не длиннее 65 знаков, описание не длиннее 160, canonical — адрес самой страницы;
   - внутренние ссылки и картинки ведут на существующие файлы;
   - карта сайта: у каждого адреса есть файл и дата правки, каждая страница (кроме файлов подтверждения) есть в карте.
2. С ключом --live: каждый файл сайта скачивается и сравнивается по SHA-256 с HEAD репозитория. С Мака сайт открывается
   только через локальный прокси (127.0.0.1:8123, elg-pzz/scripts/en0_proxy.py) — он берётся сам, если отвечает.

Запуск из корня elg-site:  python3 tools/proverka_sayta.py [--live]
Код выхода 0 — всё чисто, 1 — есть находки (список в выводе)."""
import os, re, sys, glob, hashlib, socket, subprocess, html
from html.parser import HTMLParser
from urllib.request import build_opener, ProxyHandler, Request

SITE = "https://argument-law.ru/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRICT = {"section", "div", "main", "header", "footer", "nav", "article", "aside", "ul", "ol", "table", "form", "figure",
          "details", "a", "span", "button", "h1", "h2", "h3", "h4", "h5", "h6", "script", "style"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SERVED = re.compile(r"\.(html|xml|txt|png|jpg|jpeg|webp|svg|pdf|docx|ico|css|js)$")
VERIFY_FILES = re.compile(r"^(google[0-9a-f]+|yandex_[0-9a-f]+)\.html$")


class Balance(HTMLParser):
    """Стек открытых тегов: находит незакрытые и закрытые не по порядку (с номером строки)."""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.stack, self.problems = [], []
    def handle_starttag(self, tag, attrs):
        if tag not in VOID: self.stack.append((tag, self.getpos()[0]))
    def handle_startendtag(self, tag, attrs): pass
    def handle_endtag(self, tag):
        if tag in VOID: return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                skipped = [t for t in self.stack[i + 1:] if t[0] in STRICT]
                if skipped: self.problems.append(f"строка {self.getpos()[0]}: </{tag}> закрывает, не закрыв {', '.join(f'<{t}> (строка {l})' for t, l in skipped)}")
                del self.stack[i:]; return
        if tag in STRICT: self.problems.append(f"строка {self.getpos()[0]}: лишний </{tag}>")
    def close(self):
        super().close()
        left = [t for t in self.stack if t[0] in STRICT]
        if left: self.problems.append("не закрыты до конца файла: " + ", ".join(f"<{t}> (строка {l})" for t, l in left))


def git_files():
    out = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
    return [f for f in out if f]


def local_checks():
    finds = []
    files = git_files()
    pages = sorted(f for f in files if f.endswith(".html") and "/" not in f)
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    locs = re.findall(r"<loc>https://argument-law\.ru/([^<]*)</loc>", sm)
    urls = re.findall(r"<url>.*?</url>", sm, re.S)
    for u in urls:
        if "<lastmod>" not in u: finds.append(("sitemap.xml", "адрес без даты правки: " + re.search(r"<loc>([^<]*)", u).group(1)))
    for l in locs:
        if not os.path.exists(os.path.join(ROOT, l or "index.html")): finds.append(("sitemap.xml", f"в карте адрес без файла: /{l}"))
    for f in pages:
        t = open(os.path.join(ROOT, f), encoding="utf-8").read()
        b = Balance(); b.feed(t); b.close()
        for p in b.problems: finds.append((f, "теги: " + p))
        if VERIFY_FILES.match(f): continue
        title = re.search(r"<title>(.*?)</title>", t, re.S); title = html.unescape(title.group(1).strip()) if title else ""
        desc = re.search(r'<meta name="description" content="([^"]*)"', t); desc = html.unescape(desc.group(1)) if desc else ""
        can = re.search(r'<link rel="canonical" href="([^"]*)"', t); can = can.group(1) if can else ""
        want = SITE + ("" if f == "index.html" else f)
        if not title or len(title) > 65: finds.append((f, f"заголовок {len(title)} знаков (нужно 1–65)"))
        if not desc or len(desc) > 160: finds.append((f, f"описание {len(desc)} знаков (нужно 1–160)"))
        if can != want: finds.append((f, f"canonical «{can}» вместо «{want}»"))
        if ("" if f == "index.html" else f) not in locs: finds.append((f, "страницы нет в карте сайта"))
        for h in set(re.findall(r'href="/([^"#?]*)', t)):
            if h and not h.endswith("/") and not os.path.exists(os.path.join(ROOT, h)): finds.append((f, f"битая ссылка /{h}"))
        for s in set(re.findall(r'src="/([^"#?]*)', t)):
            if not os.path.exists(os.path.join(ROOT, s)): finds.append((f, f"нет файла /{s}"))
    return pages, locs, finds


def live_checks():
    finds = []
    try:
        socket.create_connection(("127.0.0.1", 8123), timeout=1).close(); proxy = {"http": "http://127.0.0.1:8123", "https": "http://127.0.0.1:8123"}
    except OSError:
        proxy = {}
    opener = build_opener(ProxyHandler(proxy))
    files = [f for f in git_files() if SERVED.search(f) and not f.startswith("tools/")]
    ok = 0
    for f in files:
        want = hashlib.sha256(subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{f}"], capture_output=True, check=True).stdout).hexdigest()
        try:
            r = opener.open(Request(SITE + f, headers={"User-Agent": "Mozilla/5.0 (proverka_sayta)", "Cache-Control": "no-cache"}), timeout=30)
            got = hashlib.sha256(r.read()).hexdigest(); code = r.status
        except Exception as e:
            finds.append((f, f"не скачался: {type(e).__name__}: {str(e)[:80]}")); continue
        if code != 200: finds.append((f, f"ответ {code}"))
        elif got != want: finds.append((f, f"на сервере не то, что в HEAD: {got[:12]} против {want[:12]}"))
        else: ok += 1
    try:
        opener.open(Request(SITE + "net-takoy-stranicy-proverka.html", headers={"User-Agent": "Mozilla/5.0 (proverka_sayta)"}), timeout=30)
        finds.append(("—", "несуществующая страница отвечает 200, а не 404"))
    except Exception as e:
        if "404" not in str(e): finds.append(("—", f"несуществующая страница: {str(e)[:80]}"))
    return ok, len(files), ("через прокси 127.0.0.1:8123" if proxy else "напрямую"), finds


if __name__ == "__main__":
    pages, locs, finds = local_checks()
    print(f"рабочая копия: страниц {len(pages)}, в карте сайта {len(locs)}; находок {len(finds)}")
    if "--live" in sys.argv:
        ok, total, how, lf = live_checks()
        print(f"живой сайт ({how}): совпало с HEAD {ok} из {total}; находок {len(lf)}")
        finds += lf
    for f, what in finds: print(f"  {f}: {what}")
    sys.exit(1 if finds else 0)
