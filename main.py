import os
import re
import time
import random
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask

# Tạo một web server mini để Render nhận diện là Web Service Free
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot dang chay ngon lanh!"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FB_COOKIE = os.getenv("FB_COOKIE")
GROUP_ID = os.getenv("GROUP_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": FB_COOKIE
}

def get_gemini_question():
    # Sử dụng đúng endpoint v1beta và model gemini-3.8-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        "Đóng vai một khách du lịch thật đang muốn đi Hà Giang hoặc vừa đi về. "
        "Hãy viết 1 câu hỏi ngắn (2 đến 3 câu) đăng lên nhóm review để hỏi kinh nghiệm "
        "về các chủ đề: thời tiết, tìm tour, thuê xe máy, homestay Lô Lô Chải, đường đèo Mã Pí Lèng, "
        "thuyền sông Nho Quế, quán ăn... Văn phong tự nhiên, đời thường. "
        "Chỉ trả về duy nhất nội dung câu hỏi, không thêm bất kỳ lời dẫn nào."
    )
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        res = response.json()
        
        # Nếu có lỗi từ Google, in rõ nội dung lỗi ra màn hình
        if "error" in res:
            print("[-] Lỗi từ Google AI:", res["error"].get("message", res["error"]))
            return None
            
        return res['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print("[-] Lỗi khi xử lý dữ liệu Gemini:", e)
        return None


def post_to_group_via_cookie(text):
    session = requests.Session()
    session.headers.update(HEADERS)
    group_url = f"https://mbasic.facebook.com/groups/{GROUP_ID}"

    try:
        resp = session.get(group_url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", action=re.compile(r"/composer/mbasic/"))

        if not form:
            print("[-] Không tìm thấy form đăng bài. Kiểm tra lại Cookie!")
            return False

        action_url = "https://mbasic.facebook.com" + form.get("action")
        data = {}
        for input_tag in form.find_all("input"):
            name = input_tag.get("name")
            value = input_tag.get("value", "")
            if name:
                data[name] = value

        # Gán nội dung câu hỏi
        data["xc_message"] = text
        if "view_post" in data:
            data["view_post"] = "Đăng"

        # KÍCH HOẠT ĐĂNG ẨN DANH:
        data["post_anonymously"] = "true"
        data["make_anonymous"] = "1"

        post_resp = session.post(action_url, data=data, timeout=30)
        if post_resp.status_code == 200:
            print("[+] Đã gửi bài viết ẩn danh thành công qua Cookie!")
            return True
        return False
    except Exception as e:
        print("[-] Lỗi:", e)
        return False

def bot_loop():
    print("=== Bot bắt đầu chạy ngầm ===", flush=True)
    while True:
        print("Đang gọi Gemini tạo câu hỏi mới...", flush=True)
        question = get_gemini_question()
        if question:
            print(f"Nội dung: {question}", flush=True)
            post_to_group_via_cookie(question)
        
        delay = 3600 + random.randint(60, 180)
        print(f"Đang nghỉ {delay // 60} phút...", flush=True)
        time.sleep(delay)

# Chạy bot ở một luồng ngầm riêng biệt
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
