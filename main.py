import os
import re
import time
import random
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot dang chay on dinh 24/7!"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FB_COOKIE = os.getenv("FB_COOKIE")
GROUP_ID = os.getenv("GROUP_ID")

# Tự động làm sạch Cookie nếu bị dính dấu ngoặc kép thừa
if FB_COOKIE:
    FB_COOKIE = FB_COOKIE.strip('"').strip("'").strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": FB_COOKIE,
    "Referer": "https://www.facebook.com/",
    "Origin": "https://www.facebook.com"
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

    try:
        # Bước 1: Vào trang chủ Facebook để lấy mã bảo mật fb_dtsg tự động
        home_resp = session.get("https://www.facebook.com/", timeout=30)
        
        # Tìm mã token dtsg trong trang
        fb_dtsg_match = re.search(r'"DTSGInitialData",\[\],{"token":"([^"]+)"', home_resp.text)
        if not fb_dtsg_match:
            fb_dtsg_match = re.search(r'name="fb_dtsg" value="([^"]+)"', home_resp.text)
            
        if not fb_dtsg_match:
            print("[-] Không lấy được mã xác thực fb_dtsg. Cookie có thể bị đăng xuất hoặc sai định dạng!", flush=True)
            return False

        fb_dtsg = fb_dtsg_match.group(1)

        # Lấy c_user (User ID) từ Cookie
        user_id_match = re.search(r'c_user=(\d+)', FB_COOKIE)
        user_id = user_id_match.group(1) if user_id_match else ""

        # Bước 2: Gửi bài viết trực tiếp qua cổng API GraphQL / Composer
        post_url = "https://www.facebook.com/api/graphql/"
        
        # Cấu hình dữ liệu gửi bài vào Nhóm
        form_data = {
            "fb_dtsg": fb_dtsg,
            "__user": user_id,
            "__a": "1",
            "req_format": "json"
        }

        # Thử phương thức gửi bài trực tiếp qua endpoint nhóm m.facebook
        m_url = f"https://m.facebook.com/groups/{GROUP_ID}/"
        m_resp = session.get(m_url, timeout=30)
        
        # Tìm action form trên giao diện di động hiện đại
        composer_action = re.search(r'action="([^"]*composer[^"]*)"', m_resp.text)
        
        if composer_action:
            target_url = "https://m.facebook.com" + composer_action.group(1).replace("&amp;", "&")
            data = {
                "fb_dtsg": fb_dtsg,
                "message": text,
                "view_post": "Đăng",
                "post_anonymously": "true",
                "make_anonymous": "1"
            }
            # Lấy tất cả input hidden trong trang m.facebook
            inputs = re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', m_resp.text)
            for name, val in inputs:
                if name not in data:
                    data[name] = val
            data["message"] = text

            res = session.post(target_url, data=data, timeout=30)
            if res.status_code in [200, 302]:
                print("[+] ĐÃ ĐĂNG BÀI THÀNH CÔNG VÀO HÀNG ĐỢI!", flush=True)
                return True
        else:
            # Dự phòng qua Graph API mbasic fallback tự động
            mb_url = f"https://mbasic.facebook.com/composer/mbasic/?c_src=group&target={GROUP_ID}"
            mb_resp = session.get(mb_url, timeout=30)
            target = re.search(r'action="([^"]*composer[^"]*)"', mb_resp.text)
            if target:
                act = "https://mbasic.facebook.com" + target.group(1).replace("&amp;", "&")
                data = {"fb_dtsg": fb_dtsg, "xc_message": text, "view_post": "Đăng"}
                inputs = re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', mb_resp.text)
                for name, val in inputs:
                    if name not in data:
                        data[name] = val
                data["xc_message"] = text
                post_res = session.post(act, data=data, timeout=30)
                if post_res.status_code in [200, 302]:
                    print("[+] ĐÃ ĐĂNG BÀI THÀNH CÔNG VÀO HÀNG ĐỢI!", flush=True)
                    return True

        print("[-] Không gửi được form bài viết. Facebook có thể đang yêu cầu xác minh bảo mật.", flush=True)
        return False

    except Exception as e:
        print("[-] Lỗi khi xử lý gửi bài:", e, flush=True)
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
