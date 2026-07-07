# 머지 프로세스

> 팀원이 언제 어디서 무엇을 받고, 언제 어떻게 올리는지를 정리한 문서.
> 처음 헷갈릴 수 있는 `pull` vs `Pull Request` 개념부터 확인하세요.

---

## 1. 브랜치 계층

```
main (프로덕션, 배포용 — 리더만 접근)
  ↑
dev (통합 브랜치, 팀원 작업이 여기서 합쳐짐)
  ↑
작업 브랜치 (feat/<작업> · fix/<작업> · chore/<작업>)
(각자 자신의 작업 브랜치 — 완료 후 dev 머지 → 삭제)
```

## 2. 담당자

| 담당자 | 모듈 | 범위 |
|---|---|---|
| A | modules/financial/ | 재무/EQS |
| B | modules/disclosure/ | 공시 수집 |
| C (yangw) | modules/relation/ | 관계 + **리더 겸임** |
| D | modules/price/ | 주가 라벨링 |

> **브랜치명은 작업 단위로 자유** (고정된 담당자별 브랜치 없음). 각자 dev에서 작업 브랜치를 따서 작업 → dev로 PR → 머지 후 삭제.

---

## 3. ⚠️ 먼저 짚기: `pull` vs `Pull Request` — 같은 이름, 반대 방향

| 용어 | 뜻 | 방향 |
|---|---|---|
| **`git pull`** (동사) | 원격 → 내 로컬로 **받기** | ⬇ 받기 |
| **Pull Request (PR)** | "내 작업 합쳐주세요" 요청 | ⬆ 올려서 요청 |

같은 "pull"이지만 완전히 반대입니다. 이 문서에서는 구분해서 씁니다.

---

## 4. 전체 흐름 한 장 요약

```
[팀원 로컬]                    [원격 GitHub]              [리더]
 <내 작업 브랜치>                origin/<내 작업 브랜치>
   │
   ├ 작업 + 커밋
   │
   ├ git push ───────────────→ origin/<내 작업 브랜치> 갱신
   │
   │                            GitHub 웹에서
   └ PR 생성 (base: dev) ──→  Pull Request 생성됨
                                     │
                                     ├ CI 자동 실행
                                     │   (black + pytest)
                                     │
                                     ├ 빨간 X ──→ 팀원이 수정 push
                                     │               └ CI 재실행
                                     │
                                     └ 초록불 ──→ 리더 리뷰
                                                    │
                                                    └ Squash & Merge
                                                         │
                                               origin/dev 갱신
                                                         │
                                  다른 팀원이 git merge origin/dev로 받아감
```

---

## 5. 팀원 매일 루틴

### 새 작업 시작 시

```bash
git checkout dev && git pull          # 최신 dev 받기
git checkout -b feat/<작업이름>        # 작업 브랜치 생성 (예: feat/eqs-mscore)
```

### 주 1~2회 또는 다른 팀원이 큰 기능 merge 했다고 들었을 때

```bash
git fetch origin
git merge origin/dev              # 다른 팀원 작업 흡수
```

### 작업 중

```bash
# 코드 작성 후
/check                            # 리뷰 + 테스트 + PROGRESS.md 기록

git add .
git commit -m "feat: 작업 내용"
git push -u origin <내-작업-브랜치>
```

### 어느 정도 완성되어 리더 리뷰 요청하고 싶을 때

GitHub 웹에서 **Pull Request 생성** (`git` 명령 아님):
1. GitHub repo 페이지 → "Pull requests" 탭 → "New pull request" 버튼
2. **base: `dev`**, **compare: `<내-작업-브랜치>`**
3. 제목 + 설명 작성 → "Create pull request"

---

## 6. 리더의 PR 처리 (작업 브랜치 → dev)

1. GitHub PR 페이지 열기
2. **CI 자동 실행 결과 확인** (black + pytest). 빨간 X면 즉시 거부
3. 변경 코드 리뷰 (Files changed 탭)
4. 필요하면 comment로 피드백 → 팀원이 수정 push → CI 재실행
5. 초록불 + 리뷰 OK → **Squash & Merge** 클릭
6. 머지된 작업 브랜치는 **삭제** (dev에 반영 완료 — GitHub의 "Delete branch" 버튼)

## 7. 리더 본인 작업 (relation + 리드)

- 자신의 작업 브랜치에서 작업한 부분도 본인이 PR 생성 → self-merge 가능
- 단 **CI 통과는 필수** — 본인이 열었다고 스킵 불가
- 리더 권한과 코드 품질 게이트는 별개

## 8. dev → main (배포 시점)

- **리더만 수행**
- `git checkout dev && git pull`
- GitHub에서 "dev → main" PR 생성
- CI 통과 → Squash & Merge
- main 직접 push는 `.claude/settings.json` permissions로 차단됨

---

## 9. 빈도 가이드 (pull 관점)

| 언제 | 어디서 받기 |
|---|---|
| 새 작업 시작 | dev (`git pull` 후 브랜치 생성) |
| 주 1~2회 | dev (`git merge origin/dev`) |
| 배포 확인 등 특수 케이스만 | main |

**`main`은 리더 외엔 거의 pull할 일 없음.**

---

## 10. 충돌 발생 시

1. `git status`로 충돌 파일 확인
2. Claude Code에게 **"충돌 해결해줘"** 요청
3. 해결 안 되면 리더(yangw)에게 Slack 에스컬레이션
4. **`git push --force` 금지** (permissions로 차단됨)

## 11. 커밋 메시지 규칙

- `feat:` 새 기능 / `fix:` 버그 수정 / `docs:` 문서 / `test:` 테스트
- 한글 OK (예: `feat: Beneish M-score 계산 구현`)

## 12. CI 상태 확인

- GitHub repo → **Actions** 탭 → 본인 PR 또는 push의 워크플로 실행 결과 확인
- 실패 시 로그 펼쳐서 에러 메시지 확인 → Claude Code에게 **"CI 실패 원인 알려줘"** 질문
- 공용 규칙: **CI 빨간 X인 PR은 merge 불가**

---

## 한 줄 요약

> **내가 받는 건 `pull`(동사), 합쳐달라고 요청하는 건 `PR`(Pull Request).**
> 매일 `dev`를 `pull`, 작업 브랜치에서 작업 → PR, `main`은 리더만.
