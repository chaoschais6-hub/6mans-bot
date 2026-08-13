from itertools import combinations


def balance_teams(players):
    """Split 6 players into two teams of 3, minimizing the MMR gap.

    players: list of (user_id, mmr).
    Returns (team_a, team_b), each a list of (user_id, mmr).
    """
    if len(players) != 6:
        raise ValueError("Need exactly 6 players")

    n = len(players)
    best = None
    for combo in combinations(range(n), 3):
        idx_a = set(combo)
        team_a = [players[i] for i in range(n) if i in idx_a]
        team_b = [players[i] for i in range(n) if i not in idx_a]

        sum_a = sum(m for _, m in team_a)
        sum_b = sum(m for _, m in team_b)
        diff = abs(sum_a - sum_b)

        # Tie-break: keep each team's internal spread similar
        spread_a = max(m for _, m in team_a) - min(m for _, m in team_a)
        spread_b = max(m for _, m in team_b) - min(m for _, m in team_b)
        score = (diff, abs(spread_a - spread_b))

        if best is None or score < best[0]:
            best = (score, team_a, team_b)

    return best[1], best[2]
