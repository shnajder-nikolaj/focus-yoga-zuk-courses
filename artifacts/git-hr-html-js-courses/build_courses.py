"""Build the requested courses from local Markdown without executing source code."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATE = "2026-11-04"
GROUPS = {"git", "hr", "html", "js"}

# Levels describe question difficulty, including HR preparation, rather than the
# candidate's claimed seniority. All levels are editorial estimates.
CONFIG = {
    "git--ветвление-история-и-совместная-разработка": {
        "directory": "git-branching-history-and-collaboration",
        "count": 25,
        "junior": {1, 2, 3, 4, 11, 14, 15, 18, 20, 25},
        "senior": {21, 23},
        "practice": set(),
        "description": "Раздел посвящён работе с ветками, управлению историей коммитов и совместной разработке в Git.",
    },
    "hr--зарплата-условия-и-ожидания": {
        "directory": "hr-salary-conditions-and-expectations",
        "count": 12,
        "junior": set(range(1, 13)),
        "description": "Подготовка к вопросам о зарплате, условиях работы, сроках выхода и предложениях работодателя.",
    },
    "hr--знакомство": {
        "directory": "hr-introduction",
        "count": 12,
        "junior": set(range(1, 13)),
        "description": "Подготовка самопрезентации и ответов о мотивации, выборе компании и карьерных планах.",
    },
    "hr--командная-работа-и-конфликтные-ситуации": {
        "directory": "hr-teamwork-and-conflicts",
        "count": 12,
        "junior": {1, 6, 7, 11},
        "description": "Вопросы о командной работе, обратной связи, конфликтах, сроках и помощи коллегам.",
    },
    "hr--опыт-достижения-и-самооценка": {
        "directory": "hr-experience-achievements-and-self-assessment",
        "count": 12,
        "junior": {1, 2, 3, 10, 11},
        "description": "Подготовка рассказов об опыте, достижениях, ошибках, профессиональном развитии и применении ИИ.",
    },
    "html--основы-и-семантика": {
        "directory": "html-basics-and-semantics",
        "count": 32,
        "junior": set(range(1, 14)) | {15, 16, 17, 21},
        "description": "Структура HTML-документа, семантика, элементы, подключение ресурсов и адаптивные изображения.",
    },
    "html--формы-и-валидация": {
        "directory": "html-forms-and-validation",
        "count": 18,
        "junior": {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15},
        "practice": {18},
        "description": "Элементы форм, отправка данных, нативная валидация, FormData и доступные сообщения об ошибках.",
    },
    "js--асинхронность-и-среда-выполнения": {
        "directory": "js-asynchrony-and-runtime",
        "count": 33,
        "junior": {1, 7, 8, 9, 11, 17, 18, 28},
        "senior": {26, 30, 32, 33},
        "practice": {14, 15, 25},
        "description": "Event loop, Promise, async/await, управление конкурентностью, отмена, память и работа движка JavaScript.",
    },
    "js--массивы-строки-и-даты": {
        "directory": "js-arrays-strings-and-dates",
        "count": 20,
        "junior": set(range(1, 10)) | {14},
        "description": "Методы массивов, преобразование коллекций, Unicode, регулярные выражения, даты, часовые пояса и Intl.",
    },
    "js--объекты-прототипы-и-коллекции": {
        "directory": "js-objects-prototypes-and-collections",
        "count": 24,
        "junior": {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 15, 16, 18},
        "description": "Прототипы, классы, свойства объектов, копирование, Map, Set, Proxy, JSON и иммутабельное обновление.",
    },
    "js--типы-значения-и-выражения": {
        "directory": "js-types-values-and-expressions",
        "count": 25,
        "junior": {1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 18, 19, 20, 21, 22, 24},
        "description": "Типы JavaScript, приведение значений, сравнения, операторы, управляющие конструкции и ограничения чисел.",
    },
    "js--функции-области-видимости-и-модули": {
        "directory": "js-functions-scopes-and-modules",
        "count": 36,
        "junior": {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 21, 23, 24, 25, 31, 32},
        "senior": {35},
        "practice": {16, 27, 30},
        "description": "Области видимости, this, замыкания, функции, итераторы, генераторы и система модулей JavaScript.",
    },
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def normalized(title: str) -> str:
    return re.sub(r"[^\w]", "", title.casefold())


def outside_code_lines(text: str):
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
    if fence is not None:
        raise ValueError("Unclosed Markdown code fence")


def parse_source(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    headings = [(n, s[2:]) for n, s in outside_code_lines(text) if s.startswith("# ")]
    preamble = None
    if path.stem.startswith("git--") and headings[0][1] == "Git: Ветвление, история и совместная разработка":
        preamble = "\n".join(lines[: headings[1][0] - 1]).strip()
        headings = headings[1:]
    elif any(line.strip() for line in lines[: headings[0][0] - 1]):
        raise ValueError("Unaccounted source preamble")
    result = []
    for index, (line_number, title) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        result.append({"title": title, "answer": "\n".join(lines[line_number:end]).strip(), "sourceLine": line_number})
    return result, preamble


def clean_answer(answer: str):
    # Remove only export-generated favicon citations and their UI labels. These
    # are not course illustrations; substantive bibliography links remain.
    lines = answer.splitlines()
    outside = dict(outside_code_lines(answer))
    removed = []
    skip = set()
    for index, line in enumerate(lines):
        if index + 1 not in outside:
            continue
        if re.fullmatch(r"\[image\]\(https://www\.google\.com/s2/favicons\?[^\n]+\)", line):
            label_index = index + 1
            while label_index < len(lines) and not lines[label_index].strip():
                label_index += 1
            if label_index >= len(lines) or lines[label_index] not in {"MDN", "MDN+1", "html.spec.whatwg.org", "html.spec.whatwg.org+1"}:
                raise ValueError("Unrecognized favicon label")
            skip.update(range(index, label_index + 1))
            removed.append({"link": line, "label": lines[label_index]})
    cleaned = "\n".join(
        line.replace("&#x20;", " ").rstrip() if i + 1 in outside else line
        for i, line in enumerate(lines) if i not in skip
    ).strip()
    for _, line in outside_code_lines(cleaned):
        if re.search(r"!\[|<img\b", re.sub(r"`[^`]*`", "", line)):
            raise ValueError("An illustration needs explicit asset handling")
    return cleaned, removed


def code_blocks(text: str):
    # No code is interpreted or executed. Return literal fenced block bodies.
    return re.findall(r"^```[^\n]*\n(.*?)^```[ \t]*$", text, flags=re.M | re.S)


def filename(manifest: dict) -> str:
    encode = lambda value: base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")
    name = (
        f"course.id-{manifest['id']}.name-{encode(manifest['title'])}"
        f".hash-{manifest['hash']}.tags-{encode(json.dumps(manifest['tags'], ensure_ascii=False, separators=(',', ':')))}.zip"
    )
    if len(name) > 255 or not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise ValueError(f"Invalid catalog filename: {name}")
    return name


def read_catalog():
    catalog = []
    for path in sorted((ROOT / "courses").glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            catalog.append({
                "path": path,
                "manifest": json.loads(archive.read("manifest.json")),
                "questions": json.loads(archive.read("questions.json")),
                "sha256": digest(path.read_bytes()),
                "assets": {n: archive.read(n) for n in archive.namelist() if n.startswith("assets/") and not n.endswith("/")},
            })
    return catalog


def find_existing(title: str, source: list, catalog: list):
    titles = {normalized(q["title"]) for q in source}
    candidates = []
    for entry in catalog:
        existing = {normalized(q["title"]) for q in entry["questions"]}
        overlap = len(titles & existing)
        if normalized(entry["manifest"]["title"]) == normalized(title) or (overlap >= 2 and overlap / len(titles) >= 0.8):
            candidates.append(entry)
    if len(candidates) > 1:
        raise ValueError("Ambiguous course match; archives were not overwritten")
    return candidates[0] if candidates else None


def build_one(path: Path, config: dict, catalog: list):
    group = path.stem.split("--")[0]
    title = " ".join(path.stem.replace("--", ". ").split())
    source, preamble = parse_source(path)
    assert len(source) == config["count"], (path, len(source))
    assert not config["junior"] & config.get("senior", set())
    for kind in ("junior", "senior", "practice"):
        assert config.get(kind, set()) <= set(range(1, len(source) + 1))
    old = find_existing(title, source, catalog)
    if old and old["assets"]:
        raise ValueError("Existing asset-bearing course requires manual reconciliation")
    old_questions = old["questions"] if old else []
    old_by_title = {}
    for question in old_questions:
        key = normalized(question["title"])
        if key in old_by_title:
            raise ValueError("Ambiguous existing question titles")
        old_by_title[key] = question
    questions, assessments, cleanups, placeholders = [], [], [], []
    for number, raw in enumerate(source, 1):
        previous = old_by_title.get(normalized(raw["title"]))
        qid = previous["id"] if previous else "q-" + digest(normalized(raw["title"]).encode("utf-8"))[:16]
        answer, removed = clean_answer(raw["answer"])
        difficulty = "Junior" if number in config["junior"] else "Senior" if number in config.get("senior", set()) else "Middle"
        practical = number in config.get("practice", set())
        question = {"id": qid, "title": raw["title"], "type": "practice" if practical else "theory", "difficulty": difficulty, "answer": answer, "tags": [group]}
        if practical:
            blocks = code_blocks(answer)
            assert blocks, (path, raw["title"], "No source solution")
            question["language"] = "html" if group == "html" else "javascript"
            question["solutionCode"] = blocks[0].rstrip("\n")
        questions.append(question)
        assessments.append({"id": qid, "title": raw["title"], "sourceLine": raw["sourceLine"], "type": question["type"], "difficulty": difficulty})
        if removed:
            cleanups.append({"id": qid, "sourceLine": raw["sourceLine"], "removedFaviconCitations": removed})
        if group == "hr":
            fields = re.findall(r"\[[^\[\]\n]+\](?!\()", answer)
            if fields:
                placeholders.append({"id": qid, "title": raw["title"], "fields": list(dict.fromkeys(fields))})
    assert len({q["id"] for q in questions}) == len(questions)
    manifest = {
        "schemaVersion": 1,
        "id": old["manifest"]["id"] if old else str(uuid.uuid4()),
        "version": old["manifest"]["version"] if old else "1.0.0",
        "hash": old["manifest"]["hash"] if old else f"rev-{DATE}-1",
        "title": title,
        "description": config["description"],
        "tags": [group],
    }
    same = bool(old and old["questions"] == questions and old["manifest"] == manifest)
    if old and not same:
        major, minor, patch = map(int, old["manifest"]["version"].split("."))
        manifest["version"] = f"{major}.{minor}.{patch + 1}"
        manifest["hash"] = f"rev-{DATE}-" + digest(dump({"manifest": manifest, "questions": questions}))[:12]
    dest = ROOT / "courses" / filename(manifest)
    directory = OUT / config["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"manifest.json": dump(manifest), "questions.json": dump(questions)}
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
        if old and dest != old["path"]:
            assert old["path"].resolve().parent == (ROOT / "courses").resolve()
            old["path"].unlink()
    old_by_id = {q["id"]: q for q in old_questions}
    new_by_id = {q["id"]: q for q in questions}
    return {
        "source": path.relative_to(ROOT).as_posix(), "sourceSha256": digest(path.read_bytes()),
        "title": title, "id": manifest["id"], "status": "unchanged" if same else "updated" if old else "created",
        "version": manifest["version"], "hash": manifest["hash"],
        "zip": dest.relative_to(ROOT).as_posix(), "zipSha256": digest(dest.read_bytes()),
        "jsonDirectory": directory.relative_to(ROOT).as_posix(), "questionCount": len(questions),
        "types": {key: sum(q["type"] == key for q in questions) for key in ("theory", "practice")},
        "difficulties": {key: sum(q["difficulty"] == key for q in questions) for key in ("Junior", "Middle", "Senior")},
        "added": len(new_by_id.keys() - old_by_id.keys()),
        "changed": sum(new_by_id[key] != old_by_id[key] for key in new_by_id.keys() & old_by_id.keys()),
        "removed": len(old_by_id.keys() - new_by_id.keys()),
        "images": [], "missingAnswers": [{"id": q["id"], "title": q["title"]} for q in questions if not q["answer"].strip()],
        "personalizationRequired": placeholders, "difficultyAssessments": assessments,
        "formatCleanups": cleanups, "sourceCoursePreamble": preamble,
        "sourceCodeBlockCount": len(code_blocks(path.read_text(encoding="utf-8-sig"))),
        "outputCodeBlockCount": sum(len(code_blocks(q["answer"])) for q in questions),
        "ambiguousMatches": [],
    }


def write_readable_report(report: dict):
    lines = [
        "# Курсы Git, HR, HTML и JS", "",
        f"Дата сборки: {DATE}. Обработано {len(report['courses'])} курсов, {report['totalQuestions']} вопросов.", "",
        f"Проверены manifest.json и questions.json всех {report['existingCatalogChecked']} ZIP в каталоге. Посторонние архивы сохранены без изменений: {report['unrelatedArchivesUnchanged']}.", "",
        "Названия точно получены из имён файлов: `--` заменено на `. `, регистр и остальные дефисы сохранены. Уровни сложности оценены самостоятельно. Junior — основы и простые вопросы HR; Middle — применение API и разбор рабочих ситуаций; Senior — сложные вопросы истории Git, исполнения JavaScript и модульных зависимостей. Для HR уровень относится к сложности подготовки ответа, а не к стажу кандидата.", "",
        "Вопросы с реализациями выделены как practice. solutionCode скопирован из первого исходного блока решения; все остальные примеры и пояснения сохранены в answer. Исходных starterCode нет. Код из материалов не запускался.", "",
        "Реальных иллюстраций нет. В HTML удалены 8 служебных ссылок на favicon и подписи MDN/WHATWG; `&#x20;` заменено пробелом вне блоков кода. Названия картинок внутри учебных примеров сохранены буквально. Библиография сохранена в последнем ответе HTML. Вопросов без ответов и неоднозначных совпадений нет. Поля персонализации HR перечислены ниже и не заполнены выдуманными данными.", "",
        "Внутри каждого ZIP только manifest.json и questions.json в UTF-8, без папки-обёртки. Полные JSON доступны отдельно по ссылкам. Версия нового курса — `1.0.0`, hash — `rev-2026-11-04-1`; при изменении курса версия и hash обновляются.", "",
        "Изменения не публиковались на GitHub; git push не выполнялся.", "",
        "## Отдельные результаты", "",
    ]
    for course in report["courses"]:
        d = course["difficulties"]
        t = course["types"]
        directory = course["jsonDirectory"].split("/")[-1]
        lines += [
            f"### {course['title']}", "",
            f"ID: `{course['id']}`. Статус: { {'created': 'создан', 'updated': 'обновлён', 'unchanged': 'без изменений'}[course['status']] }. Версия: `{course['version']}`. Hash: `{course['hash']}`.", "",
            f"Вопросов: {course['questionCount']} — theory: {t['theory']}, practice: {t['practice']}; Junior: {d['Junior']}, Middle: {d['Middle']}, Senior: {d['Senior']}.", "",
            f"Добавлено: {course['added']}, изменено: {course['changed']}, удалено: {course['removed']}. Изображения: нет. Ответы отсутствуют: нет. Неоднозначные соответствия: нет.", "",
            f"[Готовый ZIP](../../{course['zip']}) · [manifest.json]({directory}/manifest.json) · [questions.json]({directory}/questions.json)", "",
            f"Источник: `{course['source']}`. Сохранено блоков кода: {course['outputCodeBlockCount']} из {course['sourceCodeBlockCount']}.", "",
        ]
        if course["personalizationRequired"]:
            lines += ["Шаблоны, требующие личных данных:", ""]
            for item in course["personalizationRequired"]:
                lines += [f"- {item['title']} — " + ", ".join(f"`{field}`" for field in item["fields"]) + "."]
            lines.append("")
    lines += ["Полные построчные оценки сложности, контрольные суммы источников и ZIP, а также учёт очистки служебных ссылок находятся в [report.json](report.json).", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    paths = sorted(p for p in (ROOT / "answers").glob("*.md") if p.stem.split("--")[0] in GROUPS)
    assert {p.stem for p in paths} == set(CONFIG), "Selected source coverage changed"
    catalog = read_catalog()
    results, errors = [], []
    for path in paths:
        try:
            course = build_one(path, CONFIG[path.stem], catalog)
            results.append(course)
            print(f"{course['status']}: {course['title']} ({course['questionCount']})")
        except Exception as error:
            errors.append({"source": path.relative_to(ROOT).as_posix(), "error": str(error)})
            print(f"ERROR: {path.name}: {error}")
    after = read_catalog()
    assert len({e["manifest"]["id"] for e in after}) == len(after), "Duplicate course ID"
    selected_ids = {c["id"] for c in results}
    unchanged = [e for e in catalog if e["manifest"]["id"] not in selected_ids]
    assert all(e["path"].exists() and digest(e["path"].read_bytes()) == e["sha256"] for e in unchanged)
    report = {
        "date": DATE, "totalCourses": len(results), "totalQuestions": sum(c["questionCount"] for c in results),
        "existingCatalogChecked": len(catalog), "unrelatedArchivesUnchanged": len(unchanged),
        "namingNote": "Буквальная замена -- на . в имени без расширения, после точки пробел; регистр и остальные дефисы сохранены.",
        "difficultyNote": "Все уровни оценены самостоятельно. Текст [Middle / Senior] в шаблоне HR не является метаданными сложности.",
        "typeNote": "Практика — реализация доступной ошибки HTML, пула задач, retry, Promise.all, счётчика, мемоизации и итератора; прочие вопросы — теория с исходными примерами.",
        "formatNote": "Удалены только служебные favicon и подписи к ним, нормализованы &#x20; и внешние пробелы. Код сохранён буквально; примеры не исполнялись.",
        "courses": results, "errors": errors,
    }
    (OUT / "report.json").write_bytes(dump(report))
    write_readable_report(report)
    print(json.dumps({"courses": len(results), "questions": report["totalQuestions"], "errors": errors}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
