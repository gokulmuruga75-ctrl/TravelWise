import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import SYSTEM_PROMPT

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured in the .env file.")

client = genai.Client(api_key=API_KEY)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    if not isinstance(history, list):
        history = []

    contents = []

    for item in history[-12:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        text = item.get("content")

        if role not in {"user", "model"} or not isinstance(text, str) or not text.strip():
            continue

        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=text.strip())],
            )
        )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)],
        )
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )

        answer = (response.text or "").strip()

        if not answer:
            answer = "I couldn't generate a response right now. Please try again."

        return jsonify({"response": answer})

    except Exception:
        app.logger.exception("Gemini API request failed.")
        return jsonify(
            {"error": "Something went wrong while contacting TravelWise. Please try again."}
        ), 500


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
