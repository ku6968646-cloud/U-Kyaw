import os
import asyncio
from flask import Flask, render_template, request, jsonify, session
import edge_tts
from datetime import datetime

app = Flask(__name__)
app.secret_key = "u_kyaw_secure_secret_key_2026"
AUDIO_DIR = "static"

if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

user_usage = {}
DAILY_LIMIT = 3

async def generate_audio(text, voice, filepath):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filepath)

@app.route('/')
def index():
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    today_str = datetime.now().strftime("%Y-%m-%d")

    if user_id not in user_usage or user_usage[user_id]["date"] != today_str:
        user_usage[user_id] = {"date": today_str, "count": 0}

    current_count = user_usage[user_id]["count"]
    return render_template('index.html', remaining=DAILY_LIMIT - current_count)

@app.route('/convert', methods=['POST'])
def convert():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    today_str = datetime.now().strftime("%Y-%m-%d")

    if user_id not in user_usage or user_usage[user_id]["date"] != today_str:
        user_usage[user_id] = {"date": today_str, "count": 0}

    if user_usage[user_id]["count"] >= DAILY_LIMIT:
        return jsonify({"error": "ယနေ့အတွက် အသံထုတ်ယူမှု ခွဲတမ်း (၃ ပုဒ်) ပြည့်သွားပါပြီ။ မနက်ဖြန်မှ ထပ်ကြိုးစားပါ။"}), 403

    try:
        req_data = request.get_json()
        items = req_data.get('items', [])
        if not items:
            return jsonify({"error": "No items provided"}), 400

        temp_files = []
        for i, item in enumerate(items):
            text = item.get('text', '').strip()
            raw_voice = item.get('voice', 'my-MM-NilarNeural')

            if not text:
                continue

            if any(m in raw_voice for m in ['Thiha', 'Aung', 'UThant', 'Htet']):
                voice = 'my-MM-ThihaNeural'
            else:
                voice = 'my-MM-NilarNeural'

            temp_path = os.path.join(AUDIO_DIR, f"temp_{i}.mp3")
            asyncio.run(generate_audio(text, voice, temp_path))
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                temp_files.append(temp_path)

        if not temp_files:
            return jsonify({"error": "No valid audio generated"}), 400

        user_usage[user_id]["count"] += 1

        combined_path = os.path.join(AUDIO_DIR, f"output_{user_id[:5]}.mp3")
        with open(combined_path, 'wb') as wfd:
            for f in temp_files:
                with open(f, 'rb') as fd:
                    wfd.read(fd.read())

        remaining_quota = DAILY_LIMIT - user_usage[user_id]["count"]
        return jsonify({"files": [combined_path], "remaining": remaining_quota})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
