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
# 정제 함수
# ==========================
def normalize_period(period: str) -> str:
    return period.replace("~", "-").replace(".", "/").strip()

def normalize_condition(cond: str):
    text = cond.replace(" ", "")
    if "인문" in text or "사회계열" in text:
        major = "인문사회"
    elif "이공계" in text:
        major = "이공계"
    else:
        major = "전체"

    grades = []
    for m in re.finditer(r"([1-4]),([1-4])학년", text):
        grades.extend([int(m.group(1)), int(m.group(2))])
    for m in re.finditer(r"([1-4])학년", text):
        g = int(m.group(1))
        if g not in grades:
            grades.append(g)
    if not grades:
        grades = [1, 2, 3, 4]

    return major, sorted(grades)

def clean_policy(raw):
    major, grades = normalize_condition(raw["condition"])
    return {
        "name": raw["name"],
        "type": raw["type"],
        "period": normalize_period(raw["period"]),
        "link": raw["link"],
        "major": major,
        "allowed_grade": grades,
        "grant": raw["grant"]
    }

policies_clean = [clean_policy(p) for p in raw_policies]

# ==========================
# 사용자 프로필 
# ==========================
user = {
    "major": "이공계",
    "grade": 3
}

def is_eligible(policy, user):
    ok_major = (policy["major"] == "전체") or (policy["major"] == user["major"])
    ok_grade = user["grade"] in policy["allowed_grade"]
    return ok_major and ok_grade

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

    header = tk.Label(
        root,
        text=f"FINNUT 장학금 매칭 데모\n프로필: 전공={user['major']}, 학년={user['grade']}학년",
        font=("맑은 고딕", 11, "bold"),
        justify="left"
    )
    header.pack(padx=10, pady=10, anchor="w")

    container = tk.Frame(root)
    container.pack(padx=10, pady=5, fill="both", expand=True)

    for r in matched:
        card = tk.Frame(container, bd=1, relief="solid", padx=8, pady=6)
        card.pack(fill="x", pady=5)

        tk.Label(card, text=f"{r['name']} ({r['type']})", font=("맑은 고딕", 10, "bold")).pack(anchor="w")
        tk.Label(card, text=f"기간       : {r['period']}", font=("맑은 고딕", 9)).pack(anchor="w")
        tk.Label(card, text=f"전공 요구  : {r['major']}", font=("맑은 고딕", 9)).pack(anchor="w")
        tk.Label(card, text=f"대상 학년  : {r['allowed_grade']}", font=("맑은 고딕", 9)).pack(anchor="w")
        tk.Label(card, text=f"장학 혜택  : {r['grant']}", font=("맑은 고딕", 9)).pack(anchor="w")

        link = tk.Label(card, text=r['link'], fg="blue", cursor="hand2", font=("맑은 고딕", 9, "underline"))
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda e, url=r["link"]: open_link(url))

    root.mainloop()

if __name__ == "__main__":
    show_gui()
