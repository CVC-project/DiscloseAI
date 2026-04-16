# Hooks (추후 추가 예정)

이 폴더는 Claude Code의 자동 트리거 스크립트를 저장하는 곳입니다.

## 현재 상태
- **빈 폴더**: 보호 기능은 `.claude/settings.json`의 Permissions deny rules로 처리 중
- **추후 추가 예정**: Windows 환경에서 안정적으로 동작하는 hook 스크립트 작성 후 도입

## 참고: Hooks 작성 시 주의사항 (Windows)
- `.sh` 파일은 Windows에서 동작하지 않음 → PowerShell 인라인 또는 `.bat` 파일 사용
- 데이터는 `TOOL_INPUT` 환경변수가 아니라 **stdin JSON**으로 수신 (`jq`로 파싱)
- 차단하려면 `exit 2` 사용 (`exit 1`은 경고만 출력하고 실행됨)
- 참조: https://docs.anthropic.com/en/docs/claude-code/hooks
