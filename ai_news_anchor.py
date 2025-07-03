import requests
import subprocess

# ====== CONFIGURATION ======
SERPAPI_API_KEY = "2c12bae0a3cf10429a04bd9ea9b15a962c9284971d92f451d295a4d24b68ba42"  # 🔑 Replace with your real key
OLLAMA_MODEL_NAME = "mistral"  # You can change this if you're using another model locally
# ===========================


def fetch_news_from_serpapi(topic):
    url = "https://serpapi.com/search.json"
    params = {
        "q": topic,
        "tbm": "nws",
        "api_key": SERPAPI_API_KEY
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        news_results = data.get("news_results", [])
        summaries = []

        print(f"\n📰 Top {len(news_results)} News Headlines:\n")
        for news in news_results:
            title = news.get("title", "No Title")
            snippet = news.get("snippet", "No Snippet")
            print(f"🗞️ {title}\n   {snippet}\n")
            summaries.append(f"{title}: {snippet}")
        return summaries
    else:
        print("❌ Failed to fetch news:", response.status_code)
        return []


def generate_report_with_ollama(topic, summaries):
    combined_summary = "\n".join(summaries)
    
    prompt = f"""
You are a professional news anchor AI. Using the following live news summaries, write a polished, formal, and neutral-toned news report script.
The tone should sound like a real human anchor reading it for TV. Structure it like a 60-second report.

Topic: {topic}

News Summaries:
{combined_summary}

Now write the full anchor script:
"""

    try:
        result = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL_NAME],
            input=prompt.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180
        )

        if result.returncode == 0:
            output = result.stdout.decode("utf-8")
            print("\n🎙️ AI Anchor Script:\n")
            print(output)
            return output
        else:
            print("❌ Error:", result.stderr.decode("utf-8"))
            return ""
    except Exception as e:
        print("❌ Exception occurred:", e)
        return ""


# ==============================
# MAIN FLOW
# ==============================
if __name__ == "__main__":
    print("🤖 Welcome to AI News Anchor")
    user_topic = input("📢 Enter a news topic: ")

    print("\n🔎 Fetching live news...")
    news_data = fetch_news_from_serpapi(user_topic)

    if news_data:
        print("\n🧠 Generating news script using Mistral + Ollama...")
        generate_report_with_ollama(user_topic, news_data)
    else:
        print("❌ Could not generate report due to lack of data.")
