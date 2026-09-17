#!/usr/bin/env python3
"""Массовая правка меню и подвала на всех страницах сайта: добавить ссылку на новую страницу.
Правило README: общие фрагменты правятся скриптом, не руками. По умолчанию — dry-run (ничего не пишет).
Использование:
    python3 tools/add_nav_links.py --page proverka-izyatie-krt.html --nav "Изъятие и КРТ" --footer "Проверка на изъятие и КРТ"
    python3 tools/add_nav_links.py ... --write        # записать
Меню: пункт вставляется перед кнопкой «Заказать экспертизу» (последний <a> в .nav-links). Подвал: ссылка добавляется в начало второй строки.
index.html имеет якорные ссылки без «/» и <div class="wrap nav"> — обрабатывается тем же кодом; страницы с иным подвалом (kontakty, o-kompanii, rekvizity) получают ссылку в свою вторую строку.
Файлы сайта — CRLF; скрипт сохраняет окончания строк как были."""
import argparse, glob, re, os, sys
ap = argparse.ArgumentParser(); ap.add_argument("--page", required=True); ap.add_argument("--nav", required=True); ap.add_argument("--footer", required=True); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); href = "/" + a.page.lstrip("/")
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NAV_A = re.compile(r'(<a\b[^>]*class="[^"]*\bbtn\b[^"]*"[^>]*>[^<]*</a>\s*)(?=</div>\s*</nav>|</div>\s*</div>|</nav>)', re.S)  # кнопка в конце меню
FOOT_2 = re.compile(r'(</div>\s*<div>)(?=(?:<a |Москва и Московская область))', re.S)  # начало второй строки подвала
report = []
for f in sorted(glob.glob("*.html")):
    raw = open(f, "rb").read(); crlf = b"\r\n" in raw; t = raw.decode("utf-8", "replace").replace("\r\n", "\n")
    if href in t and f != a.page: report.append((f, "уже есть ссылка")); continue
    if f == a.page: report.append((f, "сама страница — пропуск")); continue
    hdr = re.search(r"<header\b.*?</header>", t, re.S); ftr = re.search(r"<footer\b.*?</footer>", t, re.S)
    if not hdr or not ftr: report.append((f, "нет header/footer")); continue
    h = hdr.group(0); n = NAV_A.subn(lambda m: f'<a href="{href}">{a.nav}</a>\n      ' + m.group(1), h, count=1)
    fo = ftr.group(0); n2 = FOOT_2.subn(lambda m: m.group(1) + f'<a href="{href}" style="color:inherit;text-decoration:none;margin-right:18px">{a.footer}</a> · ', fo, count=1)
    status = f"меню {'+' if n[1] else '—'} подвал {'+' if n2[1] else '—'}"
    if a.write and (n[1] or n2[1]):
        t2 = t.replace(h, n[0], 1).replace(fo, n2[0], 1); out = t2.replace("\n", "\r\n") if crlf else t2; open(f, "wb").write(out.encode("utf-8")); status += " записано"
    report.append((f, status))
for f, s in report: print(f"{f:55} {s}")
print("\nитого:", sum(1 for _, s in report if s.startswith("меню +")), "меню,", sum(1 for _, s in report if "подвал +" in s), "подвал,", len(report), "файлов;", "DRY-RUN — ничего не записано" if not a.write else "записано")
