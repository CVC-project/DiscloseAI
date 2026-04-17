# 머지 프로세스

## 브랜치 계층

```
main (프로덕션, 배포용)
  ↑
dev (통합 브랜치, 매주 금요일 정리)
  ↑
feat/financial · feat/disclosure · feat/relation · feat/price
```

## 담당자

| 브랜치 | 담당자 | 비고 |
|---|---|---|
| feat/financial | A | 재무/EQS |
| feat/disclosure | B | 공시 수집 |
| feat/relation | C (yangw) | **리더 겸임** |
| feat/price | D | 주가 라벨링 |

## 팀원 매일 루틴

```bash
git checkout feat/본인담당
git pull origin feat/본인담당      # 내 원격 변경 반영
git fetch origin
git merge origin/dev              # 다른 팀원 작업 받기

# 작업 + /check

git add .
git commit -m "feat: 작업 내용"
git push origin feat/본인담당
```

## PR 흐름 (feat/* → dev, 매주 금요일)

1. 팀원: GitHub에서 "feat/xxx → dev" PR 생성
2. **CI 자동 실행** (black + pytest). 빨간 X면 merge 불가
3. 리더(yangw)가 리뷰 → 코멘트 또는 approve
4. 팀원이 수정사항 있으면 push (CI 재실행)
5. 리더가 **Squash & Merge** (feat 브랜치는 삭제 안 함, 계속 재사용)

## 리더 본인 작업 (relation + 리드)

- `feat/relation`에서 작업한 부분은 본인이 PR 생성, self-merge 가능
- 단 **CI 통과는 필수** — 본인이 열었다고 스킵 불가
- 리더 권한과 코드 품질 게이트는 별개

## dev → main (배포 시점)

- 리더만 수행
- `git checkout dev && git pull`
- GitHub에서 "dev → main" PR 생성
- CI 통과 → Squash & Merge
- main 직접 push는 `.claude/settings.json`에서 차단됨

## 충돌 발생 시

1. `git status`로 충돌 파일 확인
2. Claude Code에게 "충돌 해결해줘" 요청
3. 해결 안 되면 리더(yangw)에게 Slack 에스컬레이션
4. **`git push --force` 금지** (permissions로 차단됨)

## 커밋 메시지 규칙

- `feat:` 새 기능 / `fix:` 버그 수정 / `docs:` 문서 / `test:` 테스트
- 한글 OK (예: `feat: Beneish M-score 계산 구현`)

## CI 상태 확인

- GitHub repo → Actions 탭 → 본인 PR의 워크플로 실행 결과 확인
- 실패 시 로그 펼쳐서 에러 메시지 확인 → Claude에게 "CI 실패 원인 알려줘" 질문
