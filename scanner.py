import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
API_KEY = os.getenv("PRICEMPIRE_API_KEY", "").strip()
MIN_PRICE = float(os.getenv("MIN_PRICE", 100.0))
MAX_PRICE = float(os.getenv("MAX_PRICE", 1000.0))

print("=== KIỂM TRA BẢO MẬT (SECRETS) ===")
print(f"1. TELEGRAM_BOT_TOKEN: {'Đã nhận' if BOT_TOKEN else 'CHƯA CÓ (TRỐNG)'}")
print(f"2. TELEGRAM_CHAT_ID: {'Đã nhận' if CHAT_ID else 'CHƯA CÓ (TRỐNG)'}")
print(f"3. PRICEMPIRE_API_KEY: {'Đã nhận (' + API_KEY[:6] + '...)' if API_KEY else 'CHƯA CÓ (TRỐNG)'}")
print("==================================")

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Bỏ qua gửi tin nhắn vì chưa đủ Token hoặc Chat ID.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print("Đã gửi tin nhắn Telegram thành công!")
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def main():
    if not API_KEY:
        print("LỖI: Chưa có PRICEMPIRE_API_KEY trong GitHub Secrets. Hãy thêm vào để chạy.")
        return

    # Tự động thử các cổng API tương ứng với gói tài khoản
    endpoints = [
        f"https://api.pricempire.com/v4/trader/prices?currency=USD&api_key={API_KEY}",
        f"https://api.pricempire.com/v4/paid/items/prices?app_id=730&currency=USD&sources=buff163,buff163_buy,csfloat,skinport,steam&api_key={API_KEY}"
    ]

    items = None
    for ep in endpoints:
        print(f"Đang thử kết nối cổng: {ep.split('?')[0]} ...")
        headers = {"Authorization": f"Bearer {API_KEY}", "User-Agent": "Pricempire-Trader-Scanner/1.0"}
        req = urllib.request.Request(ep, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                items = json.loads(resp.read().decode("utf-8"))
                print("Kết nối thành công! Đang xử lý bảng giá...")
                break
        except Exception as e:
            print(f"Cổng này chưa mở: {e}")

    if not items:
        print("Không thể tải bảng giá từ các cổng API.")
        return

    results = []
    # Xử lý dữ liệu trả về (hỗ trợ cả dạng list và dạng dict)
    item_list = items if isinstance(items, list) else items.get("items", items.get("data", []))
    for item in item_list:
        name = item.get("market_hash_name", item.get("name", ""))
        prices = item.get("prices", [])
        lowest_sell = None
        highest_buy = None

        if isinstance(prices, list):
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
            results.append({"name": name, "sell": lowest_sell, "buy": highest_buy, "spread": spread, "roi": roi})

    results.sort(key=lambda x: x["roi"], reverse=True)
    top_picks = results[:8]

    if not top_picks:
        print(f"Không có skin nào trong khoảng ${MIN_PRICE:.0f} - ${MAX_PRICE:.0f} USD lúc này.")
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
