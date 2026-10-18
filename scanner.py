import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

# Lấy cấu hình từ GitHub Secrets hoặc biến môi trường
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
API_KEY = os.getenv("PRICEMPIRE_API_KEY", "").strip()
MIN_PRICE = float(os.getenv("MIN_PRICE", 100.0))
MAX_PRICE = float(os.getenv("MAX_PRICE", 1000.0))

SELL_SOURCES = "buff163,csfloat,skinport,dmarket,steam,tradeit,bitskins,skinbaron,gamerpay,shadowpay,waxpeer,marketcsgo,swapgg,csmoney,lisskins"
BUY_SOURCES = "buff163_buy,steam_buy,dmarket_buy,waxpeer_buy,csmoney_buy,marketcsgo_buy,youpin_buy,ecosteam_buy,skins_buy"

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Chưa có Telegram Token hoặc Chat ID.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print("Đã gửi tin nhắn Telegram thành công.")
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def main():
    if not API_KEY:
        print("Chưa cấu hình PRICEMPIRE_API_KEY. Dừng quét.")
        return

    url = f"https://api.pricempire.com/v4/paid/items/prices?app_id=730&currency=USD&sources={SELL_SOURCES},{BUY_SOURCES}&api_key={API_KEY}"
    headers = {"Authorization": f"Bearer {API_KEY}", "User-Agent": "GitHubActions-Scanner/1.0"}
    
    print(f"Đang tải dữ liệu từ Pricempire...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            items = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Lỗi kết nối Pricempire: {e}")
        return

    results = []
    for item in items:
        name = item.get("market_hash_name", "")
        prices = item.get("prices", [])
        lowest_sell = None
        highest_buy = None

        for p in prices:
            raw_p = p.get("price")
            if not raw_p or raw_p <= 0:
                continue
            val = float(raw_p) / 100.0
            k = p.get("provider_key", "")
            if k.endswith("_buy"):
                if highest_buy is None or val > highest_buy["price"]:
                    highest_buy = {"provider": k.replace("_buy", "").upper(), "price": val}
            else:
                if lowest_sell is None or val < lowest_sell["price"]:
                    lowest_sell = {"provider": k.upper(), "price": val}

        if lowest_sell and (MIN_PRICE <= lowest_sell["price"] <= MAX_PRICE):
            spread = (highest_buy["price"] - lowest_sell["price"]) if highest_buy else -100
            roi = (spread / lowest_sell["price"] * 100) if (highest_buy and lowest_sell["price"] > 0) else -100
            results.append({
                "name": name,
                "sell": lowest_sell,
                "buy": highest_buy,
                "spread": spread,
                "roi": roi
            })

    results.sort(key=lambda x: x["roi"], reverse=True)
    top_picks = results[:8]

    if not top_picks:
        print("Không tìm thấy skin phù hợp.")
        return

    lines = [f"🔥 <b>BÁO CÁO PRICEMPIRE (${MIN_PRICE:,.0f} - ${MAX_PRICE:,.0f} USD)</b>\n━━━━━━━━━━━━━━━━━━━"]
    for idx, r in enumerate(top_picks, 1):
        url_enc = urllib.parse.quote(r['name'])
        link = f"https://pricempire.com/cs2-skin-search?search={url_enc}"
        buy_txt = f"<b>${r['buy']['price']:,.2f}</b> ({r['buy']['provider']})" if r['buy'] else "<i>Chưa có</i>"
        spread_txt = f"+${r['spread']:,.2f} (+{r['roi']:.1f}%)" if r['spread'] >= 0 else f"-${abs(r['spread']):,.2f} ({r['roi']:.1f}%)"
        lines.append(
            f"<b>{idx}. <a href=\"{link}\">{r['name']}</a></b>\n"
            f"   🟢 Giá bán thấp nhất: <b>${r['sell']['price']:,.2f}</b> ({r['sell']['provider']})\n"
            f"   🔵 Giá mua cao nhất: {buy_txt}\n"
            f"   📊 Chênh lệch: <code>{spread_txt}</code>\n"
        )
    lines.append(f"⏰ <i>Thời gian: {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}</i>")
    send_telegram("\n".join(lines))

if __name__ == "__main__":
    main()
