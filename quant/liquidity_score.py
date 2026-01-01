def compute_liquidity_score(volume, liquidity):
    score = 0
    if volume and volume > 500_000:
        score += 50
    elif volume and volume > 100_000:
        score += 30
    else:
        score += 10

    if liquidity and liquidity > 100_000:
        score += 50
    elif liquidity and liquidity > 25_000:
        score += 30
    else:
        score += 10

    return min(score, 100)
  
