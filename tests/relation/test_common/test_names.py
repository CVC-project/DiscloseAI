"""common/names.py 단위 테스트 — normalize_company_name + build_ticker_map."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from modules.relation.common.names import (
    add_phonetic_aliases,
    korean_phonetic_variants,
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


class TestKoreanPhoneticAliases:
    """한글 음차 별칭 규칙 (2026-07-29 U-확대 — NAME_ALIASES 수기 22건의 구조적 한계).

    공시 원문은 '씨제이제일제당', registry는 'CJ제일제당' — 이 불일치로 상장사가
    비상장으로 오분류돼 링킹 실패 큐에 쌓였다(120표기·807회 실측).
    """

    @pytest.mark.parametrize(
        "name,expected_variant",
        [
            ("CJ제일제당", "씨제이제일제당"),
            ("LG전자", "엘지전자"),
            ("GS건설", "지에스건설"),
            ("KT", "케이티"),
            ("CJ CGV", "씨제이 씨지브이"),
            ("HDC현대산업개발", "에이치디씨현대산업개발"),
        ],
    )
    def test_generates_phonetic_variant(self, name, expected_variant):
        assert expected_variant in korean_phonetic_variants(name)

    @pytest.mark.parametrize(
        "name",
        ["삼성전자", "현대차", "포스코퓨처엠", "카카오"],
    )
    def test_no_variant_when_no_ascii_initials(self, name):
        assert korean_phonetic_variants(name) == set()

    def test_long_english_word_is_not_an_initialism(self):
        """5자 이상 영문 덩어리는 이니셜이 아니라 단어 — 음차 대상 아님."""
        assert korean_phonetic_variants("Hyundai Motor") == set()

    def test_alias_lookup_resolves_phonetic_form(self):
        """생성된 별칭으로 '씨제이제일제당' 표기가 CJ제일제당 티커에 링킹된다."""
        mapping = {normalize_company_name("CJ제일제당"): "097950"}
        add_phonetic_aliases(mapping, "CJ제일제당", "097950")
        assert mapping[normalize_company_name("씨제이제일제당(주)")] == "097950"

    # ── ⚠️ 회귀 박제: 실제 사명을 깨뜨리면 안 된다 ────────────────────────
    # normalize_company_name()에 음차 변환을 직접 넣으면 아래가 전부 깨진다
    # ("이마트"→"e마트", "에스원"→"s원"). 그래서 변환은 registry 사명에서
    # 생성하는 방향으로만 적용한다 — 이 테스트가 그 설계를 박제한다.
    @pytest.mark.parametrize(
        "listed_name", ["이마트", "에스원", "케이카", "티웨이항공", "비에이치"]
    )
    def test_real_names_that_look_phonetic_are_untouched(self, listed_name):
        assert normalize_company_name(listed_name) == listed_name

    def test_generated_alias_never_overwrites_real_name(self):
        """실존 사명 키가 이미 있으면 음차 별칭이 덮지 않는다(모호성 우선 회피)."""
        mapping = {normalize_company_name("에스원"): "012750"}
        add_phonetic_aliases(mapping, "SW", "999999")  # SW → '에스더블유'... 충돌 없음
        add_phonetic_aliases(mapping, "S1", "888888")  # S1 → '에스1'
        assert mapping[normalize_company_name("에스원")] == "012750"


class TestAnnotationStripping:
    """주석성 병기 제거 (2026-07-29 U-확대 전수 재훑기 — 38표기·117회 회수).

    공시 표는 회사명 칸에 각주 기호와 구사명을 함께 적는다. 같은 법인을 가리키는
    주석이므로 떼어도 신원이 안 바뀐다.
    """

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("한화오션 주식회사(주1)", "한화오션"),
            ("삼성전자(주)(*1)", "삼성전자"),
            ("삼성전자(주)  (*)", "삼성전자"),
            ("한화투자증권㈜ (주6)", "한화투자증권"),
            # 음차 변환은 normalize가 아니라 별칭 맵 계층 소관 — 여기선 각주만 떨어진다
            ("㈜엘지씨엔에스(주2)", "엘지씨엔에스"),
            # 구사명 병기 — 현재 사명이 앞에 있으므로 떼면 현재 사명으로 링킹된다
            ("㈜포스코퓨처엠(구, ㈜포스코케미칼)", "포스코퓨처엠"),
            ("롯데이노베이트㈜ (구, 롯데정보통신㈜)", "롯데이노베이트"),
            ("㈜에이치에스애드 (구. ㈜지투알)(주4)", "에이치에스애드"),
        ],
    )
    def test_strips_annotation(self, raw, expected):
        assert normalize_company_name(raw) == expected

    # ── ⚠️ 회귀 박제: 일반 괄호는 절대 떼지 않는다 (FN-013 계열) ───────────
    @pytest.mark.parametrize(
        "raw",
        [
            "DB(Philippines) Inc.",          # 괄호 떼면 상장 DB(012030)에 오링킹
            "SK이노베이션 [SK battery America]",  # 미국 배터리 법인
            "INHEE(VIETNAM)",
        ],
    )
    def test_general_parentheses_are_preserved(self, raw):
        """괄호 안이 신원을 가르는 정보일 수 있다 — 떼면 해외 자회사가 상장 모회사가 된다."""
        norm = normalize_company_name(raw)
        assert norm not in {"db", "sk이노베이션", "inhee"}, (
            f"{raw!r} -> {norm!r}: 일반 괄호가 제거돼 상장사로 오링킹될 수 있음"
        )

    def test_bare_legal_suffix_paren_still_removed(self):
        """법인격 '(주)'는 기존 접미어 규칙이 계속 처리한다(주석 규칙과 무관)."""
        assert normalize_company_name("(주)삼성전자") == "삼성전자"
        assert normalize_company_name("삼성전자(주)") == "삼성전자"
