"""Package selected local answers; never execute code found in the materials."""

from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATE = "2026-11-04"
GROUPS = {"live-coding", "network", "node.js", "react", "security", "ts"}


def config(directory, count, junior, senior, description, practice=()):
    return dict(directory=directory, count=count, junior=set(junior),
                senior=set(senior), description=description, practice=set(practice))


# Every difficulty is an editorial assessment, not source metadata.
CONFIG = {
    "live-coding--frontend-ui": config(
        "live-coding-frontend-ui", 19, {4, 8, 9, 12, 15}, {6, 18, 19},
        "Практические задания по интерфейсам: поиск, списки, таблицы, формы, доступность и управление состоянием.", range(1, 20)),
    "live-coding--js-и-ts": config(
        "live-coding-js-and-ts", 28, {1, 2, 9, 11, 20, 21, 24}, {4, 6, 8, 12, 15, 17, 22, 23, 27},
        "Реализация полифилов, асинхронных утилит, преобразований данных, кэшей и типизированного доступа к объектам.", range(1, 29)),
    "network--api-и-real-time": config(
        "network-api-and-real-time", 30, {1, 2, 3, 4, 6, 7, 11, 17, 19, 21, 25}, {8, 12, 15, 16, 18, 24, 29, 30},
        "Проектирование API, REST, GraphQL, gRPC, контракты, WebSocket, SSE и WebRTC."),
    "network--dns-tcp-udp-и-tls": config(
        "network-dns-tcp-udp-and-tls", 18, {1, 2, 3, 4, 5, 7, 8, 9, 18}, {6, 10, 12, 16},
        "DNS, транспортные протоколы, TLS, сертификаты, HTTP/2, HTTP/3, прокси и балансировка нагрузки."),
    "network--http-https-и-кэширование": config(
        "network-http-https-and-caching", 36,
        {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 26, 28, 31}, {19, 29, 30, 33, 34},
        "HTTP-методы, статусы и заголовки, браузерное и CDN-кэширование, загрузка ресурсов и сетевая диагностика."),
    "node.js--runtime-и-серверная-интеграция": config(
        "node-runtime-and-server-integration", 15, {1, 7, 8, 9, 10, 13}, {2, 3, 5, 12, 15},
        "Среда Node.js, Event Loop, модули, потоки, middleware, BFF, конфигурация и серверные HTTP-запросы."),
    "react--redux-и-rtk": config(
        "react-redux-and-rtk", 36, {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 18, 20, 21, 23}, {29, 30, 31, 32, 33, 35},
        "Модель Redux, организация состояния, селекторы, Redux Toolkit, типизация, асинхронные операции и миграция."),
    "react--rtk-query": config(
        "react-rtk-query", 18, {1, 2, 3, 5, 6, 7, 8, 9, 10, 13}, {11, 15, 16},
        "Запросы, мутации, кэш, инвалидация, подписки, оптимистические обновления и авторизация в RTK Query."),
    "react--tanstack-query": config(
        "react-tanstack-query", 24, {1, 2, 3, 4, 5, 6, 7, 9, 10, 14, 15, 17, 18, 19}, {12, 13, 21, 22, 23},
        "Серверное состояние, ключи запросов, жизненный цикл кэша, мутации, пагинация, SSR и события сервера."),
    "react--компоненты-jsx-props-и-typescript": config(
        "react-components-jsx-props-and-typescript", 29, set(range(1, 23)) | {24}, {28, 29},
        "Основы компонентов React, JSX, props, состояние, события, refs и типизация компонентного API.", {17, 23}),
    "react--проектирование-компонентов": config(
        "react-component-design", 22, {3, 9, 12, 13, 17, 18, 19, 20}, {6, 10, 11, 14, 15, 16, 21, 22},
        "Композиция, переиспользуемые и headless-компоненты, границы ответственности, безопасность HTML и модальные окна.", {22}),
    "react--рендеринг-fiber-и-оптимизация": config(
        "react-rendering-fiber-and-optimization", 26, {1, 2, 3, 4, 5, 8, 11, 14, 17, 20, 21}, {6, 7, 9, 10, 12, 13, 19, 23, 24},
        "Рендеринг, reconciliation, Fiber, конкурентные обновления, Suspense, мемоизация и профилирование React."),
    "react--тестирование-компонентов": config(
        "react-component-testing", 17, {1, 2, 3, 4, 5, 14}, {10, 11, 16, 17},
        "Тестирование пользовательского поведения, React Testing Library, асинхронные сценарии, контексты и MSW."),
    "react--формы-и-валидация": config(
        "react-forms-and-validation", 16, {1, 2, 3, 6, 8, 11, 12}, {9, 10, 13, 16},
        "React Hook Form, Zod, динамические поля, серверные ошибки, многошаговые формы, autosave и доступность."),
    "react--фреймворки-ssr-и-роутинг": config(
        "react-frameworks-ssr-and-routing", 41, {1, 2, 3, 13, 14, 15, 18, 19, 23, 24, 29, 39},
        {5, 6, 7, 8, 10, 11, 12, 25, 27, 28, 31, 32, 35, 37, 38, 40, 41},
        "CSR, SSR, SSG, ISR, hydration, Server Components, React Router, Next.js, кэширование и серверные мутации."),
    "react--хуки-эффекты-и-жизненный-цикл": config(
        "react-hooks-effects-and-lifecycle", 33, {1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 16, 18, 20, 24, 30}, {14, 21, 23, 25, 26, 27, 28, 32, 33},
        "Hooks, состояние, эффекты, синхронизация с внешними системами, новые API React и собственные хуки.", {31, 32, 33}),
    "security--web-xss-csrf-cors-и-csp": config(
        "security-web-xss-csrf-cors-and-csp", 23, {1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15, 19, 20}, {4, 5, 7, 16, 18, 21, 23},
        "XSS, CSRF, CORS, CSP, защита от clickjacking, риски зависимостей, токенов и утечек данных."),
    "security--аутентификация-и-авторизация-в-web": config(
        "security-web-authentication-and-authorization", 26, {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16}, {13, 14, 17, 19, 21, 22, 24, 25},
        "Сессии, cookie, токены, JWT, роли и атрибуты доступа, OAuth, OpenID Connect, SSO и BFF."),
    "ts--система-типов": config(
        "ts-type-system", 37, {1, 2, 3, 4, 5, 7, 8, 10, 13, 15, 17, 18, 20, 21, 36}, {24, 25, 26, 27, 28, 29, 32, 35, 37},
        "Система типов TypeScript, narrowing, generics, условные и отображаемые типы, runtime-валидация и конфигурация."),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def normalized(value):
    return re.sub(r"[^\w]", "", value.casefold())


def outside_code_lines(text):
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if match:
            if fence is None:
                fence = (match[1][0], len(match[1]))
            elif match[1][0] == fence[0] and len(match[1]) >= fence[1] and not match[2].strip():
                fence = None
            continue
        if fence is None:
            yield number, line
    if fence:
        raise ValueError("Unclosed code fence")


def code_blocks(text):
    return re.findall(r"^```[^\n]*\n(.*?)^```[ \t]*$", text, re.M | re.S)


def parse_source(path):
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    headings = [(n, line[2:]) for n, line in outside_code_lines(text) if line.startswith("# ")]
    if not headings:
        raise ValueError("Missing question headings")
    preamble = "\n".join(lines[:headings[0][0] - 1]).strip() or None
    if preamble and not (path.stem == "react--хуки-эффекты-и-жизненный-цикл" and preamble == "["):
        raise ValueError("Unaccounted source preamble")
    if headings[0][1] == "Security: Аутентификация и авторизация в Web":
        preamble = "\n".join(lines[:headings[1][0] - 1]).strip()
        if preamble != "# Security: Аутентификация и авторизация в Web":
            raise ValueError("Unexpected content under the course heading")
        headings = headings[1:]
    questions = []
    for index, (number, title) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        questions.append(dict(title=title, answer="\n".join(lines[number:end]).strip(), sourceLine=number))
    return questions, preamble


def clean_answer(answer):
    # Exported citation favicons become ordinary text links. The cited domain
    # and label come directly from the source; no external data is fetched.
    lines = answer.splitlines()
    outside = dict(outside_code_lines(answer))
    replacements, skip = [], set()
    for index, line in enumerate(lines):
        if index + 1 not in outside:
            continue
        match = re.fullmatch(r"(\s*)\[image\]\((https://www\.google\.com/s2/favicons\?[^\n]+)\)\s*", line)
        if not match:
            continue
        label_index = index + 1
        while label_index < len(lines) and not lines[label_index].strip():
            label_index += 1
        if label_index >= len(lines) or label_index + 1 not in outside:
            raise ValueError("Missing favicon citation label")
        raw_label = lines[label_index].strip()
        label = re.sub(r"\+\d+$", "", raw_label)
        domain = parse_qs(urlsplit(match[2].replace("\\&", "&")).query).get("domain", [None])[0]
        if not domain or urlsplit(domain).scheme not in {"http", "https"}:
            raise ValueError("Unrecognized favicon domain")
        lines[index] = f"{match[1]}[{label}]({domain})"
        skip.update(range(index + 1, label_index + 1))
        replacements.append(dict(original=line, label=raw_label, replacement=lines[index]))
    cleaned = "\n".join(line for i, line in enumerate(lines) if i not in skip).strip()
    for _, line in outside_code_lines(cleaned):
        prose = re.sub(r"`[^`]*`", "", line)
        if re.search(r"!\[|<img\b|\[image\]", prose, re.I):
            raise ValueError("An illustration requires explicit asset handling")
    if code_blocks(cleaned) != code_blocks(answer):
        raise ValueError("Code changed during citation cleanup")
    return cleaned, replacements


def catalog_filename(manifest):
    def encode(value):
        return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")
    tags = json.dumps(manifest["tags"], ensure_ascii=False, separators=(",", ":"))
    name = (f"course.id-{manifest['id']}.name-{encode(manifest['title'])}"
            f".hash-{manifest['hash']}.tags-{encode(tags)}.zip")
    if len(name) > 255 or not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise ValueError("Invalid catalog filename")
    return name


def read_catalog():
    result = []
    for path in sorted((ROOT / "courses").glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            result.append(dict(path=path, manifest=json.loads(archive.read("manifest.json")),
                               questions=json.loads(archive.read("questions.json")),
                               assets={n: archive.read(n) for n in archive.namelist() if n.startswith("assets/") and not n.endswith("/")},
                               sha256=digest(path.read_bytes())))
    ids = [entry["manifest"]["id"] for entry in result]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate course IDs in the catalog")
    return result


def find_existing(title, source, catalog):
    titles = {normalized(q["title"]) for q in source}
    matches = []
    overlaps = []
    for entry in catalog:
        old_titles = {normalized(q["title"]) for q in entry["questions"]}
        overlap = len(titles & old_titles)
        if overlap:
            overlaps.append(dict(id=entry["manifest"]["id"], title=entry["manifest"]["title"], overlappingQuestions=overlap))
        if normalized(entry["manifest"]["title"]) == normalized(title) or (overlap >= 2 and overlap / len(titles) >= 0.8):
            matches.append(entry)
    if len(matches) > 1:
        raise ValueError("Ambiguous match; existing archives were not overwritten")
    return (matches[0] if matches else None), overlaps


def validate_payload(manifest, questions, source, path):
    assert set(manifest) == {"schemaVersion", "id", "version", "hash", "title", "description", "tags"}
    assert type(manifest["schemaVersion"]) is int and manifest["schemaVersion"] == 1
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert re.fullmatch(r"[A-Za-z0-9._-]{1,128}", manifest["hash"])
    assert manifest["title"] == " ".join(path.stem.replace("--", ". ").split())
    assert len(manifest["tags"]) == len(set(manifest["tags"]))
    assert len(questions) == len(source)
    assert len({q["id"] for q in questions}) == len(questions)
    allowed = {"id", "title", "type", "difficulty", "answer", "tags", "language", "solutionCode"}
    for question, raw in zip(questions, source):
        assert set(question) <= allowed
        assert re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,127}", question["id"])
        assert question["type"] in {"theory", "practice"}
        assert question["difficulty"] in {"Junior", "Middle", "Senior"}
        assert question["title"] == raw["title"]
        assert question["answer"] == clean_answer(raw["answer"])[0]
        assert code_blocks(question["answer"]) == code_blocks(raw["answer"])
        assert len(question["tags"]) == len(set(question["tags"])) <= 100
        assert all(isinstance(t, str) and 0 < len(t) <= 128 for t in question["tags"])
        if "solutionCode" in question:
            assert question["solutionCode"] in [b.rstrip("\n") for b in code_blocks(raw["answer"])]


def build_one(path, settings, catalog):
    source, preamble = parse_source(path)
    assert len(source) == settings["count"], (path.name, len(source))
    assert not settings["junior"] & settings["senior"]
    for field in ("junior", "senior", "practice"):
        assert settings[field] <= set(range(1, len(source) + 1))
    title = " ".join(path.stem.replace("--", ". ").split())
    group = path.stem.split("--")[0]
    old, overlaps = find_existing(title, source, catalog)
    if old and old["assets"]:
        raise ValueError("Existing images require explicit reconciliation")
    old_questions = old["questions"] if old else []
    old_by_title = {normalized(q["title"]): q for q in old_questions}
    assert len(old_by_title) == len(old_questions), "Ambiguous existing question titles"
    questions, assessments, cleanups = [], [], []
    for number, raw in enumerate(source, 1):
        previous = old_by_title.get(normalized(raw["title"]))
        qid = previous["id"] if previous else "q-" + digest(normalized(raw["title"]).encode("utf-8"))[:16]
        answer, replacements = clean_answer(raw["answer"])
        difficulty = "Junior" if number in settings["junior"] else "Senior" if number in settings["senior"] else "Middle"
        practical = number in settings["practice"]
        question = dict(id=qid, title=raw["title"], type="practice" if practical else "theory",
                        difficulty=difficulty, answer=answer, tags=[group])
        if path.stem == "live-coding--js-и-ts":
            # Here the first block is the complete supplied implementation;
            # following blocks are usage examples. UI snippets stay in answer.
            question["language"] = "typescript" if number == 22 else "javascript"
            question["solutionCode"] = code_blocks(answer)[0].rstrip("\n")
        questions.append(question)
        assessments.append(dict(id=qid, title=raw["title"], sourceLine=raw["sourceLine"],
                                type=question["type"], difficulty=difficulty))
        if replacements:
            cleanups.append(dict(id=qid, sourceLine=raw["sourceLine"], citations=replacements))
    manifest = dict(schemaVersion=1, id=old["manifest"]["id"] if old else str(uuid.uuid4()),
                    version=old["manifest"]["version"] if old else "1.0.0",
                    hash=old["manifest"]["hash"] if old else f"rev-{DATE}-1",
                    title=title, description=settings["description"], tags=[group])
    same = bool(old and old["manifest"] == manifest and old_questions == questions)
    if old and not same:
        major, minor, patch = map(int, manifest["version"].split("."))
        manifest["version"] = f"{major}.{minor}.{patch + 1}"
        manifest["hash"] = f"rev-{DATE}-" + digest(dump(dict(manifest=manifest, questions=questions)))[:12]
    if not old:
        assert str(uuid.UUID(manifest["id"])) == manifest["id"] and uuid.UUID(manifest["id"]).version == 4
    validate_payload(manifest, questions, source, path)
    payload = {"manifest.json": dump(manifest), "questions.json": dump(questions)}
    dest = ROOT / "courses" / catalog_filename(manifest)
    if dest.exists() and (not old or dest != old["path"]):
        raise ValueError("Refusing to overwrite an unrelated destination")
    directory = OUT / settings["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in payload.items():
        (directory / name).write_bytes(body)
    if not same or dest != old["path"]:
        temporary = dest.with_suffix(".zip.tmp")
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, body in payload.items():
                info = zipfile.ZipInfo(name, (2026, 11, 4, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, body)
        with zipfile.ZipFile(temporary) as archive:
            assert archive.testzip() is None
            assert set(archive.namelist()) == set(payload)
            assert all(archive.read(name) == body for name, body in payload.items())
        temporary.replace(dest)
        if old and old["path"] != dest:
            assert old["path"].resolve().parent == (ROOT / "courses").resolve()
            old["path"].unlink()
    old_by_id = {q["id"]: q for q in old_questions}
    new_by_id = {q["id"]: q for q in questions}
    return dict(source=path.relative_to(ROOT).as_posix(), sourceSha256=digest(path.read_bytes()),
                title=title, id=manifest["id"], status="unchanged" if same else "updated" if old else "created",
                version=manifest["version"], hash=manifest["hash"], zip=dest.relative_to(ROOT).as_posix(),
                zipSha256=digest(dest.read_bytes()), jsonDirectory=directory.relative_to(ROOT).as_posix(),
                questionCount=len(questions), types=dict(Counter(q["type"] for q in questions)),
                difficulties=dict(Counter(q["difficulty"] for q in questions)),
                added=len(new_by_id.keys() - old_by_id.keys()),
                changed=sum(new_by_id[key] != old_by_id[key] for key in new_by_id.keys() & old_by_id.keys()),
                removed=len(old_by_id.keys() - new_by_id.keys()), images=[],
                missingAnswers=[dict(id=q["id"], title=q["title"]) for q in questions if not q["answer"].strip()],
                ambiguousMatches=[], catalogQuestionOverlaps=overlaps, difficultyAssessments=assessments,
                citationConversions=cleanups, sourceCoursePreamble=preamble,
                sourceCodeBlockCount=len(code_blocks(path.read_text(encoding="utf-8-sig"))),
                outputCodeBlockCount=sum(len(code_blocks(q["answer"])) for q in questions))


def write_report(report):
    lines = ["# Курсы Live Coding, Network, Node.js, React, Security и TS", "",
             f"Дата: {DATE}. Курсов: {report['totalCourses']}, вопросов: {report['totalQuestions']}.", "",
             f"Перед сборкой прочитаны manifest.json и questions.json всех {report['existingCatalogChecked']} архивов. "
             f"Посторонних ZIP сохранено без изменений: {report['unrelatedArchivesUnchanged']}.", "",
             "Каждый исходный файл — отдельный курс. Название получено буквальной заменой `--` на `. ` в имени без расширения; регистр и остальные дефисы сохранены.", "",
             "Сложность всех вопросов оценена самостоятельно: Junior — базовые понятия и простые реализации; Middle — применение API и рабочие сценарии; Senior — сложная типизация, конкурентность, архитектура и безопасность.", "",
             "Practice: задания Live Coding и реализации формы, Error Boundary, модального окна и собственных хуков React. Остальные вопросы — theory, включая вопросы с иллюстративным кодом. Решения и примеры полностью сохранены в answer. В Live Coding JS/TS первый блок реализации также помещён в solutionCode; последующие примеры остаются в answer. В UI и React фрагменты кода сохранены вместе с пояснениями в answer. Исходных starterCode нет; новые заготовки и решения не сочинялись.", "",
             f"Иллюстраций нет. {report['citationConversionCount']} служебных favicon заменены текстовыми ссылками на домен из исходной ссылки; подписи сохранены, счётчики вида +1 удалены. Обычные ссылки, библиография и содержимое блоков кода сохранены. Код из ответов не запускался.", "",
             "Общий заголовок Security исключён из вопросов. В исходнике React Hooks перед первым вопросом есть одиночный символ `[`: он учтён как артефакт оформления и не включён в вопросы. Исходный файл сохранён без изменений. Вопросов без ответов и неоднозначных совпадений нет. Совпадения отдельных вопросов между разными темами перечислены в report.json и не использованы для объединения курсов.", "",
             "В ZIP находятся только manifest.json и questions.json в UTF-8 в корне. Полные JSON доступны отдельно по ссылкам ниже. GitHub не использовался для публикации изменений.", "",
             "## Результаты", ""]
    for course in report["courses"]:
        types, levels = course["types"], course["difficulties"]
        folder = course["jsonDirectory"].split("/")[-1]
        status = {"created": "создан", "updated": "обновлён", "unchanged": "без изменений"}[course["status"]]
        lines += [f"### {course['title']}", "",
                  f"ID: `{course['id']}`. Статус: {status}. Версия: `{course['version']}`. Hash: `{course['hash']}`.", "",
                  f"Вопросов: {course['questionCount']}; theory: {types.get('theory', 0)}, practice: {types.get('practice', 0)}; "
                  f"Junior: {levels.get('Junior', 0)}, Middle: {levels.get('Middle', 0)}, Senior: {levels.get('Senior', 0)}.", "",
                  f"Добавлено: {course['added']}, изменено: {course['changed']}, удалено: {course['removed']}. "
                  "Изображения: нет. Вопросы без ответов: нет. Спорные соответствия: нет.", "",
                  f"[Готовый ZIP](../../{course['zip']}) · [manifest.json]({folder}/manifest.json) · [questions.json]({folder}/questions.json)", "",
                  f"Источник: `{course['source']}`. Блоков кода сохранено: {course['outputCodeBlockCount']} из {course['sourceCodeBlockCount']}.", ""]
    if report["errors"]:
        lines += ["## Ошибки", "", *[f"- {e['source']}: {e['error']}" for e in report["errors"]], ""]
    lines += ["Полные оценки сложности, контрольные суммы, совпадения вопросов и преобразования ссылок: [report.json](report.json).", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    paths = sorted(p for p in (ROOT / "answers").glob("*.md") if p.stem.split("--")[0] in GROUPS)
    assert {p.stem for p in paths} == set(CONFIG), "Selected source coverage changed"
    catalog = read_catalog()
    previous_report = None
    if "--resume" in sys.argv:
        previous_report = json.loads((OUT / "report.json").read_text(encoding="utf-8"))
    previous_courses = {c["source"]: c for c in previous_report["courses"]} if previous_report else {}
    source_checksums = {p: digest(p.read_bytes()) for p in (ROOT / "answers").rglob("*") if p.is_file()}
    # Record the initial state before any archive write, including files not selected.
    baseline_path = OUT / "catalog-before.json"
    if not baseline_path.exists():
        baseline_path.write_bytes(dump([dict(path=c["path"].relative_to(ROOT).as_posix(), id=c["manifest"]["id"],
                                             title=c["manifest"]["title"], sha256=c["sha256"]) for c in catalog]))
    results, errors = [], []
    for path in paths:
        try:
            course = build_one(path, CONFIG[path.stem], catalog)
            previous = previous_courses.get(course["source"])
            if (previous and course["status"] == "unchanged" and previous["id"] == course["id"]
                    and previous["zipSha256"] == course["zipSha256"] and previous["sourceSha256"] == course["sourceSha256"]):
                course = previous
            results.append(course)
            print(f"{course['status']}: {course['title']} ({course['questionCount']})")
        except Exception as error:
            errors.append(dict(source=path.relative_to(ROOT).as_posix(), error=str(error)))
            print(f"ERROR: {path.name}: {error}")
    after = read_catalog()
    selected_ids = {course["id"] for course in results}
    unrelated = [entry for entry in catalog if entry["manifest"]["id"] not in selected_ids]
    assert all(entry["path"].exists() and digest(entry["path"].read_bytes()) == entry["sha256"] for entry in unrelated)
    assert all(digest(path.read_bytes()) == checksum for path, checksum in source_checksums.items())
    assert len(after) == len(catalog) + len(selected_ids - {c["manifest"]["id"] for c in catalog})
    assert all(c["sourceCodeBlockCount"] == c["outputCodeBlockCount"] for c in results)
    report = dict(date=DATE, totalCourses=len(results), totalQuestions=sum(c["questionCount"] for c in results),
                  existingCatalogChecked=previous_report["existingCatalogChecked"] if previous_report else len(catalog),
                  unrelatedArchivesUnchanged=len(unrelated),
                  difficultyAssessment="Все уровни оценены самостоятельно; исходники не задают сложность.",
                  sourceFilesUnchanged=True, codeBlocksPreserved=True,
                  citationConversionCount=sum(len(item["citations"]) for c in results for item in c["citationConversions"]),
                  courses=results, errors=errors)
    (OUT / "report.json").write_bytes(dump(report))
    write_report(report)
    print(json.dumps(dict(courses=len(results), questions=report["totalQuestions"], errors=errors), ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
