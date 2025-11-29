class SpendingSpikeDetector:
    """
    최근 7일 평균 vs 이전 30일 평균 비교
    """

    def __init__(self):
        self.daily_history = []  # 금액 목록

    def compute_spike(self, amount: int) -> float:
        self.daily_history.append(amount)

        if len(self.daily_history) < 10:
            return 0.0  # 데이터 부족 → 급증 판단 못함

        recent7 = self.daily_history[-7:]
        prev30 = self.daily_history[-37:-7] if len(self.daily_history) >= 37 else self.daily_history[:-7]

        if not prev30:
            return 0.0

        avg_recent = sum(recent7) / len(recent7)
        avg_prev = sum(prev30) / len(prev30)

        if avg_prev == 0:
            return 0.0

        spike_ratio = (avg_recent - avg_prev) / avg_prev
        return round(spike_ratio, 2)
