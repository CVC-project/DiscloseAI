"""T2 서술문 LLM 추출기 — SGLang 배치 (valuechain/PLAN.md §3.2·§3.5, 하네스 C의 씨앗).

흐름 (C1~C4 축소판 — B0 제로샷 파일럿과 본 배치가 공유):
  VcChunk(후보) → 패스1 추출(§3.2 스키마, xgrammar 강제, greedy)
    → 패스2 검증(추출→판별, §3.5) → 후처리 검문:
       ① evidence 원문 exact-match 실패 즉시 드롭 (C3 ①)
       ② 엔티티 링킹 방어층 (transform/CLAUDE.md 5층 준용 — T2 적용분):
          L1 모호 약칭 게이트(+실존 상장사 정식명 화이트리스트) /
          L2 쌍 블록리스트 / L5 LinkFailQueue (L3·L4는 지분율 전용 — T2 비대상)
       ③ status=active만 엣지화 (past/planned는 §3.2 오염 차단 취지대로 제외)
       ④ 익명 관계는 엣지화 이연(T1 리더 결정 B 준용) / 자기 참조 무시
    → ValueChainEdge(T2) UNIQUE 키 upsert (D12 멱등, related_party._upsert_edge 준용)

엔드포인트는 shared/config의 SGLang 설정(REPORT_LLM_*)을 공유한다 — 서버 접속정보는
코드·문서에 기재 금지(보안 규칙), URL·모델명은 전부 환경변수.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor

import requests

from modules.relation.storage.models import VcChunk
from modules.relation.valuechain.extract.linking import (  # noqa: F401 — 하위호환 재노출
    GuardContext,
    blocked_pair,
    build_guard_context,
    link_counterparty,
)
from modules.relation.valuechain.extract.related_party import _upsert_edge
from shared.config import REPORT_LLM_BASE_URL, REPORT_LLM_MODEL

logger = logging.getLogger(__name__)

EXTRACTOR_VER = "t2-zs-pilot-v1|Qwen3-32B-AWQ|prompt_v1|tau=none"

# §3.2 라벨 스키마 — 교사·학생 공통, SGLang xgrammar(json_schema)로 디코딩 강제
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "counterparty": {"type": ["string", "null"]},
                    "anonymous": {"type": "boolean"},
                    "direction": {
                        "type": "string",
                        "enum": ["customer", "supplier", "competitor", "raw_material"],
                    },
                    "status": {"type": "string", "enum": ["active", "past", "planned"]},
                    "evidence": {"type": "string"},
                    "sector_hint": {"type": ["string", "null"]},
                },
                "required": [
                    "counterparty", "anonymous", "direction",
                    "status", "evidence", "sector_hint",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["relations"],
    "additionalProperties": False,
}

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "supported": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["supported", "confidence"],
    "additionalProperties": False,
}

_EXTRACT_SYSTEM = """너는 한국 상장사 사업보고서 서술문에서 밸류체인 관계를 추출하는 도구다.
앵커 기업(보고서 작성 주체) 관점에서, 주어진 원문 조각에 명시된 거래·경쟁 관계만 추출한다.

direction 정의 (앵커 기준):
- customer: 상대가 앵커의 고객/매출처 (앵커가 판매·납품하는 대상)
- supplier: 상대가 앵커의 공급처/매입처 (앵커가 구매·조달하는 대상)
- raw_material: 상대가 앵커에 원재료·원자재를 공급
- competitor: 상대가 앵커의 경쟁사

규칙:
1. counterparty는 원문에 등장한 표기 그대로. 원문에 없는 이름을 만들면 오답이다.
2. 상대가 익명("주요 고객", "글로벌 완성차 업체" 등)이면 counterparty=null, anonymous=true.
3. evidence는 관계의 근거가 되는 원문 문장을 한 글자도 바꾸지 말고 그대로 복사한다.
4. status: 현재 지속 관계=active, 과거 관계("과거 납품", "종료")=past, 계획·예정=planned.
5. 산업 동향 서술 속 단순 타사명 언급, 자사 계열사 나열, 제품·기술명은 관계가 아니다.
6. 관계가 없으면 relations를 빈 배열로 — 억지로 만들지 않는 것이 정답이다."""

_VERIFY_SYSTEM = """너는 관계 추출 결과를 검증하는 판별기다. 주어진 근거 문장이
(상대, 방향, 현재성) 주장을 실제로 지지하는지만 판단한다. 문장에 명시되지 않은
추측·상식으로 보충하면 안 된다. supported가 참일 때 confidence는 그 확신도(0~1)다."""

_EDGE_MAP = {  # direction → (edge_type, 물자 흐름상 앵커가 src인가)
    "customer": ("customer", True),        # 앵커(공급자) → 고객
    "supplier": ("supply", False),         # 공급처 → 앵커(수요자)
    "raw_material": ("raw_material", False),
    "competitor": ("competition", True),   # 무방향 관례 — 앵커를 src로
}


def _call_llm(system: str, user: str, schema: dict, schema_name: str,
              max_tokens: int, timeout: int = 180) -> dict | None:
    """SGLang OpenAI 호환 호출 — greedy + xgrammar json_schema 강제. 실패 시 None."""
    payload = {
        "model": REPORT_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        },
        # Qwen3 하이브리드 사고모드 비활성 (§3.4 — 추출 과제 불필요 + 처리량 수 배 하락)
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        r = requests.post(f"{REPORT_LLM_BASE_URL.rstrip('/')}/chat/completions",
                          json=payload, timeout=timeout)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:  # noqa: BLE001 — 배치는 개별 실패를 집계하고 계속
        logger.warning(f"LLM 호출 실패({schema_name}): {type(e).__name__}: {e}")
        return None


def extract_chunk(anchor_name: str, chunk_text: str) -> dict | None:
    """패스1: 청크 → relations JSON (스키마 강제). 실패 시 None."""
    user = f"앵커 기업: {anchor_name}\n\n원문:\n{chunk_text}"
    # max_tokens 2048: 관계 다수 청크에서 1024는 JSON 중간 절단 실측(B0 파일럿 1차)
    return _call_llm(_EXTRACT_SYSTEM, user, EXTRACTION_SCHEMA, "vc_relations", 2048)


def verify_relation(rel: dict) -> dict | None:
    """패스2: evidence가 (상대, 방향, 현재성)을 지지하는가 → supported/confidence."""
    cp = rel.get("counterparty") or "(익명)"
    user = (
        f"근거 문장: {rel.get('evidence', '')}\n\n"
        f"주장: 상대={cp}, 방향={rel.get('direction')}, 현재성={rel.get('status')}\n"
        "이 근거 문장이 위 주장을 지지하는가?"
    )
    return _call_llm(_VERIFY_SYSTEM, user, VERIFY_SCHEMA, "vc_verify", 128)


# GuardContext·build_guard_context·link_counterparty는 linking.py로 이관(2026-07-29
# U-확대 — T1 주석 파서와 공용). 이 모듈의 기존 참조·테스트는 상단 재노출 import로 유지.


def apply_relations(session, ctx: GuardContext, chunk: VcChunk, anchor_name: str,
                    as_of: int | None, result: dict) -> list[dict]:
    """패스1 결과 1건: 패스2 검증 → 검문 → T2 upsert. 검수용 레코드 반환."""
    records = []
    for rel in result.get("relations", []):
        ctx.counters["extracted"] += 1
        rec = {"chunk_id": chunk.chunk_id, "anchor": anchor_name, **rel,
               "verdict": None}
        records.append(rec)

        # C3 ①: evidence 원문 exact-match — 실패 즉시 드롭
        ev = (rel.get("evidence") or "").strip()
        if not ev or ev not in chunk.text:
            ctx.counters["evidence_mismatch"] += 1
            rec["verdict"] = "evidence_mismatch"
            continue

        # 패스2 검증 (§3.5) — no 판정 폐기
        v = verify_relation(rel)
        if v is None:
            ctx.counters["llm_error"] += 1
            rec["verdict"] = "verify_error"
            continue
        rec["confidence"] = v.get("confidence")
        if not v.get("supported"):
            ctx.counters["verify_rejected"] += 1
            rec["verdict"] = "verify_rejected"
            continue

        if rel.get("anonymous") or not rel.get("counterparty"):
            ctx.counters["anonymous"] += 1
            rec["verdict"] = "anonymous"
            continue
        if rel.get("status") != "active":
            ctx.counters["not_active"] += 1
            rec["verdict"] = "not_active"
            continue

        corp = link_counterparty(session, ctx, rel["counterparty"], chunk.chunk_id)
        if not corp:
            rec["verdict"] = "link_failed_or_queued"
            continue
        if corp == chunk.corp_code:
            ctx.counters["self_ref"] += 1
            rec["verdict"] = "self_ref"
            continue

        edge_type, anchor_first = _EDGE_MAP[rel["direction"]]
        src, dst = ((chunk.corp_code, corp) if anchor_first else (corp, chunk.corp_code))

        # L2: 쌍 블록리스트 (linking.blocked_pair — filters.apply와 동일 키, 양방향)
        if blocked_pair(ctx, src, dst):
            ctx.counters["l2_blocklisted"] += 1
            rec["verdict"] = "l2_blocklisted"
            continue

        _upsert_edge(
            session,
            src_corp=src, dst_corp=dst, edge_type=edge_type,
            tier="T2", source_kind="biz_prose", rcept_no=chunk.rcept_no,
            provenance=f"{chunk.section_key} · {chunk.chunk_id} · {ev}",
            amount=None, as_of=as_of,
            extractor_ver=EXTRACTOR_VER, confidence=v.get("confidence"),
        )
        ctx.counters["edges_kept"] += 1
        rec["verdict"] = "edge"
    return records


def run_batch(session, chunks: list[VcChunk], anchor_names: dict[str, str],
              as_of_by_rcept: dict[str, int | None],
              max_workers: int = 8) -> tuple[list[dict], dict]:
    """청크 배치: 패스1은 병렬(LLM만), 패스2+검문+DB 기록은 메인 스레드 직렬.

    Returns: (검수용 레코드 목록, counters)
    """
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        pass1 = list(pool.map(
            lambda c: extract_chunk(anchor_names.get(c.corp_code, ""), c.text), chunks
        ))

    ctx = build_guard_context(session)
    all_records: list[dict] = []
    for chunk, result in zip(chunks, pass1):
        ctx.counters["chunks"] += 1
        if result is None:
            ctx.counters["llm_error"] += 1
            continue
        all_records.extend(apply_relations(
            session, ctx, chunk, anchor_names.get(chunk.corp_code, ""),
            as_of_by_rcept.get(chunk.rcept_no), result,
        ))
    session.commit()
    logger.info(f"run_batch 결과: {ctx.counters}")
    return all_records, ctx.counters
