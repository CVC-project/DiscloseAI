# api/ — 서빙 아키텍처 실행 계획 (프론트·미들웨어·백엔드)

> **상태**: 2026-07-20. 아키텍처 정본화 완료 — 문서·CD 파이프라인 정의까지. **api/ 코드 구현은 미착수**(후속 세션).
> **소유**: 프로젝트 리더
> 관련 문서: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) §0·§3.5(현 데이터 토폴로지) · [docs/AI_DIRECTION_PLAN.md](../docs/AI_DIRECTION_PLAN.md) §3.1(GPU/Bedrock 라우팅 원칙) · [modules/relation/valuechain/PLAN.md](../modules/relation/valuechain/PLAN.md)(D11 reports.db 승격, GPU 시분할)

## 0. 배경 — 왜 이 문서가 필요한가

현재 서비스는 **순수 정적 사이트**다(§1). 그러나 확정된 다음 3가지는 서버(백엔드)가 있어야 성립한다:

1. **RAG 챗봇** — 질문에 대해 사업보고서 근거 문장을 검색하고, 그 근거를 인용해서만 답하는 Citation-Enforced 챗봇([AI_DIRECTION_PLAN §2.3①](../docs/AI_DIRECTION_PLAN.md)). 현재 v2 코파일럿은 브라우저→Gemini 직행 구조라 공개 배포 시 키가 노출된다.
2. **GPU 밸류체인** — 사업보고서 문장에서 공급·고객 관계를 추출하는 QLoRA 학습·배치 추론([valuechain/PLAN.md](../modules/relation/valuechain/PLAN.md), 리더 담당·미착수).
3. **사업보고서 원문 DB 성장** — 48개사 649MB → 전 상장사 확장 시 ~35GB(valuechain D11 추정). 브라우저로 보낼 수 있는 크기가 아니다.

이 문서는 프론트(화면) / 미들웨어(`api/`) / 백엔드(데이터·GPU)를 어떻게 나누고 연결할지의 **정본**이다. 호스팅 서비스 선택은 §6에서 확정안을 제시하되, 어느 계층이든 이사 가능하게 설계한다(계약 기반 분리).

## 1. 현재 상태 — 조사로 확인한 사실

| 사실 | 근거 |
|---|---|
| 서빙은 100% 정적: `integration/` 전체 16MB, HTML·CSS·JS + 미리 계산된 JSON. 전부 상대경로 fetch, 빌드 과정 없음(React CDN + 브라우저 내 Babel 변환) | integration/v2/index.html, integration/v2/CLAUDE.md "빌드 도구 도입 금지" |
| 런타임 서버 계산 = 0. Python은 오프라인 데이터 생성(`python -m integration.build_data`)에만 사용 | docs/ARCHITECTURE.md §0 "api/frontend 미구현" |
| 유일한 동적 요소: v2 코파일럿이 **브라우저에서 Gemini API 직접 호출** — 공개 배포 시 클라이언트 키 노출 구조 | integration/v2/src/bundle.jsx:1201 |
| Gemini 키는 gitignored `config.local.js` — 커밋 이력 없음(검증 완료). 로컬 파일에 실키 존재 → 로테이션 권장 | git log --all / git grep 스캔 (2026-07-20) |
| 사업보고서 원문 DB(`modules/report/data/reports.db` 649MB)·원시 캐시(1.5GB)는 git 밖 로컬 파일. 화면은 잘게 잘라 커밋한 `report_<ticker>.json`(회사당 ~300KB)만 사용 | .gitignore:31-34, du 실측 |
| GitHub Pages 배포([pages.yml](../.github/workflows/pages.yml))가 dev push마다 자동 게시 중. CI([ci.yml](../.github/workflows/ci.yml))는 dev·main push 및 PR마다 black·sync_codex·pytest 실행 | 워크플로 파일 실측 |

## 2. 목표 구조 — 3계층

```
[사용자 브라우저]
   │ 화면·데이터 파일 (정적)              │ AI 질문 등 실시간 요청
   ▼                                      ▼
① 프론트 (현행 유지, integration/)   ② 미들웨어 api/ (신설 예정, 리더 소유)
   HTML·CSS·JS + 미리 만든 JSON          FastAPI — /api/chat, /api/health
   변경은 딱 1곳: 코파일럿 호출처를      + 모든 AI 답변에 면책 문구 자동 부착
   Gemini 직통 → /api/chat 으로           + rate limit + LLM 키 서버 보관
                                           │
                                           ▼
                                    ③ 백엔드 (데이터·계산)
                                       - 사업보고서 원문 DB (reports.db)
                                       - 벡터 인덱스 (팀원 임베딩 산출물 — §4 C2)
                                       - GPU 서버(A100): 임베딩 배치·밸류체인 학습(시분할)
                                       - (미래) 사용자·학습 기록 DB (PostgreSQL, shared/models.py 타깃)
```

- **① 프론트는 화면·모양·동작 전부 불변.** 유일한 변경은 코파일럿 호출처(Gemini 직통 → `/api/chat`). 디자인 정본([DESIGN.md](../DESIGN.md))·구조 불변 원칙 준수.
- **② 미들웨어(`api/`)가 신설되는 층.** 역할: (a) LLM 키를 서버에 은닉 (b) 챗봇 질문을 검색→인용 강제→답변으로 처리 (c) 모든 AI 응답에 면책 문구를 기계적으로 부착 — CLAUDE.md의 "면책 로직 미구현" 항목이 여기서 해소됨.
- **③ 백엔드는 대부분 기존 자산의 재배치.** reports.db(있음), GPU 서버(세팅 있음, §4 실사 결과 참조), 벡터 인덱스(팀원 작업물 — 계약 C2로 정의, 실물 확인 전).

**AI 역할 분담**([AI_DIRECTION_PLAN §3.1](../docs/AI_DIRECTION_PLAN.md) 라우팅 원칙의 시작 형태): 문장을 검색 가능한 벡터로 바꾸는 **임베딩은 GPU가 배치 처리**(비용 흡수), **최종 인용 답변 생성은 외부 API**(Claude/Gemini — 서비스 품질이 첫인상을 결정). 질문 1건의 임베딩 변환은 api 서버 CPU로도 충분해, GPU가 꺼진 시간(학습 시간대)에도 챗봇은 생존하도록 설계.

## 3. 연결 계약 (Interface Contracts) C1~C5

| # | 무엇 ↔ 무엇 | 계약 내용 |
|---|---|---|
| **C1** | 프론트 ↔ api | `/api/chat` 요청 `{question, corp_code?, history?}` / 응답 `{answer, citations:[{rcept_no, section_key, quote}], disclaimer}` (SSE 스트리밍). api 주소는 `window.DISCLOSE_API_BASE`로 주입(기본 = same-origin `/api`) → 호스팅 조합이 바뀌어도 프론트 무수정. **폴백 규약 포함**(§4): report 데이터는 정적 커밋본 재시도, 챗봇은 "일시 중지" 안내로 우아한 저하 |
| **C2** | api ↔ 벡터 인덱스 (팀원 계약) | 청크 단위 필수 필드: `corp_code·rcept_no·section_key·char_span·원문text`(인용 앵커 역추적용). 임베딩 모델명·차원·버전 태깅, 질의-인덱스 동일 모델 원칙. **인덱스 파일의 정본 위치·백업 포함**(§4 생존 정책). 팀원 작업물 실사 후 확정 — 현재 실사 결과 인덱스 자체가 미존재(§4.1) |
| **C3** | api ↔ GPU 서버(SGLang) | OpenAI 호환 엔드포인트 호출 — `modules/report/llm.py`의 기존 클라이언트 패턴 재사용. GPU 다운 감지 시 외부 API·CPU로 자동 폴백 |
| **C4** | api ↔ reports.db | 읽기 전용(integration과 동일한 리더 소유 예외 — [integration/CLAUDE.md](../integration/CLAUDE.md) 모듈 경계 규약 준용). DB 경로는 상수 1곳 — valuechain D11 승격(`shared/data/reports.db`) 시 1곳만 변경 |
| **C5** | 면책 | 모든 AI 생성 응답에 면책 필드를 미들웨어가 강제 부착. "과거 통계·공시 기반 참고 정보" 문구, "투자 조언" 표현 금지(루트 CLAUDE.md 면책 규칙) |

## 4. 백엔드 현황 — GPU 서버 실사 결과 (2026-07-20)

읽기 전용 SSH로 실측(`tta@123.37.8.42`, A100-SXM4-80GB, 호스트명 rookie-s44).

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

- **"코퍼스 인덱스까지 이미 준비돼 있다"는 전제로 세운 계획은 없다** — 원래 §6 결정표도 "인덱스 미완" 분기를 이미 포함하고 있었으므로 설계 자체의 변경은 불필요. 다만 시작점이 예상보다 이르다(코퍼스도 부분적, 인덱스는 0).
- **필수 확인 사항 (팀원 협의 — 실행 착수 전 선행)**: `/data/discloseai/fulltext/`(394사, corp_code 키)의 정체 — ① 누가 언제 무슨 목적으로 수집했는지 ② report 모듈 정본과의 관계(독자 수집이면 이중 정본 리스크 — 데이터 정본 원칙 위반 소지) ③ 재사용 가능하면 report 파이프라인 스키마로 정합, 아니면 참고용으로만 두고 정본은 report 수집기로 재수집.
- **디스크 예산 재확인**: `/data`(197GB, 187GB 여유)를 코퍼스·인덱스·어댑터 저장 공간으로 사용. valuechain 계획의 "200GB" 표현은 실측상 `/data` 마운트를 가리키는 것으로 정정.

## 5. 데이터 생존 정책 — 정본 위치와 백업

**결정: 운영 정본 = GPU 서버 디스크(`/data`), 로컬 = 자동 백업.**

- **운영 정본 = GPU 서버 `/data`**. 데이터가 실제로 쓰이는 곳(RAG 검색·밸류체인 추출·api 서빙 동거)에 정본을 둔다. 수집기·인덱서만 여기 쓴다(쓰기 소유 단일화 — valuechain D11 원칙과 동일 사상, 위치만 로컬→GPU로 이동).
- **로컬 = 자동 백업본**: GPU→로컬 **야간 자동 동기화**(rsync 증분). 백업 대상 = 코퍼스(reports.db 상당)·벡터 인덱스·QLoRA 어댑터 가중치(+config)·CPA 검수 골드셋·라벨셋 — 재현 불가하거나 비싼 자산 전부. 사업보고서 원문 자체는 DART 재수집 가능(3~5일)하지만 백업이 훨씬 저렴.
- **계약 종료·서버 소멸 시**: 로컬 백업 → 신규 서버(Render 영구 디스크·VPS 등)로 복원. 로컬 백업본의 역할은 방문자 서빙이 아니라 **복구용**(개인 PC는 공개 서버가 아님).
- **원칙 예외 명문화**: "데이터 정본은 모듈별 로컬 SQLite" 원칙(루트 CLAUDE.md)의 공식 예외로 "운영 코퍼스 정본 = GPU 서버, 로컬 = 자동 백업"을 리더 결정으로 기록(valuechain D11의 shared 승격 예외와 같은 방식). 루트 CLAUDE.md·docs/ARCHITECTURE.md 반영은 api/ 구현 착수(P1) 시 D11 명문화와 함께 진행.

**GPU 서버가 끊겼을 때 — 화면별 폴백 체인 (C1에 포함):**
- 대시보드·갤럭시·3탭: 애초에 정적 파일(Pages 서버)에서 fetch → GPU와 무관, 항상 동작
- 사업보고서 데이터: 핵심 기업 N개의 JSON은 정적으로 계속 커밋 → `/api/reports/...` 실패 시 정적 커밋본으로 자동 폴백
- 챗봇: api까지 내려간 경우 "챗봇 일시 중지" 안내로 우아한 저하 — 사이트 나머지는 정상

**회사 수가 늘면 — `report_<ticker>.json` 정적→동적 전환:**
- 지금: 회사별 조각 JSON을 커밋 → GitHub Actions가 GitHub Pages에 게시(배포) → 브라우저가 그 서버에서 파일을 내려받음(서빙). 현재 12사 × ~300KB.
- 전환 임계: 커밋 용량 리포 +100MB 수준(≈300사 안팎)이 되면 파일 커밋을 멈추고 `/api/reports/<ticker>` 동적 서빙으로 전환 — 현재 `build_report_source.py`(`modules/report/report_source.py`) 로직을 api 핸들러로 이전, 응답 캐시 가능.
- 프론트가 고칠 곳은 "가져오는 주소" 1곳뿐 — C1이 이를 보장.

## 6. 호스팅 확정안 + 검토한 대안

**원칙: 이미 가진 것으로 시작(추가 고정비 0원), 각 계층은 언제든 이사 가능하게(계약 기반 분리).**

### 6.1 확정안 — GPU 동거

| 계층 | 선택 | 이유 | 고정비 |
|---|---|---|---|
| 프론트(정적) | GitHub Pages 유지 | 이미 자동 배포 가동 중. 무료. 나중에 Cloudflare Pages로 이사해도 정적 파일이라 이사=업로드 | 0원 |
| api 서버 | GPU 서버에 FastAPI 동거 + Cloudflare Tunnel로 외부 노출 | 코퍼스·GPU와 같은 곳 = 데이터 이동 없음. 이미 임차 중. Tunnel은 포트 개방 없이 HTTPS 자동 | 0원(+도메인 ~1.5만원/년 권장) |
| 벡터 인덱스·코퍼스 | GPU 서버 `/data` = 운영 정본 + 로컬 = 야간 자동 백업 | §5 | 0원 |
| 사용자·학습 DB | 지금 도입 안 함 → 학습 레이어 단계에 Supabase 무료 티어 | 챗봇 MVP는 로그인 없음. shared/models.py가 이미 Supabase 타깃 스키마 | 0원 |
| LLM(답변 생성) | 외부 API(Gemini 무료 티어 시작, 품질 필요 시 Claude) | C1~C5 설계 그대로 | 사용량 과금 |

**Render의 역할 — 이사 후보 1순위(지금 사용 안 함):** 유일한 상시 서버가 임차 GPU라는 리스크(계약 종료 = api 소멸)의 대비책. api를 Docker/기동 스크립트로 이식 가능하게 만들면, 계약 종료 시 [로컬 백업(§5) + git의 api 코드] → Render(영구 디스크) 또는 저가 VPS로 재기동. 프론트는 `DISCLOSE_API_BASE` 1개만 교체(C1 보장).

**주의사항**: GPU 서버는 재부팅 시 수동 재기동 필요(systemd 미영속화, §4.1) — api·Tunnel 기동 스크립트에 재기동 로직 포함 필요.

### 6.2 검토한 대안 — Supabase + Vercel (승격 경로로 병기)

| 구성 요소 | 역할 |
|---|---|
| 미들웨어 | Vercel 서버리스 함수(`api/chat.py` 파일 = 엔드포인트, 파일 기반 라우팅) |
| 벡터 검색 | Supabase pgvector |
| 코퍼스 | **가공물만 적재** — 원문 전체(35GB)는 올리지 않음 |

**적재 전략 — "GPU는 가공 공장, Supabase엔 가공물만":** GPU에서 청킹·임베딩을 배치 처리해 JSONL(청크 텍스트+벡터+메타데이터)로 export → Supabase에 멱등 upsert. 규모: 48사 ≈0.3GB(무료 티어 내), 전 상장사(~200만 청크) ≈10~20GB(Pro ~$25/mo+).

**왜 이 조합에선 GPU 디스크를 그대로 못 쓰는가**: Vercel 함수는 Vercel 데이터센터에서 실행되고 GPU 디스크는 물리적으로 다른 컴퓨터에 있다. SQLite·인덱스 파일은 같은 컴퓨터의 프로그램이 직접 여는 방식이라 네트워크 너머에서 읽을 수 없다(원격 조회가 되는 건 Postgres 같은 "접속형" DB). 데이터 위치가 조합을 결정한다: 정본=GPU 디스크 → GPU 동거 / Vercel+Supabase → 정본을 Supabase로 이사(공식 개정 필요, 로컬 백업본이 이사 소스).

**장점**: GPU 서버가 죽거나 계약이 끝나도 챗봇 완전 생존. git push 자동 배포 + 브랜치 프리뷰 내장. 학습 레이어(로그인·사용자 DB) 도입 시 Supabase가 어차피 필요.

**남는 마찰 — 질의 임베딩**: 질의 임베딩 모델은 인덱스를 만든 모델과 같아야 하는데 서버리스엔 대형 모델을 못 올린다. 완화: (a) Supabase 내장 소형 모델(gte-small)로 통일 (b) 소형 모델을 GPU 인덱싱·함수 질의 양쪽에 사용 (c) 질의만 GPU 호출(GPU 다운 시 검색 불능). 팀원 임베딩 모델 확인(C2) 후 결정.

**"코드 몇 줄로 미들웨어 없이 완결" 주장의 검증 — 절반 참**: 사용자 데이터(로그인·학습 기록)는 Supabase RLS(행 단위 보안 규칙)로 브라우저 직접 접근이 정말 가능 — 학습 레이어 승격 시 그 부분 백엔드 공수가 거의 소멸. 그러나 AI 챗봇은 LLM 키 은닉·인용 강제 검증·면책 강제·rate limit이 브라우저에 둘 수 없어 서버측 코드가 여전히 필요 — 다만 Vercel에서는 "상주 서버 운영"이 사라지고 "미들웨어 코드"만 함수 파일로 남는다. C1~C5 계약은 함수 형태로도 동일하게 이식 가능(계약은 호스팅 형태 무관).

### 6.3 확정안 vs 대안 — 전환 트리거

| 상황 | 선택 |
|---|---|
| 지금 (GPU 임차 중, 팀원 인덱스 미완 — §4.1 실사 확인) | **GPU 동거로 시작** (0원, 코퍼스 이동 없음) |
| 학습 레이어(로그인·사용자 데이터) 도입 시점 | Supabase 승격 검토 — RLS 덕에 사용자 데이터 백엔드 공수 최소 |
| GPU 서버 계약 종료 임박 | §5 로컬 백업에서 Render 또는 Supabase 승격 중 택1 |
| 어느 쪽이든 | C1~C5 계약은 불변 — 호스팅 형태와 무관하게 설계됨 |

## 7. CD(자동 배포) 설계

원리: **머지 = 배포**가 되려면 배포 과정 전체가 GitHub Actions 워크플로로 적혀 있고 사람 손 단계가 0이어야 한다.

| 계층 | 지금 | 설계(파이프라인 정의만 — §7.1) |
|---|---|---|
| 프론트(정적 파일) | dev push → Pages 자동 게시([pages.yml](../.github/workflows/pages.yml)) | main push → Pages 자동 게시로 전환(§7.1). dev push는 기존 [ci.yml](../.github/workflows/ci.yml)이 자동 검증(black·sync_codex·pytest) |
| api 서버 | 없음 | main 머지 시 Actions가 GPU 서버로 SSH 접속 → 코드 갱신 → 재기동(§7.1 3단계). Render 등으로 이사해도 접속 대상만 교체 |
| 데이터 JSON | build_data 실행 후 커밋 → 프론트 배포에 자연히 포함 | 현행 유지 |
| 코퍼스·인덱스(대용량) | git 밖 | git·자동 배포 대상 아님 — §5 동기화 스크립트로 관리 |

### 7.1 브랜치 배포 흐름 — 파이프라인 정의 (⚠️ 실제 main 병합은 미실행)

> 이번 세션은 **파이프라인 정의(설정 변경)까지만** 수행한다. `pages.yml` 트리거를 `main`으로 바꿔 두더라도, dev→main 병합 자체는 별도 명시적 결정 없이는 실행하지 않는다 — main 병합 = 실서비스 최초 발행이라는 큰 액션이므로 리더가 별도 시점에 판단.

전제: GitHub Pages는 저장소당 사이트 1개라 dev·main 두 주소를 GitHub만으로 만들 수 없다. 단계적으로 구현한다.

**1단계 (설정 변경 — 이번 세션에 반영, 실행은 보류):**
- `pages.yml`의 발동 조건을 `dev` → `main`으로 변경 → 이후 **main 머지 시점에** "실서비스 자동 배포"가 성립하도록 준비. 수동 실행 버튼(workflow_dispatch)은 유지.
- dev는 Pages를 더 이상 발행하지 않되, 기존 `ci.yml`이 push마다 자동 검증(black·sync_codex·pytest)하므로 "머지 확인은 GitHub Action으로 가능"은 유지된다.
- **부작용 고지**: 이 설정이 dev에 머지되는 순간부터, 지금까지 dev push마다 갱신되던 라이브 Pages 사이트는 **다음 main 병합 전까지 더 이상 갱신되지 않는다** (직전 상태로 고정). 실서비스 첫 발행(= dev→main 병합)은 리더가 별도로 결정·실행.

**2단계 — 스테이징 URL이 필요해지면 (사용자 계정 작업 필요):**
- Cloudflare Pages에 저장소 연결: production branch = main, 그 외 브랜치는 자동 프리뷰 주소 — "dev=스테이징 / main=실서비스"가 계정 연결만으로 완성.
- 완료되면 `pages.yml`은 삭제(중복 배포 방지). §6.2 Supabase+Vercel 승격 시엔 Vercel 프리뷰가 이 역할을 대신함.

**3단계 — api 서버의 자동 배포 (api/ 코드가 생기는 후속 P1에서):**
- `.github/workflows/deploy-api.yml` 신설: main 머지 시 Actions가 GPU 서버로 SSH 접속(저장소 Secrets에 키 보관) → 코드 갱신 → 재기동 스크립트 실행.

## 8. 후속 구현 로드맵 (이번 세션 범위 밖)

1. **P1 — api/ 스켈레톤**: FastAPI 앱, `/api/health`, 면책 미들웨어(C5), `/api/chat`이 우선 외부 LLM 프록시로만 동작(검색 없이) — GPU 없이도 로컬에서 E2E 동작 확인 가능
2. **P2 — RAG 연결**: 팀원 벡터 인덱스 실물 확인 → C2 계약과 대조·확정 → api가 검색 결과를 인용 강제 프롬프트에 결합
3. **P3 — 코퍼스 확장 동조**: `/data/discloseai/fulltext/`(§4.1) 정체 확인 후 report 파이프라인과 정합 또는 재수집. valuechain D11(reports.db shared 승격)과 시점 조율
4. **P4 — 호스팅 실행·공개**: §6 결정에 따라 Cloudflare Tunnel·도메인 연결, `pages.yml` main 트리거 실제 발동(=dev→main 병합), Gemini 키 로테이션 후 서버측 주입

기존 로컬 데모용 FastAPI 2종(`modules/disclosure/chat_server.py`, `modules/price/api.py`)은 api/ 안정화 후 각 담당자와 협의해 통합 또는 은퇴 결정 — 리더가 임의로 수정하지 않는다(모듈 경계 원칙).
