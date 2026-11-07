"""Build the 40 missing courses from local Markdown; never execute answer code."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
COURSES = ROOT / "courses"
DATE = "2026-11-07"  # User's Europe/Moscow client date.
MANIFEST_FIELDS = {"schemaVersion", "id", "version", "hash", "title", "description", "tags"}
QUESTION_FIELDS = {"id", "title", "type", "difficulty", "answer", "tags"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(path.read_bytes().decode("utf-8"))


def native_path(path):
    absolute = str(path.resolve())
    if os.name == "nt" and not absolute.startswith("\\\\?\\"):
        return "\\\\?\\" + absolute
    return absolute


def norm(text):
    return re.sub(r"[^\w]", "", text.casefold())


def headings_outside_code(text):
    fence = None
    result = []
    for index, line in enumerate(text.splitlines()):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if match:
            if fence is None:
                fence = (match[1][0], len(match[1]))
            elif match[1][0] == fence[0] and len(match[1]) >= fence[1] and not match[2].strip():
                fence = None
        elif fence is None and line.startswith("# "):
            result.append((index, line[2:]))
    if fence:
        raise ValueError("Unclosed Markdown code fence")
    return result


def parse_answers(path):
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    headings = headings_outside_code(text)
    if not headings or any(line.strip() for line in lines[:headings[0][0]]):
        raise ValueError("Missing question headings or unaccounted source preamble")
    questions = []
    for index, (start, title) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
        answer = "\n".join(lines[start + 1:end]).strip()
        if not title.strip() or not answer:
            raise ValueError("A source question has no answer")
        # This batch contains no illustrations. Do not silently discard one.
        if re.search(r"!\[|<img\b|\[image\]\(", answer, re.I):
            raise ValueError("An image requires explicit asset handling")
        questions.append({"title": title, "answer": answer})
    if len({norm(q["title"]) for q in questions}) != len(questions):
        raise ValueError("Duplicate source questions")
    return questions


def question_sections():
    text = (ROOT / "questions.md").read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    headings = headings_outside_code(text)
    result = []
    for index, (start, title) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
        questions = [line[2:] for line in lines[start + 1:end] if line.startswith(("* ", "- "))]
        result.append((title, questions))
    return result


def read_catalog():
    catalog = []
    for path in sorted(COURSES.glob("*.zip")):
        with zipfile.ZipFile(native_path(path)) as archive:
            if archive.testzip() is not None:
                raise ValueError("Damaged existing archive: " + path.name)
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            questions = json.loads(archive.read("questions.json").decode("utf-8"))
        catalog.append({"path": path, "manifest": manifest, "questions": questions})
    ids = [entry["manifest"]["id"] for entry in catalog]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate course IDs in courses/")
    return catalog


def find_existing(item, source, catalog):
    keys = {norm(q["title"]) for q in source}
    candidate_titles = {norm(item["title"]), norm(item["shortTitle"])}
    matches = []
    for entry in catalog:
        manifest = entry["manifest"]
        overlap = len(keys & {norm(q["title"]) for q in entry["questions"]})
        if (manifest["id"] == item.get("id") or norm(manifest["title"]) in candidate_titles
                or (overlap >= 2 and overlap / len(keys) >= 0.8)):
            matches.append(entry)
    if len(matches) > 1:
        raise ValueError("Ambiguous existing-course match; nothing overwritten")
    return matches[0] if matches else None


def catalog_filename(manifest, validate=True):
    def encode(value):
        return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")
    tags = json.dumps(manifest["tags"], ensure_ascii=False, separators=(",", ":"))
    filename = (f"course.id-{manifest['id']}.name-{encode(manifest['title'])}"
                f".hash-{manifest['hash']}.tags-{encode(tags)}.zip")
    if validate and (len(filename) > 255 or not re.fullmatch(r"[A-Za-z0-9._-]+", filename)):
        raise ValueError("Catalog filename exceeds format limits")
    return filename


def payload(item, source, section_title):
    junior, senior = set(item["junior"]), set(item["senior"])
    if junior & senior or not (junior | senior) <= set(range(1, len(source) + 1)):
        raise ValueError("Invalid editorial difficulty mapping")
    questions = []
    for index, raw in enumerate(source, 1):
        questions.append({
            "id": "q-" + digest(raw["title"].encode("utf-8"))[:20],
            "title": raw["title"],
            "type": "theory",
            "difficulty": "Junior" if index in junior else "Senior" if index in senior else "Middle",
            "answer": raw["answer"],
            "tags": item["tags"],
        })
    manifest = {
        "schemaVersion": 1,
        "id": item["id"],
        "version": "1.0.0",
        "hash": "rev-" + DATE + "-0000000000",
        "title": item["title"],
        "description": "Вопросы и ответы: " + section_title + ".",
        "tags": item["tags"],
    }
    if len(catalog_filename(manifest, validate=False)) > 255:
        manifest["title"] = item["shortTitle"]
    semantic = {key: value for key, value in manifest.items() if key != "hash"}
    manifest["hash"] = "rev-" + DATE + "-" + digest(dump({"manifest": semantic, "questions": questions}))[:10]
    catalog_filename(manifest)
    return manifest, questions


def validate_payload(manifest, questions, source, item):
    assert set(manifest) == MANIFEST_FIELDS
    assert type(manifest["schemaVersion"]) is int and manifest["schemaVersion"] == 1
    identifier = uuid.UUID(manifest["id"])
    assert identifier.version == 4 and str(identifier) == manifest["id"] == item["id"]
    assert manifest["version"] == "1.0.0"
    assert re.fullmatch(r"[A-Za-z0-9._-]{1,128}", manifest["hash"])
    assert manifest["title"] in (item["title"], item["shortTitle"])
    assert manifest["tags"] == list(dict.fromkeys(manifest["tags"]))
    assert manifest["description"].strip()
    assert len(questions) == len(source) == item["questions"] == 12
    assert len({q["id"] for q in questions}) == len(questions)
    for question, raw in zip(questions, source):
        assert set(question) == QUESTION_FIELDS
        assert re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,127}", question["id"])
        assert question["type"] == "theory"
        assert question["difficulty"] in {"Junior", "Middle", "Senior"}
        assert question["title"] == raw["title"]
        assert question["answer"] == raw["answer"]
        assert len(question["tags"]) == len(set(question["tags"])) <= 100
        assert all(isinstance(tag, str) and 0 < len(tag) <= 128 for tag in question["tags"])


def validate_zip(path, manifest, questions):
    assert path.name == catalog_filename(manifest)
    assert path.parent.resolve() == COURSES.resolve()
    with zipfile.ZipFile(native_path(path)) as archive:
        assert archive.namelist() == ["manifest.json", "questions.json"]
        assert archive.testzip() is None
        assert archive.read("manifest.json") == dump(manifest)
        assert archive.read("questions.json") == dump(questions)


def verify_baseline(baseline):
    for record in baseline["catalog"]:
        with open(native_path(COURSES / record["file"]), "rb") as stream:
            assert digest(stream.read()) == record["sha256"], record["file"]
    for record in baseline["sources"]:
        assert digest((ROOT / "answers" / record["source"]).read_bytes()) == record["sha256"], record["source"]
    assert digest((ROOT / "questions.md").read_bytes()) == baseline["questionsHash"]
    assert digest((ROOT / "topics.md").read_bytes()) == baseline["topicsHash"]


def package_one(item, catalog, sections, baseline_ids):
    path = ROOT / "answers" / item["source"]
    assert digest(path.read_bytes()) == item["sha256"]
    source = parse_answers(path)
    matched_sections = [title for title, qs in sections if qs == [q["title"] for q in source]]
    if len(matched_sections) != 1:
        raise ValueError("Question section does not match the complete source")
    existing = find_existing(item, source, catalog)
    if existing and (existing["manifest"]["id"] in baseline_ids or existing["manifest"]["id"] != item["id"]):
        raise ValueError("Source unexpectedly matches a pre-existing course; nothing overwritten")
    manifest, questions = payload(item, source, matched_sections[0])
    validate_payload(manifest, questions, source, item)
    filename = catalog_filename(manifest)
    zip_path = COURSES / filename
    assert zip_path.resolve().parent == COURSES.resolve()
    if existing:
        assert existing["manifest"] == manifest and existing["questions"] == questions
        assert existing["path"].name == filename
        status = "unchanged"
    else:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for member, content in (("manifest.json", manifest), ("questions.json", questions)):
                info = zipfile.ZipInfo(member, date_time=(2026, 11, 7, 12, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, dump(content), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        # Exclusive creation: no existing archive is replaced.
        with open(native_path(zip_path), "xb") as stream:
            stream.write(buffer.getvalue())
        catalog.append({"path": zip_path, "manifest": manifest, "questions": questions})
        status = "created"
    validate_zip(zip_path, manifest, questions)
    exported = OUT / item["directory"]
    exported.mkdir(exist_ok=True)
    (exported / "manifest.json").write_bytes(dump(manifest))
    (exported / "questions.json").write_bytes(dump(questions))
    with open(native_path(zip_path), "rb") as stream:
        archive_hash = digest(stream.read())
    return {
        "source": "answers/" + item["source"], "section": matched_sections[0],
        "title": manifest["title"], "originalTitle": item["title"],
        "titleShortened": manifest["title"] != item["title"], "id": manifest["id"],
        "status": status, "version": manifest["version"], "hash": manifest["hash"],
        "archive": "courses/" + filename, "filenameLength": len(filename), "sha256": archive_hash,
        "manifest": str((exported / "manifest.json").relative_to(ROOT)).replace("\\", "/"),
        "questions": str((exported / "questions.json").relative_to(ROOT)).replace("\\", "/"),
        "questionCount": len(questions), "types": dict(Counter(q["type"] for q in questions)),
        "difficulty": dict(Counter(q["difficulty"] for q in questions)),
        "addedQuestions": len(questions) if status == "created" else 0,
        "changedQuestions": 0, "removedQuestions": 0, "images": [], "unanswered": [],
    }


def write_report(results, errors, baseline):
    levels = Counter()
    for record in results:
        levels.update(record["difficulty"])
    report = {
        "date": DATE, "requestedCourses": 40, "completedCourses": len(results),
        "createdCourses": sum(r["status"] == "created" for r in results),
        "unchangedCourses": sum(r["status"] == "unchanged" for r in results),
        "questionCount": sum(r["questionCount"] for r in results),
        "types": {"theory": sum(r["questionCount"] for r in results), "practice": 0},
        "difficulty": dict(levels), "difficultyAssignedEditorially": True,
        "preservedArchives": len(baseline["catalog"]), "errors": errors,
        "ambiguousMatches": baseline["ambiguous"], "unanswered": [], "courses": results,
    }
    (OUT / "report.json").write_bytes(dump(report))
    lines = ["# Сборка 40 недостающих курсов", "",
             f"Дата: {DATE}, Europe/Moscow. Обработано {len(results)} из 40 курсов, вопросов: {report['questionCount']}.", "",
             "Все вопросы — theory. Сложность Junior/Middle/Senior оценена самостоятельно по содержанию вопросов.", "",
             "Исходные ответы, примеры и ссылки сохранены. Изображений в этих материалах нет. Вопросов без ответа нет.", "",
             f"Прежние {len(baseline['catalog'])} ZIP и исходные Markdown сохранены без изменений.", "",
             "Названия получены из имён исходных файлов с заменой `--` на `. `. Если имя ZIP превышало 255 символов, название сокращено до сохранения полного кодирования Base64URL; исходное название указано ниже.", ""]
    for record in results:
        levels_text = ", ".join(f"{name}: {record['difficulty'].get(name, 0)}" for name in ("Junior", "Middle", "Senior"))
        status = "создан" if record["status"] == "created" else "без изменений"
        directory = Path(record["manifest"]).parent.name
        lines += ["## " + record["section"], "",
                  f"Название: `{record['title']}`. ID: `{record['id']}`.", "",
                  f"Статус: {status}. Версия: `{record['version']}`. Hash: `{record['hash']}`.", "",
                  f"Вопросов: 12 theory, 0 practice; {levels_text}. Добавлено: {record['addedQuestions']}, изменено: 0, удалено: 0. Изображения: нет.", "",
                  f"[ZIP](../../{record['archive']}) · [manifest.json]({directory}/manifest.json) · [questions.json]({directory}/questions.json) · [Источник](../../{record['source']})", ""]
        if record["titleShortened"]:
            lines += ["Полное исходное название: `" + record["originalTitle"] + "`.", ""]
    if errors:
        lines += ["## Ошибки", ""] + [f"- {e['source']}: {e['error']}" for e in errors]
    else:
        lines += ["Проверки завершены: структура и JSON, UUID, ID вопросов, формат имён и декодирование metadata, полнота ответов, контроль исходников и прежних архивов. Неоднозначных соответствий и пропусков нет.", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return report


def check_outputs(plan, baseline):
    verify_baseline(baseline)
    catalog = read_catalog()
    baseline_ids = {r["id"] for r in baseline["catalog"]}
    assert len(catalog) == len(baseline["catalog"]) + len(plan) == 109
    assert {e["manifest"]["id"] for e in catalog} - baseline_ids == {p["id"] for p in plan}
    sections = question_sections()
    for item in plan:
        source = parse_answers(ROOT / "answers" / item["source"])
        section = [title for title, qs in sections if qs == [q["title"] for q in source]]
        assert len(section) == 1
        manifest = read_json(OUT / item["directory"] / "manifest.json")
        questions = read_json(OUT / item["directory"] / "questions.json")
        validate_payload(manifest, questions, source, item)
        expected_manifest, expected_questions = payload(item, source, section[0])
        assert manifest == expected_manifest and questions == expected_questions
        matches = find_existing(item, source, catalog)
        assert matches is not None and matches["manifest"]["id"] == item["id"]
        validate_zip(matches["path"], manifest, questions)
        filename = matches["path"].name
        encoded_title = filename.split(".name-", 1)[1].split(".hash-", 1)[0]
        encoded_tags = filename.split(".tags-", 1)[1][:-4]
        decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("utf-8")
        assert decode(encoded_title) == manifest["title"]
        assert json.loads(decode(encoded_tags)) == manifest["tags"]
    print("PASS: 40 ZIP / 480 theory questions; exact source-answer preservation; 69 original archives and all Markdown unchanged; 109 unique courses; filenames and exported JSON valid")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    baseline = read_json(OUT / "catalog-before.json")
    plan = read_json(OUT / "plan.json")
    assert len(plan) == len(baseline["missing"]) == 40
    assert len({item["directory"] for item in plan}) == 40
    assert baseline["ambiguous"] == []
    if args.check:
        check_outputs(plan, baseline)
        return
    verify_baseline(baseline)
    catalog = read_catalog()
    used_ids = {entry["manifest"]["id"] for entry in catalog}
    for item in plan:
        if "id" not in item:
            identifier = str(uuid.uuid4())
            while identifier in used_ids:
                identifier = str(uuid.uuid4())
            item["id"] = identifier
            used_ids.add(identifier)
    (OUT / "plan.json").write_bytes(dump(plan))
    sections = question_sections()
    baseline_ids = {r["id"] for r in baseline["catalog"]}
    results, errors = [], []
    for item in plan:
        try:
            record = package_one(item, catalog, sections, baseline_ids)
            results.append(record)
            print(f"{record['status']}: {record['title']} — 12 questions")
        except Exception as error:
            errors.append({"source": item["source"], "error": f"{type(error).__name__}: {error}"})
            print(f"ERROR: {item['source']}: {error}")
    report = write_report(results, errors, baseline)
    if errors:
        raise SystemExit(f"{len(errors)} course(s) failed; other courses completed; see report.json")
    check_outputs(plan, baseline)
    print(json.dumps({key: report[key] for key in ("createdCourses", "unchangedCourses", "questionCount", "difficulty")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
