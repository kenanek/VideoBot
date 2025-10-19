import os
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gtts
from moviepy.editor import ImageClip, concatenate_videoclips, TextClip, CompositeVideoClip
import random
from datetime import datetime
import schedule
import time

# Config
YOUTUBE_CLIENT_SECRETS = "client_secrets.json"
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "your_pexels_api_key_here")
VIDEO_TOPIC = os.getenv("VIDEO_TOPIC", "Moroccan culture tips")
OUTPUT_DIR = "output_videos"

# Generate Script
def generate_script(topic):
    prompt = f"Write a 50-word script for a 30-second video about {topic} in Darija."
    script = "Salam! Bghiti t3lm 3la l-Maghrib? 1. Zour Chefchaouen. 2. Jrrb tagine. 3. Sma3 gnawa. 4. Tkalem darija. 5. Chuf souks! Abda l-mgharba w t3lm bzzaf!"
    return script

# Fetch Images
def fetch_images(query, api_key):
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=5"
    headers = {"Authorization": api_key}
    response = requests.get(url, headers=headers).json()
    images = [photo["src"]["medium"] for photo in response["photos"]]
    for i, img_url in enumerate(images):
        img_data = requests.get(img_url).content
        with open(f"temp_image_{i}.jpg", "wb") as f:
            f.write(img_data)
    return [f"temp_image_{i}.jpg" for i in range(len(images))]

# Generate Voiceover
def generate_voiceover(text):
    tts = gtts.gTTS(text, lang="ar")
    tts.save("voiceover.mp3")
    return "voiceover.mp3"

# Create Video
def create_video(images, script, voiceover):
    clips = []
    duration_per_image = 6
    for img in images:
        clip = ImageClip(img).set_duration(duration_per_image)
        clips.append(clip)
    
    text_lines = script.split(".")[:3]
    for i, text in enumerate(text_lines):
        if text.strip():
            txt_clip = TextClip(text.strip(), fontsize=50, color="white", bg_color="black", size=(720, 1280))
            txt_clip = txt_clip.set_duration(duration_per_image).set_position(("center", "bottom"))
            clips[i] = CompositeVideoClip([clips[i], txt_clip])
    
    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.set_audio(AudioFileClip(voiceover))
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = f"{OUTPUT_DIR}/video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    final_clip.write_videofile(output_path, fps=24, codec="libx264")
    return output_path

# Upload to YouTube
def upload_to_youtube(video_path, title, description):
    flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    credentials = flow.run_local_server(port=0)
    youtube = build("youtube", "v3", credentials=credentials)
    
    body = {
        "snippet": {"title": title, "description": description, "tags": ["Morocco", "Darija", "Shorts"], "categoryId": "22"},
        "status": {"privacyStatus": "public"}
    }
    media = MediaFileUpload(video_path)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    return response["id"]

# Schedule Job
def job():
    script = generate_script(VIDEO_TOPIC)
    images = fetch_images(VIDEO_TOPIC.split()[0].lower(), PEXELS_API_KEY)
    voiceover = generate_voiceover(script)
    video_path = create_video(images, script, voiceover)
    video_id = upload_to_youtube(video_path, f"{VIDEO_TOPIC} - {datetime.now().strftime('%Y-%m-%d')}", script)
    print(f"Uploaded: https://youtu.be/{video_id}")

schedule.every().day.at("09:00").do(job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)