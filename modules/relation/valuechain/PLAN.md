# ValueChain — 밸류체인 레이어 실행 계획 (relation v2)

> 상태: **계획 수립 완료 · 실행 대기**
> 개정: v1.1 (2026-07-15) — ① reports.db shared 승격 반영 ② 처음부터 전 상장사 대상
> ③ 튜닝 하네스 정밀화(청킹·검증 2패스·운영점 튜닝) ④ 기업 추가·변경 증분 메커니즘 신설
> 개정: v1.2 (2026-07-15) — ⑤ 실행 주체 분담 명시(§0.5) ⑥ 기준점·성공/중단 판정 정본화(§3.7)
> ⑦ 루프 경계 요약표(§4.6) — 재현율 하한·최대 라운드 등 무인 루프 완주 조건 확정
> 개정: v1.3 (2026-07-21) — ⑧ universe(전 상장사 지배구조 확장) 계획과 상호 참조:
> V0 CompanyRegistry에 universe 컬럼 동시 반영, §5 엣지 문법의 레이어 분리 명시
> 개정: v1.4 (2026-07-21) — 착수 전 코드 실측 재검토 반영: ⑨ 진입 위치를 v2 셸 EgoView로
> 확정(리더 결정 — "FINANCIALS 탭"은 실재하지 않음) ⑩ reports.db 경로 상수 실측(1곳 아님 —
> 코드 4곳+테스트 1곳+문서 5곳) ⑪ GPU 서버 접속 복구(2026-07-21) 반영 — V2+ 차단 해제
> ⑫ 학생 베이스 모델 "Qwen3 고정" 해제 — B0에서 최신 릴리스 포함 4기준 재선정(§3.4·§4.2)
> ⑬ 시각화 엣지 검증 하네스 V 신설([../universe/PLAN.md](../universe/PLAN.md) §5.5 — V-1 계약 체커는 V1 export와 동시 작성)
> 소유: relation 모듈 (리더). 실행 시 이 문서의 Phase 체크박스를 세션마다 갱신.
> 관련: [../PLAN.md](../PLAN.md)(지배구조 v1), [../universe/PLAN.md](../universe/PLAN.md)(전 상장사 지배구조 확장 · universe 시각화),
> [../CLAUDE.md](../CLAUDE.md)(모듈 규칙),
> [../../../docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md), 루트 [DESIGN.md](../../../DESIGN.md)

---

## 0. 목표

### 제품 목표
v2 셸 EgoView(기업 클릭 상세 관계망, [../universe/PLAN.md](../universe/PLAN.md) LOD-2)에
**지배구조 / 밸류체인 레이어 토글**을 두고, 앵커 기업 중심의 전방(공급처)·후방(고객사)
흐름을 공시 근거와 함께 시각화한다. ★v1.4: 진입 위치를 셸 단일로 확정 — dossier 탭
진입은 비목표(구 "FINANCIALS 탭" 전제는 실재하지 않는 탭이었음. dossier 3탭 =
business/galaxy/eqs, 지배구조 시각화는 셸 bundle.jsx에만 존재).
갤럭시 → 섹터 클러스터 → 기업 진입 동선은 현행 유지.
**대상은 처음부터 전 상장사(코스피+코스닥, ~2,600사)** — 밸류체인 엣지는 을(乙) 쪽
중소형사 공시에서 흘러나오므로(비대칭 공시) 코스닥 소재·부품·장비사가 빠지면
대기업 노드의 엣지 밀도가 성립하지 않는다.

### 기술 목표 (GPU 활용의 존재 이유)
**"딥러닝으로 도메인 맞춤형 AI를 직접 만들었다"를 참으로 만든다.**
- 사업보고서 서술문에서 공급·고객·원재료·경쟁 관계를 추출하는 **한국어 금융 관계추출(RE) 모델**을
  Qwen3 QLoRA 파인튜닝으로 구축.
- 자체 라벨 데이터셋 구축 → 지도학습 → held-out 골드셋 F1 평가 → SGLang 서빙까지
  **ML 전 생애주기**를 밟는다.
- 성과 입증은 3행 비교표: `Qwen 제로샷 F1 / Claude(교사) F1 / 튜닝 Qwen F1`.
  튜닝 모델이 제로샷을 크게 상회하고 교사에 근접하는 **델타**가 산출물이다.

### 비용 목표
- galaxy(현금 은하수)는 기업당 고품질 산문 생성이라 Claude 토큰 소모가 크다.
  밸류체인은 반대로 **좁은 추출 과제 × 대량 반복**(수십만 청크, 매년 갱신)이므로
  로컬 GPU 배치 추론이 구조적으로 유리. Claude는 교사 라벨(1회성 소액)에만 사용.

### 비목표 (Non-goals)
- ❌ LLM 산문 생성 — galaxy에서 이미 실패 확인(제로샷 32B는 열린 글쓰기 불가). 추출만 한다.
- ❌ 투자 조언 — 교육 목적. "과거 통계·공시 기반 참고 정보" 문구 준수.
- ❌ 전체 관계망 한 화면 렌더 — 헤어볼 금지. §5 렌더링 정책이 유일한 표현 문법.
- ❌ 완전 커버리지 — 공시로 입증 가능한 엣지 + 통계 백본까지만. 근거 없는 엣지는 그리지 않는다.

---

## 0.5 실행 주체 분담 — 누가 무엇을 하는가 ★v1.2

| 주체 | 담당 | 경계 규칙 |
|---|---|---|
| **Claude Code (구현자 + 루프 드라이버)** | 하네스 **전 코드 구현**(청커·정형 파서·학습 config·evaluate.py·export·멱등 테스트) + **루프 오케스트레이션**(GPU 서버 SSH/CLI 실행, 게이트 판정 집행, B5 오류분석, PROGRESS.md 기록) | 게이트 판정은 evaluate.py **산출값만** 근거로 — 주관 판정 금지. galaxy MILKYWAY 드라이버와 같은 "드라이버 스킬 + 정량 게이트" 패턴 |
| **A100 GPU (계산 엔진)** | QLoRA 학습 실행(LLaMA-Factory), 배치 추론 실행(SGLang) | 코드를 만들지 않는다 — 루프 안의 학습·추론 스텝을 실행하는 계산 자원. 산출물은 어댑터(가중치)뿐 |
| **Claude API (교사)** | 라벨 생성(하네스 A), 베이스라인 상한 측정(B0 ②행) | 1회성·증분만. **학생 채점에 관여 금지** (순환 채점 차단 — 채점은 CPA 골드셋) |
| **사용자/CPA (검수자·결정권자)** | val 표본·test 100% 검수, 섹터 스팟체크(C6), 별칭 보정(M2), 중단/속행 최종 결정 | 사람 개입 지점은 이 4곳뿐 — 그 외 루프는 무인 완주 가능해야 함 |

즉 **"GPU로 학습하고, 구현은 Claude Code"가 맞다.** 정확히 말하면: Claude Code가
하네스를 코드로 만들어 루프를 돌리고, GPU는 그 루프 안에서 학습·추론이라는 계산만
수행한다. 모델(어댑터)은 GPU의 산출물, 코드·판정·기록은 전부 Claude Code의 산출물이다.

---

## 1. 확정된 설계 결정 (논의 요약)

| # | 결정 | 근거 |
|---|---|---|
| D1 | 출처는 **DART · 공정위 · 한국은행** 3원천 + 통계청 KSIC(분류 매핑용) | 전부 공적 원천 — 신뢰도 문제 없음 |
| D2 | 엣지는 **신뢰등급 3단**: T1 정형 공시 명시 / T2 서술문 모델 추출 / T3 산업연관표 추정 | 노이즈는 제거가 아니라 등급 표시로 대응 |
| D3 | **처음부터 전 상장사(~2,600) 대상** — 코스피 한정·단계 확장 안 함. 비대칭 공시(K-IFRS 1108 10% 고객)상 엣지는 코스닥 중소형사 공시에서 나온다 | v1.1 변경: 코스피→전체 단계 확장 폐기 |
| D4 | 밸류체인은 업종을 가로지른다 — **"산업군 내 한정" 금지**. 노드 소속 업종은 1개(색·위치용), 엣지는 업종 경계 자유 | 다업종 납품 소재주 엣지케이스 자동 해소 |
| D5 | 시각화는 **앵커 중앙 ego 1-hop**만: 상류(공급처) 위 → 앵커 중앙 → 하류(고객) 아래. 2-hop은 렌더 금지, 노드 클릭 시 **재구성(re-root)** + 브레드크럼 | 피라미드(앵커 최상단)는 방향 정보 상실 + 재구성 시 상류 그릴 자리 없음 |
| D6 | 발산 억제: 사이드당 **Top-N(5~8)** (등급→금액→최신성 랭킹), 나머지는 **묶음 노드** → 사이드 패널 리스트, 2-hop은 배지 힌트만 | 지배구조 뷰의 검증된 밀도 유지 |
| D7 | **데이터 정책과 렌더링 정책 분리**: relation.db에는 확보 엣지 전부 저장, Top-N·묶음은 뷰가 자를 뿐 | 랭킹 기준 변경 시 재수집 불필요 |
| D8 | 경계: **relation = 데이터 생산, integration = 화면 소유**. 기존 계약 `graph_top50.json` 불변, 밸류체인은 별도 export 신설 | CLAUDE.md 경계 원칙 |
| D9 | GPU 스택 유지: **A100 80GB + SGLang + Qwen3**. 역할만 "학습(시분할) + 과제 전용 어댑터 서빙"으로 전환 | 기존 세팅 폐기 없음 |
| D10 | 진행 방식: 수집은 전량 선행(D3), **추출·QA는 섹터 단위 증분** — 반도체 파일럿(골든) → 검증 → 섹터별 확산 | 골든→확산 패턴, 수정 용이 |
| D11 | **reports.db를 `shared/data/`로 승격** (리더 결정, v1.1). 쓰기 소유는 report 모듈 수집기 단독, 타 모듈은 read-only. relation의 자체 원문 수집(구 VcSectionCache) 폐기 | 이중 수집 해소. "정본=모듈 로컬" 원칙의 공식 예외 → ARCHITECTURE·루트 CLAUDE.md 명문화 필수 |
| D12 | **모든 증분 처리는 멱등(idempotent)** — 자연키 unique 제약 + upsert, 재실행이 중복·유실을 만들지 않아야 함 | 기업 추가·변경 시 실수 없는 확장 (§4.5) |

---

## 2. 데이터 아키텍처

### 2.1 공유 코퍼스 계층 — reports.db shared 승격 (D11)

```
shared/data/reports.db          ← modules/report/data/reports.db 이동(승격)
  쓰기: modules/report 수집기만 (report_raw · report_section · fs_account · pipeline_state)
  읽기: relation(밸류체인 추출) · 기타 모듈 read-only
```

- **승격 마이그레이션 태스크** (V0): ★v1.4 실측 — 경로 변경 지점은 "1곳"이 아니라 아래 전부.
  0. `shared/data/` 디렉터리 **신규 생성** (현재 미존재)
  1. 파일 이동 + 경로 참조 일괄 변경:
     - 코드 4곳: `modules/report/db.py:8` · `series.py:89` · `report_source.py:26` ·
       `check_golden.py` 373·565행 (db.py 외 3파일은 각자 경로를 재정의 — import 미경유)
     - 테스트 1곳: `tests/report/test_series_golden.py:17`
     - 에이전트·스킬 문서 5곳: `.claude/agents/note-extractor.md` ·
       `accuracy-verifier.md` · `completeness-auditor.md` · galaxy-golden `SKILL.md`
       (`.claude/`·`.agents/` 미러 양쪽 — 미러는 sync_codex 재실행으로)
     - 변경 후 **galaxy 파이프라인 회귀 확인 필수** + `grep -r "report/data/reports.db"` 잔존 0건
  2. 루트 CLAUDE.md "데이터 정본은 모듈별 로컬 SQLite"에 예외 명문화:
     *"shared/data/ = 리더 승인 공유 코퍼스. 쓰기 소유 모듈 1개 명시, 그 외 read-only"*
  3. docs/ARCHITECTURE.md DB 토폴로지(§3.5) 갱신 — reports.db는 현재 §3.5 표에
     행 자체가 없음 → **행 신설**(위치=shared/data/, 쓰기=report 단독) + §2 폴더 표 갱신
  4. `scripts/sync_codex.py` 재실행 (미러 갱신)
- **수집 확장**: report 모듈 수집기를 전 상장사 × 5개년으로 확장. 우선 섹션 =
  `II.사업의내용` + 연결주석(특수관계자 포함). 실측 기반 추정: 48사 646MB → 2,600사 ~35GB,
  DART 한도(1만 건/일) 내 3~5일 분량. 디스크 200GB 내 여유.
- relation은 `shared/data/reports.db`의 `report_section`을 직접 읽는다.
  **relation 쪽 원문 캐시 테이블은 만들지 않는다** (이중 정본 금지).

### 2.2 신규 테이블 (`storage/models.py` 확장 — 전부 relation.db)

```python
class CompanyRegistry(Base):         # 전 상장사 마스터 (기존 CompanyNode의 전수 확장)
    corp_code     # PK, DART 8자리
    ticker        # 6자리 (상폐 시 보존)
    name_current  # 현재 사명
    market        # KOSPI | KOSDAQ
    ksic_code / io_sector            # KSIC ↔ 산업연관표 부문 (§D1 매핑)
    listing_status  # listed | delisted(일자) | merged(승계 corp_code)
    synced_at     # 마스터 동기화 시각 (§4.5 루프가 갱신)

class CompanyAlias(Base):            # 엔티티 링킹용 별칭 사전 ★링킹 정확도의 관건
    corp_code / alias / alias_kind   # 구사명 | 약칭 | 영문명 | 그룹관용명
    valid_from / valid_to            # 사명 변경 이력 (5개년 보고서의 과거 표기 매칭)
    source        # dart_history(자동) | manual(수동 보정 큐)

class ValueChainEdge(Base):          # 밸류체인 엣지 정본
    id
    src_corp / dst_corp              # corp_code. 방향 = 물자 흐름(공급자→수요자)
    edge_type     # supply | customer | raw_material | competition
    tier          # T1 | T2 | T3
    source_kind   # rp_note | supply_contract | equity_inv | biz_prose | io_table
    rcept_no      # 근거 공시 접수번호
    provenance    # 섹션key + 청크id + 원문 문장 (T2 필수)
    amount        # 거래금액 (있으면 — 엣지 가중치)
    as_of         # 사업연도 (연도 스냅샷 — 삭제 대신 보존)
    extractor_ver # T2: 어댑터·프롬프트·임계값 버전 (재현성·역추적)
    confidence    # T2: 보정된 모델 신뢰도 (§3.6 운영점과 함께 사용)
    status        # active | superseded (정정공시 대체 — §4.5)
    superseded_by # 대체한 엣지 id (nullable)
    # UNIQUE(src_corp, dst_corp, edge_type, as_of, rcept_no)  ← 멱등 upsert 키 (D12)

class SectorIOEdge(Base):            # T3 업종 백본 (한국은행 산업연관표)
    src_sector / dst_sector / flow_amount / io_year

class VcChunk(Base):                 # 추출 단위 = 문장 윈도우 청크 (§3.1)
    chunk_id      # rcept_no + section_key + seq → 결정적 생성 (재실행 동일 id)
    rcept_no / corp_code / section_key
    text / char_span                 # 원문 오프셋 (provenance 역추적)
    has_candidate # 후보 게이트 통과 여부 (§3.1 ①단계)

class VcPipelineState(Base):         # 배치 체크포인트 — 처리 단위는 청크
    chunk_id / stage(extract|verify|link|load)
    status(pending|done|failed|requeued|skipped) / attempt / extractor_ver / updated_at

class LinkFailQueue(Base):           # 엔티티 링킹 실패 큐 → 수동 별칭 등록 워크플로
    surface_form / freq / sample_chunk_id / resolved_corp(nullable)
```

### 2.3 export 계약 (integration과의 신규 계약)

- 기존 `graph/export.py → data/graph_top50.json`(지배구조) **불변**.
- 신설 `valuechain/export.py → data/valuechain.json`:

```jsonc
{
  "as_of": "2025",
  "edges": [
    { "src": "00126380", "dst": "01234567", "type": "supply",
      "tier": "T1", "amount": 1200, "src_sector": "반도체소재", "prov": "..." }
  ],
  "sector_io": [ { "src": "화학", "dst": "2차전지", "flow": 3400 } ]
}
```

- status=superseded 엣지는 export 제외. 스키마 변경 시 integration/CLAUDE.md
  "데이터 소스 계약" + ARCHITECTURE 동시 갱신 (D8).

---

## 3. ML 파이프라인 — 교사-학생 증류 (v1.1 정밀화)

### 3.1 추출 단위: 섹션이 아니라 **문장 윈도우 청크** ★v1.1 구조 변경

v1의 "섹션 통째 입력"은 작동하지 않는다 — `II.사업의내용`은 수만~수십만 자로
컨텍스트 한도를 넘거나 주의(attention)가 희석되어 근거 회수율이 급락한다. 개정:

```
① 후보 게이트 (CPU, 모델 무관):
   섹션 → 문장 분할 → 기업명 후보(레지스트리+별칭 사전 매칭) 또는
   관계 어휘("매출처·공급·납품·매입·경쟁·원재료…") 포함 문장만 후보로
② 청킹: 후보 문장 ± 2문장 윈도우 (중복 병합, 최대 ~1.5K자) → VcChunk
③ LLM 추출은 후보 청크만 — 전체 문장의 소수만 GPU에 태움
   (무관계 대부분을 ①이 걸러 클래스 불균형·추론량 동시 해결)
④ 섹션 레벨 병합: 동일 (상대, 유형) 관계 dedupe — 최고 confidence 채택
```

### 3.2 라벨 스키마 (교사·학생 공통 — SGLang xgrammar로 디코딩 강제)

```jsonc
{
  "relations": [
    {
      "counterparty": "삼성전자",        // 원문 등장 표기 그대로. 익명이면 null
      "anonymous": false,
      "direction": "customer",           // customer | supplier | competitor | raw_material
      "status": "active",                // active | past | planned  ← "과거 납품" 오염 차단
      "evidence": "당사의 주요 매출처는…", // 원문 문장 그대로 (provenance, exact-match 검증됨)
      "sector_hint": "반도체"
    }
  ]
}
// relations: [] = 관계 없음 — 1급 출력. 원문에 없는 상대명 생성 = 오답(환각 억제가 학습 목표)
```

### 3.3 데이터셋 3분할 + 하드 네거티브

| 셋 | 규모(초기) | 라벨 주체 | 용도 |
|---|---|---|---|
| train | 3,000~5,000 청크 | Claude(교사) 2회 추출 자기일치분 | QLoRA 학습 |
| val | 400 | Claude → CPA 표본 검수 | 학습 게이트·운영점 튜닝 |
| test(골드) | 500 | **CPA 100% 검수 후 봉인** | 최종 1회 평가만. 순환 채점 차단 |

- 층화: 시장(코스피/코스닥) × 섹터 × 패턴(명시/익명/경쟁/원재료/무관계).
- **하드 네거티브 필수 포함** (①게이트를 통과했지만 관계가 아닌 청크):
  경쟁사 나열, past 관계, 계열사 단순 언급, 산업 동향 서술 속 타사명, 고객이 아닌 인용.
  → 이 유형들이 실전 오탐의 대부분 — 학습 분포에 의도적으로 과표집.
- 증강: 상대 기업명 치환(entity swap)으로 표기 일반화 (특정 사명 암기 방지).
- CPA 검수 골드셋은 그 자체로 고유 자산 (공개 데이터셋화 검토).

### 3.4 학습 레시피 (구체화)

| 항목 | 값 (초기) | 비고 |
|---|---|---|
| 베이스 | Qwen3-14B / 32B + **실행 시점 최신 오픈 릴리스**(예: Qwen3.5·Qwen3-Next 계열 등장 시 후보 포함) ★v1.4 | "Qwen3 고정" 해제 — B0에서 4기준 재선정: ⓐ SGLang 서빙+xgrammar 지원 ⓑ LLaMA-Factory QLoRA 지원(신형 아키텍처는 툴체인 지원 지연 리스크) ⓒ val 제로샷 F1 ⓓ A100 80GB 서빙·학습 동시 수용. 메모: galaxy에서 본 GPU 오류는 **열린 산문 생성** 실패 — 본 과제는 스키마 강제 좁은 추출+2패스 검증+τ 운영점이라 실패 양상이 다름. 다만 베이스 업그레이드는 B0 비용이 낮으므로 항상 후보군에 포함 |
| 방식 | QLoRA 4-bit NF4, LoRA r=32 α=64, all-linear target | LLaMA-Factory config 커밋 |
| 손실 | **completion-only** (출력 토큰만 loss — 프롬프트 마스킹) | 추출 SFT 표준 |
| 시퀀스 | 2K (청크 ≤1.5K자 전제) | 청킹 덕에 짧다 — 처리량↑ |
| lr / epoch | 1e-4 cosine / 2~3ep + val F1 조기종료 | 과적합 시 r↓ |
| thinking | **비활성** (`enable_thinking=False` / `/no_think`) | Qwen3 하이브리드 사고모드는 추출 과제에 불필요 + 처리량 수 배 하락 |
| seed·버전 | seed 고정, dataset_v{r}·adapter_v{N} 태깅 | 재현성 |
| 확장 옵션 | SFT 수렴 후 **DPO 라운드** — (정답 추출, 환각 추출) 쌍으로 환각 억제 선호학습 | G-B 통과 못할 때만 투입 |

### 3.5 추론 구조: 추출 → 검증 2패스 ★v1.1 추가

판별은 생성보다 쉽다 — 정밀도를 임계값 이전 단계에서 한 번 더 끌어올린다:

```
패스1 추출: 청크 → relations JSON (greedy, 스키마 강제)
패스2 검증: 추출된 각 관계에 대해 같은 모델(또는 검증 전용 경량 어댑터)에
  "evidence 문장이 (상대, 방향, 현재성) 관계를 지지하는가?" → yes/no + 확신도
  no → 폐기. yes → confidence에 반영
```
- 비용: 관계가 나온 청크(소수)에만 2패스 — GPU 배치라 한계비용 미미.
- 하네스 B의 ablation 항목: 검증 패스 유/무 정밀도 비교 (기여 입증).

### 3.6 운영점(operating point) 튜닝 ★v1.1 추가 — 정밀도 0.90의 보장 장치

모델이 "알아서" 0.90을 내주길 기대하지 않는다. **val 셋에서 confidence 임계값 τ를
스윕해 정밀도 ≥ 0.90을 만족하는 최대 재현율 지점을 선택**하고, 그 τ를 어댑터 버전에
함께 태깅한다(extractor_ver에 포함). τ 미달 관계는 폐기가 아니라
`tier=T2, confidence<τ`로 저장만 하고 **export에서 제외** — 훗날 임계값 완화 시 재수집 불필요 (D7).

### 3.7 기준점 · 성공/중단 판정 — 루프 경계의 정본 ★v1.2 명확화

**평가 프로토콜 (3행 모두 동일 조건 — 이를 벗어난 비교는 무효):**
- 동일 val/test 청크 · 동일 §3.2 스키마(xgrammar 강제) · 동일 링킹·후처리 · 동일 프롬프트 골격
- 지표 = (counterparty, direction, status) **튜플 단위 micro P/R/F1**
- 채점 기준은 항상 CPA 골드셋 (Claude 산출물로 채점 금지 — §0.5)

**기준점 3행 (B0에서 측정·확정 후 불변):**

| 행 | 시스템 | 역할 |
|---|---|---|
| ① | Qwen3-14B 제로샷 (32B 참고 병기) | **하한 기준점** — 튜닝 델타의 분모. "학습이 만든 개선"의 시작선 |
| ② | Claude 교사 | **상한 기준점** — 증류가 근접해야 할 천장 |
| ③ | 튜닝 Qwen @운영점 τ | 산출물 — ①·② 사이 어디에 도달했는가가 성과 |

**성공 판정 S1~S3 (test 봉인셋 1회, 부트스트랩 95% CI 병기):**
- **S1** 운영점 정밀도 ≥ 0.90 **AND 재현율 ≥ 0.50** — 재현율 하한 필수.
  (하한이 없으면 τ→1로 거의 아무것도 추출하지 않아도 "정밀도 달성"이 성립하는
  공허한 통과가 가능 — 이 구멍을 봉쇄)
- **S2** 튜닝 F1 ≥ 제로샷(①) F1 + 15pt — 학습 델타의 최소선
- **S3** 튜닝 F1 ≥ Claude(②) F1 − 5pt — 목표치. 미달해도 S1·S2 충족 시 배포 가능(기록만)
- 배포 조건 = **S1 AND S2**. S1·S2는 필수, S3는 스트레치.

**중단(abort) 판정 — 무한 루프 차단:**
- 하네스 B **최대 6라운드(+DPO 투입 시 8)** 안에 val에서 S1·S2 상당 기준 미달 → 중단.
  T1 전용 서비스 유지, 결과·원인 그대로 PROGRESS.md 기록 (부정적 결과도 성과 원장에 남김)
- val F1 **3라운드 연속 하락** → 즉시 중단·원인 분석 (라벨 오염·과적합 의심)
- 봉인 test 평가는 **1회뿐, 재시도 금지** — 실패 시 τ·모델을 test에 맞춰 고치는 순간
  테스트셋이 오염되어 3행 비교표 전체가 무효가 된다

**최종 산출:** 3행 비교표(CI) + 유형별 혼동행렬 + ablation(검증 패스 유/무, 14B vs 32B)
→ PROGRESS.md 기록

---

## 4. GPU 하네스·루프 설계 ★필수 명시 사항★

> 원칙: 모든 루프는 **게이트(정량 기준) 통과 전 다음 단계 진입 금지**,
> 모든 배치는 **체크포인트 재개 가능 + 멱등**(재실행 안전, D12),
> 모든 산출물은 **버전 태깅**(어댑터·데이터셋·임계값·config).

### 4.0 GPU 운용 모드 (시분할)

```
[서빙 모드 — 상시(주간)]
  SGLang 1인스턴스: 베이스 Qwen3
    + LoRA 어댑터 #1 (RAG 챗봇 — 팀원)      ← --lora-paths 멀티어댑터 동거
    + LoRA 어댑터 #2 (관계추출 — 본 계획)
    + 임베딩 모델 (소형, 동일 GPU 상주)

[학습 모드 — 배치(야간/주말, 팀원과 시간대 합의)]
  SGLang graceful stop → GPU 전체를 LLaMA-Factory에 할당
  → 어댑터 저장 → SGLang 재기동(신규 어댑터 로드)

처리량 감각치(계획용 — 파일럿에서 실측 보정):
  14B 배치 추론 수백~수천 청크/시간 급 → 전 상장사 후보 청크(수십만)도 일 단위 완주
  14B QLoRA 학습(train 5천 청크 × 2K seq × 3ep) → 시간 단위(하룻밤 내)
디스크 예산(200GB): 베이스 ~30GB + 어댑터(수백MB×n) + 학습 체크포인트 최신 2개만
  보존(cleanup 스크립트) + shared 코퍼스 ~35GB → 여유 확보.
```

### 4.1 하네스 A — 라벨링 루프 (Claude 교사, 증분 실행)

```
A1  샘플링    : VcChunk(후보 통과분)에서 층화 샘플 (시장×섹터×패턴)
A2  교사 추출  : Claude API, §3.2 스키마. 동일 청크 2회 추출
A3  일치 필터  : 불일치 청크 → CPA 검수 큐 / 일치분 → train 후보
A4  하드 네거티브 채굴: ①게이트 통과 + 교사 "관계 없음" 청크를 유형 분류해 과표집 (§3.3)
A5  골드 분리  : val·test 배정분 CPA 검수(test 100%) 후 봉인
── 게이트 G-A: train ≥ 목표 && 하드 네거티브 ≥ 30% && 자기일치율 ≥ 85%
    미달 시 → A1 회귀 (부족 패턴 표적 샘플링)
```

### 4.2 하네스 B — 학습 루프 (A100, F1 게이트 수렴까지 반복)

```
B0  베이스라인 : ★v1.4 선행 스텝 — 최신 오픈 릴리스 웹 조사 → 후보 매트릭스(§3.4 4기준)
                작성 → 제로샷 평가 대상 확정 (교사는 Claude 유지 — 변경 없음).
                이후 제로샷 후보군 + Claude를 val로 평가 → 비교표 1·2행
                + 학생 베이스 확정 (기본 가설: 중형 튜닝 > 대형 제로샷)
┌─ 반복 (라운드 r) ─────────────────────────────────────────┐
│ B1  컴파일   : train → LLaMA-Factory 포맷, dataset_v{r} 태깅            │
│ B2  학습     : §3.4 레시피. GPU 시분할(§4.0). config·seed 커밋          │
│ B3  운영점   : val에서 τ 스윕 → 정밀도 0.90 만족 최대 재현율 τ 선택      │
│ B4  평가     : val P/R/F1(@τ) + 유형별 혼동행렬 → PROGRESS.md           │
│ B5  오류분석  : 최다 오류 유형 (past↔active, 경쟁↔고객, 링킹 실패…)      │
│ B6  증강     : 약점 유형 표적으로 하네스 A 재호출 → train 증분           │
│ B7  ablation : 검증 패스 유/무 비교 (r=1 최초 1회 + 최종 라운드)         │
├─ 게이트 G-B: val 정밀도@τ ≥ 0.90 && 재현율@τ ≥ 0.50                     │
│              && F1 개선 < 1pt 2라운드 연속(수렴). 최대 6라운드(§3.7)     │
│   수렴 실패 시 확장 옵션 투입: DPO 라운드(§3.4, +2라운드) → 재평가       │
└──────────────────────────────────────────────────────────┘
B8  봉인 평가  : test 골드셋 **1회만** — 3행 비교표 + 95% CI 확정
B9  릴리즈    : adapter_v{N} + τ + config 묶음 태깅 → SGLang 등록
```

### 4.3 하네스 C — 배치 추론 루프 (SGLang, 섹터 단위 증분)

```
C0  큐 적재   : 대상 섹터 미처리 청크 → VcPipelineState(pending)
              (청크 id 결정적 생성 — 재적재해도 동일 키, 멱등)
┌─ 청크 배치 루프 (배치 = 수백 청크) ────────────────────────┐
│ C1  추출    : SGLang batch, xgrammar 강제, adapter_v{N}+τ 고정          │
│ C2  검증    : 2패스 판별 (§3.5) — no 판정 폐기                          │
│ C3  후처리 3단 검문:                                                    │
│      ① evidence 원문 exact-match — 실패 즉시 드롭                       │
│      ② 엔티티 링킹: 표기 → CompanyRegistry + CompanyAlias(구사명 포함)   │
│         실패 → 엣지 미생성 + LinkFailQueue 적재 (빈도순 수동 보정 대상)   │
│      ③ confidence ≥ τ 판정 (미달분도 저장, export만 제외 — §3.6)         │
│ C4  적재    : UNIQUE 키 upsert → ValueChainEdge(T2) — 재실행 중복 불가    │
│ C5  상태    : done/failed, failed는 attempt<3 재큐                       │
└─ 체크포인트: 배치마다 커밋 → 중단 시 pending부터 재개 ──────┘
C6  섹터 감사 : 무작위 30건 CPA 스팟체크 → 실측 정밀도 기록
── 게이트 G-C: 스팟 정밀도 ≥ 0.85 → 다음 섹터 진행 승인
    미달 → 오류 유형을 B5로 환류, 어댑터 재학습 후 해당 섹터만 재추론
    (extractor_ver 갱신 → 구버전 엣지는 superseded 처리, 삭제 안 함)
```

### 4.4 연간 갱신 루프 (사업보고서 시즌)

```
report 수집기(shared)가 신규 연도 적재 → 하네스 C 증분 실행(신규 rcept_no 청크만)
→ as_of 연도 스냅샷 추가 (구엣지 보존 — 타임머신 탭 연계 여지)
드리프트 감시: 신규 연도 스팟 정밀도 G-C 미달 시 → 하네스 B 재수렴
```

### 4.5 기업 마스터·증분 무결성 메커니즘 ★v1.1 신설 (D12)

기업 추가·변경·정정이 **어느 단계에서 일어나도 실수 없이 전파**되도록 하는 규칙:

```
[M1 마스터 동기화 루프 — 월 1회 + 보고서 시즌 주 1회]
  DART corpCode 전량 diff → CompanyRegistry 갱신:
    신규 상장 → 행 추가 + KSIC 매핑(auto) → 다음 하네스 C 큐에 자동 포함
    상장폐지 → listing_status=delisted (행 삭제 금지 — 과거 엣지의 참조 무결성)
    사명 변경 → name_current 갱신 + 구사명을 CompanyAlias(valid_to 포함)로 자동 이관
    합병/승계 → merged(승계 corp_code) 기록 — 뷰에서 리다이렉트 힌트

[M2 별칭 유지보수 루프]
  LinkFailQueue 빈도순 상위 → 수동 별칭 등록(CPA) → 등록 즉시
  해당 surface_form의 실패 청크만 link 단계 재큐 (전체 재추론 불필요)

[M3 정정공시 처리]
  기재정정 → 신규 rcept_no 발급됨 → 신 rcept_no 추출 완료 시
  동일 (corp, as_of, section)의 구 rcept_no 엣지 status=superseded + superseded_by 기록
  export는 active만 — 뷰에는 항상 최신 정정본만 노출

[M4 멱등성 계약 (전 단계 공통)]
  청크 id = 결정적 생성 / 엣지 = UNIQUE 키 upsert / 파이프라인 = 상태 기반 재개
  → "같은 입력 재실행 = 같은 결과, 중복 0" 이 성립하지 않는 코드는 머지 금지 (테스트로 강제)

[M5 재추출 정책]
  어댑터 버전업 기본 = 신규 연도만 적용. 소급 재추출은 G-C 미달 섹터 한정.
  전량 재처리는 명시적 명령(--reprocess-all)으로만 — 우발적 대량 재실행 차단
```

### 4.6 루프 경계 요약표 — 모든 게이트의 정량 정본 ★v1.2

> 루프 드라이버(Claude Code)는 **이 표만 보고** 속행/회귀/중단을 판정한다.
> 숫자 보정은 반도체 파일럿 후 1회에 한해 허용하되, **이 표의 개정으로만** —
> 코드 안 상수나 구두 합의로 기준을 움직이지 않는다 (루프가 완주 판정을 스스로 내릴 수 있어야 함).

| 게이트 | 판정 근거 | 통과 기준 (전부 스크립트 산출값) | 실패 시 행동 | 최대 반복 |
|---|---|---|---|---|
| **G-A** (라벨) | evaluate.py + CPA 검수 | train ≥ 3,000청크 · 하드네거 ≥ 30% · 자기일치 ≥ 85% | A1 표적 재샘플링 | 3회 — 초과 시 샘플링 전략 재설계(사람) |
| **G-B** (학습) | evaluate.py (val) | 정밀도@τ ≥ 0.90 · 재현율@τ ≥ 0.50 · F1 개선 <1pt 2라운드 연속 | B5 오류분석 → A 증강 재라운드. 수렴 실패 시 DPO | 6라운드 (+DPO 2) — 초과 시 §3.7 중단 |
| **봉인 평가** | evaluate.py (test) | S1(P≥0.90 ∧ R≥0.50) ∧ S2(제로샷+15pt) — S3는 스트레치 | **중단** — T1 전용 유지, 결과 기록 | **1회 — 재시도 절대 금지** (test 오염) |
| **G-C** (섹터 배포) | CPA 스팟 30건 | 스팟 정밀도 ≥ 0.85 | B5 환류 → 해당 섹터만 재추론(supersede) | 섹터당 2회 — 재실패 시 그 섹터 T2 보류 |
| **M4** (멱등) | pytest (CI) | 동일 배치 2회 실행 → 행 수·내용 불변 | 머지 차단 | 상시 |

---

## 5. 시각화 계약 (integration에 넘길 렌더링 정책 명세)

> 구현은 integration/dossier 소유(D8). relation은 데이터 + 이 정책 명세만 공급.
> UI 착수 시 루트 DESIGN.md 선행 준수.

| 항목 | 정책 |
|---|---|
| 진입 ★v1.4 | v2 셸 EgoView(LOD-2) 상단 `지배구조 / 밸류체인` 레이어 토글([../universe/PLAN.md](../universe/PLAN.md) §5) — dossier 탭 진입은 비목표. 갤럭시→섹터→기업 동선 불변 |
| 레이아웃 | 앵커 중앙 고정, 상류(공급처) 상단 / 하류(고객) 하단 — 물자 흐름 위→아래 |
| 표시 한도 | 1-hop만. 사이드당 Top-N(기본 6, 5~8 튜닝) — 랭킹: tier → amount → as_of |
| 잔여 처리 | 묶음 노드 "○○ 외 n사" → 클릭 시 사이드 패널 리스트 (그래프 확장 금지) |
| 탐색 | 노드 클릭 = 앵커 재구성(re-root) + 상단 브레드크럼(삼성전자 › 솔브레인 › …) |
| 엣지 스타일 | T1 실선 / T2 옅은 실선 / T3 점선 — 기존 EDGE TYPOLOGY 범례 문법에 등급 추가 |
| 레이어 문법 분리 ★v1.3 | 지배구조 레이어와 **문법 축 분리**([../universe/PLAN.md](../universe/PLAN.md) U-D14): 밸류체인은 화살표=물자 흐름(화살촉 모양을 지배구조 지분 화살촉과 다르게), 선 스타일=신뢰등급, 색=흐름색(관계유형 6색과 미충돌). 두 레이어 동시 렌더 금지 — 토글 전환 시 전용 범례로 교체 |
| 2-hop 힌트 | 이웃 노드에 "상장사 n곳 납품" 배지만 (엣지 렌더 금지) |
| 필터 | 상대 업종 칩(소재/장비/전방…) — 제한이 아닌 탐색 도구 |
| 근거 노출 | 엣지 hover/클릭 시 provenance(공시명·원문 문장) 표시 — 교육 목적의 핵심 |
| 상폐·합병 | delisted 노드는 채도 낮춤 + 라벨, merged는 승계 기업 리다이렉트 힌트 |
| 갤럭시 레벨 | 섹터 클러스터 간 T3 흐름선(산업연관표) — 업종 밸류체인 백본 (V4) |
| 면책 | "공시·통계 기반 참고 정보" 문구 — 투자 조언 표현 금지 |

---

## 6. 실행 로드맵 (수집 전량 선행 · 추출은 섹터 증분 — D3·D10)

### Phase V0 — 기반 + shared 승격
- [x] **reports.db → shared/data/ 승격 마이그레이션** (§2.1 체크리스트 4항 — galaxy 회귀 확인 포함) — 2026-07-21 완료(PROGRESS.md)
- [x] report 수집기 전 상장사 확장 → 우선 섹션(사업의내용·연결주석) 전량 수집 개시 (3~5일 배치) — 개시함(진행 중, 2026-07-21 기준 2,259/2,651 tickers)
- [x] `valuechain/` 패키지 스켈레톤 (`chunker/ extract/ train/ evaluate.py export.py`) + storage 스키마(§2.2 — UNIQUE 제약·멱등 테스트 포함) — 2026-07-21: storage 스키마는 V0에서 선완료, 패키지 스켈레톤(chunker/train/evaluate.py 뼈대 + extract/export.py 실구현)은 이번 세션 완료
- [x] CompanyRegistry 전 상장사 적재 + KSIC↔산업연관표 매핑(auto) — 2,651사(U0 게이트 PASS)
      — **universe 컬럼(market_cap_krw·cap_asof·sector_id·universe_tier·universe_rank) 동시 반영** 완료.
      M1 정기 동기화 루프(월 1회 스케줄러)는 **미가동** — 지금까지는 1회성 sync 실행뿐
      ([../universe/PLAN.md](../universe/PLAN.md) U-D5 — 스키마 합의 후 마이그레이션 1회로 완결)
- [x] CompanyAlias 초기 구축 — 2026-07-21 완료: 자동(dart_history) 파생은 report_raw
      corp_name 이력 창(2021~2025)에 실제 사명변경 사례가 0건이라 불발(수집 97.7%
      시점 기준) — top50 시절 큐레이션된 NAME_ALIASES 21건(현대차·SK·LG·HD현대·삼성
      그룹 DART 정식명↔KRX 약칭)을 manual 소스로 전량 이관(21/21 매칭). **Phase V0
      5개 항목 전부 완료.**

### Phase V1 — T1 엣지 + 뷰 v1 (GPU 무관 · 화면 검증 선행)
- [x] **정형 파서 2종으로 확정**(리더 결정, 2026-07-21 — 아래 두 결정 참조):
      **특수관계자 주석(금액) 완료**(`extract/related_party.py`, 2026-07-21 —
      매출/매입 거래금액, 당기만, 실제 삼성전자 공시 샘플 기반 pytest 13건 PASS) /
      **단일판매·공급계약 수시공시 완료**(`extract/supply_contract.py`, 2026-07-21 — DART
      엔드포인트 조사 결과: 전용 구조화 API 없음, `list.json`(pblntf_detail_ty=I001) +
      `document.xml` 파싱. 실측 발견: 계약상대방 다수가 영업기밀로 비공개(§7 리스크 기적중).
      실제 공시 2건 fixture 기반 pytest 5건 PASS)
  - **리더 결정 A — 타법인출자현황은 3번째 T1 파서로 만들지 않는다.** 지분투자
    데이터는 U1에서 이미 RelationLocal(거버넌스 레이어)로 완전히 표현됨.
    ValueChainEdge.edge_type(supply/customer/raw_material/competition)은 거래관계용이라
    지분율이 자연히 대응하지 않고, 억지로 끼워 넣으면 U-D14가 지키려는 "거버넌스 vs
    밸류체인 문법 분리"를 파서 레벨에서 다시 깨뜨림. RelationRaw 재사용 아이디어 폐기
    — 밸류체인 T1은 정형 파서 2종이 최종 스코프.
  - **리더 결정 B — 익명 엣지 스키마 확장은 T2로 이연, 지금은 안 함.** T1의 가치는
    정밀·고신뢰(§0 기술 목표)인데 익명 항목은 그 반대라 스키마를 넓혀 T1에 섞으면
    등급의 의미가 흐려짐. §7 리스크의 "카운트 기여" 취지는 현재도 LinkFailQueue
    누적 + apply() 카운터(`link_failed`/`no_counterparty`)로 약하게 충족됨(어떤
    표기가 실패했는지 빈도까지 추적 가능). T2는 confidence·운영점(τ) 스키마를
    어차피 새로 설계해야 하므로, 익명 표현은 그때 한 번에 설계해 마이그레이션
    중복을 피한다. `dst_corp NOT NULL` 유지.
- [x] `ValueChainEdge` T1 적재(멱등 upsert) + `export.py` → valuechain.json — 코드·pytest 완료
      (특수관계자 주석 1종 기준). **실 코퍼스 전량 실행은 보류** — DART 5개년 백필이 relation.db에
      장기 트랜잭션 쓰기 중이라 §2.1 "장기 배치 직렬 실행 원칙" 위반 회피, 백필 완료 후 실행
- [x] ★v1.4 하네스 V-1 계약 체커를 valuechain.json에 확장 완료
      (`test_v1_contract_checker.py`, 2026-07-21) — 스키마 형태(`test_export_json_contract_shape`)
      + 참조 무결성(엣지 src/dst 전원 CompanyRegistry 실존) + 자연키 중복 0(3회 재실행) +
      멱등 export(연속 호출 바이트 단위 diff 0, 파서 재실행 후에도 불변) + 근거 노출
      (provenance·rcept_no 전 엣지 필수) = pytest 4건 전부 PASS. 파서 2종 확정(위 참조)에
      맞춘 정식 V-1 스위트 완성 — [../universe/PLAN.md](../universe/PLAN.md) §5.5 준용
- [ ] integration에 §5 명세 전달 → 밸류체인 토글 뷰 v1 (T1만으로 렌더 검증)
- [ ] 게이트: 반도체 앵커 3사(삼성전자·SK하이닉스·소재주 1) 화면 QA 통과

### Phase V2 — 청킹 + 라벨링 + 학습 (하네스 A·B)
- [ ] 후보 게이트 + 청커 구현 → 반도체 섹터 VcChunk 생성 (§3.1)
- [ ] 하네스 A → train/val/test 구축 (하드 네거티브 ≥30%), test 봉인
- [ ] B0 베이스라인 (제로샷 14B·32B·Claude) → 학생 크기 확정
- [ ] 하네스 B 수렴 → G-B → 봉인 평가 → **3행 비교표(CI)·ablation 확정**
- [ ] 게이트: 운영점 정밀도 ≥ 0.90 (미달 시 V3 진입 금지 — T1만으로 서비스 유지)

### Phase V3 — T2 배치 추출 (하네스 C · 섹터 확산)
- [ ] 반도체 섹터 추론 → G-C 스팟체크 → 뷰에 T2 증분 반영
- [ ] 섹터별 확산: 2차전지 → 자동차 → 중공업·방산 → … (섹터당 G-C 반복)
- [ ] M2 별칭 보정 루프 상시 가동 (LinkFailQueue 소진)

### Phase V4 — T3 백본 + 갤럭시 줌아웃
- [ ] 한국은행 산업연관표 → `SectorIOEdge` → 섹터 간 흐름선
- [ ] 갤럭시 섹터 클러스터에 업종 밸류체인 오버레이 (integration)

### 병행 (전 Phase)
- [ ] PROGRESS.md에 라운드별 F1·운영점·스팟 정밀도 누적 기록 (성과 증빙 원장)
- [ ] 멱등성 테스트(M4) — 동일 배치 2회 실행 후 행 수 불변 assert — CI에 포함
- [ ] `shared/models.py` 동기화는 검증 완료 후 별도 PR (모듈 원칙 #3)

---

## 7. 리스크 · 열린 결정

| 리스크 | 대응 |
|---|---|
| shared 승격이 galaxy 파이프라인을 깨뜨림 | V0 마이그레이션에 회귀 확인 명시. ★v1.4 실측: 경로 참조는 1곳이 아니라 코드 4곳+테스트 1곳+문서 5곳(§2.1 목록) — 일괄 변경 + grep 잔존 0건 게이트 |
| GPU 접속 정보가 공개 저장소에 노출 (★v1.4 발견) | `modules/report/llm.py`의 docstring·오류 메시지에 서버 IP·계정 평문 하드코딩 — V0 이전 별도 브랜치(`fix/report-llm-secrets`)에서 환경변수로 이전·제거 (shared/config.py:30 "SSH 접속정보 기재 금지" 원칙 위반 해소) |
| "정본=모듈 로컬" 원칙과의 충돌 | 리더 결정(D11)으로 공식 예외 — ARCHITECTURE·루트 CLAUDE.md 명문화가 V0 선행 조건 |
| 코스닥 중소형사 공시 품질(서술 부실·비표준 표기) | 하드 네거티브에 코스닥 표기 과표집 + LinkFailQueue 수동 보정 루프(M2)로 흡수 |
| 공급계약 공시 상대방 "비공개" 다수 | 익명 엣지로만(카운트 기여). T1 한계는 T2가 보완 |
| 교사 라벨 비용 | 청크 단위(≤1.5K자)라 섹션 대비 토큰 소액. 자기일치 2회로 저품질 사전 차단 |
| GPU 단일 장비 (학습·서빙 경합) | §4.0 시분할 + 체크포인트 재개. 챗봇 SLA는 야간 배치 시간대 팀원 합의 |
| 모델·임계값 버전 드리프트 | extractor_ver(어댑터+τ+config) 태깅 — 모든 T2 엣지 역추적 가능. 버전업 소급은 M5 정책으로 통제 |
| 정밀도 목표 미달 | 3중 방어: 검증 2패스(§3.5) → 운영점 τ(§3.6) → DPO 옵션(§3.4). 그래도 미달 시 V2 게이트가 차단 — T1 전용으로 제품 성립 |
| val/test 표본 오차 | test 500건 + 부트스트랩 CI 병기(§3.7) — 점추정 단독 판정 금지 |
