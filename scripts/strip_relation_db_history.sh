#!/bin/sh
# FN-011: 미푸시 이력(origin/dev..HEAD)에서 relation.db blob 제거 후 push.
# 리더가 Git Bash에서 직접 실행: sh scripts/strip_relation_db_history.sh
# 사전 백업: backup/pre-filter-relation-db-20260728 태그 (이미 생성됨).
# 빈 커밋은 보존한다 — "chore: relation.db 재실행" 류 메시지가 작업 원장 역할.
set -e

cd "$(git rev-parse --show-toplevel)"

echo "[1/4] filter-branch: relation.db를 미푸시 60커밋에서 제거"
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch \
  --index-filter "git rm --cached --ignore-unmatch modules/relation/data/relation.db" \
  -- origin/dev..HEAD

echo "[2/4] feat/relation-universe-v0 를 재작성본의 동일 커밋으로 재지정"
OLD_V0_SUBJECT=$(git log -1 --format=%s backup/pre-filter-relation-db-20260728^{commit} >/dev/null 2>&1; git log -1 --format=%s 3c1067c 2>/dev/null || echo "chore(relation): report 트렁케이션 상한 해소 반영 — 밸류체인 재실행")
NEW_V0=$(git log --format="%H %s" origin/dev..HEAD | grep -F "$OLD_V0_SUBJECT" | head -1 | cut -d' ' -f1)
if [ -n "$NEW_V0" ]; then
  git branch -f feat/relation-universe-v0 "$NEW_V0"
  echo "  -> feat/relation-universe-v0 = $NEW_V0"
else
  echo "  !! 동일 제목 커밋을 못 찾음 — v0 재지정 수동 필요 (git log 확인)"
fi

echo "[3/4] 검증: 100MB 초과 blob 0건이어야 함"
BIG=$(git rev-list --objects origin/dev..HEAD | git cat-file --batch-check='%(objectsize) %(objectname) %(rest)' | awk '$1>100000000' | wc -l)
echo "  -> 100MB+ blobs: $BIG"
[ "$BIG" -eq 0 ] || { echo "  !! 아직 대용량 blob 존재 — 중단"; exit 1; }

echo "[4/4] push"
git push -u origin feat/relation-universe-viz

echo "완료. 문제 시 복구: git reset --hard backup/pre-filter-relation-db-20260728"
