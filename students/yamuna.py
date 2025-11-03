# students/yamuna.py
import os
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, time, date, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
FASTAPI_URL = os.getenv(
    "FASTAPI_URL",
    "https://at3-dataproductwithml-25593649-fastapi.onrender.com"
).rstrip("/")

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
COINDESK_API_KEY  = os.getenv("COINDESK_API_KEY", "").strip()

# NOTE: Your FastAPI endpoint returns fields like:
# {
#   "token": "BTC",
#   "prediction_for": "YYYY-MM-DD",
#   "predicted_next_day_high_usd": "$12,345.67",
#   "value": 12345.67,
#   "currency": "USD",
#   "last_data_date": "YYYY-MM-DD",
#   "data_source": "coingecko" | "coindesk"
# }

class BTCDashboard:
    def __init__(self, user_name: str):
        self.user = user_name

    # ---------- Data Fetchers ----------
    def _fetch_from_coingecko(self, days: int) -> pd.DataFrame:
        """
        CoinGecko OHLC (primary).
        Endpoint: /coins/bitcoin/ohlc?vs_currency=usd&days=<1|7|14|30|90|180|365|max>
        Returns: [[ts_ms, open, high, low, close], ...]
        """
        headers = {}
        if COINGECKO_API_KEY:
            headers["x-cg-pro-api-key"] = COINGECKO_API_KEY

        # CoinGecko only accepts certain day buckets.
        if days <= 1:   cg_days = 1
        elif days <= 7: cg_days = 7
        elif days <= 14: cg_days = 14
        elif days <= 30: cg_days = 30
        elif days <= 90: cg_days = 90
        elif days <= 180: cg_days = 180
        elif days <= 365: cg_days = 365
        else: cg_days = "max"

        url = f"https://api.coingecko.com/api/v3/coins/bitcoin/ohlc"
        resp = requests.get(url, params={"vs_currency": "usd", "days": cg_days}, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=["ts", "open", "high", "low", "close"])
        df["TIMESTAMP"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        # Uppercase OHLC for candlestick compatibility like your teammate’s code
        df["OPEN"] = df["open"]
        df["HIGH"] = df["high"]
        df["LOW"]  = df["low"]
        df["CLOSE"] = df["close"]
        return df[["TIMESTAMP", "OPEN", "HIGH", "LOW", "CLOSE"]].sort_values("TIMESTAMP")

    def _fetch_from_coindesk(self, limit_days: int, to_ts: int) -> pd.DataFrame:
        """
        CoinDesk Spot Historical (fallback).
        Endpoint: /spot/v1/historical/days (uses Authorization: Apikey <key>)
        """
        if not COINDESK_API_KEY:
            return pd.DataFrame()

        base = "https://data-api.coindesk.com/spot/v1/historical/days"
        params = {
            "market": "kraken",
            "instrument": "BTC-USD",
            "limit": int(limit_days),
            "to_ts": int(to_ts),
            "fill": "true",
            "apply_mapping": "true",
            "response_format": "JSON",
            "groups": "OHLC,VOLUME",
        }
        headers = {"Authorization": f"Apikey {COINDESK_API_KEY}"}
        resp = requests.get(base, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        js = resp.json()
        rows = js.get("Data", [])
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        needed = {"TIMESTAMP", "OPEN", "HIGH", "LOW", "CLOSE"}
        if not needed.issubset(df.columns):
            return pd.DataFrame()

        # TIMESTAMP is seconds since epoch
        df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], unit="s", utc=True)
        return df[["TIMESTAMP", "OPEN", "HIGH", "LOW", "CLOSE"]].sort_values("TIMESTAMP")

    def fetch_btc(self, start: date, end: date) -> pd.DataFrame:
        """
        Try CoinGecko first (simpler buckets). If empty/429/etc., fallback to CoinDesk
        using precise to_ts (end date midnight UTC).
        """
        n_days = (end - start).days + 1
        # 1) Try CoinGecko
        try:
            df = self._fetch_from_coingecko(n_days)
            if not df.empty:
                # Filter by date window (normalize to date)
                d0 = pd.Timestamp(start).tz_localize("UTC")
                d1 = pd.Timestamp(end + timedelta(days=1)).tz_localize("UTC")
                df = df[(df["TIMESTAMP"] >= d0) & (df["TIMESTAMP"] < d1)]
                if not df.empty:
                    return df
        except requests.HTTPError as e:
            # Show error but continue to fallback
            st.warning(f"CoinGecko error ({e.response.status_code if e.response else 'N/A'}). Trying CoinDesk…")

        # 2) Fallback CoinDesk with to_ts = end midnight UTC
        try:
            end_dt_utc = datetime.combine(end, time(0, 0), tzinfo=timezone.utc)
            df2 = self._fetch_from_coindesk(n_days, int(end_dt_utc.timestamp()))
            if not df2.empty:
                # Filter in case we got extra
                d0 = pd.Timestamp(start).tz_localize("UTC")
                d1 = pd.Timestamp(end + timedelta(days=1)).tz_localize("UTC")
                df2 = df2[(df2["TIMESTAMP"] >= d0) & (df2["TIMESTAMP"] < d1)]
                return df2
        except requests.HTTPError as e:
            st.error(f"CoinDesk error: {e}")

        return pd.DataFrame()

    # ---------- UI helpers ----------
    def _draw_candles(self, df: pd.DataFrame, title: str, predict_point=None):
        fig = go.Figure(
            data=[go.Candlestick(
                x=df["TIMESTAMP"],
                open=df["OPEN"], high=df["HIGH"],
                low=df["LOW"], close=df["CLOSE"],
                name="BTC Actual"
            )]
        )
        if predict_point:
            fig.add_trace(go.Scatter(
                x=[predict_point["date"]],
                y=[predict_point["value"]],
                mode="markers+text",
                text=["Predicted High"],
                textposition="top center",
                marker=dict(size=13, color="red", symbol="circle"),
                name="Prediction"
            ))
        fig.update_layout(
            title=title, title_x=0.5,
            yaxis_title="Price (USD)",
            xaxis_rangeslider_visible=False,
            height=560
        )
        fig.update_xaxes(tickformat="%Y-%m-%d")
        st.plotly_chart(fig, use_container_width=True)

    # ---------- Modes ----------
    def mode_chart(self):
        st.subheader(f"{self.user} — BTC Chart Mode")
        start_date = st.date_input("Start Date", value=date(2025, 9, 1), key=f"{self.user}_start_btc")
        end_date   = st.date_input("End Date", value=date(2025, 11, 1), key=f"{self.user}_end_btc")

        if st.button("Load Chart", key=f"{self.user}_chart_btc"):
            if end_date < start_date:
                st.error("End date must be after start date.")
                return
            df = self.fetch_btc(start_date, end_date)
            if df.empty:
                st.warning("No BTC data returned for the selected range.")
                return
            self._draw_candles(df, title="BTC-USD Candlestick")

    def mode_predict(self):
        st.subheader(f"{self.user} — Predict Next-Day HIGH (BTC)")

        if st.button("Predict", key=f"{self.user}_predict_btc"):
            # 1) Call your FastAPI
            try:
                res = requests.get(f"{FASTAPI_URL}/predict/BTC", timeout=30)
                res.raise_for_status()
                js = res.json()
            except Exception as e:
                st.error(f"FastAPI call failed: {e}")
                return

            # Numeric value robustly
            y_raw = js.get("value", js.get("raw_prediction_value"))
            try:
                predicted = float(y_raw)
            except Exception:
                st.error("Prediction response missing numeric value.")
                st.json(js)
                return

            # 2) Fetch recent history to show point on chart
            today_utc = datetime.now(timezone.utc).date()
            start_date = today_utc - timedelta(days=90)
            hist = self.fetch_btc(start_date, today_utc)
            if hist.empty:
                st.warning("Couldn’t load history to plot. Showing numeric prediction only.")
                st.success(f"Predicted next-day HIGH: **{predicted:,.2f} USD**")
                return

            next_date = hist["TIMESTAMP"].max() + pd.Timedelta(days=1)
            self._draw_candles(
                hist,
                title=f"BTC History + Next-Day HIGH Prediction (source: {js.get('data_source','n/a')})",
                predict_point={"date": next_date, "value": predicted},
            )
            st.success(
                f"**Predicted next-day HIGH** for **{js.get('prediction_for','next day')}**: "
                f"**{predicted:,.2f} USD**"
            )

    def run(self):
        mode = st.radio(
            f"{self.user}, choose mode:",
            ["Load Chart", "Predict"],
            key=f"{self.user}_mode_btc"
        )
        if mode == "Load Chart":
            self.mode_chart()
        else:
            self.mode_predict()
