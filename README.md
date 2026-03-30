# 🚀 BidMind AI - Real-Time Auction Engine

A high-frequency auction platform integrating **WebSockets** for real-time communication and **Machine Learning** for fraud detection and price prediction.

## 🧠 AI Features
1. **Fraud Detection**: Random Forest model analyzes bid patterns in real-time.
2. **Price Prediction**: Regression model forecasts auction closing price.
3. **Gen AI Analysis**: Uses Groq (Llama3) to analyze item descriptions for risk.

## 🛠️ Tech Stack
- **Backend**: Python FastAPI (Async WebSockets)
- **AI**: Scikit-Learn, Groq API
- **Frontend**: Vanilla JS, HTML5, CSS3
- **Infra**: Docker, SQLite

## 🏃 How to Run
1. `pip install -r requirements.txt`
2. Add `GROQ_API_KEY` to `.env`
3. Ensure `.pkl` models are in `/models`
4. `uvicorn app.main:app --reload`
5. Open `http://localhost:8000/static/index.html`