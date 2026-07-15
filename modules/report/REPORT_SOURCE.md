# 사업보고서 '원문 보기' — 로직·확장 가이드

현금 은하수(galaxy.html) 딥다이브 카드에서 **그 카드가 유래한 사업보고서 원문**(연결재무제표 5본 + 주석 전수)을 좌측 팝업으로 띄워, 딥다이브 해설과 원문을 나란히 학습하게 하는 기능. v2에서 AI 어시스턴트를 열면 3분할(원문 | 딥다이브 | AI).

## 데이터 흐름

```
reports.db report_section(주석 text_html) ─┐
raw_cache/<t>/<rcept>.xml(재무제표 2-1~2-5)─┴─▶ modules/report/report_source.py         (로직 정본)
                                                 build_report_data(ticker) → dict
                                                        │  integration이 read-only import
                                                        ▼
                              integration/dossier/build_report_source.py                 (서빙 래퍼)
                                → integration/dossier/data/report_<t>.json + report_index.json
                                                        │  galaxy.html이 버튼 클릭 시 fetch(지연)
                                                        ▼
                              integration/dossier/galaxy.html  buildSrcPanel()            (렌더)
```

- **로직은 report 모듈 소유**(`report_source.py`) — 원문은 사업보고서 데이터라 report 모듈 책임. 파일 생성(서빙)은 integration이 호출(단방향, 서빙 계층 예외).
- **결정론·LLM 무관.** 딥다이브 산문(Claude 작성)과 별개 — 여기는 원문 그대로.

## 출력 스키마 (`report_<ticker>.json`)

```json
{ "ticker":"005930", "rcept_no":"20260310002820",
  "statements": { "bs":{"title":"연결 재무상태표","blocks":[...]}, "is":.., "cis":.., "eq":.., "cf":.. },
  "notes":      { "1":{"title":"일반적 사항","blocks":[...]}, "2":.., ... } }
```
`blocks` = 문서 순서 리스트: `{"t":"p","v":"문단"}` 또는 `{"t":"table","rows":[[셀,..],..]}`.

## 핵심: 표 정렬 (colspan/rowspan 전개)

DART 표는 병합 셀(colspan/rowspan)이 많아 셀을 좌→우로 단순 평탄화하면 **열이 어긋난다**(자본변동표 등). `_table_grid()`가 병합을 **직사각 격자로 전개**한다 — (r,c) 셀맵에 배치하되 윗줄 rowspan이 점유한 칸은 건너뛰고, 병합 확장칸은 `''`로 채워 정렬 보존. 완전 빈 열·빈 행 제거. 결과: 모든 행이 동일 열 수 → 렌더가 정렬됨.

가독성·크기 가드(전부 report_source.py 상수):
- `_ROW_CAP`(60): 초장문 표는 상위 N행 + "총 N행" 표시.
- `_COL_CAP`(18)·`_CELL_CAP`(600): **비정형 표 가드** — 종속기업/계열사 목록은 DART 마크업이 뭉개져 격자가 수백 열·거대 셀이 됨(삼성 주1: 60행×1486열·23,752자 셀 = 파일의 3MB 주범). 임계 초과 표는 렌더 대신 "(대형·비정형 표 생략)" 안내로 대체. 재무 표(열≤~12·짧은 셀)는 영향 없음.
- **렌더 줄바꿈**(galaxy.html `_srcTable`): 숫자 셀은 `nowrap`+우측정렬, 텍스트 셀은 `white-space:normal`+`word-break:keep-all`+`min/max-width(84~320px)`로 **줄바꿈**해 옆으로 늘어나지 않고 한 화면에 담김. 팝업 본문 `overflow:auto`(넓은 표는 팝업 내 스크롤).
효과: 삼성 원문 2.8MB→247KB, 전 골든 합 2.0MB.

## galaxy.html 연동 (렌더러)

- **버튼**: `diveCard()` amt 아래 "⧉ 사업보고서 원문 보기" → `openSrc(key)`.
- **dive → 원문 매핑**(`_srcForDive`): APPENDIX(`nX`)→주석 X · new-dive→역-원장 주석 · 흐름 dive→재무제표(행 접두 `bs-`→bs, `is-oci/is-totalcomp`→cis, `is-`→is, `cf-`→cf, `eq-`→eq).
- **목차 클릭 = 원문 이동 + 딥다이브 동기 핀**(`srcGoto`→`_pinForNote`/`_STMT_DIVE`):
  - 주석 → **그 주석의 APPENDIX 카드 `n<no>` 우선 핀**(원장이 `dive:cited`여도), 없으면 `routing_ledger`(appendix:/new-dive:/row:/dive:cited 산문검색).
  - 재무제표 → 대표 dive(bs→assets·is→k2·cis→totalcomp·cf→k11·eq→eq-end).
- **매니페스트 게이팅**: `report_index.json`을 로드해 지원 티커만 `report_<t>.json` fetch → 미지원 티커는 "준비 중"(404 콘솔에러 0).
- **Esc**: 팝업 열림 시 팝업만 닫고, 아니면 딥다이브 unpin.

## 확장 (전 기업)

```bash
# 한 기업 (reports.db에 collector·sectioner 완료돼 있어야)
python integration/dossier/build_report_source.py 005930
# galaxy_*.json 전 골든 일괄
python integration/dossier/build_report_source.py --all
```
새 골든 완주 시: `--all` 재실행(또는 해당 티커 지정) → `report_<t>.json` + `report_index.json` 갱신 → UI 자동 지원(galaxy.html 매니페스트 판정). **galaxy_index.json(현금 은하수 탭 활성)과 짝** — 골든 추가 워크플로에 함께 넣을 것.

## 재현 재료·주의

- 커밋 대상: `report_source.py`·`build_report_source.py`·`report_<t>.json`(8본)·`report_index.json`·이 문서. reports.db·raw_cache는 gitignore(DART 키로 재현).
- 표 정렬이 여전히 이상하면 `_table_grid`의 colspan/rowspan 처리 점검(회사별 DART 마크업 편차). 파일이 크면 `_ROW_CAP` 조정.
