"""Package the next 40 missing courses, reusing the reviewed catalog builder."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "artifacts" / "missing-40-courses" / "build_courses.py"
spec = importlib.util.spec_from_file_location("reviewed_course_builder", BASE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
builder.OUT = OUT


def check_outputs(plan, baseline):
    """Verify complete sources, exported JSON, new ZIPs and preserved catalog."""
    builder.verify_baseline(baseline)
    catalog = builder.read_catalog()
    baseline_ids = {item["id"] for item in baseline["catalog"]}
    expected_ids = {item["id"] for item in plan}
    assert len(catalog) == len(baseline["catalog"]) + len(plan)
    assert {item["manifest"]["id"] for item in catalog} - baseline_ids == expected_ids
    sections = builder.question_sections()
    for item in plan:
        source = builder.parse_answers(ROOT / "answers" / item["source"])
        titles = [question["title"] for question in source]
        matching_sections = [title for title, questions in sections if questions == titles]
        assert len(matching_sections) == 1
        manifest = builder.read_json(OUT / item["directory"] / "manifest.json")
        questions = builder.read_json(OUT / item["directory"] / "questions.json")
        builder.validate_payload(manifest, questions, source, item)
        expected_manifest, expected_questions = builder.payload(item, source, matching_sections[0])
        assert manifest == expected_manifest and questions == expected_questions
        existing = builder.find_existing(item, source, catalog)
        assert existing is not None and existing["manifest"]["id"] == item["id"]
        builder.validate_zip(existing["path"], manifest, questions)
        filename = existing["path"].name
        title64 = filename.split(".name-", 1)[1].split(".hash-", 1)[0]
        tags64 = filename.split(".tags-", 1)[1][:-4]
        decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("utf-8")
        assert decode(title64) == manifest["title"]
        assert json.loads(decode(tags64)) == manifest["tags"]

    # Discovery uses headings and catalog content for legacy source formats;
    # strict source parsing is required for each newly packaged course above.
    matched_ids = set()
    missing, ambiguous = [], []
    for path in sorted((ROOT / "answers").glob("*.md")):
        text = path.read_text(encoding="utf-8-sig")
        keys = {builder.norm(title) for _, title in builder.headings_outside_code(text)}
        full_title = path.stem.replace("--", ". ").strip()
        matches = []
        for entry in catalog:
            overlap = len(keys & {builder.norm(q["title"]) for q in entry["questions"]})
            if (builder.norm(entry["manifest"]["title"]) == builder.norm(full_title)
                    or (overlap >= 2 and keys and overlap / len(keys) >= 0.8)):
                matches.append(entry["manifest"]["id"])
        if not matches:
            missing.append(path.name)
        elif len(matches) > 1:
            ambiguous.append(path.name)
        else:
            matched_ids.add(matches[0])
    assert not missing, missing
    assert not ambiguous, ambiguous
    assert matched_ids == {entry["manifest"]["id"] for entry in catalog}
    print(f"PASS: {len(plan)} ZIP / {sum(p['questions'] for p in plan)} theory questions; "
          f"{len(baseline['catalog'])} original archives and all Markdown unchanged; "
          f"{len(catalog)} unique courses; no missing or ambiguous source matches")


builder.check_outputs = check_outputs


if __name__ == "__main__":
    builder.main()
