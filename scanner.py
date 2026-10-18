import os
import sys
import time
import json
import io
import urllib.request
import urllib.parse
from datetime import datetime
from PIL import Image, ImageDraw

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
MIN_PRICE = float(os.getenv("MIN_PRICE", 100.0))
MAX_PRICE = float(os.getenv("MAX_PRICE", 1000.0))
STATE_FILE = "state.json"

ALLOWED_CATEGORIES = [
    "knife", "karambit", "bayonet", "daggers", "kukri", "stiletto", "ursus", "navaja", 
    "talon", "paracord", "survival", "skeleton", "nomad",
    "gloves", "hand wraps", "wraps", "specialist", "sport", "moto", "driver", "bloodhound", "hydra", "broken fang",
    "ak-47", "m4a4", "m4a1-s", "awp", "ssg 08", "galil", "famas", "aug", "sg 553", "scar-20", "g3sg1",
    "desert eagle", "usp-s", "glock-18", "p250", "five-seven", "tec-9", "cz75-auto", "r8 revolver", "dual berettas", "p2000",
    "mp9", "mac-10", "mp7", "mp5-sd", "ump-45", "p90", "pp-bizon", 
    "nova", "xm1014", "mag-7", "sawed-off", "m249", "negev"
]

WEARS = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]

def is_valid_skin(name: str) -> bool:
    name_lower = name.lower()
    if "souvenir" in name_lower:
        return False
    if not any(cat in name_lower for cat in ALLOWED_CATEGORIES):
        return False
    return any(w.lower() in name_lower for w in WEARS)

def render_infographic_card(skin_name: str, sell_list: list, buy_list: list, skin_img_url: str = "") -> bytes:
    W, H = 820, 480
    card = Image.new("RGB", (W, H), (13, 27, 36))
    draw = ImageDraw.Draw(card)

    left_w = 260
    draw.rectangle([(20, 20), (left_w, H - 20)], fill=(10, 20, 28))

    skin_loaded = False
    if skin_img_url:
        try:
            req = urllib.request.Request(skin_img_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_img = Image.open(io.BytesIO(resp.read()))
                raw_img = raw_img.convert("RGBA")
                raw_img.thumbnail((left_w - 40, H - 80), Image.Resampling.LANCZOS)
                x_pos = 20 + (left_w - 20 - raw_img.width) // 2
                y_pos = (H - raw_img.height) // 2
                card.paste(raw_img, (x_pos, y_pos), raw_img)
                skin_loaded = True
        except Exception:
            pass

    if not skin_loaded:
        draw.text((45, H // 2 - 10), "CS2 WEAPON", fill=(90, 115, 140))

    right_x = left_w + 20
    col_w = (W - right_x - 30) // 2

    # Header GIÁ BÁN (Xanh ngọc)
    draw.rectangle([(right_x, 20), (right_x + col_w, 60)], fill=(0, 77, 79))
    draw.text((right_x + col_w // 2 - 32, 32), "GIÁ BÁN", fill=(255, 255, 255))

    # Header GIÁ MUA (Xanh dương)
    buy_x = right_x + col_w + 10
    draw.rectangle([(buy_x, 20), (buy_x + col_w, 60)], fill=(0, 56, 92))
    draw.text((buy_x + col_w // 2 - 32, 32), "GIÁ MUA", fill=(255, 255, 255))

    y_start = 80
    row_h = 95
    red_dot = (235, 50, 50)

    # 4 giá bán ngoài Steam
    s1_price = sell_list[0]['price'] if sell_list and sell_list[0]['price'] > 0 else 1.0
    for i in range(4):
        cur_y = y_start + i * row_h
        draw.ellipse([(right_x + 5, cur_y + 4), (right_x + 13, cur_y + 12)], fill=red_dot)
        draw.text((right_x + 20, cur_y), f"Hạng {i+1}", fill=(180, 195, 210))

        if i < len(sell_list):
            item = sell_list[i]
            draw.text((right_x + 20, cur_y + 20), f"{item['price']:,.2f} USD", fill=(255, 255, 255))
            diff_text = ""
            if i > 0:
                pct = ((item['price'] - s1_price) / s1_price) * 100.0
                diff_text = f" ({pct:+.2f}%)"
            provider = item.get("provider", "Market")
            draw.text((right_x + 20, cur_y + 48), f"{provider}{diff_text}", fill=(140, 160, 180))

    # 4 giá mua (3 ngoài Steam, Hạng 4 là Steam)
    for i in range(4):
        cur_y = y_start + i * row_h
        draw.ellipse([(buy_x + 5, cur_y + 4), (buy_x + 13, cur_y + 12)], fill=red_dot)
        draw.text((buy_x + 20, cur_y), f"Hạng {i+1}", fill=(180, 195, 210))

        if i < len(buy_list):
            item = buy_list[i]
            draw.text((buy_x + 20, cur_y + 20), f"{item['price']:,.2f} USD", fill=(255, 255, 255))
            provider = "Steam" if i == 3 else item.get("provider", "Market")
            draw.text((buy_x + 20, cur_y + 48), provider, fill=(140, 160, 180))

    out_buffer = io.BytesIO()
    card.save(out_buffer, format="PNG")
    return out_buffer.getvalue()

def send_telegram_card(skin_name: str, image_bytes: bytes) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("Thiếu BOT_TOKEN hoặc CHAT_ID.")
        return False

    # Caption theo đúng chuẩn: Tiêu đề + Tên skin trong <code> để chạm nhẹ là tự copy
    caption = (
        f"<b>PRICEMPIRE 100-1000 USD</b>\n"
        f"<code>{skin_name}</code>"
    )

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{CHAT_ID}\r\n'.encode("utf-8"))

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode("utf-8"))

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n')

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="photo"; filename="alert_card.png"\r\nContent-Type: image/png\r\n\r\n')
    body.extend(image_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body))
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("ok"):
                print(f"-> Đã gửi thành công thẻ ảnh cho: {skin_name}")
                return True
            print(f"Lỗi phản hồi Telegram: {res}")
            return False
    except Exception as e:
        print(f"Lỗi khi gửi ảnh Telegram: {e}")
        return False

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state_data: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Lỗi lưu {STATE_FILE}: {e}")

def check_triggers(skin_name: str, sell_list: list, buy_list: list, old_state: dict) -> tuple[bool, str]:
    if len(sell_list) < 4 or len(buy_list) < 4:
        return False, ""

    s1 = sell_list[0]['price']
    s2 = sell_list[1]['price']
    b1 = buy_list[0]['price']
    b2 = buy_list[1]['price']
    b3 = buy_list[2]['price']

    # --- NHÁNH 1 (Kèo xả hàng chênh lệch Arbitrage) ---
    if (s1 <= s2 * 0.90) and (max(b1, b2, b3) > s1):
        return True, "NHÁNH 1 (S1 rẻ hơn S2 >= 10% & Giá mua ngoài Steam > S1)"

    # --- NHÁNH 2 (Biến động thị trường) ---
    if skin_name in old_state:
        prev = old_state[skin_name]
        prev_b1 = prev.get("b1", 0)
        prev_s2 = prev.get("s2", 0)
        prev_s3 = prev.get("s3", 0)
        prev_s4 = prev.get("s4", 0)

        if prev_b1 > 0 and (b1 <= prev_b1 * 0.95):
            return True, "NHÁNH 2 (Giá mua giảm >= 5%)"
        if prev_b1 > 0 and (b1 >= prev_b1 * 1.05):
            return True, "NHÁNH 2 (Giá mua tăng >= 5%)"
        if (prev_s2 > 0 and s2 >= prev_s2 * 1.05) or \
           (prev_s3 > 0 and sell_list[2]['price'] >= prev_s3 * 1.05) or \
           (prev_s4 > 0 and sell_list[3]['price'] >= prev_s4 * 1.05):
            return True, "NHÁNH 2 (Giá bán 2,3,4 tăng >= 5%)"

    return False, ""

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu chu kỳ quét thị trường...")
    old_state = load_state()
    new_state = dict(old_state)

    market_candidates = [
        {
            "name": "StatTrak™ AWP | Oni Taiji (Field-Tested)",
            "img_url": "https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot621FAR17PLfYQJD_9W7m5a0mvLwOq7c2DwB65R33-rF89r32wPn-EJkZDrxcoDEJgM4Y16Frwe9wOjxxcjr7ZzPnXBq63En43jcnBapwUYb3fCg23s/360fx360f",
            "sells": [
                {"price": 346.35, "provider": "DMarket"},
                {"price": 395.50, "provider": "CSFloat"},
                {"price": 412.00, "provider": "Skinport"},
                {"price": 425.06, "provider": "SkinSwap"}
            ],
            "buys": [
                {"price": 377.72, "provider": "csboard"},
                {"price": 358.76, "provider": "skinplace"},
                {"price": 353.13, "provider": "csmoney"},
                {"price": 417.15, "provider": "Steam"}
            ]
        },
        {
            "name": "★ StatTrak™ Butterfly Knife (Vanilla)",
            "img_url": "https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpovbSsLQJf1fLEcjVL49KJlY20k_jkI7fUhGJP68t-fMrw94_33ATj8kFrY2H1d46ddgE5YF-G-1K9yO_v0cDov8zOnHFguHEls3bZnhy30AYMMLLg-0Wj9w/360fx360f",
            "sells": [
                {"price": 890.00, "provider": "Buff.163"},
                {"price": 995.00, "provider": "CSFloat"},
                {"price": 1020.00, "provider": "Skinport"},
                {"price": 1045.00, "provider": "DMarket"}
            ],
            "buys": [
                {"price": 960.40, "provider": "Skins.com"},
                {"price": 945.00, "provider": "DMarket"},
                {"price": 930.00, "provider": "CSFloat"},
                {"price": 1017.80, "provider": "Steam"}
            ]
        },
        {
            "name": "AWP | Lightning Strike (Factory New)",
            "img_url": "https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot621FAR17P7NdTRH-t26q4SZlvD7PYTQgXtu5Mx2gv2PoN330VLk_kduNzymLNCSdVc5MF2G-gC2x-q90ZG8upnLm3thv3UlsyrajhKpwUYboUeY8r8/360fx360f",
            "sells": [
                {"price": 360.00, "provider": "Buff.163"},
                {"price": 410.00, "provider": "CSFloat"},
                {"price": 415.00, "provider": "Skinport"},
                {"price": 420.00, "provider": "DMarket"}
            ],
            "buys": [
                {"price": 415.00, "provider": "Market.CSGO"},
                {"price": 395.00, "provider": "CSFloat"},
                {"price": 380.00, "provider": "DMarket"},
                {"price": 435.00, "provider": "Steam"}
            ]
        }
    ]

    alerted_count = 0
    for skin in market_candidates:
        name = skin["name"]
        if not is_valid_skin(name):
            continue

        sells = skin["sells"]
        buys = skin["buys"]
        s1 = sells[0]["price"]
        if not (MIN_PRICE <= s1 <= MAX_PRICE):
            continue

        should_alert, reason = check_triggers(name, sells, buys, old_state)

        is_same = False
        if name in old_state:
            prev = old_state[name]
            if prev.get("s1") == s1 and prev.get("b1") == buys[0]["price"]:
                is_same = True

        if should_alert and not is_same:
            print(f"[CẢNH BÁO] {name} thỏa mãn {reason}")
            img_bytes = render_infographic_card(name, sells, buys, skin.get("img_url", ""))
            ok = send_telegram_card(name, img_bytes)
            if ok:
                alerted_count += 1
                new_state[name] = {
                    "s1": s1,
                    "s2": sells[1]["price"],
                    "s3": sells[2]["price"],
                    "s4": sells[3]["price"],
                    "b1": buys[0]["price"],
                    "time": datetime.now().isoformat()
                }

    save_state(new_state)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Hoàn tất chu kỳ. Đã gửi {alerted_count} cảnh báo.")

if __name__ == "__main__":
    main()
