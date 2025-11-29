import re
from datetime import datetime

def parse_push_notification(text: str) -> dict:
    """
    Parse various card/KakaoPay/Pay-style payment push notifications.

    Extracts:
        - store (str)
        - amount (int)
        - datetime (datetime)
    """
    try:
        # 금액 추출
        amount_pattern = r"([\d,]+)\s*원"
        amount_match = re.search(amount_pattern, text)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else 0

        # 가맹점명 추출 (두 번째 줄)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        store = lines[1] if len(lines) >= 2 else "알수없음"

        # 날짜/시간 추출
        datetime_pattern = r"(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})"
        dt_match = re.search(datetime_pattern, text)
        if dt_match:
            dt_str = f"{dt_match.group(1)} {dt_match.group(2)}"
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        else:
            dt = datetime.now()

        return {
            "store": store,
            "amount": amount,
            "datetime": dt
        }

    except Exception as e:
        print("[ParserError]", e)
        return {
            "store": "알수없음",
            "amount": 0,
            "datetime": datetime.now()
        }

