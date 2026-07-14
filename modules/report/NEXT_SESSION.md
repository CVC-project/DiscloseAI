# 다음 세션 핸드오프 — 시작점 커밋 `36140e8`

> 직전 세션(시작점 `4df8e25`)에서 Task 1·2 **완주**. 이 파일은 새 세션이 이어받는 지점.

## 먼저 읽기 (순서)
1. `modules/report/MILKYWAY_GENERATOR.md` — 하네스 정본.
2. `modules/report/VARIATIONS.md` — 변형 레지스트리(**S0 필수**). 특히 **V-040~051** + 채록 로그.
3. 이 파일.

## 지금 상태 — 완주 골든 6본
| 티커 | 회사 | 클러스터 | 비고 |
|---|---|---|---|
| 005930 | 삼성전자 | 제조(최상위 골든=기준) | GOLDEN_REF, viz 완비 |
| 000660 | SK하이닉스 | 메모리 | 수기 골든 |
| 035420 | NAVER | 플랫폼(cogs 결측) | 인터랙션 6(sgna 토글 skip=플랫폼) |
| 068270 | 셀트리온 | 바이오 제조 | 재사용 조립기 검증 |
| 005380 | 현대자동차 | 제조+금융 하이브리드 | 금융업채권·운용리스 BS 지배·영업현금 −(V-050) |
| 051910 | LG화학 | 화학+배터리 | 순손실인데 현금흑자·기타영업손익·중단영업(V-051) |

**전 6본: check_golden 갭 0 · 인터랙션 pytest PASS · 딥다이브 전행 0 dead(V-049 수정) · 상호 무회귀.**

## 직전 세션 완료분
- **Task 1 (V-048)**: SK·NAVER·셀트리온 APPENDIX 전수 재작성(일반론→삼성 수준). 갭 74/54/17→0.
- **Task 2 (V-050·051)**: 현대차·LG화학 골든 신규 완주. 각 accuracy-verifier·completeness-auditor 통과(교정 반영).
- **V-049 (galaxy.html)**: 서브행·정적 요약행 죽은 클릭 → grp·prefix 폴백. 6티커 죽은 클릭 0.
- 조립 스크립트는 scratchpad(세션 소멸). 재현 재료 = 커밋된 골든 JSON + facts_*.json + VARIATIONS.

## 제품 연결 (V-054 완료)
6본이 **v2 3탭에 연결됨**. 진입: `http://localhost:8000/integration/v2/index.html` → 행성 클릭 → ENTER CORPORATION → **현금 은하수** 탭(6본 활성, 나머지 "· 준비중"). 딥링크: `?corp=<ticker>`. 탭 활성은 `dossier/data/galaxy_index.json` 매니페스트(생성기 `build_galaxy_index.py`)가 판정 — **새 골든 = 생성기 재실행만으로 자동 등록**.

## 정본 계층(R8, V-055) — 다음 배치 = T1 후보 6본 완주
`corps.csv`의 `cluster,tier`가 티어 SSOT. 완주 T1 5 + T0 삼성. **미완주 T1 후보 6**(클러스터 크기·우선순위 순): 한화에어로 012450(중공업방산) → 고려아연 010130(에너지소재) → 현대건설 000720(건설) → SKT 017670(통신) → HMM 011200(해운) → KT&G 033780(소비재). 각 착수 = `/galaxy-golden <ticker>` + S0에서 corps.csv 티어·구조 확인. 전 골든 회귀 = `python -m modules.report.check_golden --all`. 상세 규약 = MILKYWAY §8.5.

## 남은 후속(우선순위 낮음 — 회귀 아님)
1. ~~viz 보강~~ **완료(V-052)** · ~~segment 미도달~~ **완료(V-053: k2 병합 + 그림자 가드 코드화)** · ~~골든→제품 연결~~ **완료(V-054: 매니페스트)**.
2. **assemble 모듈화**(잔여 최대): `build_hmc·build_lgc·viz_fill·build_galaxy_index` 등이 scratch/1회성 — `modules/report/assemble.py`로 정식 편입하면 배치 재현 비용↓(현재 golden JSON 커밋본이 유일 재현 재료).
3. **좁은행 토글 히트박스**(참고): `bs-liab`·`bs-equity`(400px) 행 정중앙 클릭이 펼침 토글과 겹침(우측 값 클릭 시 정상). 템플릿 공통.
4. **business 탭 데이터 커버리지**(별개 트랙): `business_<t>.json`이 4개(005930·017670·035420·105560)만 — 골든 6본과 불일치. 사업 개요 탭 확장 시 보강.
5. **다음 확장**: 금융·지주(D10 스코프아웃) 별도 템플릿 or 제조/플랫폼 클러스터 추가 기업(기아·카카오 등) 자동 확장.

## 검증(완주 게이트, 회사마다)
`check_golden <t>` 갭 0 · `GALAXY_TICKER=<t> pytest tests/report/test_galaxy_interaction.py` · 기존 골든 무회귀 · 렌더 콘솔에러 0(favicon 제외) · **딥다이브 전수 열림**(evaluate-click, **클릭 사이 Esc로 카드 해제 필수** — 없으면 이전 카드 잔존→오탐, V-049 교훈).
- 서버: `python -m http.server 8000`, URL `http://localhost:8000/integration/dossier/galaxy.html?ticker=<t>`.
- 인코딩: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`(Windows cp949 print 크래시 방지 — 체커 로직 정상).
