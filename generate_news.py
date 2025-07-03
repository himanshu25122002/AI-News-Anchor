import subprocess
import json

def generate_news_report(topic):
    prompt = f"""Write a professional, factual, and engaging news anchor script for the topic: "{topic}". 
The tone should be neutral, formal, and news-style. The output should sound like a real human news anchor reading the report live. 
Include all known facts, time of event, location, what happened, and a concluding statement."""

    # Use Ollama to query Mistral model
    try:
        result = subprocess.run(
            ["ollama", "run", "mistral"],
            input=prompt.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120
        )

        if result.returncode == 0:
            output = result.stdout.decode("utf-8")
            print("\n📰 News Report:\n")
            print(output)
            return output
        else:
            print("❌ Error:", result.stderr.decode("utf-8"))

    except Exception as e:
        print("❌ Exception occurred:", e)

# ==============================
# Run the script
if __name__ == "__main__":
    user_topic = input("📢 Enter the news topic: ")
    generate_news_report(user_topic)
