import os
import json
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# ============================
# 환경변수 로드
# ============================

load_dotenv()
SERVICE_KEY = os.getenv("SERVICE_KEY")

if not SERVICE_KEY:
    raise ValueError("ERROR: .env 파일에 SERVICE_KEY가 없습니다!")


# ============================
# 설정
# ============================

API_URL = "https://api.odcloud.kr/api/15028252/v1/uddi:ec86fced-7440-4c0e-8047-9f1ec27919d5"
DB_NAME = "kosaf_scholarships.db"


# ============================
# 날짜 파싱 함수
# ============================

def parse_date(date_str):
    if not date_str or date_str == "-":
        return None

    date_str = date_str.replace(".", "-").replace("/", "-").strip()
    # ex: "2025-3-01" → "2025-03-01"
    parts = date_str.split("-")
    if len(parts) == 3:
        y, m, d = parts
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return None


# ============================
# 기간 정규화 + 상태판단
# ============================

def build_period_and_status(row):
    start_raw = row.get("모집시작일", "")
    end_raw = row.get("모집종료일", "")

    start = parse_date(start_raw)
    end = parse_date(end_raw)

    today = datetime.today().date()

    if start and end:
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()

        if s <= today <= e:
            status = "진행중"
        elif today < s:
            status = "예정"
        else:
            status = "마감"
    else:
        status = "정보없음"

    return {
        "period": f"{start or start_raw} ~ {end or end_raw}",
        "start": start,
        "end": end,
        "status": status
    }


# ============================
# 신청 자격(조건) 생성
# ============================

def build_condition(row):
    fields = [
        ("신청대상", row.get("신청대상")),
        ("지원대상", row.get("지원대상")),
        ("성적기준", row.get("성적기준 상세내용")),
        ("소득기준", row.get("소득기준 상세내용")),
        ("특정자격", row.get("특정자격 상세내용")),
        ("지역거주", row.get("지역거주여부 상세내용")),
        ("자격제한", row.get("자격제한 상세내용")),
    ]

    lines = []
    for label, value in fields:
        if value and value.strip() and value != "-":
            lines.append(f"{label}: {value.strip()}")

    return "\n".join(dict.fromkeys(lines))


# ============================
# 지원내용(grant) 생성
# ============================

def build_grant(row):
    fields = [
        row.get("지원내역 상세내용"),
        row.get("지원내역"),
        row.get("지원금액"),
        row.get("장학금액"),
        row.get("급여"),
    ]

    # 가장 상세한 필드 먼저 사용
    for f in fields:
        if f and f.strip() and f != "-":
            return f.strip()

    return ""


# ============================
# DB 초기화
# ============================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            period TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            link TEXT,
            condition TEXT,
            grant TEXT,
            raw_json TEXT
        );
    """)
    conn.commit()
    conn.close()


# ============================
# API 호출
# ============================

def fetch_api(page=1, perPage=1500):
    params = {
        "page": page,
        "perPage": perPage,
        "serviceKey": SERVICE_KEY
    }
    r = requests.get(API_URL, params=params)
    r.raise_for_status()
    return r.json().get("data", [])


# ============================
# raw_policies 변환
# ============================

def convert_to_raw_policies(rows):
    raw = []

    for row in rows:
        period_data = build_period_and_status(row)

        raw.append({
            "name": row.get("상품명"),
            "type": row.get("운영기관명", ""),
            "period": period_data["period"],
            "start_date": period_data["start"],
            "end_date": period_data["end"],
            "status": period_data["status"],
            "link": row.get("홈페이지 주소", ""),
            "condition": build_condition(row),
            "grant": build_grant(row),
        })

    return raw


# ============================
# DB 저장
# ============================

def save_to_db(raw_policies):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for p in raw_policies:
        cur.execute("""
            INSERT INTO scholarships
            (name, type, period, start_date, end_date, status, link, condition, grant, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["name"],
            p["type"],
            p["period"],
            p["start_date"],
            p["end_date"],
            p["status"],
            p["link"],
            p["condition"],
            p["grant"],
            json.dumps(p, ensure_ascii=False)
        ))

    conn.commit()
    conn.close()


# ============================
# 실행
# ============================

def run():
    print("=== FINNUT 장학금 수집기 시작 ===")

    init_db()

    print("[1] API 불러오는 중…")
    rows = fetch_api()
    print(f" → {len(rows)}건 불러옴")

    print("[2] raw_policies 변환 중…")
    raw_policies = convert_to_raw_policies(rows)

    print("[3] DB 저장 중…")
    save_to_db(raw_policies)

    print("=== 완료! kosaf_scholarships.db 생성됨 ===")
    print(json.dumps(raw_policies[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
