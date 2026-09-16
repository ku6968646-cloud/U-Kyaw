import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_from_directory
import edge_tts
import asyncio
from moviepy.editor import VideoFileClip, AudioFileClip

app = Flask(__name__)

# တစ်နေ့လျှင် အသံထုတ်ယူခွင့် ကန့်သတ်ချက်
DAILY_QUOTA = 3
usage_count = 0

@app.route('/')
def index():
    global usage_count
    remaining = DAILY_QUOTA - usage_count
    return render_template('index.html', remaining=max(0, remaining))

@app.route('/convert', methods=['POST'])
def convert():
    global usage_count
    if usage_count >= DAILY_QUOTA:
        return jsonify({'error': 'ယနေ့အတွက် အသံထုတ်ယူခွင့် (Quota) ကုန်ဆုံးသွားပါပြီ။'}), 429

    if 'video' not in request.files or 'text' not in request.form:
        return jsonify({'error': 'ဗီဒီယိုဖိုင် သို့မဟုတ် စာသား မပါဝင်ပါ။'}), 400

    video_file = request.files['video']
    text = request.form['text']
    voice = request.form.get('voice', 'my-MM-NilarNeural')

    if not video_file.filename or not text.strip():
        return jsonify({'error': 'ကျေးဇူးပြု၍ ဗီဒီယိုနှင့် စာသားများကို အပြည့်အစုံ ဖြည့်စွက်ပါ။'}), 400

    try:
        # Temporary directory တွင် ဖိုင်များသိမ်းရန်
        temp_dir = tempfile.mkdtemp()
        input_video_path = os.path.join(temp_dir, 'input_video.mp4')
        output_audio_path = os.path.join(temp_dir, 'output_audio.mp3')
        output_video_path = os.path.join(temp_dir, 'output_video.mp4')

        video_file.save(input_video_path)

        # Edge TTS ဖြင့် အသံဖိုင်ထုတ်ယူခြင်း
        async def generate_speech():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_audio_path)

        asyncio.run(generate_speech())

        # MoviePy ဖြင့် ဗီဒီယိုနှင့် အသံပေါင်းစပ်ခြင်း
        video_clip = VideoFileClip(input_video_path)
        audio_clip = AudioFileClip(output_audio_path)

        # ဗီဒီယို အတိုအရှည်ကို အသံအလျားနှင့် ချိန်ညှိခြင်း (သို့မဟုတ် အသံအတိုင်း ဗီဒီယိုကို ထားရှိခြင်း)
        final_clip = video_clip.set_audio(audio_clip)
        
        # ဖိုင်ထုတ်ယူသိမ်းဆည်းခြင်း (Bitrate များကို လျှော့ချထားပြီး Render တွင် မြန်ဆန်စေရန်)
        final_clip.write_videofile(
            output_video_path,
            codec='libx264',
            audio_codec='aac',
            fps=24,
            preset='ultrafast',
            logger=None
        )

        # Clip များကို ပိတ်သိမ်းရန်
        video_clip.close()
        audio_clip.close()
        final_clip.close()

        usage_count += 1
        remaining = DAILY_QUOTA - usage_count

        return jsonify({
            'success': True,
            'video_url': '/download_result',
            'remaining': max(0, remaining)
        })

    except Exception as e:
        return jsonify({'error': f'အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}'}), 500

@app.route('/download_result')
def download_result():
    # အဆင်သင့်ဖြစ်နေသော ဗီဒီယိုဖိုင်ကို ပြန်ပေးရန်
    # (မှတ်ချက်။ ဤနေရာတွင် production အတွက် temp folder မှ ဖိုင်ကို လုံခြုံစွာ ပြန်ထုတ်ပေးရန် လိုအပ်သည်)
    return send_from_directory(tempfile.gettempdir(), 'output_video.mp4', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
        
