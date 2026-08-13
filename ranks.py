TIERS = [
    (2000, "🟣 Grand Champion"),
    (1800, "🔴 Superstar"),
    (1600, "🟠 Diamond"),
    (1400, "🟡 Platinum"),
    (1200, "🟢 Gold"),
    (1000, "🔵 Silver"),
    (0, "⚪ Bronze"),
]


def tier_for(mmr):
    """Return (emoji+name string, minimum mmr of tier, max mmr of tier)."""
    for min_mmr, name in TIERS:
        if mmr >= min_mmr:
            # compute next tier boundary for progression display
            idx = TIERS.index((min_mmr, name))
            next_min = TIERS[idx - 1][0] if idx > 0 else 99999
            return name, min_mmr, next_min
    return TIERS[-1][1], 0, TIERS[0][0]


def progress(mmr):
    name, lo, hi = tier_for(mmr)
    span = hi - lo
    pct = 0 if span <= 0 else round((mmr - lo) / span * 100)
    return name, pct