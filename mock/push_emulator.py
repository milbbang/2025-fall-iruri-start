import random

MOCK_PUSHES = [
    """[신한카드 승인] 5,800원
GS25 이대점
일시불 승인
2024-11-21 23:10""",

    """[카카오페이 결제] 4,200원
스타벅스 신촌점
승인 완료
2024-11-22 09:12""",

    """[삼성카드 승인] 12,000원
맥도날드 홍대점
일시불
2024-11-20 01:48""",

    """[KB Pay] 8,900원
올리브영 이대점
결제 성공
2024-11-25 21:25""",

    """[현대카드 승인] 2,900원
세븐일레븐 공덕점
2024-11-24 23:58"""
]


def get_random_push():
    """Return a random sample push notification text."""
    return random.choice(MOCK_PUSHES)
