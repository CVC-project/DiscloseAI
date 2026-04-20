"""HTTP 유틸 — DART·FTC API 호출 공통 인프라.

기능:
  - requests.Session 재사용
  - 재시도 3회 (exponential backoff 1·2·4초)
  - Rate limit: 요청 간 0.2초 sleep
  - DART status 핸들링 ('000' ok, '013' 데이터없음, '800' 인증실패, '900' 원본없음)
  - RAW JSON 캐시 (data/raw_cache/)

외부 사용 API:
  - dart_get(endpoint, params, use_cache=True) -> dict
  - ftc_get(api_path, params, use_cache=True) -> dict (XML도 자동 파싱 시도)
  - ftc_get_xml(api_path, params, use_cache=True) -> ElementTree (원본 XML)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import requests
from lxml import etree

from shared.config import DART_API_KEY, FTC_API_KEY

logger = logging.getLogger(__name__)

# ============================================================
# 상수
# ============================================================
DART_BASE_URL = "https://opendart.fss.or.kr/api"
FTC_BASE_URL = "https://apis.data.go.kr/1130000"

_RAW_CACHE_DIR = Path(__file__).parent.parent / "data" / "raw_cache"
_RETRY_COUNT = 3
_RETRY_BACKOFF = (1, 2, 4)
_RATE_LIMIT_SEC = 0.2
_HTTP_TIMEOUT = 20

# DART status 코드
DART_STATUS_OK = "000"
DART_STATUS_NO_DATA = "013"
DART_STATUS_AUTH_FAIL = "800"
DART_STATUS_ORIGIN_MISSING = "900"

# 세션 재사용
_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": "DiscloseAI/1.0 (relation-module)"})
    return _session


def _cache_path(prefix: str, params: dict) -> Path:
    """params로 해시 생성 후 캐시 파일 경로 반환."""
    _RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # API key는 해시 대상에서 제외 (캐시가 키 변경에 의존하지 않도록)
    hash_params = {
        k: v for k, v in params.items() if k not in ("crtfc_key", "serviceKey")
    }
    key = json.dumps(hash_params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
    return _RAW_CACHE_DIR / f"{prefix}_{digest}.json"


def _read_cache(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"캐시 읽기 실패 {path.name}: {e}")
        return None


def _write_cache(path: Path, data: Any) -> None:
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"캐시 쓰기 실패 {path.name}: {e}")


# ============================================================
# DART
# ============================================================


class DartError(RuntimeError):
    """DART API 에러 (status != 000/013/900)."""

    def __init__(self, status: str, message: str):
        super().__init__(f"DART status={status}: {message}")
        self.status = status
        self.message = message


def dart_get(endpoint: str, params: dict, use_cache: bool = True) -> dict:
    """DART OpenAPI JSON 호출.

    Returns: 응답 JSON dict. 성공 시 status='000', 데이터 없음 status='013' (정상 처리).
    Raises: DartError (status=800 인증 실패 등), requests.RequestException (네트워크).
    """
    if not DART_API_KEY:
        raise DartError("NO_KEY", "DART_API_KEY 환경변수 없음")

    prefix = f"dart_{endpoint.replace('.json', '')}"
    cache = _cache_path(prefix, params)
    if use_cache:
        cached = _read_cache(cache)
        if cached is not None:
            return cached

    req_params = {"crtfc_key": DART_API_KEY, **params}
    url = f"{DART_BASE_URL}/{endpoint}"

    last_exc: Exception | None = None
    for attempt in range(_RETRY_COUNT):
        try:
            time.sleep(_RATE_LIMIT_SEC)
            r = _get_session().get(url, params=req_params, timeout=_HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            if status == DART_STATUS_AUTH_FAIL:
                raise DartError(status, data.get("message", "인증 실패"))
            # 000/013/900 모두 정상 응답으로 취급 (호출자가 status 확인)
            if use_cache:
                _write_cache(cache, data)
            return data
        except DartError:
            raise  # 인증 실패는 재시도 안 함
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt < _RETRY_COUNT - 1:
                sleep = _RETRY_BACKOFF[attempt]
                logger.warning(
                    f"DART {endpoint} 시도 {attempt + 1}/{_RETRY_COUNT} 실패: {e}. {sleep}초 후 재시도"
                )
                time.sleep(sleep)
    assert last_exc is not None
    raise last_exc


def dart_get_binary(endpoint: str, params: dict) -> bytes:
    """DART document.json 등 바이너리 응답용 (ZIP 다운로드)."""
    if not DART_API_KEY:
        raise DartError("NO_KEY", "DART_API_KEY 환경변수 없음")

    req_params = {"crtfc_key": DART_API_KEY, **params}
    url = f"{DART_BASE_URL}/{endpoint}"

    last_exc: Exception | None = None
    for attempt in range(_RETRY_COUNT):
        try:
            time.sleep(_RATE_LIMIT_SEC)
            r = _get_session().get(url, params=req_params, timeout=60)
            r.raise_for_status()
            return r.content
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt < _RETRY_COUNT - 1:
                time.sleep(_RETRY_BACKOFF[attempt])
    assert last_exc is not None
    raise last_exc


# ============================================================
# FTC (공정거래위원회)
# ============================================================


class FtcError(RuntimeError):
    """FTC API 에러 (resultCode != 00)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"FTC resultCode={code}: {message}")
        self.code = code
        self.message = message


def _xml_to_dict(elem: etree._Element) -> Any:
    """XML element를 재귀적으로 dict/list로 변환."""
    children = list(elem)
    if not children:
        return elem.text or ""
    # 같은 태그가 여러 개면 list
    result: dict = {}
    for child in children:
        tag = etree.QName(child).localname
        value = _xml_to_dict(child)
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(value)
        else:
            result[tag] = value
    return result


def ftc_get_xml(api_path: str, params: dict, use_cache: bool = True) -> etree._Element:
    """FTC OpenAPI XML 호출 — 원본 ElementTree 반환.

    api_path 예: 'publicYmList/publicYmListApi'
    """
    if not FTC_API_KEY:
        raise FtcError("NO_KEY", "FTC_API_KEY 환경변수 없음")

    prefix = f"ftc_{api_path.replace('/', '_')}"
    cache = _cache_path(prefix, params)
    if use_cache:
        cached_xml_path = cache.with_suffix(".xml")
        if cached_xml_path.exists():
            try:
                return etree.fromstring(cached_xml_path.read_bytes())
            except Exception as e:  # noqa: BLE001
                logger.warning(f"XML 캐시 읽기 실패: {e}")

    req_params = {"serviceKey": FTC_API_KEY, "numOfRows": 1000, "pageNo": 1, **params}
    url = f"{FTC_BASE_URL}/{api_path}"

    last_exc: Exception | None = None
    for attempt in range(_RETRY_COUNT):
        try:
            time.sleep(_RATE_LIMIT_SEC)
            r = _get_session().get(url, params=req_params, timeout=_HTTP_TIMEOUT)
            r.raise_for_status()
            root = etree.fromstring(r.content)
            # 에러 응답은 OpenAPI_ServiceResponse 형식
            if etree.QName(root).localname == "OpenAPI_ServiceResponse":
                err_code = root.findtext(".//returnReasonCode", "?")
                err_msg = root.findtext(".//returnAuthMsg", "알 수 없는 에러")
                raise FtcError(err_code, err_msg)
            # 정상 응답의 resultCode 확인
            result_code = root.findtext(".//resultCode")
            if result_code and result_code != "00":
                result_msg = root.findtext(".//resultMsg", "")
                # 데이터 없음은 정상 처리 (호출자에게 빈 결과 반환)
                if result_code not in ("03",):  # 03 = NODATA_ERROR
                    raise FtcError(result_code, result_msg)
            if use_cache:
                cache.with_suffix(".xml").write_bytes(r.content)
            return root
        except FtcError:
            raise
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt < _RETRY_COUNT - 1:
                sleep = _RETRY_BACKOFF[attempt]
                logger.warning(
                    f"FTC {api_path} 시도 {attempt + 1}/{_RETRY_COUNT} 실패: {e}. {sleep}초 후 재시도"
                )
                time.sleep(sleep)
    assert last_exc is not None
    raise last_exc


def ftc_get(api_path: str, params: dict, use_cache: bool = True) -> dict:
    """FTC OpenAPI → XML을 dict로 변환하여 반환.

    Returns: {'resultCode', 'resultMsg', 'totalCount', 'items': [...]}
    """
    root = ftc_get_xml(api_path, params, use_cache=use_cache)
    data = _xml_to_dict(root)
    # 최상위가 ServiceName이고 그 아래 여러 필드가 있음
    # 공정위 응답은 보통 resultCode/resultMsg + totalCount/numOfRows/pageNo + <item 태그들>
    if not isinstance(data, dict):
        return {"raw": data}
    # items 추출: resultCode/resultMsg 등 메타 필드 외의 반복 가능 항목
    return data


def ftc_get_all_pages(api_path: str, params: dict, item_key: str) -> list[dict]:
    """페이징 자동 순회하여 모든 item 반환.

    item_key: 응답 dict에서 반복 항목의 태그명 (예: 'publicYm', 'kmbnt', 'psitnCmpny').
    """
    page = 1
    all_items: list[dict] = []
    num_of_rows = params.get("numOfRows", 1000)
    while True:
        params_with_page = {**params, "pageNo": page, "numOfRows": num_of_rows}
        data = ftc_get(api_path, params_with_page)
        items = data.get(item_key) if isinstance(data, dict) else None
        if not items:
            break
        if not isinstance(items, list):
            items = [items]
        # dict가 아닌 경우 skip
        items = [x for x in items if isinstance(x, dict)]
        all_items.extend(items)

        # totalCount로 반복 종료 판정
        total = data.get("totalCount")
        try:
            total_int = int(total) if total else 0
        except (TypeError, ValueError):
            total_int = 0
        if len(all_items) >= total_int or len(items) < num_of_rows:
            break
        page += 1
        if page > 100:  # 안전 장치
            logger.warning(f"페이징 100회 초과 — {api_path}")
            break
    return all_items
