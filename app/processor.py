"""Processor: 주사위 굴리기와 라운드·매치 판정.

규칙 ID는 docs/01-requirements.md 참고.
일부러 심은 버그는 'PLANTED BUG-xxx' 주석으로 표시하고 docs/planted-bugs.md에 기록한다.
"""
import itertools
import random
import re

WINS_TO_FINISH = 3   # R-03
MAX_ROUNDS = 10      # R-04
DICE_COUNTS = (2, 3)  # R-05

# R-06: 한글·영문·숫자 2~10자
# PLANTED BUG-002: 최대 길이를 9로 잘못 적어 10자 닉네임이 거부된다.
NICKNAME_PATTERN = re.compile(r"[가-힣A-Za-z0-9]{2,9}")


def is_valid_nickname(nickname: str) -> bool:
    return NICKNAME_PATTERN.fullmatch(nickname) is not None


def roll(seed: int, round_no: int, dice_count: int) -> tuple[list[int], list[int]]:
    """R-07: 매치 seed와 라운드 번호로 굴린다. 어느 서버가 처리해도 결과가 같다."""
    rng = random.Random(f"{seed}-{round_no}")
    player = [rng.randint(1, 6) for _ in range(dice_count)]
    cpu = [rng.randint(1, 6) for _ in range(dice_count)]
    return player, cpu


def all_same(dice: list[int]) -> bool:
    """2개면 더블, 3개면 트리플 (R-02)."""
    return len(set(dice)) == 1


def judge_round(player: list[int], cpu: list[int]) -> str:
    """라운드 결과: PLAYER / CPU / DRAW (R-01, R-02)."""
    player_sum, cpu_sum = sum(player), sum(cpu)
    if player_sum > cpu_sum:
        return "PLAYER"
    if cpu_sum > player_sum:
        return "CPU"

    player_same, cpu_same = all_same(player), all_same(cpu)
    if player_same and not cpu_same:
        return "PLAYER"
    if cpu_same and not player_same:
        return "CPU"
    if player_same and cpu_same:
        # PLANTED BUG-001: R-02에 따르면 무승부여야 하는데 플레이어 승리로 처리한다.
        return "PLAYER"
    return "DRAW"


def judge_match(player_wins: int, cpu_wins: int, rounds_played: int) -> str | None:
    """매치 결과: PLAYER / CPU / DRAW, 아직 진행 중이면 None (R-03, R-04)."""
    if player_wins >= WINS_TO_FINISH:
        return "PLAYER"
    if cpu_wins >= WINS_TO_FINISH:
        return "CPU"
    if rounds_played >= MAX_ROUNDS:
        if player_wins > cpu_wins:
            return "PLAYER"
        if cpu_wins > player_wins:
            return "CPU"
        return "DRAW"
    return None


def theoretical_distribution(dice_count: int) -> dict[int, float]:
    """주사위 합계의 이론 확률 (S-02)."""
    counts: dict[int, int] = {}
    for faces in itertools.product(range(1, 7), repeat=dice_count):
        total = sum(faces)
        counts[total] = counts.get(total, 0) + 1
    all_cases = 6 ** dice_count
    return {total: count / all_cases for total, count in sorted(counts.items())}
