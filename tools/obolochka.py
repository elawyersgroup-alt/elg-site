"""Общая оболочка сайта (задача Игоря 25.09.2026): шапка, меню, подвал и блок стилей SHELL — на все страницы с содержимым.

Образец — praktika.html (внутренняя страница новой оболочки): блок стилей между «/* === SHELL:» и «/* === /SHELL === */»,
<header class="site-head"> (кнопка «Обсудить задачу» ведёт на /kontakty.html), <footer class="site-foot"> и скрипт выпадающих
меню. Главная и четыре страницы из архива Игоря не трогаются, служебные файлы подтверждения прав (google…, yandex_…) — тоже.

Что делается со страницей старой оболочки:
  1. старые правила для header, footer и .burger обезвреживаются, а не удаляются: header → header:not(.site-head),
     footer → footer:not(.site-foot), .burger → .nav .burger (старая кнопка меню жила внутри .nav); комментарии не трогаются;
  2. в :root добавляется --sheet (цвет, которым пользуется SHELL; на новых страницах он есть, на старых не было);
  3. блок SHELL — в конец первого <style>, после старых правил; если блок уже есть — заменяется целиком (скрипт можно
     запускать повторно после правки образца);
  4. старые <header>…</header> и <footer>…</footer> заменяются шапкой и подвалом образца, скрипт меню — перед </body>.
Переводы строк страницы сохраняются (CRLF у старых страниц).

    python3 tools/obolochka.py            — изменить рабочую копию и напечатать, что сделано
    python3 tools/obolochka.py --proverka — ничего не писать, только показать, какие страницы изменятся"""
import glob, io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOVYE = {"index.html", "praktika.html", "dlya-sobstvennikov.html", "dlya-developerov.html", "o-kompanii.html"}
SH_A, SH_B = "/* === SHELL:", "/* === /SHELL === */"


def obrazec():
    t = io.open(os.path.join(ROOT, "praktika.html"), encoding="utf-8", newline="").read().replace("\r\n", "\n")
    shell = t[t.index(SH_A):t.index(SH_B) + len(SH_B)]
    head = re.search(r'<header class="site-head".*?</header>', t, re.S).group(0)
    foot = re.search(r'<footer class="site-foot".*?</footer>', t, re.S).group(0)
    js = [s for s in re.findall(r"<script>.*?</script>", t, re.S) if "querySelectorAll('.has-drop>button')" in s]
    assert shell and head and foot and len(js) == 1 and 'href="/kontakty.html">Обсудить задачу<' in head
    return shell, head, foot, js[0]


def obezvredit(css):
    """Селекторы старых правил: header, footer, .burger — чтобы не цеплять новую шапку и подвал. Только текст перед «{»."""
    def sel(seg):
        parts = re.split(r"(/\*.*?\*/)", seg, flags=re.S)
        for i, p in enumerate(parts):
            if p.startswith("/*") or p.lstrip().startswith("@"): continue
            p = re.sub(r"(?<![\w.#:-])header(?![\w-]|:not\()", "header:not(.site-head)", p)
            p = re.sub(r"(?<![\w.#:-])footer(?![\w-]|:not\()", "footer:not(.site-foot)", p)
            p = re.sub(r"(?<![\w-])(?<!\.nav )\.burger(?![\w-])", ".nav .burger", p)
            parts[i] = p
        return "".join(parts)
    return re.sub(r"([^{}]+)(?=\{)", lambda m: sel(m.group(1)), css)


def odna(fn, shell, head, foot, js):
    raw = io.open(fn, encoding="utf-8", newline="").read(); nl = "\r\n" if "\r\n" in raw else "\n"; t = raw.replace("\r\n", "\n")
    was = t
    if SH_A in t:  # повторный прогон: блок и шапка уже новые — заменить на текущий образец
        t = t[:t.index(SH_A)] + shell + t[t.index(SH_B) + len(SH_B):]
        t = re.sub(r'<header class="site-head".*?</header>', lambda m: head, t, count=1, flags=re.S)
        t = re.sub(r'<footer class="site-foot".*?</footer>', lambda m: foot, t, count=1, flags=re.S)
    else:
        assert len(re.findall(r"<header\b", t)) == 1 and len(re.findall(r"<footer\b", t)) == 1, "ожидается одна шапка и один подвал"
        t = re.sub(r"(<style[^>]*>)(.*?)(</style>)", lambda m: m.group(1) + obezvredit(m.group(2)) + m.group(3), t, flags=re.S)
        if "--sheet" not in t:
            t = re.sub(r"(:root\s*\{)", r"\1\n  --sheet:#FBFAF6;", t, count=1)
        i = t.index("</style>"); t = t[:i] + "\n" + shell + "\n" + t[i:]
        t = re.sub(r"<header\b.*?</header>", lambda m: head, t, count=1, flags=re.S)
        t = re.sub(r"<footer\b.*?</footer>", lambda m: foot, t, count=1, flags=re.S)
    if "querySelectorAll('.has-drop>button')" not in t:
        i = t.rindex("</body>"); t = t[:i] + js + "\n" + t[i:]
    return (t != was), t.replace("\n", nl)


def main():
    shell, head, foot, js = obrazec(); izm = []
    for fn in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        b = os.path.basename(fn)
        if b in NOVYE or re.match(r"(google|yandex_)", b): continue
        ch, new = odna(fn, shell, head, foot, js)
        if ch:
            izm.append(b)
            if "--proverka" not in sys.argv: io.open(fn, "w", encoding="utf-8", newline="").write(new)
    print(f"страниц изменено: {len(izm)}" + (" (проверка, ничего не записано)" if "--proverka" in sys.argv else ""))
    return izm


if __name__ == "__main__":
    main()
