import joblib
import os
import json  # ← IMPORTANT
from groq import Groq
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Load Models Once at Startup
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
try:
    price_model = joblib.load(os.path.join(MODEL_DIR, 'price_predictor.pkl'))
    fraud_model = joblib.load(os.path.join(MODEL_DIR, 'fraud_detector.pkl'))
    MODELS_LOADED = True
except:
    MODELS_LOADED = False
    print("⚠️ Warning: ML Models not found. Running in mock mode.")

# Gen AI Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def predict_price(starting_price, duration_hours):
    if not MODELS_LOADED:
        return starting_price * 1.5
    try:
        pred = price_model.predict([[starting_price, duration_hours]])
        return round(pred[0], 2)
    except:
        return starting_price * 1.5

def detect_fraud(amount, time_left, user_id):
    if not MODELS_LOADED:
        return False
    try:
        prob = fraud_model.predict_proba([[amount, time_left, user_id]])[0][1]
        return prob > 0.5 
    except:
        return False

async def analyze_item_groq(description: str):
    """Analyze item description using Groq AI → returns Python dict"""
    if not os.getenv("GROQ_API_KEY"):
        return {"risk_level": "unknown", "summary": "GROQ_API_KEY not set"}
    
    try:
        # Run in thread to avoid blocking async loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            messages=[{
                "role": "user", 
                "content": f"Analyze this auction item for fraud risk. Return JSON: {{risk_level: 'low/med/high', summary: 'short text'}}. Item: {description}"
            }],
            model="llama3-8b-8192",
            temperature=0.5,
            max_tokens=150,
            response_format={"type": "json_object"}
        ))
        
        # Parse JSON string → Python dict ✅
        raw_content = response.choices[0].message.content
        return json.loads(raw_content)
        
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e}")
        return {"risk_level": "unknown", "summary": "AI response malformed"}
    except Exception as e:
        print(f"⚠️ Groq API error: {e}")
        return {"risk_level": "error", "summary": str(e)}