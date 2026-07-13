"""integration 데이터 갱신 오케스트레이터 — 명령 하나로 전 화면 데이터 갱신.

흩어져 있던 생성 스크립트의 단일 진입점 (ARCHITECTURE §1-6 ⑵).
모듈 DB(정본)는 읽기만 하고, 산출물은 전부 integration/ 아래에 쓴다.

기본 실행 (안전·결정적 — 부수효과 없음)::

    python -m integration.build_data
      1) integration.extract_data
         → data/{eqs_summary,disclosures,price_scenarios}.json
         → data/graph_top50.json (modules/relation 산출물 무변환 동기화)

opt-in 단계 (부수효과 있음 — 필요할 때만)::

    --business : dossier/extract_business_json.py
                 (design/prototypes/kospi50 프로토타입 → dossier/data/business_*.json.
                  프로토타입이 미확정판이라 기본 실행에서 제외 — DOSSIER_TABS_PLAN Step 2)
    --history  : scripts/refresh_history_percentile.py
                 (modules/financial/data/eqs_data.json history·percentile 재계산)

각 단계는 subprocess로 격리 실행 — 한 단계가 실패해도 원인 단계가 명확하다.

⚠️ 알려진 함정 (ARCHITECTURE §1-6): eqs_data.json의 market_cap이 전건 null인 상태에서
   실행하면 eqs_summary.json의 시총이 null로 덮인다 — 재생성 전 시총 재적재 확인 (git diff로 점검 권장).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(desc: str, args: list[str]) -> int:
    print(f"\n[build_data] >> {desc}")
    result = subprocess.run([sys.executable, *args], cwd=ROOT)
    if result.returncode != 0:
        print(f"[build_data] FAIL({result.returncode}): {desc}", file=sys.stderr)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--business",
        action="store_true",
        help="business_*.json 재추출 (프로토타입 소스)",
    )
    parser.add_argument(
        "--history", action="store_true", help="eqs_data.json history/percentile 재계산"
    )
    opts = parser.parse_args()

    steps: list[tuple[str, list[str]]] = [
        (
            "공유 JSON + relation 그래프 동기화 (extract_data)",
            ["-m", "integration.extract_data"],
        ),
    ]
    if opts.history:
        steps.append(
            ("eqs history/percentile 재계산", ["scripts/refresh_history_percentile.py"])
        )
    if opts.business:
        steps.append(
            ("business_*.json 재추출", ["integration/dossier/extract_business_json.py"])
        )

    failed = [desc for desc, args in steps if _run(desc, args) != 0]
    if failed:
        print(
            f"\n[build_data] 실패 {len(failed)}건: {', '.join(failed)}", file=sys.stderr
        )
        return 1
    print(f"\n[build_data] OK — {len(steps)}단계 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
