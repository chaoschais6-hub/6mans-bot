K = 32


def expected(a, b):
    """Expected score of rating `a` against rating `b` (0..1)."""
    return 1 / (1 + 10 ** ((b - a) / 400))


def apply_match_result(team1_ratings, team2_ratings, score1, score2):
    """teamN_ratings: list of (user_id, mmr).

    Returns a list of (user_id, new_mmr, delta, won).
    Each player's expected score is their rating vs. the opponent's team average.
    """
    if score1 == score2:
        raise ValueError("Ties are not supported")

    winners = team1_ratings if score1 > score2 else team2_ratings
    losers = team2_ratings if score1 > score2 else team1_ratings

    win_avg = sum(r for _, r in winners) / len(winners)
    lose_avg = sum(r for _, r in losers) / len(losers)

    updates = []
    for uid, rating in winners:
        new = round(rating + K * (1 - expected(rating, lose_avg)))
        updates.append((uid, new, new - rating, True))
    for uid, rating in losers:
        new = round(rating + K * (0 - expected(rating, win_avg)))
        updates.append((uid, new, new - rating, False))
    return updates
