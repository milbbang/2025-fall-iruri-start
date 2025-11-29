import json
import re
import webbrowser
import tkinter as tk
from tkinter import messagebox

# ==========================
# JSON 데이터 로딩
# ==========================
with open("sample_push.json", "r", encoding="utf-8") as f:
    raw_policies = json.load(f)

# ==========================
# 기간 정규화
# ==========================
def normalize_period(period: str) -> str:
    if not period:
        return ""
    return period.replace("~", "-").replace(".", "/").strip()

# ==========================
# 조건 정규화 헬퍼들
# ==========================

def extract_track(text: str) -> str:
    t = text.replace(" ", "")
    track = "전체"
    if any(k in t for k in ["인문", "사회계열", "인문계열"]):
        track = "인문사회"
    if any(k in t for k in ["이공계", "자연계열", "공학계열"]):
        track = "이공계"
    return track

def extract_grades(text: str):
    t = text.replace(" ", "")
    grades = []

    for m in re.finditer(r"([1-4]),([1-4])학년", t):
        g1, g2 = int(m.group(1)), int(m.group(2))
        for g in (g1, g2):
            if g not in grades:
                grades.append(g)

    for m in re.finditer(r"([1-4])학년", t):
        g = int(m.group(1))
        if g not in grades:
            grades.append(g)

    if not grades:
        grades = [1, 2, 3, 4]

    grades.sort()
    return grades

def extract_regions(text: str):
    regions = re.findall(r'([가-힣]+시|[가-힣]+군|[가-힣]+구)', text)
    unique = []
    for r in regions:
        if r not in unique:
            unique.append(r)
    return unique

def extract_gender(text: str):
    t = text.replace(" ", "")
    genders = []
    if any(k in t for k in ["여학생", "여성", "여대생", "여자"]):
        genders.append("F")
    if any(k in t for k in ["남학생", "남성", "남자"]):
        genders.append("M")

    if not genders:
        genders = ["M", "F"]

    genders = list(dict.fromkeys(genders))
    return genders

def extract_age_range(text: str):
    t = text.replace(" ", "")
    age_min, age_max = 0, 100

    m = re.search(r"(\d{1,2})~(\d{1,2})세", t)
    if m:
        age_min = int(m.group(1))
        age_max = int(m.group(2))
        return age_min, age_max

    m = re.search(r"(\d{1,2})세이상", t)
    if m:
        age_min = int(m.group(1))

    m = re.search(r"(\d{1,2})세이하", t)
    if m:
        age_max = int(m.group(1))

    return age_min, age_max

def extract_income_deciles(text: str):
    t = text.replace(" ", "")
    deciles = []

    m = re.search(r"소득분위(\d)~(\d)분위", t)
    if m:
        start, end = int(m.group(1)), int(m.group(2))
        deciles = list(range(start, end + 1))

    if not deciles:
        m = re.search(r"소득분위(\d)분위이하", t)
        if m:
            end = int(m.group(1))
            deciles = list(range(1, end + 1))

    if not deciles:
        m = re.search(r"소득분위(\d)분위이상", t)
        if m:
            start = int(m.group(1))
            deciles = list(range(start, 10))

    if not deciles:
        m = re.search(r"소득분위(\d)분위", t)
        if m:
            d = int(m.group(1))
            deciles = [d]

    if not deciles:
        deciles = list(range(1, 10))

    return deciles

def normalize_condition(cond: str):
    if cond is None:
        cond = ""

    track = extract_track(cond)
    grades = extract_grades(cond)
    regions = extract_regions(cond)
    genders = extract_gender(cond)
    age_min, age_max = extract_age_range(cond)
    income_deciles = extract_income_deciles(cond)

    return {
        "track": track,
        "allowed_grade": grades,
        "regions": regions,
        "genders": genders,
        "age_min": age_min,
        "age_max": age_max,
        "income_deciles": income_deciles
    }

# ==========================
# 정책 JSON 정제
# ==========================
def clean_policy(raw):
    cond_info = normalize_condition(raw.get("condition", ""))
    return {
        "name": raw.get("name"),
        "type": raw.get("type"),
        "period": normalize_period(raw.get("period", "")),
        "link": raw.get("link"),
        "conditions": cond_info,
        "grant": raw.get("grant", ""),
        "raw_condition": raw.get("condition", "")
    }

policies_clean = [clean_policy(p) for p in raw_policies]

# ==========================
# 사용자 프로필
# ==========================
user = {
    "track": "이공계",     # 인문사회 / 이공계
    "region": "서울시",    # 예: "서울시", "수원시", "부산광역시"
    "gender": "F",         # "M" / "F"
    "age": 21,
    "grade": 3,            # 대학생 아니면 None 가능
    "income_decile": 3     # 1~9
}

# ==========================
# 매칭 로직
# ==========================
def check_track(policy_cond, user):
    track = policy_cond["track"]
    return (track == "전체") or (track == user["track"])

def check_grade(policy_cond, user):
    if user["grade"] is None:
        return True
    return user["grade"] in policy_cond["allowed_grade"]

def check_region(policy_cond, user):
    regions = policy_cond["regions"]
    if not regions:
        return True
    return any(r in user["region"] for r in regions)

def check_gender(policy_cond, user):
    genders = policy_cond["genders"]
    return user["gender"] in genders

def check_age(policy_cond, user):
    return policy_cond["age_min"] <= user["age"] <= policy_cond["age_max"]

def check_income(policy_cond, user):
    return user["income_decile"] in policy_cond["income_deciles"]

def is_eligible(policy, user):
    cond = policy["conditions"]
    return (
        check_track(cond, user) and
        check_grade(cond, user) and
        check_region(cond, user) and
        check_gender(cond, user) and
        check_age(cond, user) and
        check_income(cond, user)
    )

def filter_policies(policies, user):
    return [p for p in policies if is_eligible(p, user)]

matched = filter_policies(policies_clean, user)

# ==========================
# GUI 팝업 출력 & 링크 클릭
# ==========================
def open_link(url):
    webbrowser.open(url)

def show_gui():
    root = tk.Tk()
    root.title("FINNUT 장학금 매칭 데모")

    if not matched:
        messagebox.showinfo("FINNUT 장학금 추천", "조건에 맞는 장학금이 없습니다.")
        root.destroy()
        return

    profile_text = (
        f"학부={user['track']}, "
        f"거주지역={user['region']}, "
        f"성별={user['gender']}, "
        f"나이={user['age']}, "
        f"학년={user['grade']}학년, "
        f"소득분위={user['income_decile']}분위"
    )

    header = tk.Label(
        root,
        text=f"FINNUT 장학금 매칭 데모\n프로필: {profile_text}",
        font=("맑은 고딕", 11, "bold"),
        justify="left"
    )
    header.pack(padx=10, pady=10, anchor="w")

    container = tk.Frame(root)
    container.pack(padx=10, pady=5, fill="both", expand=True)

    for r in matched:
        c = r["conditions"]

        card = tk.Frame(container, bd=1, relief="solid", padx=8, pady=6)
        card.pack(fill="x", pady=5)

        tk.Label(card, text=f"{r['name']} ({r['type']})",
                 font=("맑은 고딕", 10, "bold")).pack(anchor="w")
        tk.Label(card, text=f"기간 : {r['period']}",
                 font=("맑은 고딕", 9)).pack(anchor="w")

        # ===== 여기부터: '제한이 있는 조건만' 표시 =====
        any_condition_shown = False

        # 학부(트랙) 제한 있을 때만
        if c["track"] != "전체":
            tk.Label(card, text=f"학부/계열 : {c['track']}",
                     font=("맑은 고딕", 9)).pack(anchor="w")
            any_condition_shown = True

        # 학년 제한 있을 때만
        if c["allowed_grade"] != [1, 2, 3, 4]:
            tk.Label(card, text=f"대상 학년 : {c['allowed_grade']}",
                     font=("맑은 고딕", 9)).pack(anchor="w")
            any_condition_shown = True

        # 거주지역 제한 있을 때만
        if c["regions"]:
            tk.Label(card, text=f"거주지역 : {c['regions']}",
                     font=("맑은 고딕", 9)).pack(anchor="w")
            any_condition_shown = True

        # 성별 제한 있을 때만 (['M','F']는 제한 없음으로 간주)
        if not (set(c["genders"]) == {"M", "F"}):
            pretty_gender = {
                "M": "남성",
                "F": "여성"
            }
            readable = [pretty_gender.get(g, g) for g in c["genders"]]
            tk.Label(card, text=f"성별 : {', '.join(readable)}",
                     font=("맑은 고딕", 9)).pack(anchor="w")
            any_condition_shown = True

        # 나이 제한 있을 때만 (0~100은 제한 없음)
        if not (c["age_min"] == 0 and c["age_max"] == 100):
            tk.Label(card,
                     text=f"나이 : {c['age_min']}세 ~ {c['age_max']}세",
                     font=("맑은 고딕", 9)).pack(anchor="w")
            any_condition_shown = True

        # 소득분위 제한 있을 때만 (1~9 전체는 제한 없음)
        if c["income_deciles"] != list(range(1, 10)):
            tk.Label(card,
                     text=f"소득분위 : {c['income_deciles']}",
                     font=("맑은 고딕", 9)).pack(anchor="w")
            any_condition_shown = True

        # 어떤 제한도 없으면 "특별 제한 없음" 한 줄만
        if not any_condition_shown:
            tk.Label(card,
                     text="특별 제한 조건 없음 (전국, 전 학부, 전 학년, 전 성별, 전 연령, 전 소득분위)",
                     font=("맑은 고딕", 9), wraplength=500, justify="left").pack(anchor="w")

        # 장학 혜택
        tk.Label(card, text=f"장학 혜택 : {r['grant']}",
                 font=("맑은 고딕", 9), wraplength=500,
                 justify="left").pack(anchor="w")

        # 링크
        link = tk.Label(card, text=r['link'], fg="blue", cursor="hand2",
                        font=("맑은 고딕", 9, "underline"))
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda e, url=r["link"]: open_link(url))

    root.mainloop()

if __name__ == "__main__":
    show_gui()
