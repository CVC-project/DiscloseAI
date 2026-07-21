# api/ — 서빙 아키텍처 실행 계획 (프론트·미들웨어·백엔드)

> **상태**: 2026-07-20. 아키텍처 정본화 완료 — 문서·CD 파이프라인 정의까지. **api/ 코드 구현은 미착수**(후속 세션).
> **소유**: 프로젝트 리더
> 관련 문서: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) §0·§3.5(현 데이터 토폴로지) · [docs/AI_DIRECTION_PLAN.md](../docs/AI_DIRECTION_PLAN.md) §3.1(GPU/Bedrock 라우팅 원칙) · [modules/relation/valuechain/PLAN.md](../modules/relation/valuechain/PLAN.md)(D11 reports.db 승격, GPU 시분할)

## 0. 배경 — 왜 이 문서가 필요한가

현재 서비스는 **순수 정적 사이트**다(§1). 그러나 확정된 다음 3가지는 서버(백엔드)가 있어야 성립한다:

1. **RAG 챗봇** — 질문에 대해 사업보고서 근거 문장을 검색하고, 그 근거를 인용해서만 답하는 Citation-Enforced 챗봇([AI_DIRECTION_PLAN §2.3①](../docs/AI_DIRECTION_PLAN.md)). 현재 v2 코파일럿은 브라우저→Gemini 직행 구조라 공개 배포 시 키가 노출된다.
2. **GPU 밸류체인** — 사업보고서 문장에서 공급·고객 관계를 추출하는 QLoRA 학습·배치 추론([valuechain/PLAN.md](../modules/relation/valuechain/PLAN.md), 리더 담당·미착수).
3. **사업보고서 원문 DB 성장** — 48개사 649MB → 전 상장사 확장 시 ~35GB(valuechain D11 추정). 브라우저로 보낼 수 있는 크기가 아니다.

이 문서는 프론트(화면) / 미들웨어(`api/`) / 서빙 저장소(Supabase) / 배치 연산(GPU)을 어떻게 나누고 연결할지의 **정본**이다. 호스팅은 §6에서 **Supabase+Vercel을 처음부터 쓰는 것으로 확정**하되(사용자 결정 2026-07-20), 계약 기반 분리로 어느 계층이든 이사 가능하게 설계한다.

## 1. 현재 상태 — 조사로 확인한 사실

| 사실 | 근거 |
|---|---|
| 서빙은 100% 정적: `integration/` 전체 16MB, HTML·CSS·JS + 미리 계산된 JSON. 전부 상대경로 fetch, 빌드 과정 없음(React CDN + 브라우저 내 Babel 변환) | integration/v2/index.html, integration/v2/CLAUDE.md "빌드 도구 도입 금지" |
| 런타임 서버 계산 = 0. Python은 오프라인 데이터 생성(`python -m integration.build_data`)에만 사용 | docs/ARCHITECTURE.md §0 "api/frontend 미구현" |
| 유일한 동적 요소: v2 코파일럿이 **브라우저에서 Gemini API 직접 호출** — 공개 배포 시 클라이언트 키 노출 구조 | integration/v2/src/bundle.jsx:1201 |
| Gemini 키는 gitignored `config.local.js` — 커밋 이력 없음(검증 완료). 로컬 파일에 실키 존재 → 로테이션 권장 | git log --all / git grep 스캔 (2026-07-20) |
| 사업보고서 원문 DB(`modules/report/data/reports.db` 649MB)·원시 캐시(1.5GB)는 git 밖 로컬 파일. 화면은 잘게 잘라 커밋한 `report_<ticker>.json`(회사당 ~300KB)만 사용 | .gitignore:31-34, du 실측 |
| GitHub Pages 배포([pages.yml](../.github/workflows/pages.yml))가 dev push마다 자동 게시 중. CI([ci.yml](../.github/workflows/ci.yml))는 dev·main push 및 PR마다 black·sync_codex·pytest 실행 | 워크플로 파일 실측 |

## 2. 목표 구조 — 서빙은 전부 클라우드, GPU는 서빙 경로 밖

**핵심 결정(사용자, 2026-07-20): 처음부터 Supabase를 쓴다.** GPU 서버는 RAW 원문 보관 + 배치 연산(임베딩·밸류체인 추출/학습)에만 쓰고, 그 **가공물(임베딩 벡터·밸류체인 데이터 등)만 Supabase에 적재**한다. 사용자 질문 처리(서빙)는 전부 클라우드(Vercel 함수 + Supabase)에서 일어나고 **GPU는 서빙 경로에 들어오지 않는다** → 챗봇이 GPU IP 고정·가동 여부에 묶이지 않는다(§6.3의 IP 제약 해소).

```
[사용자 브라우저]
   │ 화면·정적 JSON (기존 대시보드)        │ AI 질문 (실시간)
   ▼                                       ▼
① 프론트 (현행 유지, integration/)    ② 미들웨어 api/ = Vercel 서버리스 함수 (신설, 리더 소유)
   HTML·CSS·JS + 미리 만든 JSON           /api/chat, /api/health
   변경 딱 1곳: 코파일럿 호출처            + 면책 문구 강제 + rate limit + 키(Supabase·LLM) 은닉
   Gemini 직통 → /api/chat                  │  질문 임베딩(API) → 검색 → 인용 강제 → 생성
                                            ├──→ ③a 임베딩 API (Gemini text-embedding) — 질문 벡터화
                                            ├──→ ③b Supabase (관리형 클라우드 DB)
                                            │       - pgvector 임베딩 벡터 + 청크 원문·메타(인용 앵커)
                                            │       - (이후) valuechain 엣지 · 사용자·학습 데이터
                                            └──→ ③c 외부 LLM API (Gemini/Claude-Bedrock) — 답변 생성
                                                     │  (③ 전부 클라우드 API — GPU 불필요)
   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
   ④ GPU 서버(A100) — 서빙 경로 밖, 밸류체인 QLoRA 전용
      RAW 원문 코퍼스(/data) 보관 + 밸류체인 관계추출 QLoRA 학습/추론
      (RAG 인덱싱 임베딩은 GPU 아닌 임베딩 API로 — §6.3 길 A)
```

- **① 프론트는 화면·모양·동작 전부 불변.** 유일한 변경은 코파일럿 호출처(Gemini 직통 → `/api/chat`). 디자인 정본([DESIGN.md](../DESIGN.md))·구조 불변 원칙 준수.
- **② 미들웨어(`api/`) = Vercel 서버리스 함수.** 역할: (a) 임베딩·Supabase·LLM 키를 서버(환경변수)에 은닉 (b) 질문 임베딩(API)→pgvector 검색→인용 강제→LLM 생성 (c) 모든 AI 응답에 면책 문구를 기계적으로 부착 — CLAUDE.md "면책 로직 미구현" 해소. 상주 서버·고정 IP 불필요, 자체 무거운 연산 없음(전부 클라우드 API 중계).
- **③ 서빙 백엔드 = 임베딩 API + Supabase + LLM API.** 셋 다 관리형 클라우드라 GPU 가동과 무관. Supabase는 이미 프로젝트가 전제(.env `SUPABASE_URL`·`SUPABASE_KEY`·`DATABASE_URL`, `shared/db.py` lazy 엔진, `shared/models.py` 타깃 스키마)라 스캐폴딩이 갖춰져 있음.
- **④ GPU는 밸류체인 전용.** RAW 원문 보관 + 밸류체인 QLoRA 연산만(진짜 GPU가 필요한 유일한 작업). RAG 임베딩은 GPU를 안 씀(§6.3 길 A) — 서빙과 완전 분리.

**AI 역할 분담**(길 A 확정, §6.3): **임베딩(문서·질문)은 호스팅 임베딩 API**(Gemini text-embedding — 유계 비용), **답변 생성도 외부 API**(Gemini/Claude). **GPU는 RAG에서 빠지고 밸류체인 QLoRA 전용** — 상용 작업(임베딩)은 API가, GPU만 할 수 있는 일(도메인 파인튜닝)은 GPU가. ([AI_DIRECTION_PLAN §3.1](../docs/AI_DIRECTION_PLAN.md)의 "임베딩=GPU"는 무한 고빈도 Graphiti 대비였고, 유계 문서 코퍼스엔 API로 충분 — §6.3.)

## 3. 연결 계약 (Interface Contracts) C1~C5

| # | 무엇 ↔ 무엇 | 계약 내용 |
|---|---|---|
| **C1** | 프론트 ↔ api | `/api/chat` 요청 `{question, corp_code?, history?}` / 응답 `{answer, citations:[{rcept_no, section_key, quote}], disclaimer}` (SSE 스트리밍). api 주소는 `window.DISCLOSE_API_BASE`로 주입(기본 = same-origin `/api`) → 호스팅 조합이 바뀌어도 프론트 무수정. **폴백 규약 포함**(§4): report 데이터는 정적 커밋본 재시도, 챗봇은 "일시 중지" 안내로 우아한 저하 |
| **C2** | api ↔ Supabase pgvector | 청크 = Supabase 테이블 1행, 필수 필드: `corp_code·rcept_no·section_key·char_span·원문text·embedding(vector)`. 인용 문장(quote)은 이 행의 `원문text`에서 나오므로 **인용에 GPU 원문 접근 불필요**. 임베딩 모델명·차원·버전을 행/테이블 메타로 태깅, **질의-인덱스 동일 모델**(§6.3). GPU 배치가 이 테이블에 멱등 upsert(재실행 중복 0 — valuechain D12 정신). 실사(§4.1) 결과 인덱스 미존재 → 백지에서 이 계약대로 구축 |
| **C3** | 인덱싱 배치 → Supabase (서빙 아님) | RAW 원문을 청킹 → **임베딩 API로 벡터화**(§6.3 길 A, GPU 칩 불필요) → C2 테이블로 아웃바운드 upsert. 질의 임베딩도 같은 API. **GPU는 이 경로에 없음** → GPU 다운과 무관하게 검색 생존. (SGLang GPU는 밸류체인 QLoRA 학습·배치 추론 전용 — `modules/report/llm.py` 클라이언트 패턴) |
| **C4** | api ↔ RAW 원문 | 서빙에는 원문 원본이 불필요(인용은 C2 청크에 있음). 원문 원본이 필요한 경우(재인덱싱·`report_<ticker>` 상세)는 GPU 배치나 사전 가공으로 처리 — 서빙 요청 경로에서 GPU/원본 DB를 직접 읽지 않는다 |
| **C5** | 면책 | 모든 AI 생성 응답에 면책 필드를 미들웨어가 강제 부착. "과거 통계·공시 기반 참고 정보" 문구, "투자 조언" 표현 금지(루트 CLAUDE.md 면책 규칙) |

## 4. 백엔드 현황 — GPU 서버 실사 결과 (2026-07-20)

읽기 전용 SSH로 실측(리더 개인 임차 GPU 서버, A100-SXM4-80GB — 접속 정보는 로컬 세션 메모리에만 보관, 공개 저장소엔 미기재).

### 4.1 실측 결과

| 항목 | 실측 | 계획 문서 가정과의 차이 |
|---|---|---|
| 디스크 구성 | **2개 분리**: 루트 96GB(49GB 사용·43GB 여유) + `/data` 197GB(857MB 사용·**187GB 여유**) | [AI_DIRECTION_PLAN §9.2](../docs/AI_DIRECTION_PLAN.md)의 "200GB" 가정은 루트(96GB)와 불일치 — `/data`가 그 여유분에 해당하는 별도 마운트로 확인됨. 합산 가용량은 가정과 유사하되 단일 디스크 아님 |
| 사업보고서 코퍼스 | `/data/discloseai/fulltext/` **683MB, 394개 폴더**(8자리 DART `corp_code` 키) | **"전 상장사 5개년치가 이미 올라가 있다"는 전제는 사실과 다름.** 394사는 전 상장사(~2,600사)에 크게 못 미치고, 폴더 키 체계(corp_code 8자리)가 로컬 `reports.db`/`raw_cache`(ticker 6자리 키)와 달라 **report 모듈 정본 파이프라인 산출물이 아닌 별도 수집분**으로 추정. 소유자·목적 미상 — 팀원 확인 필요 |
| `reports.db` 자체 | GPU 서버에 **없음** (`find`로 미검출) | 정본은 여전히 로컬(`modules/report/data/reports.db`, 649MB, gitignored) 1곳뿐 |
| 벡터 인덱스·임베딩 산출물 | **없음** (`*embed*`·`*vector*`·`*.faiss`·`chroma`·`qdrant` 전부 0건) | RAG 임베딩 작업은 아직 착수되지 않은 상태로 확인됨 — C2 계약은 실물 대조 없이 설계만 확정 |
| `/data/discloseai/workspace/` | 98MB, git 저장소 아님. relation·disclosure·financial DB 사본 포함 | origin에 새로 확인된 `feat/eqs-v3-calibration-integration` 브랜치 관련 임시 작업공간으로 추정(미검증) |
| `/data/discloseai/profiles/` | `CORPCODE.xml`(29MB)·`company_profiles.json`·`krx_listed_tickers.json` | 기업 마스터 데이터 일부 — valuechain `CompanyRegistry`(§2.2) 준비 자산일 가능성 |
| SGLang 서빙 상태 | **가동 중** — `Qwen/Qwen3-32B-AWQ`, port 30000, PID 4896, 부팅 이후(Jul12) 연속 추정 | [메모 기록](../.claude 세션 메모 — GPU 서버 세팅)의 "재부팅 시 수동 재기동 필요"와 별개로 현재는 살아있음. 재기동 스크립트는 여전히 systemd 미영속화 상태로 확인 필요 |
| 홈 백업 | `~/backups/discloseai/discloseai_fulltext_20260713_145428.tar.gz` — `/data/discloseai/fulltext/`와 동일 백업으로 추정(2026-07-13) | fulltext 컬렉션이 최소 1회 백업된 이력은 있음 |

### 4.2 결론 및 후속 조치

- **서빙은 GPU와 분리(§2 결정) → 이 실사 결과가 서빙을 막지 않는다.** 코퍼스·인덱스가 GPU에 부분적이거나 없다는 사실은 **인덱싱(오프라인 준비)**의 시작점 문제일 뿐, **서빙(Supabase+Vercel)**과는 독립. 인덱스는 백지(0건)라 §6.3 임베딩 모델을 지금 자유롭게 고를 수 있는 **오히려 좋은 타이밍**.
- **필수 확인 사항 (팀원 협의 — 인덱싱 착수 전 선행)**: `/data/discloseai/fulltext/`(394사, corp_code 키)의 정체 — ① 누가 언제 무슨 목적으로 수집했는지 ② report 모듈 정본과의 관계(독자 수집이면 이중 정본 리스크 — 데이터 정본 원칙 위반 소지) ③ 재사용 가능하면 임베딩 인덱싱의 입력으로 활용, 아니면 report 수집기로 재수집. (이 코퍼스는 **인덱싱 입력**일 뿐 서빙 저장소가 아니므로, 정체 확인이 서빙 착수를 막지는 않음)
- **디스크 예산 재확인**: `/data`(197GB, 187GB 여유)를 RAW 코퍼스·배치 작업·어댑터 공간으로 사용. valuechain 계획의 "200GB" 표현은 실측상 `/data` 마운트를 가리키는 것으로 정정. (서빙 벡터는 GPU가 아니라 Supabase에 적재 — §5)

## 5. 데이터 정본·저장 계층 (2계층)

**결정: RAW 정본 = GPU `/data`(+로컬 백업), 서빙 저장소 = Supabase(RAW에서 파생·재생성 가능).** 오늘의 `integration/data/*.json`(모듈 DB에서 파생된 서빙 사본)과 정확히 같은 사상 — 정본은 따로, 서빙용 파생물은 별도 계층.

| 계층 | 무엇 | 위치 | 백업·복구 |
|---|---|---|---|
| **RAW 정본** | 사업보고서 원문 코퍼스, CPA 골드셋·라벨셋, QLoRA 어댑터 가중치 | GPU `/data` | 로컬로 **야간 자동 동기화**(rsync 증분). 재현 불가·고비용 자산이라 백업 필수(원문 자체는 DART 재수집 가능하나 3~5일) |
| **서빙 저장소(파생)** | 임베딩 벡터+청크(pgvector), valuechain 엣지, (이후)사용자·학습 | Supabase | Supabase 관리형 백업(Pro는 자동 PITR; 무료 티어는 주기적 `pg_dump` export 자체 운영). **손실돼도 RAW에서 재인덱싱해 복원 가능** |

- **쓰기 소유 단일화**: RAW는 수집기·인덱서만, Supabase 서빙 테이블은 GPU 배치 업로더만 upsert(멱등). 읽기는 api가 Supabase에서.
- **GPU/서버 계약 종료 시**: 서빙(임베딩 API+Vercel+Supabase)은 GPU와 무관하므로 **챗봇은 계속 산다.** GPU가 필요한 건 밸류체인 QLoRA뿐 → 그것만 새 GPU/Render로 옮기면 됨(재인덱싱은 임베딩 API라 RAW 백업만 있으면 어디서든). 로컬 RAW 백업이 이사 소스.
- **원칙 예외 명문화**: "데이터 정본은 모듈별 로컬 SQLite" 원칙(루트 CLAUDE.md)의 공식 예외로 "RAW 코퍼스 정본 = GPU `/data`+로컬 백업 / 서빙 파생 저장소 = Supabase"를 리더 결정으로 기록. 루트 CLAUDE.md·docs/ARCHITECTURE.md 반영은 api/ 구현 착수(P1) 시 valuechain D11 명문화와 함께.

**서빙 경로엔 GPU가 없다 → 폴백은 "저장소/생성 실패" 기준 (C1):**
- 대시보드·갤럭시·3탭: 정적 파일(Pages/Vercel)에서 fetch → api·Supabase·GPU 전부와 무관, 항상 동작
- 챗봇: Supabase 검색 실패 또는 LLM API 오류 시 "챗봇 일시 중지" 안내로 우아한 저하 — 사이트 나머지는 정상. **GPU 다운은 챗봇 서빙에 영향 없음**(GPU는 서빙 경로 밖 — §2)

**회사 수가 늘면 — `report_<ticker>.json` 정적→동적 전환:**
- 지금: 회사별 조각 JSON을 커밋 → 정적 서빙(12사 × ~300KB).
- 전환 임계(커밋 용량 리포 +100MB 수준, ≈300사): 파일 커밋을 멈추고 **가공된 report 표시 데이터도 Supabase 테이블로 적재** → `/api/reports/<ticker>`가 Supabase에서 조회(`build_report_source.py` 로직을 인덱싱 배치로 이전). 프론트는 fetch 주소 1곳만 교체(C1). 이때도 서빙은 GPU 무관.

## 6. 호스팅 확정안 — Supabase + Vercel (처음부터)

**결정(사용자, 2026-07-20):** 나중에 이관하지 않고 **처음부터 Supabase를 쓴다.** 이유: (1) 이관 비용·정본 재정의를 피하고 한 저장 타깃으로 일관 (2) 챗봇 서빙 경로에서 GPU를 완전히 빼 **GPU IP 고정·가동 여부에 챗봇이 안 묶임**(§6.4의 IP 제약이 근본 해소) (3) 프로젝트가 이미 Supabase 전제로 스캐폴딩됨(.env `SUPABASE_URL`·`SUPABASE_KEY`·`DATABASE_URL`, `shared/db.py`, `shared/models.py`).

### 6.1 계층별 확정 구성

| 계층 | 선택 | 이유 | 고정비 |
|---|---|---|---|
| 프론트(정적) | **GitHub Pages(dev) + Vercel(main) 병행** | dev=팀 개발 확인용(무변경), main=실서비스. 독립 서비스라 병행 무충돌(§7) | 0원 |
| api 미들웨어 | **Vercel 서버리스 함수**(`api/*.py`=엔드포인트) | 프론트와 같은 배포 단위, 상주 서버·고정 IP 불필요. 키는 Vercel 환경변수 | 0원(무료 티어) |
| 서빙 저장소(검색) | **Supabase pgvector** | 관리형·원격 조회·백업 내장. 임베딩 벡터+청크 원문·메타 | 0원(무료 500MB DB) → 전 상장사 규모 시 Pro $25/mo |
| RAW 코퍼스 + 밸류체인 연산 | **GPU 서버 `/data`(+로컬 백업)** | 원문 보관 + 밸류체인 QLoRA — 서빙 경로 밖(§2·§5). RAG 임베딩은 API(§6.3) | 0원(임차 중) |
| LLM(답변 생성) | 외부 API(Gemini 무료 시작, 품질 필요 시 Claude/Bedrock) | 키는 Vercel 환경변수 | 사용량 과금 |

규모 감각: 임베딩 벡터+청크는 48사 ≈0.3GB(무료 티어 내), 전 상장사(~200만 청크) ≈10~20GB(Pro). 원문 35GB는 **Supabase에 안 올림**(GPU에만).

### 6.2 무엇을 어디에 두나 — 과잉 이관 금지

Supabase로 옮기는 건 **새로 생기는 크고 자라는 데이터**뿐. 이미 잘 도는 작은 정적 JSON은 그대로 둔다.

| 데이터 | 위치 | 비고 |
|---|---|---|
| 기존 대시보드 JSON (eqs_summary·disclosures·price_scenarios·graph_top50·firm_*·business_*·galaxy_*) | **정적 커밋 유지** | 작고 안정적 — 정적이 최적. **변경 0** |
| RAG 임베딩 벡터 + 청크(원문·메타) | **Supabase pgvector** | 처음부터 |
| valuechain 엣지(ValueChainEdge — valuechain PLAN §2.2 스키마) | **Supabase** | valuechain 착수 시 |
| 사용자·학습 데이터 | **Supabase** | 학습 레이어 착수 시 (RLS로 브라우저 직접 접근 가능) |
| RAW 원문 코퍼스·QLoRA 어댑터 | **GPU `/data`(+로컬 백업)** | 서빙 경로 밖 |

### 6.3 임베딩을 어디서 하나 — 2가지 길 (C2에서 확정)

**용어 정리 먼저.** "임베딩"은 답변 LLM(Gemini/Claude)과 **다른 별개 모델**이다 — 텍스트를 검색용 벡터로 바꾸는 좌표 변환기(답변은 안 만든다). 그리고 두 번 일어난다: ① 문서 전체(수백만 청크 — 인덱싱, 1회+연 1회) ② 질문 1건(매 질의). **철칙: ①과 ②는 반드시 같은 모델·버전**이어야 검색이 성립한다(다른 좌표계면 검색 결과가 무의미).

> **⚠️ 핵심 오해 방지 — "같은 모델" ≠ "같은 GPU/기계".** 모델은 **이식 가능한 파일(가중치)**이다. 팀원이 GPU에서 인덱싱에 쓴 그 모델 파일을 **api 서버에 복사**해두면, 질문 1건은 그 서버의 **CPU**로 임베딩하면 된다 — 같은 모델, 다른 하드웨어, 검색 정상. 문서 수백만 개는 CPU론 너무 느려 GPU를 쓴 것이고, 질문 한 문장은 CPU로 몇~수백 ms면 끝난다. 따라서 **인덱싱을 GPU로 해뒀어도 질의는 GPU가 필요 없고, 팀원의 GPU IP는 서빙 경로에 안 들어온다.** 챙길 것은 "그 모델 파일 확보"뿐 — 오픈소스(bge·e5·gte)면 HuggingFace에서 다운, 커스텀 파인튜닝이면 가중치를 GPU에서 복사(그래도 CPU에서 돌아감). 질의가 진짜 GPU를 요구하는 유일한 경우 = 임베딩 모델이 초대형(수십억 파라미터)이라 CPU 지연이 너무 클 때인데, 그때조차 "아무 클라우드 GPU에 한 번 올리기"이지 팀원의 특정 서버·IP에 묶이는 게 아니다.

GPU가 등장하는 이유는 필수가 아니라 **비용 선택**이다 — AI_DIRECTION §3.1이 "수백만 청크를 임베딩 API로 돌리면 호출비가 쌓이니 그 대량 작업만 자체 GPU로 무료 처리"를 정했기 때문. 따라서 두 길:

- **길 A — 임베딩도 API로 (✅ 확정, 사용자 결정 2026-07-21):** 문서·질문 둘 다 호스팅 임베딩 API(생성에 Gemini를 쓰므로 **임베딩도 Gemini text-embedding-004** 권장 — 한국어 지원·무료 티어·벤더 일원화). RAG에 GPU가 **한 번도** 안 들어감. 비용은 문서 인덱싱이 1회성 유계(48사 ≈ 몇 센트, 전 상장사 ≈ 대략 $15~40) + 질문당 거의 0. 사업보고서는 공개 데이터라 API 전송에 프라이버시 문제 없음.
- **길 B — 문서 인덱싱만 GPU (대안, 지금 미채택):** 수백만 청크를 자체 GPU로 무료 임베딩, 질문은 같은 모델을 api 서버 CPU로. 자체 도메인 파인튜닝 임베딩을 만들고 싶어질 때만 이 길로. (참고: 소형 모델이면 CPU 질의가 수십 ms라 느리진 않으나, 서버리스에 모델을 올리면 콜드스타트·용량·운영 부담이 생김 → 길 A가 단순.)

**확정 이유 = 길 A.** 길 A의 본질적 이점은 raw 속도가 아니라 **단순함**: 서버리스에 모델을 안 올려 콜드스타트·용량·운영 부담이 없고, 임베딩은 제공사 최적화 인프라가 처리, 우리 서버는 중계+보안만. §3.1의 "임베딩=GPU"는 Graphiti(사용자 행동마다 임베딩 → 무한 고빈도)의 비용 폭주 대비였고, **유계인 문서 코퍼스 인덱싱엔 API로 충분**. **귀결: GPU는 RAG에서 빠지고 밸류체인 QLoRA(진짜 GPU 필요) 전용으로 남는다** — 상용 작업(임베딩)은 API, GPU만 할 수 있는 일(파인튜닝)은 GPU로 역할이 겹치지 않는다.

- **인덱싱 모델 = 질의 모델** 철칙(모델명·차원·버전을 C2 테이블 메타에 태깅). 제공사가 그 모델을 폐기하면 RAW에서 재인덱싱(드묾).
- 인덱싱 배치 = RAW 코퍼스를 읽어 임베딩 API 호출 → Supabase upsert 하는 잡. **GPU 칩 불필요**(어디서 돌려도 됨 — GPU 서버에서 CPU로, 또는 로컬).
- 실사(§4.1)에서 **인덱스 0건** 확인 → 백지라 처음부터 길 A로 구축. 팀원이 이미 임베딩했다면 어떤 모델인지 C2에서 확인 후 정합/재인덱싱.

### 6.4 IP 고정 문제 — 이 구조에선 발생 안 함

사용자 우려: "GPU를 매 질문마다 호출하면 GPU 고정 IP에서만 챗봇이 된다." → **이 구조에선 매 질문에 GPU를 호출하지 않는다.** 서빙 경로 = 브라우저 → Vercel 함수 → Supabase(검색) → LLM API(생성), 전부 클라우드 고정 주소. GPU는 오프라인 배치로 Supabase에 벡터를 밀어 넣을 뿐(아웃바운드), 서빙 요청이 GPU로 들어갈 일이 없다. 따라서 GPU의 IP가 무엇이든·켜져 있든 챗봇 서빙과 무관.

### 6.5 대안·폴백 (지금 주력 아님)

- **api를 GPU에 FastAPI로 동거 + Cloudflare Tunnel**: Supabase-우선안에선 불필요. 굳이 대형 GPU 임베딩 모델을 질의에도 쓰고 싶을 때만 고려하되, 챗봇 가용성이 GPU 가동에 묶이는 단점(그래서 비권장).
- **Render/VPS**: GPU 계약 종료 시 **밸류체인 QLoRA**(GPU 필요)를 옮길 곳. RAG 재인덱싱은 임베딩 API라 GPU 불필요. 서빙(Vercel+Supabase)은 GPU와 무관하므로 이 이사에도 챗봇은 안 멈춤.

## 7. CD(자동 배포) 설계

원리: **머지 = 배포**가 되려면 배포 과정 전체가 자동 트리거로 적혀 있고 사람 손 단계가 0이어야 한다. **GitHub Pages와 Vercel은 완전히 독립된 서비스라, 서로 다른 브랜치를 각자 트리거로 삼아 동시에 운용해도 충돌하지 않는다** — "사이트 1개당 브랜치 1개" 제약은 GitHub Pages *내부*의 제약일 뿐, 다른 서비스를 추가로 붙이는 것까지 막지 않는다. 순차 이관(하나를 버리고 다른 것으로 갈아탐)이 아니라 **병행 운용**(둘 다 켜둠)이 정답.

| 계층 | 지금 | 설계 (§7.1) |
|---|---|---|
| 프론트 — 개발 확인용 | dev push → GitHub Pages 자동 게시([pages.yml](../.github/workflows/pages.yml)) | **무변경.** dev 커밋마다 팀 내부 확인 URL로 계속 사용 |
| 프론트 — 실서비스 | 없음 | **신설**: main push → Vercel 자동 배포(§7.1). GitHub Pages와 나란히 병행 운용, 서로 간섭 없음 |
| api 미들웨어 | 없음 | **신설**: Vercel 서버리스 함수 — main push 시 프론트와 함께 자동 배포(별도 SSH·서버 관리 없음). Supabase·LLM 키는 Vercel 환경변수(§7.1) |
| 데이터 JSON | build_data 실행 후 커밋 → 프론트 배포에 자연히 포함 | 현행 유지 |
| 서빙 벡터(Supabase) | 없음 | GPU 배치가 Supabase로 upsert — git·프론트 배포와 무관(§5·§6.2) |
| RAW 코퍼스(대용량) | git 밖 | git·자동 배포 대상 아님 — §5 로컬 백업으로 관리 |

### 7.1 브랜치 배포 흐름 — 병행 모델 (GitHub Pages=dev, Vercel=main)

**GitHub Pages (dev) — 무변경, 되돌림 완료:** `pages.yml` 트리거는 그대로 `dev` 유지한다(1차 작성 시 `main`으로 바꿨다가, "서비스를 병행하면 되지 굳이 갈아탈 필요가 없다"는 지적으로 원복 — 되돌림 완료). dev에 머지될 때마다 자동 갱신되는 팀 내부 개발 확인용 URL 역할을 계속한다.

**Vercel (main) — 신설, 사용자 계정 작업 필요:**
1. Vercel 가입 → GitHub 저장소(`CVC-project/DiscloseAI`) 연결(브라우저 OAuth — 사용자만 가능)
2. 프로젝트 설정: Root Directory = `integration/`(정적 사이트라 빌드 커맨드 불필요, Framework Preset = Other), Production Branch = `main`
3. 연결 즉시 main push마다 자동 프로덕션 배포 시작. Vercel은 기본적으로 다른 브랜치 push에도 자동 프리뷰 URL을 주므로, 원한다면 dev도 Vercel 프리뷰로 추가 확인 가능(선택, GitHub Pages와 중복이라도 무해)
4. 프론트 코드 변경 0 — 정적 파일이라 호스팅 추가는 설정만으로 끝남

**api 미들웨어의 자동 배포 = Vercel 함수 (api/ 코드가 생기는 P2에서):**
- api/를 Vercel 서버리스 함수로 배치(`api/chat.py` 등 파일=엔드포인트). Vercel이 저장소를 이미 배포 중이므로 **별도 배포 워크플로 불필요** — main push = 프론트+api 함께 자동 배포. Supabase URL·키, LLM 키는 Vercel 프로젝트 Environment Variables에 등록(리포 하드코딩 금지 — 루트 CLAUDE.md 보안 규칙).
- **GPU 서버는 서빙 경로에 없으므로 SSH 자동배포 워크플로가 필요 없다.** GPU의 배치 작업(인덱싱·학습)은 수동 또는 크론으로 실행 — 서빙 배포와 완전히 분리.

## 8. 후속 구현 로드맵 (이번 세션 범위 밖)

1. **P1 — Supabase 기반 세팅**: Supabase 프로젝트 생성 → pgvector 확장 켜기 → 청크 테이블(C2 필드: corp_code·rcept_no·section_key·char_span·원문text·embedding) 생성. .env/`shared/db.py`가 이미 Supabase 연결 준비됨.
2. **P1 — api/ 스켈레톤(Vercel 함수)**: `/api/health`, 면책 미들웨어(C5), `/api/chat`이 우선 외부 LLM 프록시로만(검색 없이) — Supabase·GPU 없이도 로컬 E2E 확인.
3. **P2 — 임베딩 파이프라인 + RAG 연결**: 임베딩 모델 확정(§6.3 길 A — 기본 Gemini text-embedding, 팀원 기존 인덱스 있으면 C2에서 대조) → 인덱싱 배치(RAW 청킹 → 임베딩 API → Supabase upsert) → api가 pgvector 검색 결과를 인용 강제 프롬프트로 결합 → LLM 생성. Vercel 배포.
4. **P3 — 코퍼스 확장·valuechain**: `/data/discloseai/fulltext/`(§4.1) 정체 확인 후 인덱싱 입력으로 정합 또는 재수집. valuechain 엣지 Supabase 적재(valuechain PLAN §2.2 스키마) — D11 시점 조율.
5. **P4 — 공개**: Vercel 계정 연결(§7.1, main 프로덕션), 도메인, Gemini 키 로테이션 후 Vercel 환경변수 주입.

기존 로컬 데모용 FastAPI 2종(`modules/disclosure/chat_server.py`, `modules/price/api.py`)은 api/ 안정화 후 각 담당자와 협의해 통합 또는 은퇴 결정 — 리더가 임의로 수정하지 않는다(모듈 경계 원칙).
