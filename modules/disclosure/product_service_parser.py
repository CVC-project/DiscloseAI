"""Deterministic extractor for DART II.2 product/service revenue tables.

This deliberately does not use an LLM.  A business-report card must prefer
the table under ``II. 사업의 내용 > 2. 주요 제품 및 서비스`` over free-text
mentions such as research, development, contracts, customers, or periods.
"""

from __future__ import annotations

import re
from typing import Any

_NON_BUSINESS_LABELS = {
    "합계",
    "소계",
    "기타",
    "연구",
    "연구부문",
    "개발",
    "개발부문",
    "연구개발",
    "판매금액",
    "매출액",
    "용역기간",
    "계약기간",
    "비고",
    "구분",
    "품목",
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _number(value: Any) -> float | None:
    raw = _text(value).replace(",", "").replace("%", "")
    if not raw or raw in {"-", "N/A", "n/a"}:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _is_business_label(value: str) -> bool:
    label = _text(value)
    compact_label = re.sub(r"\s+", "", label)
    if (
        len(label) < 2
        or label in _NON_BUSINESS_LABELS
        or compact_label in _NON_BUSINESS_LABELS
    ):
        return False
    if re.fullmatch(r"제?\s*\d+\s*기", label):
        return False
    return not any(
        token in label for token in ("연구부문", "개발부문", "용역기간", "판매금액")
    )


def _find_chapter_ii(parsed: dict[str, Any]) -> dict[str, Any] | None:
    for chapter in parsed.get("chapters") or []:
        title = _text(chapter.get("title"))
        if title.startswith("II.") and "사업의 내용" in title:
            return chapter
    return None


def _find_product_node(chapter: dict[str, Any]) -> dict[str, Any] | None:
    nodes = list(chapter.get("children") or [])
    while nodes:
        node = nodes.pop(0)
        title = _text(node.get("title"))
        if "주요 제품" in title and "서비스" in title:
            return node
        nodes.extend(node.get("children") or [])
    return None


def _share_from_row(row: list[Any]) -> float | None:
    """Return the first annual percentage following a monetary amount.

    DART tables vary in header shape, but product tables conventionally place
    the latest-year amount immediately before its ratio.  Requiring a large
    preceding amount avoids mistaking a year number for a revenue share.
    """
    for index in range(1, len(row)):
        value = _number(row[index])
        previous = _number(row[index - 1])
        if (
            value is not None
            and previous is not None
            and previous > 100
            and 0 <= value <= 100
        ):
            return round(value / 100, 4)
    return None


def extract_product_service_segments(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract reported product/service groups with latest revenue shares.

    Empty is intentional when the report has no suitable revenue table.  The
    caller must then fall back to the business-overview text, rather than
    fabricating a product group from arbitrary section headings.
    """
    chapter = _find_chapter_ii(parsed)
    node = _find_product_node(chapter) if chapter else None
    if node is None:
        return []

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for table in node.get("tables") or []:
        rows = table.get("rows") or []
        for row in rows:
            if not isinstance(row, list) or not row:
                continue
            name = _text(row[0])
            share = _share_from_row(row)
            if share is None or share <= 0 or not _is_business_label(name):
                continue
            if name in seen:
                continue
            seen.add(name)
            result.append(
                {
                    "name": name,
                    "desc": f"사업보고서 주요 제품·서비스 표 기준 매출 비중 {share * 100:.1f}%",
                    "revenue_share": share,
                    "source": "product_service_table",
                    "source_section": "II.2 주요 제품 및 서비스",
                }
            )

    # A product/service table with shares is authoritative.  Small '기타'
    # rows are deliberately excluded from the planet cards.
    return [segment for segment in result if segment["name"] != "기타"][:4]
