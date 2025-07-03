import requests, json, os, base64, time
from pathlib import Path
from gtts import gTTS
import ffmpeg

# 🔑 Your API Keys
SERPAPI_KEY = "2c12bae0a3cf10429a04bd9ea9b15a962c9284971d92f451d295a4d24b68ba42"
DID_API_KEY = "aGltYW5zaHViaGFnYXQyNTEyQGdtYWlsLmNvbQ:Zx0KNl3vQZKrJsRKfmtOW"

# Encode the D-ID API key in Basic Auth format
encoded_auth = base64.b64encode(DID_API_KEY.encode("utf-8")).decode("utf-8")
AUTH_HEADER = {"Authorization": f"Basic {encoded_auth}"}

# 🧠 Fetch News
def fetch_news(query):
    print("🔍 Fetching news from SerpAPI...")
    url = f"https://serpapi.com/search.json?q={query}&api_key={SERPAPI_KEY}&tbm=nws"
    response = requests.get(url).json()
    articles = response.get("news_results", [])[:5]
    return "\n".join([f"{a['title']} - {a.get('snippet', '')}" for a in articles])

# 🧠 Generate Script
def generate_script(context):
    print("🧠 Generating news script via Mistral...")
    prompt = (
        "You are a neutral, professional news summarizer. "
        "Avoid emotional tone or expressions like 'smile' or 'sad voice'. "
        "Just provide a clean spoken script for a news anchor.\n"
        f"News context:\n{context}\n\nScript:"
    )
    with open("temp_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    return os.popen("ollama run mistral < temp_prompt.txt").read().strip()

# 🎙️ Generate Voice
def generate_voice(script_text, output_path="output/voice.mp3"):
    print("🎤 Generating voice with gTTS (Google TTS)...")
    Path("output").mkdir(exist_ok=True)
    words = script_text.split()
    if len(words) > 100:
        print("⚠️ Script too long, trimming to 100 words for D-ID...")
        script_text = " ".join(words[:100])
    gTTS(text=script_text, lang='en', slow=False).save(output_path)
    wav_output = "output/voice.wav"
    os.system(f"ffmpeg -y -i {output_path} -ar 44100 -ac 1 -acodec pcm_s16le {wav_output}")
    return wav_output

# 🧑‍💼 Generate Avatar with Retry
def generate_avatar_video(voice_path, script_text, avatar_image_url=None):
    print("🧑‍💻 Uploading voice and generating avatar video via D-ID...")
    image_url = avatar_image_url or "https://i.imgur.com/0MZ4X0B.jpg"
    with open(voice_path, 'rb') as f:
        voice_data = f.read()

    # Upload Audio
    upload_res = requests.post(
        "https://api.d-id.com/audios",
        headers=AUTH_HEADER,
        files={"audio": ("voice.wav", voice_data, "audio/wav")}
    )
    if upload_res.status_code != 200:
        raise Exception(f"❌ Audio upload failed: {upload_res.text}")
    audio_url = upload_res.json().get("url")

    # Attempt to create talk with retry
    for attempt in range(3):
        payload = {
            "script": {"type": "audio", "audio_url": audio_url},
            "source_url": image_url,
            "config": {"stitch": True}
        }
        headers = {**AUTH_HEADER, "Content-Type": "application/json"}
        res = requests.post("https://api.d-id.com/talks", headers=headers, json=payload)

        if res.status_code == 500:
            print(f"⚠️ Attempt {attempt+1}: D-ID API error: {res.text}")
            time.sleep(3)
            continue
        elif res.status_code not in [200, 201]:
            raise Exception(f"❌ Video creation failed: {res.text}")
        else:
            talk_id = res.json().get("id")
            break
    else:
        raise Exception("❌ D-ID is down or error persists. Try again later.")

    # Poll for result
    for attempt in range(30):
        time.sleep(4)
        status_res = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers).json()
        print(f"🕒 Attempt {attempt+1}: Status -> {status_res.get('status', 'unknown')}")
        if status_res.get("status") == "done":
            video_url = status_res.get("result_url")
            break
        elif status_res.get("status") == "error":
            raise Exception(f"❌ Avatar video error: {status_res.get('error', {}).get('description', 'Unknown')}")
    else:
        raise Exception("❌ Timed out waiting for avatar video.")

    # Download
    output_path = "output/avatar.mp4"
    with open(output_path, "wb") as f:
        f.write(requests.get(video_url).content)
    print("✅ Avatar video saved to:", output_path)
    return output_path

# 🎮 Merge with B-roll
def merge_with_broll(avatar_path, broll_path="assets/broll_clip.mp4", output_path="output/final_news_video.mp4"):
    print("🎮 Merging avatar and b-roll scenes...")
    Path("output").mkdir(exist_ok=True)
    avatar_input = ffmpeg.input(avatar_path)
    if os.path.exists(broll_path):
        broll_input = ffmpeg.input(broll_path, ss=0, t=5)
        concat = ffmpeg.concat(broll_input, avatar_input, v=1, a=1).node
        output = ffmpeg.output(concat[0], concat[1], output_path)
    else:
        output = ffmpeg.output(avatar_input, output_path)
    output.run(overwrite_output=True)
    return output_path

# 🔁 Pipeline
def generate_news_video(news_topic):
    print(f"\n🤖 Starting AI Anchor Pipeline for: {news_topic}")
    headlines = fetch_news(news_topic)
    if not headlines:
        raise Exception("❌ No news found for the given topic.")
    script = generate_script(headlines)
    voice_path = generate_voice(script)
    avatar_path = generate_avatar_video(voice_path, script)
    final_video = merge_with_broll(avatar_path)
    print(f"\n✅ Final video ready: {final_video}")

# 🟢 Start
if __name__ == "__main__":
    topic = input("📢 Enter a news topic: ")
    generate_news_video(topic)
