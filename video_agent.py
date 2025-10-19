import os
import random
import schedule
import time
from moviepy.editor import ImageClip, concatenate_videoclips, TextClip, CompositeVideoClip
from gtts import gTTS
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import requests

# إعدادات
OUTPUT_DIR = "output_videos"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# إعداد YouTube بـ service account
credentials = Credentials.from_service_account_file('service_account.json', scopes=['https://www.googleapis.com/auth/youtube.upload'])
youtube = build('youtube', 'v3', credentials=credentials)

# مفتاح Pexels (من env variable)
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY', 'YOUR_DEFAULT_KEY')  # بدل بـ secrets
VIDEO_TOPIC = os.getenv('VIDEO_TOPIC', 'دروس الدارجة')

# جلب صور من Pexels
def get_pexels_images():
    url = f"https://api.pexels.com/v1/search?query={VIDEO_TOPIC}&per_page=5"
    headers = {"Authorization": PEXELS_API_KEY}
    response = requests.get(url, headers=headers)
    data = response.json()
    return [photo['src']['large'] for photo in data['photos']]

# توليد فيديو
def generate_video():
    images = get_pexels_images()
    clips = [ImageClip(img).set_duration(5) for img in images[:3]]
    video = concatenate_videoclips(clips, method="compose")

    # نص وصوت
    text = TextClip("دروس يومية بالدارجة", fontsize=70, color='white', bg_color='black')
    text = text.set_duration(5).set_position('bottom')
    video = CompositeVideoClip([video, text])

    # صوت
    tts = gTTS(text="مرحبا، هاد درس يومي بالدارجة!", lang='ar')
    tts.save("temp_audio.mp3")
    video = video.set_audio("temp_audio.mp3")

    # حفظ الفيديو
    output_path = os.path.join(OUTPUT_DIR, f"video_{int(time.time())}.mp4")
    video.write_videofile(output_path, fps=24)

    return output_path

# رفع الفيديو ليوتيوب
def upload_to_youtube(video_path):
    body = {
        'snippet': {'title': f'{VIDEO_TOPIC} - {time.strftime("%Y-%m-%d")}', 'description': 'فيديو يومي', 'tags': [VIDEO_TOPIC], 'categoryId': '22'},
        'status': {'privacyStatus': 'public'}
    }
    with open(video_path, 'rb') as video_file:
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=video_file
        )
        response = request.execute()
    return response['id']

# الدالة الرئيسية
def job():
    video_path = generate_video()
    video_id = upload_to_youtube(video_path)
    print(f"Video uploaded: https://youtu.be/{video_id}")

# تشغيل كل يوم 9 صباحا (يمكن تعديلها)
schedule.every().day.at("09:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
