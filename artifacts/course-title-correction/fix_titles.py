"""Correct catalog titles and keep shortened source names in sync.

Run without arguments to preview, --apply to update, --check to verify.
Answer text and every ZIP member except manifest.json are preserved verbatim.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
COURSES = ROOT / "courses"
DATE = "2026-11-07"

# Reviewed short topics: the same wording drives topics, questions, source slug,
# manifest.title, and finally the encoded ZIP filename.
SHORT_TOPICS = {
    "distributed-systems--consistent-hashing-распределение-данных-и-координация":
        "Distributed Systems: Consistent Hashing и координация",
    "performance--профилирование-оптимизация-и-нагрузочное-тестирование-k6-jmeter":
        "Performance: профилирование и нагрузочные тесты, k6 и JMeter",
    "database--реляционная-модель-связи-нормализация-и-проектирование-схем":
        "Database: реляционная модель, связи, нормализация и схемы",
    "system-design--проектирование-платежей-заказов-бронирования-и-инвентаризации":
        "System Design: платежи, заказы, бронирование и инвентаризация",
    "backend--идемпотентность-дедупликация-outbox-inbox-и-надёжная-обработка-событий":
        "Backend: идемпотентность, дедупликация и Outbox/Inbox",
    "system-design--проектирование-чатов-уведомлений-лент-и-real-time-систем":
        "System Design: чаты, уведомления, ленты и Real-time",
    "architecture--saga-pattern-распределённые-бизнес-процессы-и-согласованность":
        "Architecture: Saga, бизнес-процессы и согласованность",
    "architecture--c4-model-adr-технические-решения-и-эволюция-архитектуры":
        "Architecture: C4 model, ADR, решения и эволюция архитектуры",
    "database--миграции-репликация-резервное-копирование-и-восстановление":
        "Database: миграции, репликация, бэкапы и восстановление",
    "architecture--монолит-модульный-монолит-микросервисы-и-архитектурные-компромиссы":
        "Architecture: монолиты, микросервисы и компромиссы",
    "backend--http-сервер-жизненный-цикл-запроса-middleware-и-обработка-ошибок":
        "Backend: HTTP-сервер, цикл запроса, middleware и ошибки",
    "system-design--проектирование-файловых-хранилищ-поиска-и-обработки-медиа":
        "System Design: файловые хранилища, поиск и медиа",
    "messaging--брокеры-очереди-pub-sub-гарантии-доставки-и-обработка-ошибок":
        "Messaging: брокеры, очереди, Pub/Sub, доставка и ошибки",
    "product-engineering--продуктовые-метрики-ab-тестирование-аналитика-и-приоритизация":
        "Product Engineering: метрики, A/B-тесты и приоритизация",
    "system-design--вертикальное-и-горизонтальное-масштабирование-load-balancing":
        "System Design: масштабирование и Load Balancing",
    "software-engineering--технический-долг-code-review-документация-и-владение-сервисами":
        "Software Engineering: техдолг, Code Review и Ownership",
    "system-design--требования-ограничения-компромиссы-и-методология-проектирования":
        "System Design: требования, компромиссы и методология",
    "distributed-systems--распределённые-транзакции-часы-и-порядок-событий":
        "Distributed Systems: транзакции, часы и порядок событий",
    "docker--оптимизация-образов-безопасность-и-управление-ресурсами":
        "Docker: оптимизация образов, безопасность и ресурсы",
    "backend--rest-api-проектирование-версионирование-пагинация-и-фильтрация":
        "Backend: REST API, версии, пагинация и фильтрация",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def norm(value):
    return re.sub(r"[^\w]", "", value.casefold())


def native(path):
    absolute = str(path.resolve())
    return "\\\\?\\" + absolute if os.name == "nt" else absolute


def encode(value):
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def catalog_filename(manifest):
    tags = json.dumps(manifest["tags"], ensure_ascii=False, separators=(",", ":"))
    result = (f"course.id-{manifest['id']}.name-{encode(manifest['title'])}"
              f".hash-{manifest['hash']}.tags-{encode(tags)}.zip")
    if len(result) > 255 or not re.fullmatch(r"[A-Za-z0-9._-]+", result):
        raise ValueError(f"Invalid filename ({len(result)}): {manifest['title']}")
    return result


def catalog():
    result = []
    for path in sorted(COURSES.glob("*.zip")):
        with zipfile.ZipFile(native(path)) as archive:
            assert archive.testzip() is None, path
            entries = [(info, archive.read(info)) for info in archive.infolist()]
            assert len({info.filename for info, _ in entries}) == len(entries), path
            members = {info.filename: data for info, data in entries}
        result.append(dict(path=path, entries=entries, members=members,
                           manifest=json.loads(members["manifest.json"]),
                           questions=json.loads(members["questions.json"])))
    assert len({item["manifest"]["id"] for item in result}) == len(result)
    return result


def topics():
    return [re.sub(r"^\d+\.\s*", "", line)
            for line in (ROOT / "topics.md").read_text(encoding="utf-8-sig").splitlines()
            if re.match(r"^\d+\. ", line)]


def source_references():
    references = defaultdict(set)
    for path in (ROOT / "artifacts").rglob("report.json"):
        for item in json.loads(path.read_text(encoding="utf-8-sig")).get("courses", []):
            if "source" in item and "id" in item and (ROOT / item["source"]).is_file():
                references[item["id"]].add(item["source"])
    return references


def original_topic(path, all_topics):
    matches = [t for t in all_topics if norm(t) == norm(path.stem)]
    if path.stem.startswith("backend--go-python-java-kotlin-и-csharp-"):
        matches = [t for t in all_topics if t.startswith("Backend: Go, Python,")]
    if path.stem == "ts--система-типов":
        matches = ["TS: Система типов"]  # The old topic list only says TS.
    assert len(matches) == 1, (path, matches)
    return matches[0]


def source_slug(old_path, topic):
    prefix = old_path.stem.split("--", 1)[0]
    subtitle = re.sub(r"[^\w.]+", "-", topic.split(": ", 1)[1].casefold()).strip("-")
    return old_path.with_name(f"{prefix}--{subtitle}.md")


def plan_updates(items):
    all_topics, references = topics(), source_references()
    plan = []
    for item in items:
        old = item["manifest"]
        matches = references[old["id"]]
        assert len(matches) == 1, (old["id"], matches)
        source = Path(next(iter(matches)))
        source_bytes = (ROOT / source).read_bytes()
        assert norm(item["questions"][0]["title"]) in norm(source_bytes.decode("utf-8-sig")), source
        old_topic = original_topic(source, all_topics)
        new_topic = SHORT_TOPICS.get(source.stem, old_topic)
        new_source = source_slug(source, new_topic) if source.stem in SHORT_TOPICS else source
        if new_source != source:
            assert not (ROOT / new_source).exists(), new_source
        title = new_topic.replace(": ", ". ", 1).replace("C4 Model", "C4 model")
        manifest = dict(old)
        if old["title"] != title:
            manifest["title"] = title
            version = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", old["version"])
            assert version, old["version"]
            manifest["version"] = f"{version[1]}.{version[2]}.{int(version[3]) + 1}"
            revision = hashlib.sha256(dump({k: v for k, v in manifest.items() if k != "hash"}))
            for name, data in sorted(item["members"].items()):
                if name != "manifest.json":
                    revision.update(name.encode("utf-8"))
                    revision.update(data)
            manifest["hash"] = f"rev-{DATE}-{revision.hexdigest()[:10]}"
        name = catalog_filename(manifest)
        plan.append(dict(item=item, manifest=manifest, filename=name, source=source.as_posix(),
                         newSource=new_source.as_posix(), oldTopic=old_topic, topic=new_topic,
                         sourceSha256=digest(source_bytes), renamedSource=source != new_source))
    assert len({p["source"] for p in plan}) == len(plan)
    assert len({p["newSource"] for p in plan}) == len(plan)
    assert len({p["manifest"]["title"] for p in plan}) == len(plan)
    return plan


def rewrite_topics(data, plan, is_questions=False):
    text = data.decode("utf-8")
    for p in plan:
        if p["topic"] == p["oldTopic"]:
            continue
        prefix = r"(# )" if is_questions else r"(\d+\. )"
        pattern = rf"(?m)^{prefix}{re.escape(p['oldTopic'])}(?=\r?$)"
        text, count = re.subn(pattern, lambda m: m[1] + p["topic"], text)
        assert count == 1, (p["oldTopic"], count)
    return text.encode("utf-8")


def apply_updates(plan):
    baseline_path = OUT / "catalog-before.json"
    if baseline_path.exists():
        raise RuntimeError("Baseline already exists; use --check to verify the completed run")
    baseline = dict(date=DATE, courses=[], documents={})
    for p in plan:
        item, manifest = p["item"], p["manifest"]
        q = item["questions"]
        baseline["courses"].append(dict(
            id=manifest["id"], source=p["source"], newSource=p["newSource"],
            sourceSha256=p["sourceSha256"], oldTopic=p["oldTopic"], topic=p["topic"],
            renamedSource=p["renamedSource"], oldManifest=item["manifest"], manifest=manifest,
            oldArchive=item["path"].name, archive=p["filename"],
            members={name: digest(data) for name, data in item["members"].items()},
            questionCount=len(q), types=dict(Counter(v["type"] for v in q)),
            difficulties=dict(Counter(v["difficulty"] for v in q))))
    documents = {}
    for name, is_questions in (("topics.md", False), ("questions.md", True)):
        old_data = (ROOT / name).read_bytes()
        documents[name] = rewrite_topics(old_data, plan, is_questions)
        baseline["documents"][name] = dict(before=digest(old_data), after=digest(documents[name]))

    # Stage and verify every archive before replacing any catalog file.
    for p in plan:
        item, manifest = p["item"], p["manifest"]
        folder = OUT / manifest["id"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "manifest.json").write_bytes(dump(manifest))
        (folder / "questions.json").write_bytes(item["members"]["questions.json"])
        staging = folder / "course.zip.tmp"
        with zipfile.ZipFile(staging, "w") as archive:
            for info, data in item["entries"]:
                archive.writestr(info, dump(manifest) if info.filename == "manifest.json" else data)
        with zipfile.ZipFile(staging) as archive:
            assert archive.testzip() is None
            assert json.loads(archive.read("manifest.json")) == manifest
            assert {info.filename for info in archive.infolist()} == set(item["members"])
            for name, data in item["members"].items():
                if name != "manifest.json":
                    assert archive.read(name) == data
    baseline_path.write_bytes(dump(baseline))

    for name, data in documents.items():
        (ROOT / name).write_bytes(data)
    for p in plan:
        old_source, new_source = ROOT / p["source"], ROOT / p["newSource"]
        if old_source != new_source:
            assert old_source.resolve().parent == new_source.resolve().parent == (ROOT / "answers").resolve()
            old_source.rename(new_source)
        item, manifest = p["item"], p["manifest"]
        folder = OUT / manifest["id"]
        destination = COURSES / p["filename"]
        assert item["path"].resolve().parent == destination.resolve().parent == COURSES.resolve()
        assert not destination.exists() or destination == item["path"]
        shutil.copyfile(native(item["path"]), folder / "previous.zip.tmp")
        os.replace(folder / "course.zip.tmp", native(destination))
        if item["path"] != destination:
            os.unlink(native(item["path"]))
    return check()


def check():
    baseline = json.loads((OUT / "catalog-before.json").read_bytes())
    items = catalog()
    by_id = {item["manifest"]["id"]: item for item in items}
    assert set(by_id) == {p["id"] for p in baseline["courses"]}
    for name, values in baseline["documents"].items():
        assert digest((ROOT / name).read_bytes()) == values["after"], name
    report_courses = []
    for p in baseline["courses"]:
        item, manifest = by_id[p["id"]], p["manifest"]
        assert item["manifest"] == manifest
        assert item["path"].name == p["archive"] == catalog_filename(manifest)
        assert set(item["members"]) == set(p["members"])
        for name, sha in p["members"].items():
            if name != "manifest.json":
                assert digest(item["members"][name]) == sha, (p["id"], name)
        old = p["oldManifest"]
        assert {k: v for k, v in old.items() if k not in {"title", "hash", "version"}} == {
            k: v for k, v in manifest.items() if k not in {"title", "hash", "version"}}
        assert manifest["version"] != old["version"] and manifest["hash"] != old["hash"]
        source = ROOT / p["newSource"]
        assert source.is_file() and digest(source.read_bytes()) == p["sourceSha256"]
        if p["renamedSource"]:
            assert not (ROOT / p["source"]).exists()
            assert norm(source.stem) == norm(p["topic"])
            assert p["topic"] in topics()
            assert "# " + p["topic"] in (ROOT / "questions.md").read_text(encoding="utf-8")
        folder = OUT / p["id"]
        assert (folder / "manifest.json").read_bytes() == item["members"]["manifest.json"]
        assert (folder / "questions.json").read_bytes() == item["members"]["questions.json"]
        report_courses.append(dict(
            source=p["newSource"], previousSource=p["source"], sourceSha256=p["sourceSha256"],
            title=manifest["title"], previousTitle=old["title"], id=manifest["id"],
            status="updated", version=manifest["version"], hash=manifest["hash"],
            archive="courses/" + item["path"].name, filenameLength=len(item["path"].name),
            shortened=p["renamedSource"], questionCount=p["questionCount"], types=p["types"],
            difficulties=p["difficulties"], addedQuestions=0, changedQuestions=0, removedQuestions=0,
            images=[name for name in item["members"] if name.startswith("assets/")],
            manifest=(folder / "manifest.json").relative_to(ROOT).as_posix(),
            questions=(folder / "questions.json").relative_to(ROOT).as_posix()))
    assert {p["newSource"] for p in baseline["courses"]} == {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "answers").glob("*.md")}
    report = dict(date=DATE, totalCourses=len(items), updatedCourses=len(items),
                  shortenedTitles=sum(p["shortened"] for p in report_courses),
                  totalQuestions=sum(p["questionCount"] for p in report_courses),
                  maxFilenameLength=max(len(item["path"].name) for item in items),
                  answersUnchanged=True, questionPayloadsUnchanged=True, imagesUnchanged=True,
                  idsUnchanged=True, validationPassed=True, courses=report_courses)
    (OUT / "report.json").write_bytes(dump(report))
    lines = ["# Исправление названий курсов", "", f"Дата: {DATE}.", "",
             f"Обновлены {len(items)} курсов; сокращены и синхронизированы {report['shortenedTitles']} названий.",
             f"Сохранены {report['totalQuestions']} вопросов; ответы, код, изображения и ID не изменены.",
             f"Максимальная длина имени ZIP: {report['maxFilenameLength']} из 255 символов.", "",
             "| Название | Статус | Версия | Вопросов | Имя ZIP |", "| --- | --- | --- | ---: | ---: |"]
    for p in report_courses:
        lines.append(f"| {p['title']} | обновлён | {p['version']} | {p['questionCount']} | {p['filenameLength']} |")
    lines += ["", "## Сокращённые названия и переименования источников", ""]
    for p in report_courses:
        if p["shortened"]:
            lines += [f"- `{p['previousSource']}` → `{p['source']}`; название: **{p['title']}**."]
    lines += ["", "Полные manifest.json и questions.json каждого курса находятся в подпапке его ID.",
              "Подробные ID, hash, распределения вопросов, пути и проверка сохранности — в report.json.",
              "Изменено только название темы и метаданные курса; отсутствующие ответы не переоценивались.", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "courses"}, ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        plan = plan_updates(catalog())
        print(json.dumps(dict(courses=len(plan), renamedSources=sum(p["renamedSource"] for p in plan),
                              maxFilenameLength=max(len(p["filename"]) for p in plan)), ensure_ascii=False))
        if args.apply:
            apply_updates(plan)
        else:
            for p in plan:
                if p["renamedSource"]:
                    print(f"{p['manifest']['title']} ({len(p['filename'])}): {p['source']} -> {p['newSource']}")
