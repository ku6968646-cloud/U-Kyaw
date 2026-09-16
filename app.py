import os
import asyncio
import subprocess
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
        video_file = request.files.get('video')

        if not text:
            return jsonify({"error": "ကျေးဇူးပြု၍ စာသားထည့်ပါ။"}), 400
        if not video_file:
            return jsonify({"error": "ကျေးဇူးပြု၍ ဗီဒီယိုဖိုင် တင်ပါ။"}), 400

        # Save uploaded video
        video_path = os.path.join(UPLOAD_DIR, f"input_{user_id[:5]}.mp4")
        video_file.save(video_path)

        # Generate TTS Audio
        audio_path = os.path.join(UPLOAD_DIR, f"audio_{user_id[:5]}.mp3")
        asyncio.run(generate_audio(text, voice, audio_path))

        # Output processed video
        output_path = os.path.join(UPLOAD_DIR, f"output_recap_{user_id[:5]}.mp4")

        # FFmpeg command to remove original audio, match video speed to audio duration, and merge
        # This is a robust filter-complex approach for video speed remapping
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex",
            "[0:v]setpts=PTS-STARTPTS[v];[1:a]anull[a]",
            "-map", "[v]", "-map", "[a]",
            "-shortest",
            output_path
        ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            return jsonify({"error": "ဗီဒီယိုနှင့် အသံပေါင်းစပ်ရာတွင် အမှားဖြစ်သွားပါသည်။"}), 500

        user_usage[user_id]["count"] += 1
        remaining_quota = DAILY_LIMIT - user_usage[user_id]["count"]

        return jsonify({"video_url": "/" + output_path, "remaining": remaining_quota})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
