# modules/report — 사업보고서 원문·정형계정 수집 파이프라인

> 자동 로드(Progressive Disclosure). 부모 규약: [../../CLAUDE.md](../../CLAUDE.md)
> 소유: 프로젝트 리더 (Q1 승인 2026-07-08). 실행 계획: [integration/dossier/DOSSIER_TABS_PLAN.md](../../integration/dossier/DOSSIER_TABS_PLAN.md) Phase 3·§2

## 이 모듈의 목적

삼성전자 기준으로 만든 "기본 틀(galaxy 템플릿 + JSON 스키마)"에, 사업보고서 **5개년** 원문·정형계정을
저장해 두고 (Phase 4) 자체 GPU LLM이 주석 수치·설명·5개년 해석을 채워 48사로 확장한다.

- **데이터 생산 모듈** — 다른 데이터 모듈과 import 금지(단방향). integration이 `data/publish/`를 read-only pull.
- **LLM은 숫자를 만들지 않는다(D7)** — 본표·시계열은 코드(collector·fs_enrich·series)가 채우고, LLM은 빈 슬롯(주석 표·산문·5개년 해석)만.

## 파이프라인 (실행 순서)

```
collector.py   corps.csv → dart.list(정기공시) → 최신 5 사업보고서 → dart.document → raw_cache/
sectioner.py   raw_cache → 목차/주석번호 분할 → report_section (표 HTML 보존 + text_md)
fs_enrich.py   fnlttSinglAcntAll 48×5 → fs_account (미확보 계정 5개년 보강)
series.py      firm_json + fs_account + (Phase4)주석추출 → S 24키×5점 (5점 완결 판정)
[Phase 4]      story.py·llm.py·extract.py·stylelint.py·validate.py·publish.py → data/publish/galaxy_<t>.json
```
DART 키 필요: `python -m modules.report.collector` / `.fs_enrich` / `.sectioner`.

## reports.db 비커밋 사유

`data/reports.db`·`raw_cache/`·`review/`는 **원문·중간 산출물이라 대용량**(raw_cache 60~120MB, 섹션 텍스트 ×5년).
`.gitignore`로 제외. **커밋 대상은 `data/publish/`(검증 통과 JSON)와 `corps.csv`(시드)뿐.** DART 키만 있으면 재현 가능.

## 계정 → 소스 매핑표 (S 24키 × 소스) — 초안, backfill에서 검증·보정

`series.py:SOURCE_MAP`이 코드 정본. 소스: **A**=firm_*.json(확보) · **B**=fs_account(fnlttSinglAcntAll) · **D**=파생 · **N**=주석추출(Phase4)

| 키 | 소스 | 계정ID / 근거 |
|---|---|---|
| revenue·op·ni·ocf·cash·assets·debt·equity | A\|B | firm_json 본표 우선, fs_account 보강 |
| cogs·sgna·pretax·tax·oci·icf·capex·fin·div·buyback·eps | B | fnlttSinglAcntAll (IS/CF/CE) |
| dep | B\|N | 감가상각비 — CF 또는 성격별비용 |
| gross | D | revenue − cogs |
| tci | D | ni + oci |
| **rnd** | **N** | 연구개발활동 표 / 성격별 비용 (R13 소스 미확정 — backfill 확인) |
| **dsOp** | **N** | 부문정보(주30) DS 영업이익 |

> ⚠️ N(주석 의존) 키가 5점 미완성이면 galaxy_<t>.json의 해당 dive `five=skip`. 5점 완결률은 series 리포트로.

## DART 수집 다중화 부채 (R6)

원문 수집이 disclosure(B)·relation(C)에 이어 report까지 3중, 재무 정형은 financial + report `fnlttSinglAcntAll` 이중.
[이슈 #43](https://github.com/CVC-project/DiscloseAI/issues/43)에 등재. ARCHITECTURE.md 부채 표에도 반영.

## 착수 조건 (Phase 4)

R4 **완료(2026-07-12)**: A100(원격) 드라이버 535→580-server 업그레이드 + SGLang(Qwen/Qwen3-32B-AWQ, xgrammar 구조화 출력)을 `report-llm.service`(systemd)로 상시화. 노트북은 SSH 터널(`ssh -N -L 30000:127.0.0.1:30000 <user>@<GPU_IP>`)로 접속, `REPORT_LLM_BASE_URL=http://127.0.0.1:30000/v1`(shared/config.py). 상세: [integration/dossier/DOSSIER_TABS_PLAN.md](../../integration/dossier/DOSSIER_TABS_PLAN.md) §3·§9 R4. Phase 3(수집)는 DART 키만으로 진행 가능 — 이제 Phase 4 LLM 하네스(story·llm·extract·validate·publish)도 착수 가능.
