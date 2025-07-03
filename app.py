import streamlit as st
import os
from pathlib import Path
import subprocess
import requests, base64
from gtts import gTTS
import ffmpeg

# API KEYS
SERPAPI_KEY = "2c12bae0a3cf10429a04bd9ea9b15a962c9284971d92f451d295a4d24b68ba42"
DID_API_KEY = "aGltYW5zaHViaGFnYXQyNTEyQGdtYWlsLmNvbQ:Zx0KNl3vQZKrJsRKfmtOW"
encoded_auth = base64.b64encode(DID_API_KEY.encode("utf-8")).decode("utf-8")
AUTH_HEADER = {"Authorization": f"Basic {encoded_auth}"}

# Step 1
def fetch_news(query):
    st.info("🔍 Fetching news...")
    url = f"https://serpapi.com/search.json?q={query}&api_key={SERPAPI_KEY}&tbm=nws"
    response = requests.get(url).json()
    articles = response.get("news_results", [])[:5]
    headlines = [f"{a['title']} - {a.get('snippet','')}" for a in articles]
    return "\n".join(headlines)

# Step 2
def generate_script(context):
    st.info("🧠 Generating script via Mistral...")
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

# Step 3
def generate_voice(script_text, output_path="input/voice.mp3"):
    st.info("🎤 Generating voice...")
    Path("input").mkdir(exist_ok=True)
    tts = gTTS(text=script_text, lang='en', slow=False)
    tts.save(output_path)
    wav_output = "input/voice.wav"
    os.system(f"ffmpeg -y -i {output_path} -ar 44100 -ac 1 -acodec pcm_s16le {wav_output}")
    return wav_output

# Step 4
def generate_avatar_video_wav2lip(face_path, audio_path, output_path):
    st.info("🧑‍💻 Generating avatar video...")
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
            return output_path
        else:
            raise Exception("Wav2Lip output video not found.")
    except Exception as e:
        st.error(f"Wav2Lip failed: {e}")
        return None

# Step 5
def merge_with_broll(avatar_path, broll_path="assets/broll_clip.mp4", output_path="output/final_news_video.mp4"):
    if not avatar_path or not os.path.exists(avatar_path):
        raise Exception("❌ Avatar video not found.")
    st.info("🎮 Merging avatar and B-roll...")
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

# Pipeline
def generate_news_video(news_topic):
    headlines = fetch_news(news_topic)
    if not headlines:
        st.error("❌ No news found.")
        return
    st.success("📰 Top headlines fetched!")

    script = generate_script(headlines)
    st.success("📜 Script generated!")

    voice_path = generate_voice(script)
    st.success("🎧 Voiceover ready!")

    face_path = "input/face.jpg"
    if not os.path.exists(face_path):
        st.error("❌ 'input/face.jpg' is missing.")
        return

    output_avatar_path = "output/avatar.mp4"
    avatar_path = generate_avatar_video_wav2lip(face_path, voice_path, output_avatar_path)
    if not avatar_path:
        return

    final_video = merge_with_broll(avatar_path)
    return final_video

# Streamlit UI
st.set_page_config(page_title="🎙️ AI Anchor", layout="centered")
st.title("🎙️ AI News Anchor Generator")
st.markdown("Automatically fetches news, creates a script, voiceover, avatar, and adds B-roll visuals.")

topic = st.text_input("📢 Enter a news topic", placeholder="e.g. earthquake in Delhi")

if st.button("🎬 Generate Video"):
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        with st.spinner("⏳ Running pipeline..."):
            final_output = generate_news_video(topic)
            if final_output and os.path.exists(final_output):
                st.success("✅ Video generated successfully!")
                st.video(final_output)
            else:
                st.error("❌ Video generation failed.")
