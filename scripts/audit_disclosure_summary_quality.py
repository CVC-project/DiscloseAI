from __future__ import annotations

import collections
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "modules" / "disclosure" / "data" / "fulltext"
REPORT_JSON = ROOT / "modules" / "disclosure" / "data" / "summary_quality_report.json"
REPORT_TXT = ROOT / "modules" / "disclosure" / "data" / "summary_quality_report.txt"

MIN_PRODUCTS = 1
MAX_PRODUCTS = 12
MIN_SEGMENTS = 1
MAX_SEGMENTS = 6
MIN_NOTE_LENGTH = 80
MAX_NOTE_LENGTH = 650
MAX_SEGMENT_DESC_LENGTH = 70

BAD_PATTERNS = [
    "품 목",
    "매출유형",
    "구체적용도",
    "비율",
    "금융부채",
    "건설중인자산",
    "법인세",
    "공정가치",
    "상각후원가",
    "감가상각",
    "회계처리",
    "정부보조금",
    "연구과제",
    "효과 및",
    "단위",
    "회사명",
    "판매경로",
    "납품 익월",
    "수 출",
    "제품군",
    "품 목 군",
    "품 목(",
    "매출비중",
    "사업연도",
    "사업년도",
    "사업구분",
    "부문 합계",
    "은행차입금",
    "담보부 은행차입금",
    "무담보 은행차입금",
    "기업은행",
    "씨티은행",
    "금융기관",
    "충당부채",
    "비유동",
    "자본금",
]

EXACT_BAD_LABELS = {
    "매출액",
    "금융자산",
    "외화증권",
    "유가증권",
    "유동",
    "비유동",
    "소속",
    "개량",
    "개선",
    "제작매출액",
}

REVIEW_PATTERNS = [
    "사업부문",
    "사업소",
    "주요사업",
    "리스",
]

GUIDANCE_ONLY_PATTERNS = [
    "사업보고서를 확인하세요",
    "사업보고서를 확인해",
    "원문을 확인하세요",
    "원문을 확인해",
    "확인해주세요",
    "확인해 주세요",
    "먼저 봅니다",
    "먼저 보세요",
]

REPETITIVE_ENDINGS = [
    "확인할 필요가 있습니다",
    "확인해야 합니다",
    "보는 것이 좋습니다",
    "봐야 합니다",
]


def is_bad_label(value: str) -> bool:
    normalized = value.strip()
    if normalized in EXACT_BAD_LABELS:
        return True
    return any(pattern in normalized for pattern in BAD_PATTERNS)


def load_summaries() -> list[dict]:
    summaries = []
    for path in BASE.glob("*/*/summary.json"):
        if "batch_runs" in path.parts:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_path"] = str(path.relative_to(ROOT))
        summaries.append(data)
    return summaries


def audit() -> dict:
    summaries = load_summaries()
    issue_rows = []
    deterministic_issue_rows = []
    manual_review_rows = []
    contract_rows = []
    product_counter = collections.Counter()
    segment_counter = collections.Counter()

    for data in summaries:
        products = data.get("products") or []
        segments = data.get("segments") or []
        note = data.get("investor_notes") or ""
        contract_issue = []

        if len(products) < MIN_PRODUCTS:
            contract_issue.append("products_empty")
        if len(products) > MAX_PRODUCTS:
            contract_issue.append("products_too_many")
        if len(segments) < MIN_SEGMENTS:
            contract_issue.append("segments_empty")
        if len(segments) > MAX_SEGMENTS:
            contract_issue.append("segments_too_many")
        if note and len(note) < MIN_NOTE_LENGTH:
            contract_issue.append("note_too_short")
        if len(note) > MAX_NOTE_LENGTH:
            contract_issue.append("note_too_long")
        if any(pattern in note for pattern in GUIDANCE_ONLY_PATTERNS):
            contract_issue.append("guidance_only_phrase")
        if sum(note.count(pattern) for pattern in REPETITIVE_ENDINGS) >= 2:
            contract_issue.append("repetitive_check_phrase")

        bad_products = []
        review_products = []
        for value in products:
            if is_bad_label(value):
                bad_products.append(value)
                product_counter[value] += 1
            elif any(pattern in value for pattern in REVIEW_PATTERNS) or len(value) > 42:
                review_products.append(value)

        bad_segments = []
        review_segments = []
        for segment in segments:
            name = segment.get("name", "") if isinstance(segment, dict) else str(segment)
            desc = segment.get("desc", "") if isinstance(segment, dict) else ""
            if is_bad_label(name):
                bad_segments.append(name)
                segment_counter[name] += 1
            elif any(pattern in name for pattern in REVIEW_PATTERNS) or len(name) > 42:
                review_segments.append(name)
            if len(desc) > MAX_SEGMENT_DESC_LENGTH:
                contract_issue.append("segment_desc_too_long")

        note_issue = []
        if "사업보고서에서 확인되는 핵심 내용은" in note:
            note_issue.append("old_phrase")
        if "판매경로 판매방법" in note or "매출 및 수주상황 매출실적" in note:
            note_issue.append("raw_heading")
        if len(note) > 650:
            note_issue.append("too_long")
        if note and not note.endswith(("다.", "니다.", "요.", ".")):
            note_issue.append("possibly_cut")

        if bad_products or bad_segments or note_issue:
            row = {
                "corp_code": data.get("corp_code"),
                "corp_name": data.get("corp_name"),
                "model_used": data.get("model_used"),
                "bad_products": bad_products,
                "bad_segments": bad_segments,
                "review_products": review_products,
                "review_segments": review_segments,
                "note_issue": note_issue,
                "note_preview": note[:260],
                "path": data.get("_path"),
            }
            issue_rows.append(row)
            if data.get("model_used") == "deterministic-local-parser-v1":
                deterministic_issue_rows.append(row)
            else:
                manual_review_rows.append(row)
        if contract_issue:
            contract_rows.append(
                {
                    "corp_code": data.get("corp_code"),
                    "corp_name": data.get("corp_name"),
                    "model_used": data.get("model_used"),
                    "contract_issue": sorted(set(contract_issue)),
                    "products_count": len(products),
                    "segments_count": len(segments),
                    "note_length": len(note),
                    "path": data.get("_path"),
                }
            )

    note_lengths = [len(data.get("investor_notes") or "") for data in summaries]
    report = {
        "total": len(summaries),
        "manual_or_llm": sum(1 for x in summaries if x.get("model_used") != "deterministic-local-parser-v1"),
        "deterministic": sum(1 for x in summaries if x.get("model_used") == "deterministic-local-parser-v1"),
        "empty_products": [
            {"corp_code": x.get("corp_code"), "corp_name": x.get("corp_name"), "path": x.get("_path")}
            for x in summaries
            if not x.get("products")
        ],
        "empty_segments": [
            {"corp_code": x.get("corp_code"), "corp_name": x.get("corp_name"), "path": x.get("_path")}
            for x in summaries
            if not x.get("segments")
        ],
        "empty_notes": [
            {"corp_code": x.get("corp_code"), "corp_name": x.get("corp_name"), "path": x.get("_path")}
            for x in summaries
            if not x.get("investor_notes")
        ],
        "note_length": {
            "min": min(note_lengths) if note_lengths else 0,
            "median": statistics.median(note_lengths) if note_lengths else 0,
            "max": max(note_lengths) if note_lengths else 0,
        },
        "issue_count": len(issue_rows),
        "deterministic_issue_count": len(deterministic_issue_rows),
        "manual_review_count": len(manual_review_rows),
        "contract_issue_count": len(contract_rows),
        "review_hint_count": sum(
            1
            for data in summaries
            if any(
                pattern in str(value)
                for pattern in REVIEW_PATTERNS
                for value in (data.get("products") or [])
            )
            or any(
                pattern in (segment.get("name", "") if isinstance(segment, dict) else str(segment))
                for pattern in REVIEW_PATTERNS
                for segment in (data.get("segments") or [])
            )
        ),
        "issues": issue_rows,
        "deterministic_issues": deterministic_issue_rows,
        "manual_review_issues": manual_review_rows,
        "contract_issues": contract_rows,
        "top_bad_products": product_counter.most_common(30),
        "top_bad_segments": segment_counter.most_common(30),
    }
    return report


def main() -> None:
    report = audit()
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "Disclosure summary quality report",
        f"total: {report['total']}",
        f"manual_or_llm: {report['manual_or_llm']}",
        f"deterministic: {report['deterministic']}",
        f"empty_products: {len(report['empty_products'])}",
        f"empty_segments: {len(report['empty_segments'])}",
        f"empty_notes: {len(report['empty_notes'])}",
        f"note_length: {report['note_length']}",
        f"issue_count: {report['issue_count']}",
        f"deterministic_issue_count: {report['deterministic_issue_count']}",
        f"manual_review_count: {report['manual_review_count']}",
        f"contract_issue_count: {report['contract_issue_count']}",
        f"review_hint_count: {report['review_hint_count']}",
        "",
        "Deterministic issue samples:",
    ]
    for row in report["deterministic_issues"][:50]:
        lines.append(
            f"- {row['corp_code']} {row['corp_name']} products={row['bad_products'][:3]} "
            f"segments={row['bad_segments'][:3]} note={row['note_issue']}"
        )
    lines.extend(["", "Manual/LLM review samples:"])
    for row in report["manual_review_issues"][:50]:
        lines.append(
            f"- {row['corp_code']} {row['corp_name']} products={row['bad_products'][:3]} "
            f"segments={row['bad_segments'][:3]} note={row['note_issue']}"
        )
    lines.extend(["", "Summary card contract samples:"])
    for row in report["contract_issues"][:50]:
        lines.append(
            f"- {row['corp_code']} {row['corp_name']} issues={row['contract_issue']} "
            f"products={row['products_count']} segments={row['segments_count']} note_len={row['note_length']}"
        )
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("total", "manual_or_llm", "deterministic", "note_length", "issue_count", "deterministic_issue_count", "manual_review_count", "contract_issue_count")}, ensure_ascii=False, indent=2))
    print(f"empty_products={len(report['empty_products'])} empty_segments={len(report['empty_segments'])} empty_notes={len(report['empty_notes'])}")
    print(f"saved {REPORT_JSON}")
    print(f"saved {REPORT_TXT}")


if __name__ == "__main__":
    main()
