from utils.parser import parse_push_notification
from utils.category_rules import categorize_store
from utils.impulsive_detector import ImpulsiveDetector
from utils.spending_spike import SpendingSpikeDetector
from utils.fhi_calculator import calculate_fhi
from mock.push_emulator import get_random_push


# 엔진 초기화
impulsive_engine = ImpulsiveDetector()
spike_engine = SpendingSpikeDetector()


def main():
    print("\n================ FINNUT 기술 데모 ================\n")

    # 1. 푸시 알림 랜덤 생성
    push = get_random_push()
    print("수신한 푸시 알림:\n")
    print(push)
    print("--------------------------------------------------")

    # 2. 파싱
    parsed = parse_push_notification(push)
    store = parsed["store"]
    amount = parsed["amount"]
    dt = parsed["datetime"]

    print("\n 파싱 결과")
    print(f"- 가맹점명: {store}")
    print(f"- 금액: {amount}원")
    print(f"- 시간: {dt.strftime('%Y-%m-%d %H:%M')}")

    # 3. 카테고리 분류
    category = categorize_store(store)

    # 4. 충동 구매 점수
    impulsive_score = impulsive_engine.compute_score(dt, amount)

    # 5. 지출 급증 분석
    spike_score = spike_engine.compute_spike(amount)

    print("\n 소비 분석")
    print(f"- 카테고리: {category}")
    print(f"- 충동구매 점수: {impulsive_score}")
    print(f"- 급증 감지: {spike_score}")

    # 6. 금융건강지수(FHI) 계산
    fhi = calculate_fhi(impulsive_score, spike_score)

    print("\n FHI")
    print(f"- 이번 소비 반영 후 FHI: {fhi}점")
    print("\n==================================================\n")


if __name__ == "__main__":
    main()
