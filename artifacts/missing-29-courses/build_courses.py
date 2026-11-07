"""Package the final 29 missing courses without executing source examples."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys
import uuid


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "artifacts" / "missing-40-courses" / "build_courses.py"
spec = importlib.util.spec_from_file_location("reviewed_course_builder", BASE)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
b.OUT = OUT
b.DATE = "2026-11-07"  # User's Europe/Moscow client date.
EXPECTED_COURSES = 29


def discover(catalog):
    missing, ambiguous, matched_ids = [], [], set()
    for path in sorted((ROOT / "answers").glob("*.md")):
        text = path.read_text(encoding="utf-8-sig")
        keys = {b.norm(title) for _, title in b.headings_outside_code(text)}
        full_title = path.stem.replace("--", ". ").strip()
        matches = []
        for entry in catalog:
            overlap = len(keys & {b.norm(q["title"]) for q in entry["questions"]})
            if (b.norm(entry["manifest"]["title"]) == b.norm(full_title)
                    or (overlap >= 2 and keys and overlap / len(keys) >= 0.8)):
                matches.append(entry["manifest"]["id"])
        if not matches:
            missing.append(path.name)
        elif len(matches) > 1:
            ambiguous.append({"source": path.name, "matches": matches})
        else:
            matched_ids.add(matches[0])
    return missing, ambiguous, matched_ids


def initialize(plan):
    baseline_path = OUT / "catalog-before.json"
    if baseline_path.exists():
        baseline = b.read_json(baseline_path)
        assert all("id" in item and "sha256" in item for item in plan)
        return baseline
    catalog = b.read_catalog()
    missing, ambiguous, matched = discover(catalog)
    assert not ambiguous, ambiguous
    assert set(missing) == {item["source"] for item in plan}, missing
    assert len(missing) == EXPECTED_COURSES
    assert matched == {entry["manifest"]["id"] for entry in catalog}
    baseline = {
        "date": b.DATE,
        "catalog": [{
            "file": entry["path"].name,
            "id": entry["manifest"]["id"],
            "title": entry["manifest"]["title"],
            "version": entry["manifest"]["version"],
            "hash": entry["manifest"]["hash"],
            "sha256": b.digest(entry["path"].read_bytes()),
        } for entry in catalog],
        "sources": [{"source": path.name, "sha256": b.digest(path.read_bytes())}
                    for path in sorted((ROOT / "answers").glob("*.md"))],
        "questionsHash": b.digest((ROOT / "questions.md").read_bytes()),
        "topicsHash": b.digest((ROOT / "topics.md").read_bytes()),
        "missing": missing,
        "ambiguous": ambiguous,
    }
    used_ids = {entry["manifest"]["id"] for entry in catalog}
    for item in plan:
        identifier = str(uuid.uuid4())
        while identifier in used_ids:
            identifier = str(uuid.uuid4())
        used_ids.add(identifier)
        item["id"] = identifier
        item["sha256"] = b.digest((ROOT / "answers" / item["source"]).read_bytes())
    (OUT / "plan.json").write_bytes(b.dump(plan))
    baseline_path.write_bytes(b.dump(baseline))
    return baseline


def validate_payload(manifest, questions, source, item):
    assert set(manifest) == b.MANIFEST_FIELDS
    assert type(manifest["schemaVersion"]) is int and manifest["schemaVersion"] == 1
    identifier = uuid.UUID(manifest["id"])
    assert identifier.version == 4 and str(identifier) == manifest["id"] == item["id"]
    assert manifest["version"] == "1.0.0"
    assert re.fullmatch(r"[A-Za-z0-9._-]{1,128}", manifest["hash"])
    assert manifest["title"] in (item["title"], item["shortTitle"])
    assert manifest["tags"] == list(dict.fromkeys(manifest["tags"]))
    assert manifest["description"].strip()
    assert len(questions) == len(source) == item["questions"] == 10
    assert len({q["id"] for q in questions}) == len(questions)
    for question, raw in zip(questions, source):
        assert set(question) == b.QUESTION_FIELDS
        assert re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,127}", question["id"])
        assert question["id"] == "q-" + b.digest(raw["title"].encode("utf-8"))[:20]
        assert question["type"] == "theory"
        assert question["difficulty"] in {"Junior", "Middle", "Senior"}
        assert question["title"] == raw["title"]
        assert question["answer"] == raw["answer"]
        assert len(question["tags"]) == len(set(question["tags"])) <= 100
        assert all(isinstance(tag, str) and 0 < len(tag) <= 128 for tag in question["tags"])


b.validate_payload = validate_payload


def check_outputs(plan, baseline):
    b.verify_baseline(baseline)
    catalog = b.read_catalog()
    baseline_ids = {entry["id"] for entry in baseline["catalog"]}
    expected_ids = {item["id"] for item in plan}
    assert len(catalog) == len(baseline["catalog"]) + EXPECTED_COURSES == 178
    assert {entry["manifest"]["id"] for entry in catalog} - baseline_ids == expected_ids
    sections = b.question_sections()
    filename_lengths = []
    for item in plan:
        source = b.parse_answers(ROOT / "answers" / item["source"])
        titles = [question["title"] for question in source]
        matching = [title for title, qs in sections if qs == titles]
        assert matching == [item["section"]]
        manifest = b.read_json(OUT / item["directory"] / "manifest.json")
        questions = b.read_json(OUT / item["directory"] / "questions.json")
        validate_payload(manifest, questions, source, item)
        expected_manifest, expected_questions = b.payload(item, source, matching[0])
        assert manifest == expected_manifest and questions == expected_questions
        existing = b.find_existing(item, source, catalog)
        assert existing is not None and existing["manifest"]["id"] == item["id"]
        b.validate_zip(existing["path"], manifest, questions)
        filename = existing["path"].name
        filename_lengths.append(len(filename))
        encoded_title = filename.split(".name-", 1)[1].split(".hash-", 1)[0]
        encoded_tags = filename.split(".tags-", 1)[1][:-4]
        decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("utf-8")
        assert decode(encoded_title) == manifest["title"]
        assert json.loads(decode(encoded_tags)) == manifest["tags"]
        if manifest["title"] != item["title"]:
            full_manifest = dict(manifest, title=item["title"])
            assert len(b.catalog_filename(full_manifest, validate=False)) > 255
    missing, ambiguous, matched = discover(catalog)
    assert not missing and not ambiguous, (missing, ambiguous)
    assert matched == {entry["manifest"]["id"] for entry in catalog}
    print(f"PASS: {EXPECTED_COURSES} ZIP / 290 theory questions; exact Markdown preservation; "
          f"{len(baseline['catalog'])} original ZIPs unchanged; "
          f"178 unique courses; max filename {max(filename_lengths)} characters; no missing or ambiguous matches")


def write_report(results, errors, baseline, validation_passed):
    levels = Counter()
    for record in results:
        levels.update(record["difficulty"])
    report = {
        "date": b.DATE,
        "timezone": "Europe/Moscow",
        "requestedCourses": EXPECTED_COURSES,
        "completedCourses": len(results),
        "createdCourses": sum(r["status"] == "created" for r in results),
        "unchangedCourses": sum(r["status"] == "unchanged" for r in results),
        "updatedCourses": 0,
        "questionCount": sum(r["questionCount"] for r in results),
        "types": {"theory": sum(r["questionCount"] for r in results), "practice": 0},
        "difficulty": dict(levels),
        "difficultyAssignedEditorially": True,
        "preservedArchives": len(baseline["catalog"]),
        "totalCourses": len(list(b.COURSES.glob("*.zip"))),
        "shortenedTitles": sum(r["titleShortened"] for r in results),
        "validationPassed": validation_passed,
        "remainingMissing": [] if validation_passed else None,
        "errors": errors,
        "ambiguousMatches": baseline["ambiguous"],
        "unanswered": [],
        "courses": results,
    }
    (OUT / "report.json").write_bytes(b.dump(report))
    lines = ["# Сборка 29 недостающих курсов", "",
             f"Дата: {b.DATE}, Europe/Moscow. Обработано {len(results)} из 29 курсов; вопросов: {report['questionCount']}.", "",
             "Все вопросы — theory. Сложность Junior/Middle/Senior назначена самостоятельно по содержанию вопросов.", "",
             "Ответы, пояснения, код и ссылки сохранены полностью. Изображений в выбранных материалах нет.", "",
             f"Прежние {len(baseline['catalog'])} ZIP и все исходные Markdown сохранены без изменений.", "",
             "Названия получены из имён исходных файлов с заменой `--` на `. `. Если полное имя ZIP превышало 255 символов, сокращено название в manifest; Base64URL не обрезался. Полные исходные названия указаны ниже.", ""]
    for record in results:
        level_text = ", ".join(f"{name}: {record['difficulty'].get(name, 0)}" for name in ("Junior", "Middle", "Senior"))
        status = "создан" if record["status"] == "created" else "без изменений"
        directory = Path(record["manifest"]).parent.name
        lines += ["## " + record["section"], "",
                  f"Название: `{record['title']}`. ID: `{record['id']}`.", "",
                  f"Статус: {status}. Версия: `{record['version']}`. Hash: `{record['hash']}`.", "",
                  f"Вопросов: {record['questionCount']} theory, 0 practice; {level_text}. Добавлено: {record['addedQuestions']}, изменено: 0, удалено: 0. Изображения: нет.", "",
                  f"[ZIP](../../{record['archive']}) · [manifest.json]({directory}/manifest.json) · [questions.json]({directory}/questions.json) · [Источник](../../{record['source']})", ""]
        if record["titleShortened"]:
            lines += [f"Полное исходное название: `{record['originalTitle']}`.", ""]
    if errors:
        lines += ["## Ошибки", ""] + [f"- {e['source']}: {e['error']}" for e in errors]
    elif validation_passed:
        lines += ["Проверки пройдены: структура ZIP, CRC, JSON/schema, UUID, ID вопросов, допустимые поля и уровни, формат и декодирование имён, полнота ответов, экспорт JSON, контроль исходников и прежних архивов.", "",
                  "Всего 178 уникальных ZIP-курсов для 178 файлов ответов. Пропусков, неоднозначных соответствий и вопросов без ответов нет.", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return report


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan = b.read_json(OUT / "plan.json")
    assert len(plan) == EXPECTED_COURSES
    assert len({item["source"] for item in plan}) == EXPECTED_COURSES
    assert len({item["directory"] for item in plan}) == EXPECTED_COURSES
    baseline = initialize(plan)
    assert len(baseline["missing"]) == EXPECTED_COURSES and not baseline["ambiguous"]
    if args.check:
        check_outputs(plan, baseline)
        return
    b.verify_baseline(baseline)
    catalog = b.read_catalog()
    sections = b.question_sections()
    baseline_ids = {entry["id"] for entry in baseline["catalog"]}
    results, errors = [], []
    for item in plan:
        try:
            result = b.package_one(item, catalog, sections, baseline_ids)
            results.append(result)
            print(f"{result['status']}: {result['title']} - {result['questionCount']} questions")
        except Exception as error:
            errors.append({"source": item["source"], "error": f"{type(error).__name__}: {error}"})
            print(f"ERROR: {item['source']}: {error}")
    if errors:
        write_report(results, errors, baseline, False)
        raise SystemExit(f"{len(errors)} course(s) failed; see report.json; other courses completed")
    try:
        check_outputs(plan, baseline)
    except Exception as error:
        errors.append({"source": "final verification", "error": f"{type(error).__name__}: {error}"})
        write_report(results, errors, baseline, False)
        raise
    report = write_report(results, errors, baseline, True)
    print(json.dumps({key: report[key] for key in ("createdCourses", "unchangedCourses", "questionCount", "difficulty", "shortenedTitles", "totalCourses", "validationPassed")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
