import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# paste your API key here (temporary test)
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("GROQ_API_KEY not found in environment")
else:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Give me a cool AI fact"}],
        model="llama-3.3-70b-versatile",
    )
    print(response.choices[0].message.content)