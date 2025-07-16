# ✅ نسخة معدلة لتعمل بشكل صحيح مع GitHub Actions بدون الاعتماد على session file محلي

import os
import re
import requests
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest

# GitHub Actions Secrets (يجب ضبطها من واجهة GitHub)
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']
channel_username = 'ahwalaltreq'
api_url = 'https://ahwal-checkpoints-api.onrender.com/api/v1/checkpoints/update'

client = TelegramClient(StringSession(session_string), api_id, api_hash)

CHECKPOINT_TO_CITY = {
    "قلنديا": "القدس", "الكونتينر": "بيت لحم", "حوارة": "نابلس", "بيت إيل": "رام الله",
    "الزعيم": "القدس", "شعفاط": "القدس", "دير شرف": "نابلس", "ديرشرف": "نابلس",
    "الولجة": "بيت لحم", "ترقوميا": "الخليل", "النبي يونس": "الخليل", "زعترة": "نابلس",
    "صرة": "نابلس", "صره": "نابلس", "العزرية": "القدس", "جسر حلحول": "الخليل",
    "سدة قراوة": "سلفيت", "جماعين": "سلفيت", "شقبا": "رام الله", "كرملو": "رام الله",
    "ترمسعيا": "رام الله", "دير دبوان": "رام الله", "ديردبوان": "رام الله",
    "بوابة اللبن": "نابلس", "بوابة سلفيت": "سلفيت", "بوابة بروقين الغربية": "سلفيت",
    "بديا": "سلفيت", "بوابة بروقين الشرقية": "سلفيت"
}

checkpoint_keywords = ["حاجز", "بوابة", "مفتوح", "مغلق", "مغلقه", "مغلقة", "ازدحام", "سالك", "سالكة", "سالكه"]
KNOWN_CHECKPOINTS = list(CHECKPOINT_TO_CITY.keys())

LAST_ID_FILE = "last_id.txt"

def load_last_message_id():
    if os.path.exists(LAST_ID_FILE):
        try:
            return int(open(LAST_ID_FILE, 'r').read().strip())
        except:
            return 0
    return 0

def save_last_message_id(message_id):
    with open(LAST_ID_FILE, 'w') as f:
        f.write(str(message_id))

def normalize_arabic(text):
    return text.replace("ى", "ي").replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").lower()

def extract_status(text):
    if "مفتوح" in text: return "مفتوح"
    if "مغلق" in text or "مغلقه" in text: return "مغلق"
    if "ازدحام" in text: return "ازدحام"
    if "سالكة" in text or "سالكه" in text or "سالك" in text: return "سالكة"
    return "غير معروف"

def extract_name(text):
    for cp in KNOWN_CHECKPOINTS:
        if cp in text:
            return cp
    match = re.search(r"(?:حاجز|بوابة)\s+([^\n،:]+)", text)
    return match.group(1).strip() if match else "غير معروف"

def extract_city_from_checkpoint(cp):
    return CHECKPOINT_TO_CITY.get(cp, "غير معروف")

def extract_checkpoint_data(text, msg_id, msg_date):
    norm_text = normalize_arabic(text)
    if any(k in norm_text for k in checkpoint_keywords):
        name = extract_name(text)
        city = extract_city_from_checkpoint(name)
        return {
            "name": name,
            "city": city,
            "status": extract_status(norm_text),
            "sourceText": text,
            "sourceMessageId": msg_id,
            "latitude": 0.0,
            "longitude": 0.0,
            "effectiveAt": msg_date.isoformat()
        }
    return None

async def run_scraper():
    last_seen_id = load_last_message_id()
    await client.start()
    entity = await client.get_entity(channel_username)
    messages = await client(GetHistoryRequest(
        peer=entity,
        limit=100,
        offset_id=0,
        max_id=0,
        min_id=last_seen_id + 1,
        offset_date=None,
        add_offset=0,
        hash=0
    ))

    for message in reversed(messages.messages):
        if hasattr(message, 'message') and message.id > last_seen_id:
            data = extract_checkpoint_data(message.message, message.id, message.date)
            if data:
                print(f"\n✅ نقطة جديدة ({message.id}): {data['name']} | {data['status']}")
                try:
                    res = requests.post(api_url, json=data)
                    print("➡️ تم الإرسال بنجاح" if res.status_code == 200 else f"⚠️ فشل - كود: {res.status_code}")
                except Exception as e:
                    print(f"❌ خطأ أثناء الإرسال: {e}")
            last_seen_id = max(last_seen_id, message.id)
            save_last_message_id(last_seen_id)

import asyncio
asyncio.run(run_scraper())
