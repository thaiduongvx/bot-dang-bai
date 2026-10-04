import os
import re
import time
import random
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot dang chay on dinh 24/7!"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FB_COOKIE = os.getenv("FB_COOKIE")
GROUP_ID = os.getenv("GROUP_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": FB_COOKIE
}

def generate_local_question():
    """Tự động sinh câu hỏi tự nhiên 100% khi Google AI nghẽn mạng"""
    chao = ["Chào mọi người ạ,", "Mọi người cho em hỏi chút,", "Các bác ơi,", "Cả nhà mình ơi,", "Em chào cả nhà,"]
    khi_nao = ["cuối tuần này", "tuần sau", "tháng này", "mấy hôm nữa", "sắp tới"]
    noi_dung = [
        "thời tiết trên Đồng Văn đêm xuống có lạnh lắm chưa ạ, đã cần mang áo phao dày chưa mọi người?",
        "hoa tam giác mạch ở khu Lũng Cú với Lũng Táo tầm này nở rộ chưa các bác?",
        "đoạn đèo Mã Pí Lèng đợt này đường sá đi lại có đoạn nào đang sửa chữa khó đi không ạ?",
        "đi thuyền sông Nho Quế nên đi bến Tà Làng hay bến mới thì đường xuống đỡ dốc hơn ạ?",
        "bên mình có ai nhận tour ghép ô tô 3N2Đ xuất phát tối thứ 5 hoặc thứ 6 không, cho em xin lịch trình với.",
        "em định thuê xe máy tự lái từ TP lên Đồng Văn, cung này đi lần đầu có gắt quá không mọi người?",
        "có homestay nào ở Lô Lô Chải view thoáng, yên tĩnh cho nhóm bạn 4 người không ạ, cho em xin review với.",
        "buổi tối ở thị trấn Đồng Văn có quán lẩu gà đen hay đồ nướng nào ngon chuẩn vị không các bác?"
    ]
    duoi = [
        "Ai vừa đi về cho em xin ít kinh nghiệm với ạ.",
        "Em cảm ơn mọi người nhiều nhé!",
        "Ai có thông tin tư vấn giúp em với ạ.",
        "Lần đầu đi nên còn bỡ ngỡ, mong các bác chỉ giáo."
    ]
    return f"{random.choice(chao)} {random.choice(khi_nao)} {random.choice(noi_dung)} {random.choice(duoi)}"

def get_question():
    """Gọi Gemini 3.8 Flash, nếu gặp lỗi sẽ tự chuyển sang câu hỏi tự nhiên"""
    if GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": "Đóng vai khách du lịch hỏi ngắn 2 câu kinh nghiệm đi Hà Giang (thời tiết, homestay, đèo, tour). Chỉ trả về câu hỏi, không thêm lời dẫn."}]
            }]
        }
        try:
            res = requests.post(url, json=payload, timeout=15).json()
            if "candidates" in res:
                return res['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception:
            pass
            
    return generate_local_question()

def post_to_group_via_cookie(text):
    session = requests.Session()
    session.headers.update(HEADERS)
    group_url = f"https://mbasic.facebook.com/groups/{GROUP_ID}"

    try:
        resp = session.get(group_url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", action=re.compile(r"/composer/mbasic/"))

        if not form:
            print("[-] Không tìm thấy khung đăng bài. Hãy kiểm tra lại Cookie!", flush=True)
            return False

        action_url = "https://mbasic.facebook.com" + form.get("action")
        data = {}
        for input_tag in form.find_all("input"):
            name = input_tag.get("name")
            value = input_tag.get("value", "")
            if name:
                data[name] = value

        data["xc_message"] = text
        if "view_post" in data:
            data["view_post"] = "Đăng"

        data["post_anonymously"] = "true"
        data["make_anonymous"] = "1"

        post_resp = session.post(action_url, data=data, timeout=30)
        if post_resp.status_code == 200:
            print("[+] ĐÃ ĐĂNG BÀI THÀNH CÔNG VÀO HÀNG ĐỢI!", flush=True)
            return True
        return False
    except Exception as e:
        print("[-] Lỗi gửi bài:", e, flush=True)
        return False

def bot_loop():
    print("=== Bot bắt đầu chạy ngầm ===", flush=True)
    while True:
        question = get_question()
        print(f"\n[+] Nội dung chuẩn bị đăng: {question}", flush=True)
        
        post_to_group_via_cookie(question)
        
        delay = 3600 + random.randint(30, 120)
        print(f"[i] Đang nghỉ {delay // 60} phút trước bài tiếp theo...", flush=True)
        time.sleep(delay)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
