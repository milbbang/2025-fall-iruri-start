def calculate_fhi(impulsive: float, spike: float) -> float:
    """
    금융건강지수(FHI) = 100 - (충동구매*40 + 급증*30)
    """
    score = 100 - (impulsive * 40 + max(0, spike) * 30)
    return round(max(score, 0), 2)

