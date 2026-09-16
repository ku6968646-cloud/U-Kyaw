import os
import asyncio
from flask import Flask, render_template, request, jsonify, session
import edge_tts
from datetime import datetime

app = Flask(__name__)
app.secret_key = "u_kyaw_secure_secret_key_2026"
UPLOAD_DIR = "static"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

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
        return jsonify({"error": "ယနေ့အတွက် အသံထုတ်ယူမှု ခွဲတမ်း (၃ ပုဒ်) ပြည့်သွားပါပြီ။"}), 403

    try:
        text = request.form.get('text', '').strip()
        voice = request.form.get('voice', 'my-MM-NilarNeural')

        if not text:
            return jsonify({"error": "ကျေးဇူးပြု၍ စာသားထည့်ပါ။"}), 400

        audio_filename = f"audio_{user_id[:5]}.mp3"
        audio_path = os.path.join(UPLOAD_DIR, audio_filename)
        
        asyncio.run(generate_audio(text, voice, audio_path))

        user_usage[user_id]["count"] += 1
        remaining_quota = DAILY_LIMIT - user_usage[user_id]["count"]

        return jsonify({
            "audio_url": "/" + audio_path,
            "remaining": remaining_quota
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
        
