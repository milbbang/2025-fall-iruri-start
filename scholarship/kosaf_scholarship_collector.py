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

BASE_URL = "https://api.odcloud.kr/api/15028252/v1"
DB_NAME = "kosaf_scholarships.db"

# 월별 UDDI 엔드포인트 목록
KOSAF_UDDIS = [
    "uddi:c7637c78-fbdd-481d-a59d-c6c12ce51a13",
    "uddi:90147b2a-2d3c-4d4f-844e-a379630e9938",
    "uddi:9398a88a-d06c-4fc4-b230-82b8ec37e304",
    "uddi:a33c3d7b-2c21-46d1-a722-9a5343660030",
    "uddi:29173521-fc01-40c0-b5c8-a557b0953c6e",
    "uddi:15a0c0b7-83cf-47ed-ae2a-f000df024d2",
    "uddi:44d9db52-042d-417b-a3b0-e3172204f631",
    "uddi:ec86fced-7440-4c0e-8047-9f1ec27919d5",
    "uddi:c40ccdc5-8f56-4f1c-8531-f0264213f98c",
]

# ============================
# 날짜 파싱 함수
# ============================

def parse_date(date_str):
    if not date_str or date_str == "-":
        return None

    date_str = date_str.replace(".", "-").replace("/", "-").strip()
    parts = date_str.split("-")

    if len(parts) == 3:
        y, m, d = parts
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    return None

# ============================
# 기간 정규화 + 상태 판단
# (※ 2주차 기준에서는 임시 사용)
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

    # 중복 제거
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

    for f in fields:
        if f and f.strip() and f != "-":
            return f.strip()

    return ""

# ============================
# DB 초기화 (Upsert용 UNIQUE)
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
            raw_json TEXT,
            UNIQUE(name, type, link)
        );
    """)

    conn.commit()
    conn.close()

# ============================
# API 호출
# ============================

def fetch_api(uddi, page=1, perPage=1500):
    url = f"{BASE_URL}/{uddi}"
    params = {
        "page": page,
        "perPage": perPage,
        "serviceKey": SERVICE_KEY
    }

    r = requests.get(url, params=params)
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
            # ✅ API 원본 그대로 저장
            "raw_json": json.dumps(row, ensure_ascii=False)
        })

    return raw

# ============================
# DB 저장 (Upsert)
# ============================

def save_to_db(raw_policies):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for p in raw_policies:
        cur.execute("""
            INSERT INTO scholarships
            (name, type, period, start_date, end_date, status, link, condition, grant, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name, type, link)
            DO UPDATE SET
                period = excluded.period,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                status = excluded.status,
                condition = excluded.condition,
                grant = excluded.grant,
                raw_json = excluded.raw_json;
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
            p["raw_json"]
        ))

    conn.commit()
    conn.close()

# ============================
# 실행
# ============================

def run():
    print("=== FINNUT 장학금 데이터 수집 시작 ===")
    init_db()

    total = 0

    for uddi in KOSAF_UDDIS:
        print(f"[UDDI] {uddi} 수집 중...")
        rows = fetch_api(uddi)
        print(f" → {len(rows)}건 수집")

        raw_policies = convert_to_raw_policies(rows)
        save_to_db(raw_policies)

        total += len(raw_policies)

    print(f"=== 완료! 총 {total}건 처리됨 ===")
    print(f"DB 파일: {DB_NAME}")

if __name__ == "__main__":
    run()
