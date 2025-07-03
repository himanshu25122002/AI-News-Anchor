import requests, json, os, base64
from pathlib import Path
from gtts import gTTS
import ffmpeg
import time
import subprocess  # 🆕 Needed for Wav2Lip

# 🔑 Your API Keys
SERPAPI_KEY = "2c12bae0a3cf10429a04bd9ea9b15a962c9284971d92f451d295a4d24b68ba42"
DID_API_KEY = "aGltYW5zaHViaGFnYXQyNTEyQGdtYWlsLmNvbQ:Zx0KNl3vQZKrJsRKfmtOW"

# Encode D-ID API key
encoded_auth = base64.b64encode(DID_API_KEY.encode("utf-8")).decode("utf-8")
AUTH_HEADER = {"Authorization": f"Basic {encoded_auth}"}

# 🧠 Step 1: Fetch News from SerpAPI
def fetch_news(query):
    print("🔍 Fetching news from SerpAPI...")
    url = f"https://serpapi.com/search.json?q={query}&api_key={SERPAPI_KEY}&tbm=nws"
    response = requests.get(url).json()
    articles = response.get("news_results", [])[:5]
    headlines = [f"{a['title']} - {a.get('snippet','')}" for a in articles]
    return "\n".join(headlines)

# 🧠 Step 2: Generate News Script
def generate_script(context):
    print("🧠 Generating news script via Mistral...")
    prompt = (
        "You are a neutral, professional news summarizer. "
        "Avoid emotional tone or expressions like 'with a smile' or 'sad voice'. "
        "Just provide a clear spoken summary for a news anchor script.\n"
        f"News context:\n{context}\n\nScript:"
    )
    with open("temp_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    output = os.popen("ollama run mistral < temp_prompt.txt").read()
    return output.strip()

# 🎙️ Step 3: Generate Voice with gTTS
def generate_voice(script_text, output_path="input/voice.mp3"):
    print("🎤 Generating voice with gTTS (Google TTS)...")
    # No trimming needed for local Wav2Lip
    words = script_text.split()
    print(f"📝 Script length: {len(words)} words")

    Path("input").mkdir(exist_ok=True)
    tts = gTTS(text=script_text, lang='en', slow=False)
    tts.save(output_path)
    wav_output = "input/voice.wav"
    os.system(f"ffmpeg -y -i {output_path} -ar 44100 -ac 1 -acodec pcm_s16le {wav_output}")
    return wav_output

# 🆕 Step 4: Generate Avatar Video with Wav2Lip

def generate_avatar_video_wav2lip(face_path, audio_path, output_path):
    print("🧑‍💻 Generating avatar video using Wav2Lip...")
    command = [
        "python", "Wav2Lip/inference.py",
        "--checkpoint_path", "Wav2Lip/checkpoints/wav2lip_gan.pth",
        "--face", face_path,
        "--audio", audio_path
    ]

    try:
        subprocess.run(command, check=True)
        if os.path.exists("results/result_voice.mp4"):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            os.replace("results/result_voice.mp4", output_path)
            print(f"✅ Avatar video generated: {output_path}")
            return output_path
        else:
            raise Exception("Wav2Lip output video not found.")
    except Exception as e:
        print(f"❌ Wav2Lip failed: {e}")
        return None

# 🎮 Step 5: Merge with B-roll
def merge_with_broll(avatar_path, broll_path="assets/broll_clip.mp4", output_path="output/final_news_video.mp4"):
    if not avatar_path or not os.path.exists(avatar_path):
        raise Exception("❌ Avatar video not found, cannot merge with B-roll.")
    
    print("🎮 Merging avatar and b-roll scenes...")
    Path("output").mkdir(exist_ok=True)
    
    avatar_input = ffmpeg.input(avatar_path)

    if os.path.exists(broll_path):
        broll_input = ffmpeg.input(broll_path, ss=0, t=5)
        video, audio = ffmpeg.concat(broll_input.video, broll_input.audio,
                                     avatar_input.video, avatar_input.audio, v=1, a=1).node
        output = ffmpeg.output(video, audio, output_path)
    else:
        output = ffmpeg.output(avatar_input, output_path)
    
    output.run(overwrite_output=True)
    return output_path


# 🔁 Main Pipeline
def generate_news_video(news_topic):
    print(f"\n🤖 Starting AI Anchor Pipeline for: {news_topic}")
    headlines = fetch_news(news_topic)
    if not headlines:
        raise Exception("❌ No news found.")
    script = generate_script(headlines)
    voice_path = generate_voice(script)

    # ✅ You MUST place your avatar image at: input/face.jpg
    face_path = "input/face.jpg"
    output_avatar_path = "output/avatar.mp4"
    avatar_path = generate_avatar_video_wav2lip(face_path, voice_path, output_avatar_path)

    final_video = merge_with_broll(avatar_path)
    print(f"\n✅ Final news video saved to: {final_video}")

# 🟢 Entry Point
if __name__ == "__main__":
    topic = input("📢 Enter a news topic: ")
    generate_news_video(topic)
