"""MultiDiGraph → 프로토타입 호환 JSON export.

출력: modules/relation/data/graph_top50.json
스키마: 각 노드 dict에 rl 배열 포함. rl 요소는 "대상명:relation_type:detail" 3-split.

상세는 modules/relation/graph/CLAUDE.md 참조.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from modules.relation.graph.build import build_graph

logger = logging.getLogger(__name__)

_OUTPUT_PATH = Path(__file__).parent.parent / "data" / "graph_top50.json"


def _format_detail(edata: dict) -> str:
    """엣지 상세 문자열 생성 — 프로토타입 3-split 호환 (':' 금지, 짧게)."""
    ratio = edata.get("ratio")
    if ratio is not None:
        return f"{ratio}%"
    # ftc_group은 group_name 추출 (JSON에서)
    detail = edata.get("detail") or ""
    if detail.startswith("{"):
        import json

        try:
            obj = json.loads(detail)
            if isinstance(obj, dict) and "group_name" in obj:
                return f"{obj['group_name']} 계열"
        except (ValueError, TypeError):
            pass
    # 콜론은 rl 구분자이므로 제거
    return detail.replace(":", " ")[:40]


def export_json(output_path: Path | None = None) -> Path:
    """build_graph() 결과를 프로토타입 호환 JSON으로 저장.

    Returns: 생성된 파일 경로.
    """
    G = build_graph()

    nodes_output: list[dict] = []
    for node_id, attrs in G.nodes(data=True):
        # 해당 노드에서 나가는 엣지 → rl 배열 ("대상명:relation_type:detail")
        rl: list[tuple] = []
        for _src, target, key, edata in G.out_edges(node_id, keys=True, data=True):
            target_name = G.nodes[target].get("n", target)
            rt = edata.get("relation_type", "")
            detail = _format_detail(edata)
            # 프로토타입 호환 형식: "대상명:relation_type:detail"
            # ratio 내림차순 정렬용 키
            ratio_sort = -(edata.get("ratio") if edata.get("ratio") is not None else -1)
            rl.append((ratio_sort, rt, f"{target_name}:{rt}:{detail}"))
        # ratio 내림차순 (큰 지분이 먼저) + relation_type 알파벳순
        rl.sort(key=lambda x: (x[0], x[1]))

        nodes_output.append(
            {
                "n": attrs.get("n", node_id),
                "t": node_id,
                "s": attrs.get("s", "기타"),
                "sz": attrs.get("sz", 1.0),
                "mc": attrs.get("mc", "-"),
                "group": attrs.get("group"),
                "rl": [item[2] for item in rl],
            }
        )

    path = output_path or _OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(nodes_output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 자체 검증 — in+out degree 0인 노드를 고아로 판정
    total_edges = sum(len(n["rl"]) for n in nodes_output)
    incoming_count: dict = {}
    for n in nodes_output:
        for rl_item in n["rl"]:
            target_name = rl_item.split(":", 1)[0]
            incoming_count[target_name] = incoming_count.get(target_name, 0) + 1
    true_orphans = [
        n["n"]
        for n in nodes_output
        if not n["rl"] and incoming_count.get(n["n"], 0) == 0
    ]

    logger.info(
        f"export: 노드 {len(nodes_output)}개, 엣지 {total_edges}개, "
        f"고아(연결0) {len(true_orphans)}개 → {path}"
    )
    if true_orphans:
        logger.info(f"  고아 노드: {true_orphans}")
    return path
