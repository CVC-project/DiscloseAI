"""KOSPI 50 → 섹터 수동 매핑 + 섹터별 평균 수익성 비율.

배경:
- pykrx의 ``get_market_sector_classifications`` 는 2025년 초 KRX 웹사이트 개편
  이후 JSON 파싱 실패로 미동작 (KRX_ID/KRX_PW 로그인 요구).
- KRX 공식 업종분류 API는 개인 키 발급 + CSV OTP 방식으로 번거로움.

해결:
- KOSPI 50(현재 분석 대상 universe) 한정으로 10개 섹터 하드코딩.
- ``batch.py`` 결과 + ``translator.ratios`` 로 섹터별 평균 계산.
- 결과를 JSON 캐시 (``modules/financial/data/_sector_stats.json``) 로 저장 → dashboard 로드.

나중에 pykrx가 고쳐지거나 종목 수가 늘면 ``SECTORS`` 딕셔너리만 교체하면 됨.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from typing import Dict, Iterable, List, Optional

# ---------------------------------------------------------------------------
# KOSPI 50 → 섹터 하드코딩 매핑
# ---------------------------------------------------------------------------

# 한 회사는 정확히 1개 섹터에 속함.
# 분류 기준: KRX 업종분류 + 시장 통용 분류 절충 (같은 매출·비용 구조 기업끼리).
SECTORS: Dict[str, List[str]] = {
    "반도체/전자부품": [
        "삼성전자",
        "SK하이닉스",
        "삼성전기",
        "한미반도체",
    ],
    "2차전지/배터리": [
        "LG에너지솔루션",
        "삼성SDI",
        "포스코퓨처엠",
    ],
    "자동차": [
        "현대차",
        "기아",
        "현대모비스",
    ],
    "금융/보험": [
        "KB금융",
        "신한지주",
        "하나금융지주",
        "우리금융지주",
        "메리츠금융지주",
        "미래에셋증권",
        "삼성생명",
        "삼성화재",
    ],
    "조선": [
        "HD현대중공업",
        "HD한국조선해양",
        "한화오션",
        "삼성중공업",
    ],
    "화학/정유/소재": [
        "LG화학",
        "SK이노베이션",
        "고려아연",
        "POSCO홀딩스",
    ],
    "바이오/제약": [
        "삼성바이오로직스",
        "셀트리온",
    ],
    "인터넷/IT서비스": [
        "NAVER",
        "카카오",
    ],
    "중공업/방산/전기장비": [
        "한화에어로스페이스",
        "두산에너빌리티",
        "효성중공업",
        "HD현대일렉트릭",
        "LS ELECTRIC",
        "현대로템",
        "한화시스템",
        "LIG넥스원",
    ],
    "지주/복합기업": [
        "SK",
        "두산",
        "삼성물산",
        "HD현대",
        "SK스퀘어",
    ],
    "통신/유틸리티/운송/기타": [
        "SK텔레콤",
        "한국전력",
        "HMM",
        "현대건설",
        "KT&G",
    ],
}

# ETF 등 재무제표 없는 종목 — 섹터 미포함. 현재 universe에는 ETF가 없지만
# 안전망으로 빈 set 유지 (향후 ETF 추가 시 여기에 등록).
_EXCLUDED: set = set()


def get_sector(name: str) -> Optional[str]:
    """기업명으로 섹터 조회. 매핑 없으면 None."""
    needle = name.strip()
    if needle in _EXCLUDED:
        return None
    for sector, members in SECTORS.items():
        if needle in members:
            return sector
    return None


def sector_members(sector: str) -> List[str]:
    """섹터명으로 구성 기업 리스트."""
    return list(SECTORS.get(sector, []))


# ---------------------------------------------------------------------------
# 섹터별 평균 수익성 비율
# ---------------------------------------------------------------------------


@dataclass
class SectorStats:
    """단일 섹터의 평균 수익성 지표. 값은 모두 퍼센트(%).

    n_companies 는 각 비율 계산에 실제로 참여한 회사 수의 **최대값**이 아니라
    '섹터 전체 중 유효 데이터가 하나 이상 있었던 회사 수'. 비율별 샘플 수는
    참여 기업마다 None이 섞일 수 있어 별도 추적하지 않는다 (MVP 단순화).
    """

    sector: str
    n_companies: int
    avg_gross_margin: Optional[float] = None
    avg_operating_margin: Optional[float] = None
    avg_net_margin: Optional[float] = None
    avg_roe: Optional[float] = None
    avg_roa: Optional[float] = None
    members: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    xs = [v for v in values if v is not None]
    if not xs:
        return None
    return sum(xs) / len(xs)


def compute_sector_stats(
    company_ratios: Dict[str, Dict[str, Optional[float]]],
) -> Dict[str, SectorStats]:
    """각 회사의 비율 dict → 섹터별 평균 집계.

    Parameters
    ----------
    company_ratios
        ``{회사이름: {"gross_margin": v, "operating_margin": v, ...}}``

    Returns
    -------
    섹터명 → SectorStats 매핑. 섹터에 유효 데이터 회사가 하나도 없으면 제외.
    """
    # 섹터 → [회사별 비율 dict]
    grouped: Dict[str, List[Dict[str, Optional[float]]]] = {s: [] for s in SECTORS}
    members_seen: Dict[str, List[str]] = {s: [] for s in SECTORS}

    for name, ratios in company_ratios.items():
        sector = get_sector(name)
        if sector is None:
            continue
        grouped[sector].append(ratios)
        members_seen[sector].append(name)

    out: Dict[str, SectorStats] = {}
    for sector, rows in grouped.items():
        if not rows:
            continue
        out[sector] = SectorStats(
            sector=sector,
            n_companies=len(rows),
            avg_gross_margin=_mean(r.get("gross_margin") for r in rows),
            avg_operating_margin=_mean(r.get("operating_margin") for r in rows),
            avg_net_margin=_mean(r.get("net_margin") for r in rows),
            avg_roe=_mean(r.get("roe") for r in rows),
            avg_roa=_mean(r.get("roa") for r in rows),
            members=members_seen[sector],
        )
    return out


# ---------------------------------------------------------------------------
# 캐시 I/O — dashboard.py와 batch.py가 공유
# ---------------------------------------------------------------------------

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "data")
_CACHE_FILE = os.path.join(_CACHE_DIR, "_sector_stats.json")


def save_sector_stats(stats: Dict[str, SectorStats], path: Optional[str] = None) -> str:
    """섹터 통계를 JSON으로 저장. 기본 경로 반환."""
    out_path = path or _CACHE_FILE
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    payload = {k: v.as_dict() for k, v in stats.items()}
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    return out_path


def load_sector_stats(path: Optional[str] = None) -> Dict[str, SectorStats]:
    """저장된 섹터 통계 로드. 파일 없으면 빈 dict.

    스키마 진화 대비: ``SectorStats`` 가 나중에 필드를 추가해도 구버전 JSON을
    읽을 수 있도록, dataclass fields로 한정한 알려진 키만 **v로 전달한다.
    (구버전 JSON이 새 필드 누락 시 ``field(default_factory=...)`` 기본값 적용,
    미래 JSON에 모르는 키가 있으면 조용히 무시.)
    """
    in_path = path or _CACHE_FILE
    if not os.path.exists(in_path):
        return {}
    with open(in_path, "r", encoding="utf-8") as fp:
        raw = json.load(fp)
    known = {f.name for f in fields(SectorStats)}
    return {
        k: SectorStats(**{fk: v[fk] for fk in known if fk in v}) for k, v in raw.items()
    }
