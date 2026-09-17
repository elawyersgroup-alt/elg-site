#!/usr/bin/env python3
"""Массовая правка меню и подвала на всех страницах сайта: добавить ссылку на новую страницу.
Правило README: общие фрагменты правятся скриптом, не руками. По умолчанию — dry-run (ничего не пишет).
Использование:
    python3 tools/add_nav_links.py --page proverka-izyatie-krt.html --nav "Изъятие и КРТ" --footer "Проверка на изъятие и КРТ"
    python3 tools/add_nav_links.py ... --write        # записать
Меню: пункт вставляется перед кнопкой «Заказать экспертизу» (последний <a> в .nav-links). Подвал: ссылка добавляется в начало второй строки.
index.html имеет якорные ссылки без «/» и <div class="wrap nav"> — обрабатывается тем же кодом; страницы с иным подвалом (kontakty, o-kompanii, rekvizity) получают ссылку в свою вторую строку.
Повторный запуск безопасен: если ссылка уже стоит в меню или подвале, туда она второй раз не добавляется. Дополнительно --rename "Старый пункт=Новый пункт" переименовывает пункт меню на всех страницах.
Файлы сайта — CRLF (часть строк внутри — LF); скрипт окончания строк не меняет, вставки идут с преобладающим окончанием файла. Первый прогон 17.09 (коммит afdfa0a) ещё выравнивал LF→CRLF, поэтому его diff шире двух строк на файл."""
import argparse, glob, re, os, sys
ap = argparse.ArgumentParser(); ap.add_argument("--page", required=True); ap.add_argument("--nav", required=True); ap.add_argument("--footer", required=True); ap.add_argument("--write", action="store_true"); ap.add_argument("--rename", action="append", default=[], help="Старый текст пункта=Новый текст"); ap.add_argument("--move-to-footer", action="append", default=[], help="Текст пункта меню, который убирается из меню и добавляется ссылкой в подвал")
a = ap.parse_args(); href = "/" + a.page.lstrip("/")
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NAV_A = re.compile(r'(<a\b[^>]*class="[^"]*\bbtn\b[^"]*"[^>]*>[^<]*</a>\s*)(?=</div>\s*</nav>|</div>\s*</div>|</nav>)', re.S)  # кнопка в конце меню
FOOT_2 = re.compile(r'(</div>\s*<div>)(?=(?:<a |Москва и Московская область))', re.S)  # начало второй строки подвала
report = []
for f in sorted(glob.glob("*.html")):
    raw = open(f, "rb").read(); t = raw.decode("utf-8", "replace"); nl = "\r\n" if raw.count(b"\r\n") >= raw.count(b"\n") // 2 else "\n"  # окончания строк не трогаем: правим текст как есть, вставки — с преобладающим окончанием файла
    hdr = re.search(r"<header\b.*?</header>", t, re.S); ftr = re.search(r"<footer\b.*?</footer>", t, re.S)
    if not hdr or not ftr: report.append((f, "нет header/footer")); continue
    h = hdr.group(0); fo = ftr.group(0)  # ссылка ставится и на самой новой странице: меню на всех страницах одинаковое
    n = (h, 0) if f'href="{href}"' in h else NAV_A.subn(lambda m: f'<a href="{href}">{a.nav}</a>{nl}      ' + m.group(1), h, count=1)
    n2 = (fo, 0) if f'href="{href}"' in fo else FOOT_2.subn(lambda m: m.group(1) + f'<a href="{href}" style="color:inherit;text-decoration:none;margin-right:18px">{a.footer}</a> · ', fo, count=1)
    if f'href="{href}"' in h and f'href="{href}"' in fo and not a.rename and not a.move_to_footer: report.append((f, "ссылка уже в меню и подвале")); continue
    h_new = n[0]; ren = 0; fo_new = n2[0]; moved = 0
    for r in a.rename:
        o_, n_ = r.split("=", 1); c = h_new.count(f">{o_}</a>"); h_new = h_new.replace(f">{o_}</a>", f">{n_}</a>"); ren += c
    for label in a.move_to_footer:  # пункт из меню — в подвал, с тем же href (на index якорь без «/», на остальных — «/#…»)
        mm = re.search(r'[ \t]*<a href="([^"]+)">' + re.escape(label) + r'</a>[ \t]*\r?\n?', h_new)
        if mm:
            h_new = h_new.replace(mm.group(0), "", 1); moved += 1
            if f'>{label}</a>' not in fo_new:
                fo_new = FOOT_2.sub(lambda m: m.group(1) + f'<a href="{mm.group(1)}" style="color:inherit;text-decoration:none;margin-right:18px">{label}</a> · ', fo_new, count=1)
    status = f"меню {'+' if n[1] else '—'} подвал {'+' if n2[1] else '—'}" + (f" переименовано {ren}" if ren else "") + (f" в подвал {moved}" if moved else "")
    if a.write and (n[1] or n2[1] or ren or moved):
        t2 = t.replace(h, h_new, 1).replace(fo, fo_new, 1); open(f, "wb").write(t2.encode("utf-8")); status += " записано"
    report.append((f, status))
for f, s in report: print(f"{f:55} {s}")
print("\nитого:", sum(1 for _, s in report if s.startswith("меню +")), "меню,", sum(1 for _, s in report if "подвал +" in s), "подвал,", len(report), "файлов;", "DRY-RUN — ничего не записано" if not a.write else "записано")
