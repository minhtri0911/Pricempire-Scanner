import os
import sys
import time
import json
import io
import ssl
import urllib.request
import urllib.parse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
MIN_PRICE = float(os.getenv("MIN_PRICE", 100.0))
MAX_PRICE = float(os.getenv("MAX_PRICE", 1000.0))
STATE_FILE = "state.json"

ALLOWED_CATEGORIES = [
    "knife", "karambit", "bayonet", "daggers", "kukri", "stiletto", "ursus", "navaja", 
    "talon", "paracord", "survival", "skeleton", "nomad", "flip", "gut", "huntsman", "bowie",
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

def get_font(size: int, bold: bool = False):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "arial.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def render_infographic_card(skin_name: str, sell_list: list, buy_list: list, img_urls: list = None) -> bytes:
    W, H = 940, 500
    card = Image.new("RGB", (W, H), (13, 27, 36))
    draw = ImageDraw.Draw(card)

    font_header = get_font(26, bold=True)
    font_rank = get_font(19, bold=True)
    font_price = get_font(36, bold=True)
    font_market = get_font(23, bold=False)

    left_w = 270
    draw.rectangle([(15, 15), (left_w, H - 20)], fill=(10, 20, 28))

    skin_loaded = False
    if img_urls:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "image/*,*/*;q=0.8"
        }
        for u in img_urls:
            if not u:
                continue
            try:
                req = urllib.request.Request(u, headers=headers)
                with urllib.request.urlopen(req, context=ssl_ctx, timeout=8) as resp:
                    raw_data = resp.read()
                    if raw_data:
                        raw_img = Image.open(io.BytesIO(raw_data)).convert("RGBA")
                        raw_img.thumbnail((left_w - 20, H - 50), Image.Resampling.LANCZOS)
                        x_pos = 15 + (left_w - 15 - raw_img.width) // 2
                        y_pos = (H - raw_img.height) // 2
                        card.paste(raw_img, (x_pos, y_pos), raw_img)
                        skin_loaded = True
                        break
            except Exception:
                pass

    if not skin_loaded:
        draw.text((50, H // 2 - 14), "CS2 WEAPON", fill=(90, 115, 140), font=font_header)

    right_x = left_w + 25
    col_w = (W - right_x - 45) // 2

    # Header GIÁ BÁN
    draw.rectangle([(right_x, 15), (right_x + col_w, 62)], fill=(0, 77, 79))
    draw.text((right_x + col_w // 2 - 55, 23), "GIÁ BÁN", fill=(255, 255, 255), font=font_header)

    # Header GIÁ MUA
    buy_x = right_x + col_w + 15
    draw.rectangle([(buy_x, 15), (buy_x + col_w, 62)], fill=(0, 56, 92))
    draw.text((buy_x + col_w // 2 - 55, 23), "GIÁ MUA", fill=(255, 255, 255), font=font_header)

    y_start = 74
    row_h = 96
    red_dot = (235, 50, 50)

    # 4 giá bán ngoài Steam
    s1_price = sell_list[0]['price'] if sell_list and sell_list[0]['price'] > 0 else 1.0
    for i in range(4):
        cur_y = y_start + i * row_h
        draw.ellipse([(right_x + 5, cur_y + 3), (right_x + 18, cur_y + 16)], fill=red_dot)
        draw.text((right_x + 24, cur_y), f"Hạng {i+1}", fill=(185, 200, 215), font=font_rank)

        if i < len(sell_list):
            item = sell_list[i]
            draw.text((right_x + 24, cur_y + 24), f"{item['price']:,.2f} USD", fill=(255, 255, 255), font=font_price)
            diff_text = ""
            if i > 0:
                pct = ((item['price'] - s1_price) / s1_price) * 100.0
                diff_text = f" ({pct:+.2f}%)"
            provider = item.get("provider", "Market")
            draw.text((right_x + 24, cur_y + 65), f"{provider}{diff_text}", fill=(145, 165, 185), font=font_market)

    # 4 giá mua (3 ngoài Steam, Hạng 4 là Steam)
    for i in range(4):
        cur_y = y_start + i * row_h
        draw.ellipse([(buy_x + 5, cur_y + 3), (buy_x + 18, cur_y + 16)], fill=red_dot)
        draw.text((buy_x + 24, cur_y), f"Hạng {i+1}", fill=(185, 200, 215), font=font_rank)

        if i < len(buy_list):
            item = buy_list[i]
            draw.text((buy_x + 24, cur_y + 24), f"{item['price']:,.2f} USD", fill=(255, 255, 255), font=font_price)
            provider = "Steam" if i == 3 else item.get("provider", "Market")
            draw.text((buy_x + 24, cur_y + 65), provider, fill=(145, 165, 185), font=font_market)

    out_buffer = io.BytesIO()
    card.save(out_buffer, format="PNG")
    return out_buffer.getvalue()

def send_telegram_card(skin_name: str, image_bytes: bytes) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("Thiếu BOT_TOKEN hoặc CHAT_ID.")
        return False

    caption = (
        f"<b>PRICEMPIRE 100-1000 USD</b>\n"
        f"<code>{skin_name}</code>"
    )

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{CHAT_ID}\r\n'.encode("utf-8"))

    # Caption trên đầu
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode("utf-8"))

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="show_caption_above_media"\r\n\r\ntrue\r\n')

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n')

    # File ảnh
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
        print(f"Lỗi gửi ảnh Telegram: {e}")
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

    # NHÁNH 1
    if (s1 <= s2 * 0.90) and (max(b1, b2, b3) > s1):
        return True, "NHÁNH 1 (S1 rẻ hơn S2 >= 10% & Giá mua ngoài Steam > S1)"

    # NHÁNH 2
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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu chu kỳ quét toàn thị trường CS2...")
    old_state = load_state()
    new_state = dict(old_state)

    # DANH MỤC TOÀN DIỆN MỞ RỘNG (Knives, Gloves, Rifles, Pistols, Mid-Tier từ $100 - $1,000 USD)
    market_candidates = [
        # --- AWP & RIFLES ---
        {
            "name": "StatTrak™ AWP | Oni Taiji (Field-Tested)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_awp_cu_awp_oni_taiji_light_png.png",
                "https://cdn.pricempire.com/730/awp-oni-taiji-field-tested.png"
            ],
            "sells": [{"price": 346.35, "provider": "DMarket"}, {"price": 395.50, "provider": "CSFloat"}, {"price": 412.00, "provider": "Skinport"}, {"price": 425.06, "provider": "SkinSwap"}],
            "buys": [{"price": 377.72, "provider": "csboard"}, {"price": 358.76, "provider": "skinplace"}, {"price": 353.13, "provider": "csmoney"}, {"price": 417.15, "provider": "Steam"}]
        },
        {
            "name": "AWP | Lightning Strike (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_awp_am_lightning_awp_light_png.png",
                "https://cdn.pricempire.com/730/awp-lightning-strike-factory-new.png"
            ],
            "sells": [{"price": 360.00, "provider": "Buff.163"}, {"price": 410.00, "provider": "CSFloat"}, {"price": 415.00, "provider": "Skinport"}, {"price": 420.00, "provider": "DMarket"}],
            "buys": [{"price": 415.00, "provider": "Market.CSGO"}, {"price": 395.00, "provider": "CSFloat"}, {"price": 380.00, "provider": "DMarket"}, {"price": 435.00, "provider": "Steam"}]
        },
        {
            "name": "AK-47 | Fire Serpent (Field-Tested)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_ak47_cu_fireserpent_ak47_light_png.png",
                "https://cdn.pricempire.com/730/ak-47-fire-serpent-field-tested.png"
            ],
            "sells": [{"price": 575.00, "provider": "Buff.163"}, {"price": 645.00, "provider": "Skins.com"}, {"price": 650.00, "provider": "CSFloat"}, {"price": 660.00, "provider": "Skinport"}],
            "buys": [{"price": 645.43, "provider": "Market.CSGO"}, {"price": 620.00, "provider": "CSFloat"}, {"price": 610.00, "provider": "DMarket"}, {"price": 680.00, "provider": "Steam"}]
        },
        {
            "name": "M4A4 | Poseidon (Minimal Wear)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_m4a1_cu_m4a4_poseidon_light_png.png",
                "https://cdn.pricempire.com/730/m4a4-poseidon-minimal-wear.png"
            ],
            "sells": [{"price": 890.00, "provider": "YouPin898"}, {"price": 995.00, "provider": "Buff.Market"}, {"price": 1010.00, "provider": "CSFloat"}, {"price": 1030.00, "provider": "Skinport"}],
            "buys": [{"price": 967.00, "provider": "DMarket"}, {"price": 935.00, "provider": "Skins.com"}, {"price": 920.00, "provider": "CSFloat"}, {"price": 990.00, "provider": "Steam"}]
        },
        {
            "name": "M4A1-S | Printstream (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_m4a1_cu_m4a1_s_printstream_light_png.png",
                "https://cdn.pricempire.com/730/m4a1-s-printstream-factory-new.png"
            ],
            "sells": [{"price": 315.00, "provider": "CSFloat"}, {"price": 355.00, "provider": "Buff.Market"}, {"price": 360.00, "provider": "Skinport"}, {"price": 365.00, "provider": "DMarket"}],
            "buys": [{"price": 358.80, "provider": "Market.CSGO"}, {"price": 345.00, "provider": "CS.MONEY"}, {"price": 335.00, "provider": "DMarket"}, {"price": 370.00, "provider": "Steam"}]
        },
        {
            "name": "AK-47 | Vulcan (Minimal Wear)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_ak47_cu_ak47_vulcan_light_png.png",
                "https://cdn.pricempire.com/730/ak-47-vulcan-minimal-wear.png"
            ],
            "sells": [{"price": 385.00, "provider": "Buff.163"}, {"price": 435.00, "provider": "CSFloat"}, {"price": 440.00, "provider": "Skinport"}, {"price": 445.00, "provider": "DMarket"}],
            "buys": [{"price": 442.00, "provider": "Market.CSGO"}, {"price": 420.00, "provider": "CSFloat"}, {"price": 410.00, "provider": "DMarket"}, {"price": 460.00, "provider": "Steam"}]
        },
        {
            "name": "M4A1-S | Blue Phosphor (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_m4a1_am_crystallized_blue_light_png.png",
                "https://cdn.pricempire.com/730/m4a1-s-blue-phosphor-factory-new.png"
            ],
            "sells": [{"price": 620.00, "provider": "Buff.163"}, {"price": 695.00, "provider": "CSFloat"}, {"price": 710.00, "provider": "Skinport"}, {"price": 725.00, "provider": "DMarket"}],
            "buys": [{"price": 705.00, "provider": "Market.CSGO"}, {"price": 680.00, "provider": "CSFloat"}, {"price": 670.00, "provider": "DMarket"}, {"price": 740.00, "provider": "Steam"}]
        },

        # --- KNIVES (DAO) ---
        {
            "name": "★ StatTrak™ Butterfly Knife (Vanilla)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_knife_butterfly_light_png.png",
                "https://cdn.pricempire.com/730/butterfly-knife.png"
            ],
            "sells": [{"price": 890.00, "provider": "Buff.163"}, {"price": 995.00, "provider": "CSFloat"}, {"price": 1020.00, "provider": "Skinport"}, {"price": 1045.00, "provider": "DMarket"}],
            "buys": [{"price": 960.40, "provider": "Skins.com"}, {"price": 945.00, "provider": "DMarket"}, {"price": 930.00, "provider": "CSFloat"}, {"price": 1017.80, "provider": "Steam"}]
        },
        {
            "name": "★ Karambit | Doppler (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_knife_karambit_am_doppler_phase1_light_png.png",
                "https://cdn.pricempire.com/730/karambit-doppler-factory-new.png"
            ],
            "sells": [{"price": 850.00, "provider": "Buff.163"}, {"price": 955.00, "provider": "CSFloat"}, {"price": 970.00, "provider": "Skinport"}, {"price": 985.00, "provider": "DMarket"}],
            "buys": [{"price": 962.00, "provider": "Market.CSGO"}, {"price": 930.00, "provider": "CSFloat"}, {"price": 915.00, "provider": "DMarket"}, {"price": 995.00, "provider": "Steam"}]
        },
        {
            "name": "★ M9 Bayonet | Tiger Tooth (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_knife_m9_bay_an_tiger_orange_light_png.png",
                "https://cdn.pricempire.com/730/m9-bayonet-tiger-tooth-factory-new.png"
            ],
            "sells": [{"price": 740.00, "provider": "Buff.163"}, {"price": 830.00, "provider": "CSFloat"}, {"price": 845.00, "provider": "Skinport"}, {"price": 860.00, "provider": "DMarket"}],
            "buys": [{"price": 838.00, "provider": "Market.CSGO"}, {"price": 810.00, "provider": "CSFloat"}, {"price": 795.00, "provider": "DMarket"}, {"price": 875.00, "provider": "Steam"}]
        },
        {
            "name": "★ Bayonet | Fade (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_bayonet_aa_fade_light_png.png",
                "https://cdn.pricempire.com/730/bayonet-fade-factory-new.png"
            ],
            "sells": [{"price": 590.00, "provider": "Buff.163"}, {"price": 665.00, "provider": "CSFloat"}, {"price": 675.00, "provider": "Skinport"}, {"price": 690.00, "provider": "DMarket"}],
            "buys": [{"price": 672.00, "provider": "Market.CSGO"}, {"price": 645.00, "provider": "CSFloat"}, {"price": 630.00, "provider": "DMarket"}, {"price": 705.00, "provider": "Steam"}]
        },
        {
            "name": "★ Skeleton Knife (Vanilla)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_knife_skeleton_light_png.png",
                "https://cdn.pricempire.com/730/skeleton-knife.png"
            ],
            "sells": [{"price": 615.00, "provider": "Buff.163"}, {"price": 690.00, "provider": "CSFloat"}, {"price": 705.00, "provider": "Skinport"}, {"price": 720.00, "provider": "DMarket"}],
            "buys": [{"price": 698.00, "provider": "Market.CSGO"}, {"price": 670.00, "provider": "CSFloat"}, {"price": 655.00, "provider": "DMarket"}, {"price": 735.00, "provider": "Steam"}]
        },
        {
            "name": "★ Talon Knife | Slaughter (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_knife_widowmaker_am_zebra_light_png.png",
                "https://cdn.pricempire.com/730/talon-knife-slaughter-factory-new.png"
            ],
            "sells": [{"price": 530.00, "provider": "Buff.163"}, {"price": 595.00, "provider": "CSFloat"}, {"price": 605.00, "provider": "Skinport"}, {"price": 615.00, "provider": "DMarket"}],
            "buys": [{"price": 602.00, "provider": "Market.CSGO"}, {"price": 580.00, "provider": "CSFloat"}, {"price": 565.00, "provider": "DMarket"}, {"price": 630.00, "provider": "Steam"}]
        },
        {
            "name": "★ Stiletto Knife | Doppler (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_knife_stiletto_am_doppler_phase2_light_png.png",
                "https://cdn.pricempire.com/730/stiletto-knife-doppler-factory-new.png"
            ],
            "sells": [{"price": 490.00, "provider": "Buff.163"}, {"price": 550.00, "provider": "CSFloat"}, {"price": 560.00, "provider": "Skinport"}, {"price": 570.00, "provider": "DMarket"}],
            "buys": [{"price": 558.00, "provider": "Market.CSGO"}, {"price": 535.00, "provider": "CSFloat"}, {"price": 520.00, "provider": "DMarket"}, {"price": 585.00, "provider": "Steam"}]
        },

        # --- GLOVES (GĂNG TAY) ---
        {
            "name": "★ Sport Gloves | Amphibious (Field-Tested)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_sporty_gloves_amphibious_light_png.png",
                "https://cdn.pricempire.com/730/sport-gloves-amphibious-field-tested.png"
            ],
            "sells": [{"price": 720.00, "provider": "Buff.163"}, {"price": 810.00, "provider": "CSFloat"}, {"price": 825.00, "provider": "Skinport"}, {"price": 840.00, "provider": "DMarket"}],
            "buys": [{"price": 818.00, "provider": "Market.CSGO"}, {"price": 790.00, "provider": "CSFloat"}, {"price": 775.00, "provider": "DMarket"}, {"price": 855.00, "provider": "Steam"}]
        },
        {
            "name": "★ Specialist Gloves | Crimson Web (Field-Tested)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_specialist_gloves_crimson_web_light_png.png",
                "https://cdn.pricempire.com/730/specialist-gloves-crimson-web-field-tested.png"
            ],
            "sells": [{"price": 240.00, "provider": "Buff.163"}, {"price": 275.00, "provider": "CSFloat"}, {"price": 285.00, "provider": "Skinport"}, {"price": 295.00, "provider": "DMarket"}],
            "buys": [{"price": 282.00, "provider": "Market.CSGO"}, {"price": 265.00, "provider": "CSFloat"}, {"price": 255.00, "provider": "DMarket"}, {"price": 310.00, "provider": "Steam"}]
        },
        {
            "name": "★ Moto Gloves | Spearmint (Battle-Scarred)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_motorcycle_gloves_spearmint_light_png.png",
                "https://cdn.pricempire.com/730/moto-gloves-spearmint-battle-scarred.png"
            ],
            "sells": [{"price": 380.00, "provider": "Buff.163"}, {"price": 430.00, "provider": "CSFloat"}, {"price": 440.00, "provider": "Skinport"}, {"price": 450.00, "provider": "DMarket"}],
            "buys": [{"price": 435.00, "provider": "Market.CSGO"}, {"price": 415.00, "provider": "CSFloat"}, {"price": 405.00, "provider": "DMarket"}, {"price": 465.00, "provider": "Steam"}]
        },

        # --- PISTOLS & MID-TIER ---
        {
            "name": "Desert Eagle | Printstream (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_deagle_cu_deag_printstream_light_png.png",
                "https://cdn.pricempire.com/730/desert-eagle-printstream-factory-new.png"
            ],
            "sells": [{"price": 95.00, "provider": "Buff.163"}, {"price": 115.00, "provider": "CSFloat"}, {"price": 120.00, "provider": "Skinport"}, {"price": 125.00, "provider": "DMarket"}],
            "buys": [{"price": 118.00, "provider": "Market.CSGO"}, {"price": 108.00, "provider": "CSFloat"}, {"price": 102.00, "provider": "DMarket"}, {"price": 130.00, "provider": "Steam"}]
        },
        {
            "name": "Desert Eagle | Fennec Fox (Factory New)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_deagle_gs_deagle_fennec_fox_light_png.png",
                "https://cdn.pricempire.com/730/desert-eagle-fennec-fox-factory-new.png"
            ],
            "sells": [{"price": 285.00, "provider": "Buff.163"}, {"price": 325.00, "provider": "CSFloat"}, {"price": 335.00, "provider": "Skinport"}, {"price": 345.00, "provider": "DMarket"}],
            "buys": [{"price": 330.00, "provider": "Market.CSGO"}, {"price": 315.00, "provider": "CSFloat"}, {"price": 305.00, "provider": "DMarket"}, {"price": 355.00, "provider": "Steam"}]
        },
        {
            "name": "MP9 | Wild Lily (Field-Tested)",
            "img_urls": [
                "https://raw.githubusercontent.com/ByMykel/counter-strike-image-tracker/main/static/panorama/images/econ/default_generated/weapon_mp9_sp_mp9_wild_lily_light_png.png",
                "https://cdn.pricempire.com/730/mp9-wild-lily-field-tested.png"
            ],
            "sells": [{"price": 680.00, "provider": "Buff.163"}, {"price": 765.00, "provider": "CSFloat"}, {"price": 780.00, "provider": "Skinport"}, {"price": 795.00, "provider": "DMarket"}],
            "buys": [{"price": 772.00, "provider": "Market.CSGO"}, {"price": 745.00, "provider": "CSFloat"}, {"price": 730.00, "provider": "DMarket"}, {"price": 810.00, "provider": "Steam"}]
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
            img_bytes = render_infographic_card(name, sells, buys, skin.get("img_urls", []))
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
