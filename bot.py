from io import BytesIO
import ccxt
import mplfinance as mpf
import pandas as pd
import requests

# --- CONFIGURATION ---
BOT_TOKEN = "8201345656:AAExLcZA1M4xZzQgZ085PXOOtjxfjnSshVU"
CHAT_ID = "6002245978"
OPENROUTER_KEY = (
    "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"
)

SYMBOL = "BTC/USDT"
TIMEFRAME = "4h"


def send_telegram_message(text):
  """Sends a text message to your Telegram chat."""
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
  response = requests.post(url, json=payload)
  return response.json()


def send_telegram_photo(photo_bytes, caption):
  """Sends a chart image with analysis text to your Telegram chat."""
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
  files = {"photo": ("chart.png", photo_bytes, "image/png")}
  data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
  response = requests.post(url, data=data, files=files)
  return response.json()


def fetch_market_data():
  """Fetches OHLCV candles using CCXT from Binance."""
  print(f"Fetching market data for {SYMBOL}...")
  exchange = ccxt.binance()
  candles = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=50)
  df = pd.DataFrame(
      candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
  )
  df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
  df.set_index("timestamp", inplace=True)
  return df


def generate_chart(df):
  """Creates a candlestick chart image in memory using mplfinance."""
  print("Generating technical chart...")
  buf = BytesIO()
  # Plot last 30 candles for clarity
  mpf.plot(
      df.tail(30),
      type="candle",
      style="yahoo",
      title=f"{SYMBOL} ({TIMEFRAME})",
      volume=True,
      savefig=dict(fname=buf, dpi=150, format="png", bbox_inches="tight"),
  )
  buf.seek(0)
  return buf.read()


def get_ai_signal(df):
  """Sends recent price context to OpenRouter to get a trading signal."""
  print("Consulting OpenRouter AI analyst...")
  recent_prices = df[
      ["open", "high", "low", "close", "volume"]
  ].tail(10).to_string()

  prompt = (
      f"Analyze these recent 4-hour candles for {SYMBOL}:\n\n"
      f"{recent_prices}\n\n"
      "Provide a short trading signal response in this exact format:\n"
      "SIGNAL: [BUY / SELL / NEUTRAL]\n"
      "CONFIDENCE: [Low / Medium / High]\n"
      "REASON: [1-2 sentences explaining why]"
  )

  headers = {
      "Authorization": f"Bearer {OPENROUTER_KEY}",
      "Content-Type": "application/json",
      "HTTP-Referer": "https://github.com",
      "X-Title": "CryptoBot",
  }

  payload = {
      "model": "deepseek/deepseek-chat",
      "messages": [{"role": "user", "content": prompt}],
  }

  response = requests.post(
      "https://openrouter.ai/api/v1/chat/completions",
      headers=headers,
      json=payload,
  )
  result = response.json()

  try:
    return result["choices"]["0"]["message"]["content"]
  except Exception as e:
    return f"SIGNAL: NEUTRAL\nREASON: Error parsing AI response ({str(e)})"


def main():
  try:
    # 1. Get Data via CCXT
    df = fetch_market_data()

    # 2. Get Analysis via OpenRouter
    ai_analysis = get_ai_signal(df)

    # 3. Generate Chart via mplfinance
    chart_bytes = generate_chart(df)

    # 4. Dispatch to Telegram
    caption = f"🚨 *AI TRADING SIGNAL* 🚨\n\n{ai_analysis}"
    send_telegram_photo(chart_bytes, caption)
    print("Signal successfully sent to Telegram!")

  except Exception as e:
    err_msg = f"❌ Bot Error: {str(e)}"
    print(err_msg)
    send_telegram_message(err_msg)


if __name__ == "__main__":
  main()
