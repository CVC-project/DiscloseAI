"""ingest/_http.py 단위 테스트 — HTTP 유틸 인프라."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from lxml import etree

from modules.relation.ingest._http import (
    _cache_path,
    _read_cache,
    _write_cache,
    _xml_to_dict,
    DartError,
    FtcError,
)


class TestCachePath:
    """_cache_path 함수 테스트."""

    def test_cache_path_same_params_same_hash(self):
        """같은 params는 같은 해시 생성."""
        params1 = {"corp_code": "005930", "bsns_year": "2023"}
        params2 = {"corp_code": "005930", "bsns_year": "2023"}
        path1 = _cache_path("dart_test", params1)
        path2 = _cache_path("dart_test", params2)
        assert path1 == path2

    def test_cache_path_different_params_different_hash(self):
        """다른 params는 다른 해시 생성."""
        params1 = {"corp_code": "005930", "bsns_year": "2023"}
        params2 = {"corp_code": "005930", "bsns_year": "2024"}
        path1 = _cache_path("dart_test", params1)
        path2 = _cache_path("dart_test", params2)
        assert path1 != path2

    def test_cache_path_ignores_api_key_dart(self):
        """DART API key 제외하고 해시 생성."""
        params1 = {"corp_code": "005930", "crtfc_key": "KEY1"}
        params2 = {"corp_code": "005930", "crtfc_key": "KEY2"}
        path1 = _cache_path("dart_test", params1)
        path2 = _cache_path("dart_test", params2)
        # API key가 다르면 hash가 달라져야 함 (정규화 후 같은 params)
        assert path1 == path2

    def test_cache_path_ignores_api_key_ftc(self):
        """FTC API key (serviceKey) 제외하고 해시 생성."""
        params1 = {"corp_code": "005930", "serviceKey": "FTCKEY1"}
        params2 = {"corp_code": "005930", "serviceKey": "FTCKEY2"}
        path1 = _cache_path("ftc_test", params1)
        path2 = _cache_path("ftc_test", params2)
        assert path1 == path2

    def test_cache_path_includes_other_params(self):
        """API key 외의 모든 params는 해시에 포함."""
        params1 = {
            "corp_code": "005930",
            "bsns_year": "2023",
            "serviceKey": "KEY",
        }
        params2 = {
            "corp_code": "005930",
            "bsns_year": "2024",
            "serviceKey": "KEY",
        }
        path1 = _cache_path("test", params1)
        path2 = _cache_path("test", params2)
        assert path1 != path2

    def test_cache_path_creates_directory(self):
        """캐시 디렉토리가 없으면 생성."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 실제 _cache_path는 고정 경로 사용하므로 여기서는 로직만 검증
            path = _cache_path("test", {"k": "v"})
            assert path.parent.exists()


class TestReadWriteCache:
    """_read_cache / _write_cache 테스트."""

    def test_read_cache_nonexistent_returns_none(self):
        """존재하지 않는 파일 읽기 → None."""
        path = Path("/tmp/nonexistent_cache_file_xyz.json")
        result = _read_cache(path)
        assert result is None

    def test_write_read_cache_roundtrip(self):
        """데이터 쓰기 후 읽기."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test.json"
            data = {"key": "value", "number": 42}
            _write_cache(cache_file, data)
            result = _read_cache(cache_file)
            assert result == data

    def test_read_cache_invalid_json_returns_none(self):
        """JSON 파싱 실패 → None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "invalid.json"
            cache_file.write_text("not valid json", encoding="utf-8")
            result = _read_cache(cache_file)
            assert result is None

    def test_write_cache_ensures_utf8(self):
        """캐시 파일이 UTF-8로 저장되는지 확인."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "korean.json"
            data = {"기업명": "삼성전자"}
            _write_cache(cache_file, data)
            content = cache_file.read_text(encoding="utf-8")
            assert "삼성전자" in content

    def test_read_cache_preserves_structure(self):
        """복잡한 데이터 구조 유지."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "complex.json"
            data = {
                "list": [1, 2, 3],
                "nested": {"a": {"b": "c"}},
                "korean": "한글",
            }
            _write_cache(cache_file, data)
            result = _read_cache(cache_file)
            assert result == data


class TestXmlToDict:
    """_xml_to_dict 재귀 변환 테스트."""

    def test_xml_to_dict_leaf_element(self):
        """텍스트만 있는 요소."""
        xml_str = "<item>Hello</item>"
        elem = etree.fromstring(xml_str.encode())
        result = _xml_to_dict(elem)
        assert result == "Hello"

    def test_xml_to_dict_empty_element(self):
        """텍스트 없는 요소 → 빈 문자열."""
        xml_str = "<item></item>"
        elem = etree.fromstring(xml_str.encode())
        result = _xml_to_dict(elem)
        assert result == ""

    def test_xml_to_dict_simple_nested(self):
        """단순 중첩 구조."""
        xml_str = "<root><name>Samsung</name><ticker>005930</ticker></root>"
        elem = etree.fromstring(xml_str.encode())
        result = _xml_to_dict(elem)
        assert result == {"name": "Samsung", "ticker": "005930"}

    def test_xml_to_dict_duplicate_tags_become_list(self):
        """같은 태그 여러 개 → list."""
        xml_str = "<root>" "<item>A</item>" "<item>B</item>" "<item>C</item>" "</root>"
        elem = etree.fromstring(xml_str.encode())
        result = _xml_to_dict(elem)
        assert result == {"item": ["A", "B", "C"]}

    def test_xml_to_dict_mixed_single_and_multiple(self):
        """단일 요소에서 시작해 다중이 되는 경우."""
        xml_str = "<root>" "<item>First</item>" "<item>Second</item>" "</root>"
        elem = etree.fromstring(xml_str.encode())
        result = _xml_to_dict(elem)
        assert isinstance(result["item"], list)
        assert result["item"] == ["First", "Second"]

    def test_xml_to_dict_deeply_nested(self):
        """깊이 있는 중첩 구조."""
        xml_str = (
            "<root>"
            "<company>"
            "<info>"
            "<name>Samsung</name>"
            "</info>"
            "</company>"
            "</root>"
        )
        elem = etree.fromstring(xml_str.encode())
        result = _xml_to_dict(elem)
        assert result == {"company": {"info": {"name": "Samsung"}}}

    def test_xml_to_dict_complex_mixed_structure(self):
        """여러 단일 + 다중 요소 혼합."""
        xml_str = (
            "<root>"
            "<name>Test</name>"
            "<items>"
            "<item>Item1</item>"
            "<item>Item2</item>"
            "</items>"
            "</root>"
        )
        elem = etree.fromstring(xml_str.encode())
        result = _xml_to_dict(elem)
        assert result["name"] == "Test"
        assert isinstance(result["items"], dict)
        assert result["items"]["item"] == ["Item1", "Item2"]

    def test_xml_to_dict_with_numeric_content(self):
        """숫자 값도 문자열로 반환."""
        xml_str = "<root><count>100</count></root>"
        elem = etree.fromstring(xml_str.encode())
        result = _xml_to_dict(elem)
        # 숫자도 문자열로 반환됨
        assert result == {"count": "100"}


class TestDartError:
    """DartError 예외 클래스 테스트."""

    def test_dart_error_preserves_status_message(self):
        """status와 message가 속성으로 저장됨."""
        err = DartError("800", "인증 실패")
        assert err.status == "800"
        assert err.message == "인증 실패"

    def test_dart_error_str_representation(self):
        """예외 메시지 형식."""
        err = DartError("800", "인증 실패")
        assert "DART status=800" in str(err)
        assert "인증 실패" in str(err)

    def test_dart_error_is_runtime_error(self):
        """RuntimeError를 상속함."""
        err = DartError("800", "test")
        assert isinstance(err, RuntimeError)


class TestFtcError:
    """FtcError 예외 클래스 테스트."""

    def test_ftc_error_preserves_code_message(self):
        """code와 message가 속성으로 저장됨."""
        err = FtcError("03", "데이터 없음")
        assert err.code == "03"
        assert err.message == "데이터 없음"

    def test_ftc_error_str_representation(self):
        """예외 메시지 형식."""
        err = FtcError("03", "데이터 없음")
        assert "FTC resultCode=03" in str(err)
        assert "데이터 없음" in str(err)

    def test_ftc_error_is_runtime_error(self):
        """RuntimeError를 상속함."""
        err = FtcError("03", "test")
        assert isinstance(err, RuntimeError)
