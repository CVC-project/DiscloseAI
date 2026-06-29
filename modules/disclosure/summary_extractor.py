"""사업보고서 parsed.json → company_summary 1행 추출 (모듈 ③ 2b PoC).

3탭 "참고서" UI의 데이터 소스를 AI(AWS Bedrock Haiku 4.5)로 생성한다.

작업 분할 (비용 최적화):
  Task A — products·segments  ← 챕터 II "사업의 내용" 만 (~18K tokens)
  Task B — financial_highlights ← 챕터 III 상위 표 7개 (~30K tokens)
  Task C — glossary_terms     ← Bedrock 미사용, 기존 glossary DB로 본문 string match
  Task D — investor_notes     ← A·B 결과만 합성 (~5K tokens)

1종목 예상 비용 ≈ $0.07 (Haiku 4.5, $1/M in · $5/M out 기준)

실행::

    python -m modules.disclosure.summary_extractor                  # 삼성 PoC
    python -m modules.disclosure.summary_extractor <corp> <rcept>
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from .db import get_local_session, init_local_db
from .glossary import GLOSSARY
from .models import CompanySummary

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "modules" / "disclosure" / "data" / "fulltext"

BEDROCK_API_KEY = os.getenv("BEDROCK_API_KEY", "")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
EXTRACT_MODEL = os.getenv(
    "BEDROCK_EXTRACT_MODEL", "anthropic.claude-haiku-4-5-20251001-v1:0"
)


# ──────────────────────────────────────────────────────────────────
# Bedrock 호출 (chat_server와 같은 converse 패턴, JSON 결과 파싱 강화)
# ──────────────────────────────────────────────────────────────────


def _bedrock_url(model: str) -> str:
    model_id = model if model.startswith(("us.", "global.", "arn:")) else f"us.{model}"
    return (
        f"https://bedrock-runtime.{BEDROCK_REGION}.amazonaws.com"
        f"/model/{model_id}/converse"
    )


def _call_bedrock(
    system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2
) -> dict[str, Any]:
    if not BEDROCK_API_KEY:
        raise RuntimeError("BEDROCK_API_KEY가 .env에 없습니다.")
    body = {
        "system": [{"text": system}],
        "messages": [{"role": "user", "content": [{"text": user}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    resp = requests.post(
        _bedrock_url(EXTRACT_MODEL),
        headers={
            "Authorization": f"Bearer {BEDROCK_API_KEY}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    parts = data.get("output", {}).get("message", {}).get("content", [])
    text = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict))
    return {"text": text.strip(), "usage": data.get("usage", {})}


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}|\[[\s\S]*\]")


def _parse_json_lenient(text: str, default):
    """모델이 ```json 펜스를 두르거나 앞뒤 잡설을 붙여도 JSON만 빼내 파싱."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _JSON_BLOCK.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    print(f"[WARN] JSON 파싱 실패, 기본값 반환. 앞 200자:\n  {text[:200]!r}")
    return default


# ──────────────────────────────────────────────────────────────────
# 챕터·표 → 프롬프트용 텍스트 변환
# ──────────────────────────────────────────────────────────────────


def _find_chapter(parsed: dict, title_prefix: str) -> dict | None:
    for ch in parsed.get("chapters", []):
        if ch.get("title", "").startswith(title_prefix):
            return ch
    return None


def _table_to_md(t: dict) -> str:
    lines = []
    for row in t.get("headers", []):
        lines.append("| " + " | ".join(row) + " |")
    if t.get("headers"):
        cols = max((len(r) for r in t["headers"]), default=0)
        lines.append("|" + "|".join(["---"] * cols) + "|")
    for row in t.get("rows", []):
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _node_to_text(node: dict, *, max_tables: int | None = None) -> str:
    """노드 → 단락·표 합쳐 plain text. max_tables가 정해지면 표 개수 제한."""
    out: list[str] = []
    title = node.get("title")
    if title:
        out.append(f"### {title}")
    for p in node.get("paragraphs", []):
        out.append(p)
    tables = node.get("tables", [])
    if max_tables is not None:
        tables = tables[:max_tables]
    for t in tables:
        out.append(_table_to_md(t))
    for ch in node.get("children", []):
        sub_max = None if max_tables is None else max(0, max_tables - len(tables))
        out.append(_node_to_text(ch, max_tables=sub_max))
    return "\n\n".join(s for s in out if s)


# ──────────────────────────────────────────────────────────────────
# Task A — products + segments (챕터 II "사업의 내용")
# ──────────────────────────────────────────────────────────────────

_PROMPT_PRODUCTS = """당신은 한국 상장사 사업보고서를 분석해 초보 투자자가 알아볼 수 있는
"제품/서비스 목록"과 "사업부문" 정보를 추출합니다.

다음 JSON 스키마를 그대로 출력하세요. 다른 문장·코드펜스 금지.

{
  "products": ["대표 제품·서비스 이름들 (최대 12개)"],
  "segments": [
    {
      "name": "사업부문명",
      "desc": "한 줄 설명 (40자 내외)",
      "revenue_share": 0.0  // 매출 비중 0~1, 모르면 null
    }
  ]
}

규칙:
- products는 일반 투자자가 들었을 때 알아챌 수 있는 이름을 우선 (예: "갤럭시", "DDR5", "HBM").
- segments는 보고서가 명시한 사업부문 (예: "DX부문", "DS부문") 그대로.
- revenue_share는 본문에 숫자가 있을 때만 채우고, 없으면 null."""


def task_products_segments(parsed: dict) -> dict:
    ch = _find_chapter(parsed, "II.")
    if ch is None:
        print("[WARN] 챕터 II 없음 → Task A 건너뜀")
        return {"products": [], "segments": []}
    text = _node_to_text(ch)[:60000]  # 안전 상한
    res = _call_bedrock(_PROMPT_PRODUCTS, text, max_tokens=1200)
    print(f"[Task A] usage={res['usage']}")
    return _parse_json_lenient(res["text"], {"products": [], "segments": []})


# ──────────────────────────────────────────────────────────────────
# Task B — financial_highlights (챕터 III 상위 표 7개)
# ──────────────────────────────────────────────────────────────────

_PROMPT_FIN = """당신은 한국 상장사 사업보고서의 재무 정보에서 초보 투자자가 알아야 할
핵심 항목 5~8개를 추출합니다.

다음 JSON 배열만 출력하세요. 다른 문장·코드펜스 금지.

[
  {
    "item": "매출액(연결)",       // 항목명
    "value": "302조 2,300억",     // 단위까지 사람이 읽기 좋게 (원·% 등)
    "yoy": "+8.1%",              // 전년 대비, 알 수 없으면 null
    "explain": "한 줄 풀이 — 어떤 의미인지, 어떻게 봐야 하는지 (60자 내외)"
  }
]

권장 항목: 매출액·영업이익·당기순이익·총자산·부채비율·ROE·영업현금흐름 중 본문에서
실제 확인되는 것. value는 본문 수치를 가공해 사람이 한눈에 보기 좋게."""


def _select_finance_tables(chapter_iii: dict) -> str:
    """챕터 III를 보내되 표는 상위 7개만 — 요약재무·연결재무상태표 위주 포함."""
    txt = _node_to_text(chapter_iii, max_tables=7)
    return txt[:90000]


def task_financial_highlights(parsed: dict) -> list[dict]:
    ch = _find_chapter(parsed, "III.")
    if ch is None:
        print("[WARN] 챕터 III 없음 → Task B 건너뜀")
        return []
    text = _select_finance_tables(ch)
    res = _call_bedrock(_PROMPT_FIN, text, max_tokens=1500)
    print(f"[Task B] usage={res['usage']}")
    out = _parse_json_lenient(res["text"], [])
    return out if isinstance(out, list) else []


# ──────────────────────────────────────────────────────────────────
# Task C — glossary_terms (로컬 string match, Bedrock 미사용)
# ──────────────────────────────────────────────────────────────────


def task_glossary_terms(parsed: dict) -> list[str]:
    """본문 전체 텍스트에 등장하는 glossary label만 추출 (중복 제거, 정렬)."""
    blob_parts: list[str] = []
    def walk(node):
        blob_parts.extend(node.get("paragraphs", []))
        for t in node.get("tables", []):
            for row in t.get("headers", []) + t.get("rows", []):
                blob_parts.extend(row)
        for c in node.get("children", []):
            walk(c)
    for ch in parsed.get("chapters", []):
        walk(ch)
    blob = "\n".join(blob_parts)
    found = sorted({e.label for e in GLOSSARY.values() if e.label and e.label in blob})
    print(f"[Task C] 본문에서 발견된 용어 {len(found)}개")
    return found


# ──────────────────────────────────────────────────────────────────
# Task D — investor_notes (A·B 결과 + 회사명만 합성)
# ──────────────────────────────────────────────────────────────────

_PROMPT_NOTES = """당신은 주식 투자가 처음인 사람에게 회사를 200~300자로 풀어 설명합니다.

아래 JSON에 추출된 사업·재무 정보를 근거로, 한 단락(줄바꿈 없음)으로 작성하세요.
- 친절하고 평이한 한국어
- 어려운 회계·재무 용어는 쉬운 말로 한 줄 풀이
- "사세요/파세요/매수 추천" 같은 투자 조언 금지
- 항상 "과거 공시 기반 참고 정보"라는 톤

출력은 단락 텍스트 하나만 (JSON 아님, 따옴표·머리말 없이)."""


def task_investor_notes(corp_name: str, prods: dict, fins: list[dict]) -> str:
    payload = json.dumps(
        {"corp_name": corp_name, "products_segments": prods, "financials": fins},
        ensure_ascii=False,
    )
    res = _call_bedrock(_PROMPT_NOTES, payload, max_tokens=800, temperature=0.4)
    print(f"[Task D] usage={res['usage']}")
    return res["text"].strip()


# ──────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────


def _source_version(path: Path) -> str:
    st = path.stat()
    h = hashlib.md5(f"{st.st_mtime_ns}-{st.st_size}".encode()).hexdigest()[:12]
    return f"{st.st_size}-{h}"


def extract_for_company(corp_code: str, rcept_no: str) -> CompanySummary:
    parsed_path = DATA_DIR / corp_code / rcept_no / "parsed.json"
    if not parsed_path.exists():
        raise FileNotFoundError(f"parsed.json 없음: {parsed_path}")

    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    corp_name = parsed.get("corp_name") or "(이름 없음)"
    print(f"\n{'=' * 60}\n  {corp_name} ({corp_code}) — {rcept_no}\n{'=' * 60}")

    prods = task_products_segments(parsed)
    fins = task_financial_highlights(parsed)
    terms = task_glossary_terms(parsed)
    notes = task_investor_notes(corp_name, prods, fins)

    init_local_db()
    s = get_local_session()
    row = s.query(CompanySummary).filter_by(corp_code=corp_code).first()
    if row is None:
        row = CompanySummary(corp_code=corp_code)
        s.add(row)
    row.corp_name = corp_name
    row.rcept_no = rcept_no
    row.rcept_dt = parsed.get("rcept_dt")
    row.products = json.dumps(prods.get("products", []), ensure_ascii=False)
    row.segments = json.dumps(prods.get("segments", []), ensure_ascii=False)
    row.financial_highlights = json.dumps(fins, ensure_ascii=False)
    row.glossary_terms = json.dumps(terms, ensure_ascii=False)
    row.investor_notes = notes
    row.model_used = EXTRACT_MODEL
    row.source_version = _source_version(parsed_path)
    row.generated_at = date.today()
    s.commit()
    s.refresh(row)
    print(f"\n[OK] company_summary id={row.id} 저장 완료")
    print(f"  products({len(prods.get('products', []))}): "
          f"{prods.get('products', [])[:6]}...")
    print(f"  segments({len(prods.get('segments', []))}): "
          f"{[s['name'] for s in prods.get('segments', []) if 'name' in s]}")
    print(f"  financials({len(fins)})")
    print(f"  glossary_terms({len(terms)})")
    print(f"\n[investor_notes]\n{notes}")

    # UI(firm.html 참고서 패널)가 fetch하는 JSON 파일도 옆에 둠 — DB는 integration에서
    # 직접 못 읽음(데이터 모듈 간 import 금지). parsed.json 폴더 안에 summary.json.
    export_path = export_json(row, parsed_path.parent)
    print(f"[OK] {export_path} ({export_path.stat().st_size:,} bytes)")

    s.close()
    return row


def export_json(row: CompanySummary, dest_dir: Path) -> Path:
    """CompanySummary 1행 → summary.json (UI가 fetch).

    firm.html의 참고서 패널이 ``modules/disclosure/data/fulltext/<corp>/<rcept>/
    summary.json``을 fetch 해 재무 카드·요약 단락·용어 목록을 렌더한다.
    """
    payload = {
        "corp_code": row.corp_code,
        "corp_name": row.corp_name,
        "rcept_no": row.rcept_no,
        "rcept_dt": row.rcept_dt,
        "products": row.get_products(),
        "segments": row.get_segments(),
        "financial_highlights": row.get_financial_highlights(),
        "kam": row.get_kam(),
        "emphasis": row.get_emphasis(),
        "glossary_terms": row.get_glossary_terms(),
        "investor_notes": row.investor_notes or "",
        "model_used": row.model_used,
        "source_version": row.source_version,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / "summary.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    if len(sys.argv) >= 3:
        corp_code, rcept_no = sys.argv[1], sys.argv[2]
    else:
        corp_code, rcept_no = "00126380", "20260310002820"
    try:
        extract_for_company(corp_code, rcept_no)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
