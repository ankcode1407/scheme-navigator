import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {
            "role": "user",
            "content": "I am a farmer in UP with 1.5 hectares of land. What government schemes might I qualify for?"
        }
    ],
    max_tokens=500
)

print(response.choices[0].message.content)