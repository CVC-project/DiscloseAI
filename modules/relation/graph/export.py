"""MultiDiGraph → 프로토타입 호환 JSON export.

출력: modules/relation/data/graph_top50.json
스키마: 각 노드 dict에 rl 배열 포함. rl 요소는 "대상명:relation_type:detail" 3-split 문자열.

상세는 modules/relation/graph/CLAUDE.md 참조.
"""

from __future__ import annotations

from pathlib import Path

_OUTPUT_PATH = Path(__file__).parent.parent / "data" / "graph_top50.json"


def export_json(output_path: Path | None = None) -> Path:
    """build_graph() 결과를 프로토타입 호환 JSON으로 저장.

    Returns: 생성된 파일 경로.
    """
    raise NotImplementedError("Phase 2e에서 구현")
