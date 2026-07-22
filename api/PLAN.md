# api/ — 서빙 아키텍처 실행 계획 (프론트·미들웨어·백엔드)

> **상태**: 2026-07-20 아키텍처 정본화 → **2026-07-22 개정**: DartChatbot 실사(§4.3) 반영, 로드맵을 챗봇 가동 보장형 M0~M5로 교체(§8). **api/ 코드 구현은 미착수**.
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
   Gemini 직통 → /api/chat                  │  질문 임베딩(같은 모델) → 검색 → 인용 강제 → 생성
                                            ├──→ ③a 질의 임베딩 (문서와 동일 모델, api層/호스팅 — §6.3)
                                            ├──→ ③b Supabase (관리형 클라우드 DB)
                                            │       - pgvector 임베딩 벡터(GPU 산출) + 청크 원문·메타
                                            │       - (이후) valuechain 엣지 · 사용자·학습 데이터
                                            └──→ ③c 외부 LLM API (Gemini/Claude-Bedrock) — 답변 생성
                                                     │  (③ 전부 GPU 박스 IP와 무관)
   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
   ④ GPU 서버(A100) — 서빙 요청 경로 밖, 오프라인 배치
      RAW 원문(/data) + 문서 임베딩(GPU) → 벡터를 디스크→Supabase 적재 + 밸류체인 QLoRA
      (질의 임베딩은 GPU 박스가 아니라 같은 모델을 안정된 곳에서 — §6.3)
```

- **① 프론트는 화면·모양·동작 전부 불변.** 유일한 변경은 코파일럿 호출처(Gemini 직통 → `/api/chat`). 디자인 정본([DESIGN.md](../DESIGN.md))·구조 불변 원칙 준수.
- **② 미들웨어(`api/`) = Vercel 서버리스 함수.** 역할: (a) 임베딩·Supabase·LLM 키를 서버(환경변수)에 은닉 (b) 질문을 **문서와 같은 모델로 임베딩** → pgvector 검색 → 인용 강제 → LLM 생성 (c) 모든 AI 응답에 면책 문구를 기계적으로 부착 — CLAUDE.md "면책 로직 미구현" 해소. 상주 서버·고정 IP 불필요.
- **③ 서빙 백엔드 = (질의 임베딩) + Supabase + LLM API.** 셋 다 팀원 GPU 박스 IP와 무관(§6.3). Supabase는 이미 프로젝트가 전제(.env `SUPABASE_URL`·`SUPABASE_KEY`·`DATABASE_URL`, `shared/db.py` lazy 엔진, `shared/models.py` 타깃 스키마)라 스캐폴딩이 갖춰져 있음.
- **④ GPU는 오프라인 배치.** RAW 원문 보관 + **문서 임베딩**(대량, GPU 유리) + 밸류체인 QLoRA. 산출 벡터를 디스크→Supabase로 올리고 빠짐 — 서빙 **요청** 경로엔 안 들어감.

**AI 역할 분담**(§6.3 확정): **문서 임베딩 = GPU**(대량 배치, 디스크→Supabase), **질의 임베딩 = 같은 모델을 안정된 곳(api層/호스팅)에서** — GPU 박스 IP 비의존, **답변 생성 = 외부 LLM API**(Gemini/Claude). GPU는 문서 임베딩·밸류체인 QLoRA를 오프라인 배치로 처리하고 서빙 요청엔 관여하지 않는다.

## 3. 연결 계약 (Interface Contracts) C1~C5

| # | 무엇 ↔ 무엇 | 계약 내용 |
|---|---|---|
| **C1** | 프론트 ↔ api | `/api/chat` 요청 `{question, corp_code?, history?}` / 응답 `{answer, citations:[{rcept_no, section_key, quote}], disclaimer}` (SSE 스트리밍). api 주소는 `window.DISCLOSE_API_BASE`로 주입(기본 = same-origin `/api`) → 호스팅 조합이 바뀌어도 프론트 무수정. **폴백 규약 포함**(§4): report 데이터는 정적 커밋본 재시도, 챗봇은 "일시 중지" 안내로 우아한 저하 |
| **C2** | api ↔ Supabase pgvector | 청크 = Supabase 테이블 1행, 필수 필드: `corp_code·rcept_no·section_key·char_span·원문text·embedding(vector)`. 인용 문장(quote)은 이 행의 `원문text`에서 나오므로 **인용에 GPU 원문 접근 불필요**. 임베딩 모델명·차원·버전을 행/테이블 메타로 태깅, **질의-인덱스 동일 모델**(§6.3). GPU 배치가 이 테이블에 멱등 upsert(재실행 중복 0 — valuechain D12 정신). 실사(§4.1) 결과 인덱스 미존재 → 백지에서 이 계약대로 구축 |
| **C3** | 인덱싱 배치 → Supabase (서빙 아님) | RAW 원문을 청킹 → **GPU가 문서 임베딩**(대량) → 벡터를 디스크→ C2 테이블로 아웃바운드 upsert. 질의 임베딩은 **같은 모델을 안정된 곳**에서(§6.3). **서빙 요청 경로엔 GPU 없음** → GPU 다운과 무관하게 검색 생존. (SGLang GPU는 문서 임베딩·밸류체인 QLoRA 배치 전용 — `modules/report/llm.py` 클라이언트 패턴) |
| **C4** | api ↔ RAW 원문 | 서빙에는 원문 원본이 불필요(인용은 C2 청크에 있음). 원문 원본이 필요한 경우(재인덱싱·`report_<ticker>` 상세)는 GPU 배치나 사전 가공으로 처리 — 서빙 요청 경로에서 GPU/원본 DB를 직접 읽지 않는다 |
| **C5** | 면책 | 모든 AI 생성 응답에 면책 필드를 미들웨어가 강제 부착. "과거 통계·공시 기반 참고 정보" 문구, "투자 조언" 표현 금지(루트 CLAUDE.md 면책 규칙) |

## 4. 백엔드 현황 — GPU 서버 실사 결과 (2026-07-20, 2026-07-21 재실사로 일부 정정)

읽기 전용 SSH로 실측(리더 개인 임차 GPU 서버, A100-SXM4-80GB — 접속 정보는 로컬 세션 메모리에만 보관, 공개 저장소엔 미기재).

### 4.1 실측 결과

| 항목 | 실측 | 계획 문서 가정과의 차이 |
|---|---|---|
| 디스크 구성 | **2개 분리**: 루트 96GB(2026-07-20 49GB → 2026-07-21 57GB 사용) + `/data` 197GB(856MB 사용·**187GB 여유**, 변동 없음) | [AI_DIRECTION_PLAN §9.2](../docs/AI_DIRECTION_PLAN.md)의 "200GB" 가정은 루트(96GB)와 불일치 — `/data`가 그 여유분에 해당하는 별도 마운트로 확인됨. 합산 가용량은 가정과 유사하되 단일 디스크 아님. 루트 사용량 증가는 §4.1 후속 정정 참조 |
| 사업보고서 코퍼스 ⚠️정정 | `/data/discloseai/fulltext/` **683MB, 95개 폴더**(8자리 DART `corp_code` 키) — 2026-07-20 실사 시점엔 394개 폴더였으나 **2026-07-21 재실사에서 95개로 확인**. 원인: `/data/discloseai/manifests/eqs_v3_raw_recovery_95.log`에 "raw recovery targets=95 years=2021~2025"로 명시된, 95개사 목록과 정확히 일치 | **"전 상장사 5개년치가 이미 올라가 있다"는 전제는 여전히 사실과 다름.** 나아가 이 폴더는 **고정 코퍼스가 아니라 `/data/discloseai/workspace/DiscloseAI-eqs-v3`(EQS v3 보정 워크스페이스)가 실시간으로 수집·재구성 중인 임시 산출물**로 확인됨 — 394라는 수치는 그 작업 도중의 스냅샷이었을 뿐. 폴더 키 체계(corp_code 8자리)도 로컬 `reports.db`/`raw_cache`(ticker 6자리 키)와 달라 report 모듈 정본 파이프라인 산출물이 아님. **relation/universe 계획(전 상장사 지배구조·밸류체인 원문 원천)의 데이터 소스로 이 디렉터리를 재사용할 수 없음** — 목적이 다르고(EQS 보정용) 개수가 유동적 |
| `reports.db` 자체 | GPU 서버에 **없음** (`find`로 미검출, 2026-07-21 재확인) | 정본은 여전히 로컬(`modules/report/data/reports.db`, 649MB, gitignored) 1곳뿐 |
| 벡터 인덱스·임베딩 산출물 | **없음** (`*embed*`·`*vector*`·`*.faiss`·`chroma`·`qdrant` 전부 0건, 2026-07-21 재확인) | RAG 임베딩 작업은 아직 착수되지 않은 상태로 확인됨 — C2 계약은 실물 대조 없이 설계만 확정 |
| `/data/discloseai/workspace/` 및 신규 하위 산출물 | `DiscloseAI-eqs-v3/`(98MB, git 저장소 아님) + 2026-07-21 재실사에서 추가 확인된 `/data/discloseai/eqs/`(calibration json)·`financial/`(panels json, 최대 11MB)·`fulltext_external/`(1개사, 540KB)·`manifests/`(배치 로그·pid) | `feat/eqs-v3-calibration-integration` 브랜치의 EQS v3 보정 파이프라인 산출물로 확인(2026-07-16~20 배치 로그 다수). fulltext의 394→95 변화도 이 파이프라인 활동의 결과 — relation/valuechain과 무관한 별도 목적 워크스페이스 |
| `/data/discloseai/profiles/` | `CORPCODE.xml`(29MB)·`company_profiles.json`·`krx_listed_tickers.json` | 기업 마스터 데이터 일부 — valuechain `CompanyRegistry`(§2.2) 준비 자산일 가능성 (미변경) |
| SGLang 서빙 상태 | **가동 중** — `Qwen/Qwen3-32B-AWQ`, port 30000, PID 4896, 부팅(Jul12) 이후 2026-07-21 재확인 시점까지 연속 가동 확인 | 로컬 세션 메모의 "재부팅 시 수동 재기동 필요"와 별개로 현재는 살아있음. 재기동 스크립트는 여전히 systemd 미영속화 상태로 확인 필요 |
| 홈 백업 | `~/backups/discloseai/discloseai_fulltext_20260713_145428.tar.gz` — `/data/discloseai/fulltext/`와 동일 백업으로 추정(2026-07-13) | fulltext 컬렉션이 최소 1회 백업된 이력은 있음(단, 위 정정대로 이 컬렉션 자체가 EQS 임시 산출물) |

### 4.2 결론 및 후속 조치

- **서빙은 GPU와 분리(§2 결정) → 이 실사 결과가 서빙을 막지 않는다.** 코퍼스·인덱스가 GPU에 부분적이거나 없다는 사실은 **인덱싱(오프라인 준비)**의 시작점 문제일 뿐, **서빙(Supabase+Vercel)**과는 독립. 인덱스는 백지(0건)라 §6.3 임베딩 모델을 지금 자유롭게 고를 수 있는 **오히려 좋은 타이밍**.
- **`/data/discloseai/fulltext/`(및 형제 산출물 eqs·financial·fulltext_external·manifests) 정체는 2026-07-21 재실사로 해소됨** — EQS v3 보정 워크스페이스의 임시 산출물로 확인, report 모듈 정본과 무관. **인덱싱·relation/universe 확장의 입력으로 재사용하지 않는다** — report 수집기로 전 상장사를 새로 수집한다(valuechain PLAN V0 / [relation/universe/PLAN.md](../modules/relation/universe/PLAN.md) U0).
- **디스크 예산 재확인**: `/data`(197GB, 187GB 여유, 변동 없음)를 RAW 코퍼스·배치 작업·어댑터 공간으로 사용. valuechain 계획의 "200GB" 표현은 실측상 `/data` 마운트를 가리키는 것으로 정정. (서빙 벡터는 GPU가 아니라 Supabase에 적재 — §5). 루트 디스크(49→57GB)는 EQS v3 워크스페이스 활동으로 증가 중이라 여유(43→34GB)가 줄고 있음 — 지속 증가 시 워크스페이스 소유자에게 정리 확인 필요.

### 4.3 DartChatbot 실사 (2026-07-22) — RAG 챗봇 실물이 이미 GPU 서버에서 가동 중

PR #57(v2 코파일럿 연결)·#46(disclosure 어댑터)이 호출하는 **DartChatbot의 실물을 GPU 서버에서 읽기 전용 SSH로 실측**(접속 정보는 공개 저장소 미기재 원칙 유지). §4.1의 "벡터 인덱스 없음" 판정은 `/data` 기준이었고, **홈 디렉터리에 완결된 RAG 챗봇이 별도로 존재**함이 확인됨.

| 항목 | 실측 (2026-07-22) |
|---|---|
| 위치·상태 | GPU 서버 홈 `~/dartchatbot`(전체 6.8GB). uvicorn(포트 8000) + ngrok 무료 터널이 프로세스로 가동 중(2026-07-21 기동). `APP_MODE=bedrock`, `/api/health` = `status: ready` 실측 |
| 답변 생성 | **Amazon Bedrock** `us.anthropic.claude-sonnet-4-6`(us-east-1, Bearer 토큰 — 키는 서버 `.env`에만 존재). converse 호출 정상 응답 실측 |
| 임베딩 | **`intfloat/multilingual-e5-small`**(revision 고정, **CPU 실행** — health 실측 `device: cpu`). 오픈·소형 모델이라 질의 임베딩을 어디서든 재현 가능 — **서빙에 GPU 불필요** |
| 벡터 저장 | 벡터 DB 아님 — **회사별 NumPy float32 인덱스**(runtime data 릴리스에 포함). pgvector 이식은 기계적 변환으로 가능 |
| 데이터 | `releases/dart-runtime-2023-2025-v1` 1.2GB — 2023~2025 정기보고서 파싱 청크 + OpenDART 정형 JSONL + 매니페스트·체크섬. 정형 지표(EPS 등)는 LLM이 아닌 JSONL 직접 조회 |
| CORS | `https://cvc-project.github.io` 이미 허용 → dev(GitHub Pages)에서 즉시 동작 가능. **Vercel 프로덕션 도메인은 미포함** — §8 M1에서 추가 |
| 영속화 | **systemd 미등록**(uvicorn·ngrok 모두) → 재부팅 시 챗봇 다운. ngrok 무료 터널은 재기동 시 URL 변경 |

**시사점**: §0의 "코파일럿 키 노출" 문제는 PR #57 구조(키는 서버측)로 해소 방향. 남은 리스크는 (a) 프론트에 ngrok 임시 URL 하드코딩 — 터널 재기동마다 프론트 수정 필요 (b) systemd 미영속 (c) 서빙이 GPU 박스 동거 — §2 "서빙 경로에 GPU 없음" 원칙과 **임시** 충돌. 셋 다 §8 개정 로드맵(M0·M1·M4)에서 해소한다. §6.3의 "확인할 것(C2) — 문서 임베딩 모델"은 이 실사로 해소됨.

## 5. 데이터 정본·저장 계층 (2계층)

**결정: RAW 정본 = GPU `/data`(+로컬 백업), 서빙 저장소 = Supabase(RAW에서 파생·재생성 가능).** 오늘의 `integration/data/*.json`(모듈 DB에서 파생된 서빙 사본)과 정확히 같은 사상 — 정본은 따로, 서빙용 파생물은 별도 계층.

| 계층 | 무엇 | 위치 | 백업·복구 |
|---|---|---|---|
| **RAW 정본** | 사업보고서 원문 코퍼스, CPA 골드셋·라벨셋, QLoRA 어댑터 가중치 | GPU `/data` | 로컬로 **야간 자동 동기화**(rsync 증분). 재현 불가·고비용 자산이라 백업 필수(원문 자체는 DART 재수집 가능하나 3~5일) |
| **서빙 저장소(파생)** | 임베딩 벡터+청크(pgvector), valuechain 엣지, (이후)사용자·학습 | Supabase | Supabase 관리형 백업(Pro는 자동 PITR; 무료 티어는 주기적 `pg_dump` export 자체 운영). **손실돼도 RAW에서 재인덱싱해 복원 가능** |

- **쓰기 소유 단일화**: RAW는 수집기·인덱서만, Supabase 서빙 테이블은 GPU 배치 업로더만 upsert(멱등). 읽기는 api가 Supabase에서.
- **GPU/서버 계약 종료 시**: 벡터는 이미 Supabase에 있고 서빙(질의 임베딩+Vercel+Supabase)은 GPU 박스와 무관하므로 **챗봇은 계속 산다**(신규 인덱싱만 잠시 멈춤). GPU가 필요한 오프라인 작업(문서 임베딩·밸류체인 QLoRA)만 새 GPU/Render로 옮기면 됨 — 로컬 RAW 백업이 이사 소스.
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
| RAW 코퍼스 + GPU 배치 | **GPU 서버 `/data`(+로컬 백업)** | 원문 보관 + 문서 임베딩 + 밸류체인 QLoRA — 서빙 **요청** 경로 밖(§2·§5·§6.3) | 0원(임차 중) |
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

### 6.3 임베딩 구성 (확정) — 문서=GPU, 질의=같은 모델 API

**용어 정리 먼저.** "임베딩"은 답변 LLM(Gemini/Claude)과 **다른 별개 모델**이다 — 텍스트를 검색용 벡터로 바꾸는 좌표 변환기(답변은 안 만든다). 그리고 두 번 일어난다: ① 문서 전체(수백만 청크 — 인덱싱, 1회+연 1회) ② 질문 1건(매 질의). **철칙: ①과 ②는 반드시 같은 모델·버전**이어야 검색이 성립한다(다른 좌표계면 검색 결과가 무의미).

> **⚠️ 핵심 오해 방지 — "같은 모델" ≠ "같은 GPU/기계".** 모델은 **이식 가능한 파일(가중치)**이다. 팀원이 GPU에서 인덱싱에 쓴 그 모델 파일을 **api 서버에 복사**해두면, 질문 1건은 그 서버의 **CPU**로 임베딩하면 된다 — 같은 모델, 다른 하드웨어, 검색 정상. 문서 수백만 개는 CPU론 너무 느려 GPU를 쓴 것이고, 질문 한 문장은 CPU로 몇~수백 ms면 끝난다. 따라서 **인덱싱을 GPU로 해뒀어도 질의는 GPU가 필요 없고, 팀원의 GPU IP는 서빙 경로에 안 들어온다.** 챙길 것은 "그 모델 파일 확보"뿐 — 오픈소스(bge·e5·gte)면 HuggingFace에서 다운, 커스텀 파인튜닝이면 가중치를 GPU에서 복사(그래도 CPU에서 돌아감). 질의가 진짜 GPU를 요구하는 유일한 경우 = 임베딩 모델이 초대형(수십억 파라미터)이라 CPU 지연이 너무 클 때인데, 그때조차 "아무 클라우드 GPU에 한 번 올리기"이지 팀원의 특정 서버·IP에 묶이는 게 아니다.

**확정 구성(사용자, 2026-07-21):**

- **문서(인덱싱) = GPU가 임베딩 (결정됨):** 사업보고서 텍스트를 GPU가 임베딩해 벡터를 **디스크에 저장** → Supabase pgvector에 적재. 대량이라 GPU가 비용·속도상 유리(§3.1 원칙 유지). ※ 팀원이 이미 진행 중/완료.
- **질의(매 질문) = API가 같은 모델로 임베딩만:** api 미들웨어가 질문 1건을 **문서와 동일한 모델**로 벡터화해서 위 pgvector와 비교 검색.

**철칙 = 질의 임베딩 모델 = 문서 임베딩 모델**(같은 가중치·버전). 좌표계가 일치해야 검색이 성립(모델명·차원·버전을 C2 테이블 메타에 태깅).

**질의 임베딩을 GPU 박스 IP에 안 묶는 법** — 같은 모델을 GPU가 아닌 안정된 곳에서 돌린다:
- (a) **api 서버가 그 모델을 직접 로드**(오픈·소형 모델이면 CPU로 수십 ms) — "같은 모델 ≠ 같은 GPU"(위 박스).
- (b) **그 모델을 호스팅한 추론 엔드포인트 호출**(오픈 모델을 서비스하는 API, 또는 커스텀 모델을 별도 상시 인스턴스에 올림).
- 둘 다 팀원 GPU 서버 IP와 무관 → 챗봇이 GPU 가동에 안 묶임. (질의를 GPU 서버 엔드포인트로 직접 보내면 GPU 상시가동 필요 → 비권장.)

**확인할 것(C2, 팀원)**: 문서를 **어떤 모델**로 임베딩했는지 → 오픈 모델이면 (a)/(b) 자유, 커스텀 파인튜닝이면 그 가중치 파일을 질의 쪽에도 배치. 어느 쪽이든 GPU 상시가동은 서빙에 불필요.
→ **해소(2026-07-22, §4.3 실사)**: `intfloat/multilingual-e5-small`(오픈·소형·revision 고정, CPU 실행 실측) — (a) 방식 그대로 가능. 질의 임베딩의 GPU 의존 없음 확정.

### 6.4 IP 고정 문제 — 이 구조에선 발생 안 함

사용자 우려: "질의 임베딩을 GPU로 하면 GPU 고정 IP에서만 챗봇이 된다." → **이 구조에선 질의 임베딩을 GPU 박스로 보내지 않는다.** 서빙 경로 = 브라우저 → Vercel 함수 → **질의 임베딩(같은 모델을 api層/호스팅에서, §6.3)** → Supabase(검색) → LLM API(생성), 전부 GPU 박스 IP와 무관한 안정 주소. GPU는 오프라인 배치로 **문서** 벡터를 디스크→Supabase에 밀어 넣을 뿐(아웃바운드), 서빙 요청이 GPU로 들어갈 일이 없다. 따라서 GPU의 IP가 무엇이든·켜져 있든 챗봇 서빙과 무관. (핵심은 "같은 모델"이지 "같은 GPU"가 아니라는 점 — §6.3 박스.)

### 6.5 대안·폴백 (지금 주력 아님)

- **api를 GPU에 FastAPI로 동거 + Cloudflare Tunnel**: Supabase-우선안에선 불필요. 굳이 대형 GPU 임베딩 모델을 질의에도 쓰고 싶을 때만 고려하되, 챗봇 가용성이 GPU 가동에 묶이는 단점(그래서 비권장).
- **Render/VPS**: GPU 계약 종료 시 **GPU 배치 작업**(문서 임베딩·밸류체인 QLoRA)을 옮길 곳. 서빙(질의 임베딩+Vercel+Supabase)은 GPU 박스와 무관하므로 이 이사에도 챗봇은 안 멈춤(신규 인덱싱만 잠시 멈춤).

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

## 8. 구현 로드맵 — 챗봇 가동 보장형 (2026-07-22 개정)

> **개정 배경**: DartChatbot 실사(§4.3)로 "RAG 챗봇 실물 + Bedrock + 1.2GB runtime data"가 이미 GPU 서버에서 가동 중임이 확인됨. 로드맵을 "백지에서 P1~P4 구축"에서 **"기존 실물을 dev→main 승격 게이트에 태우고, 정본 구조(Supabase+Vercel)로 단계 이식"** 으로 개정. **불변 원칙: main 머지로 배포된 사이트에서는 챗봇이 반드시 동작해야 한다(M3 게이트).**

- **M0 — dev 머지 게이트 (PR #57 보완)**: 프론트 호출 주소를 ngrok URL 하드코딩에서 **기본 same-origin `/api/chat` + `window.__DART_CHAT_URL` 주입 폴백**(C1 사상)으로 수정. dev(GitHub Pages)에서는 주입값(현 터널 URL)으로 동작 — CORS는 이미 허용됨(§4.3). 이 상태로 dev 머지. 이후 백엔드가 어떻게 바뀌어도 프론트 재수정 불필요.
- **M1 — 챗봇 서버 상시화 (GPU 서버, PR 작성자와 협의)**: uvicorn·터널을 systemd 등록해 재부팅 생존(§4.3 미영속 리스크 해소). CORS 허용 목록에 Vercel 프로덕션 도메인 추가.
- **M2 — Vercel 1차 연결 (api/ 최초 코드 = 얇은 프록시)**: `api/chat.py` Vercel 함수 = DartChatbot 프록시. 오리진 주소는 **Vercel 환경변수 `DART_CHAT_ORIGIN`에만** 둔다(리포·프론트에 서버 주소·터널 URL 미기재 — 보안 규칙). 이 함수가 C5 면책 문구 부착 + rate limit 담당. 프론트는 M0 덕에 무수정(same-origin `/api/chat`). Vercel 프로젝트 연결은 §7.1 절차.
- **M3 — main 머지 게이트 (배포 = 챗봇 가동 확인)**: Vercel 배포 URL에서 챗봇 실질문→실응답(출처 포함) 확인을 **main 머지 통과 조건으로 명문화**. 실패 시 머지 중단. 이 게이트가 "배포 사이트의 챗봇은 반드시 동적"을 보증하는 장치.
- **M4 — 정본 이행 (구 P1~P2 통합)**: DartChatbot 자산을 Supabase+Vercel로 이식 — ① NumPy 인덱스+청크 → Supabase pgvector(C2, 기계적 변환 — §4.3) ② 정형 JSONL → Supabase 테이블 ③ 질의 임베딩 `multilingual-e5-small`을 api層/호스팅으로(§6.3 (a)) ④ Bedrock 키를 Vercel 환경변수로. 완료 시 `api/chat`이 프록시에서 자체 RAG로 교체되고 **서빙이 GPU 박스에서 완전 이탈**(§2 원칙 충족) — M2의 프록시·`DART_CHAT_ORIGIN` 제거.
- **M5 — 코퍼스 확장·valuechain (구 P3~P4)**: 49사 → 전 상장사 확장 시 GPU가 문서 임베딩 배치(C3, 동일 모델 유지), valuechain 엣지 Supabase 적재(valuechain PLAN §2.2), 도메인·키 로테이션.

**M2~M4의 임시 상태 명시**: M2 완료~M4 완료 사이에는 서빙이 GPU 박스(DartChatbot 동거)에 의존한다 — §2 "서빙 경로에 GPU 없음" 원칙의 **의도된 임시 예외**(리더 결정 2026-07-22). GPU 다운 시 챗봇만 우아한 저하(C1 폴백), 사이트 나머지는 정적이라 무영향.

기존 로컬 데모용 FastAPI 2종(`modules/disclosure/chat_server.py`, `modules/price/api.py`)은 api/ 안정화 후 각 담당자와 협의해 통합 또는 은퇴 결정 — 리더가 임의로 수정하지 않는다(모듈 경계 원칙). PR #46(disclosure 어댑터)은 배포 서빙 경로 밖이므로 M 게이트와 무관하게 독립 판단.
