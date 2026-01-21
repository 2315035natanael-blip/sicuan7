import yfinance as yf
import pandas as pd
import numpy as np


def get_market_data():

    tickers = {
        "IHSG": "^JKSE",
        "BBCA": "BBCA.JK",
        "TLKM": "TLKM.JK"
    }

    results = {}

    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)

            if df.empty:
                results[name] = {
                    "trend": "Data tidak tersedia",
                    "confidence": "Rendah"
                }
                continue

            close = df["Close"]

            sma20 = close.rolling(20).mean()
            sma50 = close.rolling(50).mean()

            # ambil angka terakhir sebagai FLOAT
            last_close = float(close.iloc[-1])
            last_sma20 = float(sma20.iloc[-1])
            last_sma50 = float(sma50.iloc[-1])

            # jika ada NaN
            if np.isnan(last_sma20) or np.isnan(last_sma50):
                trend = "Data belum cukup"
                confidence = "Rendah"

            else:
                if last_close > last_sma20 and last_sma20 > last_sma50:
                    trend = "Naik (Uptrend)"
                    confidence = "Tinggi"
                elif last_close < last_sma20 and last_sma20 < last_sma50:
                    trend = "Turun (Downtrend)"
                    confidence = "Tinggi"
                else:
                    trend = "Sideways"
                    confidence = "Sedang"

            results[name] = {
                "trend": trend,
                "confidence": confidence
            }

        except Exception as e:
            results[name] = {
                "trend": "Error ambil data",
                "confidence": "Rendah"
            }

    return results
