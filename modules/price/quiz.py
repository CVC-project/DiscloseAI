"""공시 기반 주가 예측 퀴즈 CLI

실행:
    python -m modules.price.quiz
"""

from __future__ import annotations

import random
import sys
from modules.price.quiz_data import QUIZ_LIST

LABEL_CHOICES = {
    "1": "수혜",
    "2": "악재",
    "3": "중립",
}

LABEL_EMOJI = {
    "수혜": "📈",
    "악재": "📉",
    "중립": "➡️",
}

CATEGORY_TAG = {
    "물적분할":   "[물적분할]",
    "유상증자":   "[유상증자]",
    "생산전략":   "[생산전략]",
    "대형협력":   "[대형협력]",
    "대형M&A":    "[대형M&A]",
    "합병":       "[합병]",
    "합병철회":   "[합병철회]",
    "지주사전환": "[지주사전환]",
    "회계이슈":   "[회계이슈]",
    "해외리스크": "[해외리스크]",
}


def _divider(char: str = "─", width: int = 60) -> str:
    return char * width


def _ask_question(q: dict, index: int, total: int) -> bool:
    """문제를 출력하고 정답 여부를 반환."""
    tag = CATEGORY_TAG.get(q["category"], f"[{q['category']}]")

    print()
    print(_divider("═"))
    print(f"  문제 {index}/{total}   {tag}")
    print(_divider("─"))
    print(f"  기업  : {q['company']} ({q['ticker']})")
    print(f"  날짜  : {q['date']}")
    print(f"  공시  : {q['title']}")
    print(_divider("─"))
    print()
    for line in q["context"].splitlines():
        print(f"  {line.strip()}")
    print()
    print(_divider("─"))
    print("  이 공시 후 주가는?")
    print("    1. 수혜 (상승, +2% 이상)")
    print("    2. 악재 (하락, -2% 이하)")
    print("    3. 중립")
    print()

    while True:
        raw = input("  답 입력 (1/2/3, q=종료): ").strip().lower()
        if raw == "q":
            print("\n퀴즈를 종료합니다.")
            sys.exit(0)
        if raw in LABEL_CHOICES:
            break
        print("  1, 2, 3 중 하나를 입력하세요.")

    chosen = LABEL_CHOICES[raw]
    correct = q["answer"]
    is_correct = chosen == correct

    print()
    if is_correct:
        print(f"  ✅  정답!  {LABEL_EMOJI[correct]} {correct}")
    else:
        print(f"  ❌  오답.  정답: {LABEL_EMOJI[correct]} {correct}  (입력: {chosen})")

    change = q["change_pct"]
    sign = "+" if change >= 0 else ""
    print(f"  실제 변동: {sign}{change}%  ({q['window']})")
    print()
    print("  [해설]")
    for line in q["explanation"].splitlines():
        print(f"  {line.strip()}")
    print()

    input("  Enter 키를 누르면 다음 문제로 이동합니다...")
    return is_correct


def _show_result(score: int, total: int) -> None:
    print()
    print(_divider("═"))
    print(f"  최종 결과: {score} / {total} 정답")
    pct = score / total * 100
    if pct == 100:
        grade = "완벽! 공시 분석 전문가 수준입니다 🏆"
    elif pct >= 80:
        grade = "훌륭합니다! 공시 독해력이 뛰어납니다 👏"
    elif pct >= 60:
        grade = "양호합니다. 조금 더 연습하면 전문가 수준에 도달할 수 있습니다 📚"
    elif pct >= 40:
        grade = "공시와 주가의 관계를 조금 더 공부해보세요 📖"
    else:
        grade = "아직 갈 길이 멉니다. 공시 유형별 시장 반응 패턴을 익혀보세요 💪"
    print(f"  {grade}")
    print(_divider("═"))
    print()


def run_quiz(shuffle: bool = True) -> None:
    questions = list(QUIZ_LIST)
    if shuffle:
        random.shuffle(questions)

    print()
    print(_divider("═"))
    print("  📊  공시 기반 주가 예측 퀴즈")
    print("  코스피 상위 50 실제 사건 · 15문항")
    print(_divider("─"))
    print("  공시 내용을 읽고 주가 방향을 맞혀보세요.")
    print("  수혜(+2% 이상) / 악재(-2% 이하) / 중립")
    print(_divider("─"))
    mode = input("  문제 순서: 랜덤(Enter) / 원래 순서(n): ").strip().lower()
    if mode == "n":
        questions = sorted(QUIZ_LIST, key=lambda x: x["id"])
    print()

    score = 0
    total = len(questions)
    for i, q in enumerate(questions, start=1):
        if _ask_question(q, i, total):
            score += 1

    _show_result(score, total)


if __name__ == "__main__":
    run_quiz()
