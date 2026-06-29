"""DART 사업보고서 XML → 구조화 JSON 변환 (모듈 ③ 1단계 b).

수집된 사업보고서 XML(dart4.xsd 스키마)을 챕터·섹션 트리로 파싱해
UI가 fetch해서 바로 렌더할 수 있는 JSON으로 저장한다.

XML 구조 (관찰):
  DOCUMENT
    BODY
      COVER          ← 표지 (제목·페이지 정보)
      SECTION-1      ← 챕터 (I. 회사의 개요, II. 사업의 내용, …) — 14개
        TITLE        ← 챕터 제목
        LIBRARY      ← 한 챕터 안의 데이터 모음
        SECTION-2    ← 절 (1., 2., 3., …)
          TITLE
          P          ← 본문 단락
          TABLE      ← 표
          SECTION-3  ← 항 (드물게 추가 depth)

파서는:
  - SECTION-1 단위로 챕터 트리 생성
  - 각 노드에 paragraphs(P 텍스트 배열), tables([{headers, rows}] 배열),
    children(하위 섹션) 부여
  - 빈 노드·공백만 있는 단락 정리
  - 표 셀은 strip + 공백 정규화
  - DART 메타 속성(ATOC, AID, ACLASS 등)은 무시

⚠️ XML 파서 선택: lxml-xml은 일부 문서에서 중간에 끊김. html.parser가 dart4.xsd
   문서에 안정적 (HTML 파서가 케이스 무시·소문자화하므로 find/find_all 시 lower).

저장 경로:
  modules/disclosure/data/fulltext/<corp_code>/<rcept_no>/parsed.json

실행::

    python -m modules.disclosure.fulltext_parser           # 삼성전자 PoC
    python -m modules.disclosure.fulltext_parser <corp_code> <rcept_no>
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from bs4.element import Tag

# DART dart4.xsd는 XML이지만 lxml-xml은 중간에 끊김 — html.parser가 안정.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "modules" / "disclosure" / "data" / "fulltext"


def _clean_text(s: str) -> str:
    """공백 정규화 — 연속 공백·줄바꿈을 단일 공백으로 합치고 양끝 trim."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def _extract_paragraphs(container: Tag) -> list[str]:
    """직속 자식 P 태그만 → 텍스트 배열. 하위 SECTION 내의 P는 제외."""
    out: list[str] = []
    for p in container.find_all("p", recursive=False):
        t = _clean_text(p.get_text(" ", strip=True))
        if t:
            out.append(t)
    return out


def _extract_table(table: Tag) -> dict[str, list[list[str]]] | None:
    """TABLE → {headers: [[..],..], rows: [[..],..]}.

    THEAD 안의 TR → headers, TBODY/직속 TR → rows.
    빈 행·전부 공백 행 제거.
    """

    # DART XML은 표 셀로 ``<TE>`` 를 사용 (HTML의 <td>·<th>가 아님).
    # 일부 표는 표준 <td>/<th>도 쓰니까 셋 다 허용.
    _CELL_TAGS = ["th", "td", "te"]

    def row_cells(tr: Tag) -> list[str]:
        cells = tr.find_all(_CELL_TAGS, recursive=False)
        out = []
        for c in cells:
            t = _clean_text(c.get_text(" ", strip=True))
            out.append(t)
        return out

    headers: list[list[str]] = []
    rows: list[list[str]] = []

    thead = table.find("thead")
    if thead:
        for tr in thead.find_all("tr", recursive=True):
            r = row_cells(tr)
            if any(c for c in r):
                headers.append(r)

    tbody = table.find("tbody")
    body_trs = (
        tbody.find_all("tr", recursive=False)
        if tbody
        else table.find_all("tr", recursive=False)
    )
    for tr in body_trs:
        r = row_cells(tr)
        if any(c for c in r):
            rows.append(r)

    if not headers and not rows:
        return None
    return {"headers": headers, "rows": rows}


def _extract_tables(container: Tag) -> list[dict]:
    """직속 자식 TABLE만 → 표 배열. TABLE-GROUP 안의 TABLE도 평탄화 포함."""
    tables = []
    for t in container.find_all("table", recursive=False):
        parsed = _extract_table(t)
        if parsed:
            tables.append(parsed)
    for tg in container.find_all("table-group", recursive=False):
        for t in tg.find_all("table", recursive=False):
            parsed = _extract_table(t)
            if parsed:
                tables.append(parsed)
    return tables


def _section_title(section: Tag) -> str:
    """직속 TITLE 태그의 텍스트. 없으면 빈 문자열."""
    title = section.find("title", recursive=False)
    if title is None:
        # LIBRARY는 TITLE을 직속 아닌 깊은 곳에 가질 수 있음
        title = section.find("title")
    return _clean_text(title.get_text(" ", strip=True)) if title else ""


def _build_node(section: Tag, level: int) -> dict[str, Any]:
    """SECTION 태그 1개 → dict 노드 (재귀).

    children은 하위 SECTION-N+1 만. LIBRARY는 한 단계 펼쳐서 처리.
    """
    node: dict[str, Any] = {
        "level": level,
        "title": _section_title(section),
        "paragraphs": [],
        "tables": [],
        "children": [],
    }

    # 자식 순회 — 단락·표는 직속만 모음
    for child in section.find_all(recursive=False):
        name = (child.name or "").lower()
        if name in ("title",):
            continue  # 이미 처리
        if name == "p":
            t = _clean_text(child.get_text(" ", strip=True))
            if t:
                node["paragraphs"].append(t)
        elif name in ("table",):
            parsed = _extract_table(child)
            if parsed:
                node["tables"].append(parsed)
        elif name == "table-group":
            for t in child.find_all("table", recursive=False):
                parsed = _extract_table(t)
                if parsed:
                    node["tables"].append(parsed)
        elif name == "library":
            # LIBRARY는 챕터 안의 데이터 묶음 — 한 단계 펼치되 children에 안 넣음
            # (LIBRARY 안의 SECTION-N+1을 챕터 직속처럼 다룸)
            for grand in child.find_all(recursive=False):
                gname = (grand.name or "").lower()
                if gname.startswith("section-"):
                    node["children"].append(_build_node(grand, level + 1))
                elif gname == "p":
                    t = _clean_text(grand.get_text(" ", strip=True))
                    if t:
                        node["paragraphs"].append(t)
                elif gname in ("table",):
                    parsed = _extract_table(grand)
                    if parsed:
                        node["tables"].append(parsed)
        elif name.startswith("section-"):
            node["children"].append(_build_node(child, level + 1))
        # 그 외 (PGBRK·IMG·EXTRACTION·SUMMARY 등)는 무시

    return node


def parse_report(xml_path: Path, meta: dict[str, str] | None = None) -> dict:
    """사업보고서 XML 파일 1개 → 트리 JSON."""
    text = xml_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(text, "html.parser")

    document = soup.find("document")
    body = document.find("body") if document else None
    if body is None:
        raise ValueError(f"<DOCUMENT><BODY> 구조를 찾지 못함: {xml_path}")

    # 챕터 = BODY 직속 SECTION-1
    chapters: list[dict] = []
    for sec1 in body.find_all("section-1", recursive=False):
        chapters.append(_build_node(sec1, level=1))

    company = document.find("company-name")
    doc_name = document.find("document-name")
    out = {
        "corp_code": (
            meta.get("corp_code")
            if meta
            else (company.get("aregcik") if company else None)
        ),
        "corp_name": _clean_text(company.get_text()) if company else None,
        "document_name": _clean_text(doc_name.get_text()) if doc_name else None,
        "rcept_no": meta.get("rcept_no") if meta else None,
        "rcept_dt": meta.get("rcept_dt") if meta else None,
        "report_nm": meta.get("report_nm") if meta else None,
        "chapter_count": len(chapters),
        "chapters": chapters,
    }
    return out


def _summarize_tree(node: dict, depth: int = 0) -> tuple[int, int, int]:
    """노드 통계 — (총 노드, 총 단락, 총 표) 재귀 합산."""
    n, p, t = 1, len(node.get("paragraphs", [])), len(node.get("tables", []))
    for c in node.get("children", []):
        sub = _summarize_tree(c, depth + 1)
        n += sub[0]
        p += sub[1]
        t += sub[2]
    return n, p, t


def main() -> int:
    # CLI: corp_code, rcept_no (없으면 삼성전자 PoC 디폴트)
    if len(sys.argv) >= 3:
        corp_code, rcept_no = sys.argv[1], sys.argv[2]
    else:
        corp_code, rcept_no = "00126380", "20260310002820"

    src_dir = DATA_DIR / corp_code / rcept_no
    xml_path = src_dir / f"{rcept_no}.xml"
    if not xml_path.exists():
        print(f"[ERROR] XML 없음: {xml_path}", file=sys.stderr)
        return 1

    print(f"[INFO] 파싱: {xml_path} ({xml_path.stat().st_size:,} bytes)")
    parsed = parse_report(xml_path, meta={"corp_code": corp_code, "rcept_no": rcept_no})

    # 통계
    total_nodes = total_p = total_t = 0
    for ch in parsed["chapters"]:
        n, p, t = _summarize_tree(ch)
        total_nodes += n
        total_p += p
        total_t += t

    print(
        f"[OK] {parsed['corp_name']} / {parsed['document_name']}\n"
        f"     챕터 {parsed['chapter_count']}, 총 노드 {total_nodes}, "
        f"단락 {total_p}, 표 {total_t}"
    )

    # 챕터 트리 요약 출력 (처음 2단계만)
    print("\n[챕터 트리 요약]")
    for ch in parsed["chapters"]:
        n, p, t = _summarize_tree(ch)
        print(f"  • {ch['title']:<40s}  (단락 {p}, 표 {t}, 노드 {n})")
        for sub in ch.get("children", [])[:8]:
            sp, st = len(sub.get("paragraphs", [])), len(sub.get("tables", []))
            print(f"      └─ {sub['title']:<36s}  (단락 {sp}, 표 {st})")

    # 저장
    out_path = src_dir / "parsed.json"
    out_path.write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[저장] {out_path} ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
