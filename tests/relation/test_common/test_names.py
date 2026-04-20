"""common/names.py 단위 테스트 — normalize_company_name + build_ticker_map."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from modules.relation.common.names import (
    build_ticker_map,
    normalize_company_name,
)


class TestNormalizeCompanyName:
    """normalize_company_name 함수 테스트."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            # 기본 정규화: 괄호 법인 제거
            ("(주)삼성전자", "삼성전자"),
            ("삼성전자주식회사", "삼성전자"),
            ("㈜삼성전자", "삼성전자"),
            # 공백 제거
            ("삼 성 전 자", "삼성전자"),
            ("삼성 전자", "삼성전자"),
            # 영문 법인 접미어 제거
            ("Samsung Co.,Ltd.", "samsung"),
            ("Samsung Inc.", "samsung"),
            ("Apple Corporation", "apple"),
            # NAME_ALIASES 적용
            ("삼성에스디아이", "삼성sdi"),
            ("에스케이하이닉스", "sk하이닉스"),
            ("엘지전자", "lg전자"),
            ("케이티앤지", "kt&g"),
            ("엘지화학", "lg화학"),
            ("에스케이텔레콤", "sk텔레콤"),
            ("에이치디현대중공업", "hd현대중공업"),
            ("현대자동차", "현대차"),
            # 복합: 공백 제거 후 alias 적용
            ("SK 하이닉스", "sk하이닉스"),
            ("LG 전자", "lg전자"),
            # 소문자 정규화
            ("SAMSUNG ELECTRONICS", "samsungelectronics"),
            # 빈 입력
            ("", ""),
            (None, ""),
        ],
    )
    def test_normalize_company_name(self, input_name, expected):
        """여러 정규화 규칙 검증."""
        assert normalize_company_name(input_name) == expected

    def test_normalize_preserves_korean(self):
        """한글 기업명 기본 유지 (alias 제외)."""
        assert normalize_company_name("포스코") == "포스코"
        assert normalize_company_name("POSCO홀딩스") == "posco홀딩스"

    def test_normalize_multiple_suffixes(self):
        """여러 법인 접미어 제거 (반복)."""
        # "주식회사"와 "(주)" 혼합 경우
        result = normalize_company_name("(주)삼성전자주식회사")
        assert result == "삼성전자"

    def test_normalize_whitespace_around_suffixes(self):
        """접미어 전후 공백 처리."""
        result = normalize_company_name("삼성전자 Co., Ltd.")
        # 공백이 있어도 제거 가능해야 함
        assert "co" not in result.lower() or result == "삼성전자"

    def test_normalize_alias_case_insensitive(self):
        """alias 매칭이 대소문자 무관해야 함."""
        # "SK하이닉스"를 여러 방식으로 입력해도 같은 결과
        assert normalize_company_name("에스케이하이닉스") == "sk하이닉스"
        assert normalize_company_name("SK하이닉스") == "sk하이닉스"


class TestBuildTickerMap:
    """build_ticker_map 함수 테스트."""

    def test_build_ticker_map_basic(self):
        """CSV 로드 후 정규화된 이름으로 매핑."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["corp_name", "ticker"])
            writer.writeheader()
            writer.writerow({"corp_name": "삼성전자", "ticker": "005930"})
            writer.writerow({"corp_name": "SK하이닉스", "ticker": "000660"})
            csv_path = f.name

        try:
            result = build_ticker_map(csv_path)
            assert result["삼성전자"] == "005930"
            assert result["sk하이닉스"] == "000660"
        finally:
            Path(csv_path).unlink()

    def test_build_ticker_map_with_aliases(self):
        """alias 포함 CSV 로드."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["corp_name", "ticker"])
            writer.writeheader()
            # FTC 정식명칭으로 저장
            writer.writerow({"corp_name": "에스케이하이닉스", "ticker": "000660"})
            # alias 규칙에 의해 "sk하이닉스"로 정규화됨
            csv_path = f.name

        try:
            result = build_ticker_map(csv_path)
            # 정규화 후 alias 적용 → "sk하이닉스" 키
            assert "sk하이닉스" in result
            assert result["sk하이닉스"] == "000660"
        finally:
            Path(csv_path).unlink()

    def test_build_ticker_map_empty_rows_skip(self):
        """빈 행이나 필드가 없는 행 건너뛰기."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["corp_name", "ticker"])
            writer.writeheader()
            writer.writerow({"corp_name": "삼성전자", "ticker": "005930"})
            writer.writerow({"corp_name": "", "ticker": "000000"})  # 빈 이름
            writer.writerow({"corp_name": "현대차", "ticker": ""})  # 빈 ticker
            csv_path = f.name

        try:
            result = build_ticker_map(csv_path)
            assert len(result) == 1
            assert result["삼성전자"] == "005930"
        finally:
            Path(csv_path).unlink()

    def test_build_ticker_map_duplicate_normalized_names(self):
        """정규화 후 동일한 이름 — 나중 행이 덮어씀."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["corp_name", "ticker"])
            writer.writeheader()
            # 둘 다 정규화 시 "삼성전자"
            writer.writerow({"corp_name": "삼성전자", "ticker": "005930"})
            writer.writerow({"corp_name": "(주)삼성전자", "ticker": "005931"})
            csv_path = f.name

        try:
            result = build_ticker_map(csv_path)
            # 나중 행이 덮어씀
            assert result["삼성전자"] == "005931"
        finally:
            Path(csv_path).unlink()

    def test_build_ticker_map_whitespace_trimmed(self):
        """CSV 필드의 앞뒤 공백 자동 제거."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["corp_name", "ticker"])
            writer.writeheader()
            writer.writerow({"corp_name": "  삼성전자  ", "ticker": "  005930  "})
            csv_path = f.name

        try:
            result = build_ticker_map(csv_path)
            assert "삼성전자" in result
            assert result["삼성전자"] == "005930"
        finally:
            Path(csv_path).unlink()
