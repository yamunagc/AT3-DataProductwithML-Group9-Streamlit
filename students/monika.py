import os
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, time, date, timezone

# 🔗 FastAPI endpoint (GET)
API_URL = os.getenv("ETH_API_URL", "https://nextdaycrypto-app.onrender.com/predict/ethereum")

# 🔑 Coindesk Data API (same as Tung’s structure)
API_KEY = os.getenv(
    "COINDESK_API_KEY",
    "0ca81b617a4bec78667e6b6608ca433e7401719954d66f3415d4d82670272aa6"
)

class ETHDashboard:
    def __init__(self, user_name: str = "ETH"):
        self.user = user_name

    # -----------------------------
    # 📊 Fetch Historical Data (Coindesk)
    # -----------------------------
    def fetch_eth(self, limit: int, to_ts: int):
        """Fetch daily OHLC + Volume data for ETH-USD."""
        url = (
            "https://data-api.coindesk.com/index/cc/v1/historical/days"
            f"?market=cadli"
            f"&instrument=ETH-USD"
            f"&limit={limit}"
            f"&to_ts={to_ts}"
            "&fill=true&apply_mapping=true&response_format=JSON&groups=OHLC,VOLUME"
        )
        headers = {"X-CoinAPI-Key": API_KEY}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get("Data", [])

    # -----------------------------
    # 📈 Draw Candlestick Chart
    # -----------------------------
    def draw_chart(self, df, title="ETH-USD Candlestick Chart", predict_point=None):
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df["TIMESTAMP"],
                    open=df["OPEN"], high=df["HIGH"],
                    low=df["LOW"], close=df["CLOSE"],
                    name="ETH Actual"
                )
            ]
        )

        # Add the predicted point if provided
        if predict_point:
            fig.add_trace(go.Scatter(
                x=[predict_point["date"]],
                y=[predict_point["value"]],
                mode="markers+text",
                text=["Predicted Next-Day HIGH"],
                textposition="top center",
                marker=dict(size=13, color="red", symbol="circle"),
                name="Prediction"
            ))

        fig.update_layout(
            title=title,
            title_x=0.5,
            yaxis_title="Price (USD)",
            xaxis_rangeslider_visible=False,
            height=550
        )
        fig.update_xaxes(tickformat="%Y-%m-%d")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # 📊 Historical Chart Mode
    # -----------------------------
    def mode_chart(self):
        st.subheader("📈 Ethereum Historical Data")

        start_date = st.date_input("Start Date", value=date(2025, 8, 26))
        end_date = st.date_input("End Date", value=date(2025, 10, 28))

        if st.button("📊 Load Historical Chart"):
            n_days = (end_date - start_date).days + 1
            if n_days <= 0:
                st.error("End date must be after start date.")
                return

            end_dt_utc = datetime.combine(end_date, time(0, 0), tzinfo=timezone.utc)
            to_ts = int(end_dt_utc.timestamp())

            data = self.fetch_eth(limit=n_days, to_ts=to_ts)
            df = pd.DataFrame(data or [])
            if df.empty:
                st.warning("No data returned for the selected range.")
                return

            df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], unit="s", utc=True)
            self.draw_chart(df)

    # -----------------------------
    # 🤖 Prediction Mode
    # -----------------------------
    
    def mode_predict(self):
        st.subheader("🤖 Predict Ethereum Next-Day HIGH")

        if st.button("🚀 Predict using Live API (GET /predict/ethereum)"):
            try:
                # GET from your FastAPI (server fetches features for last completed UTC day D; predicts D+1)
                res = requests.get(API_URL, timeout=30)
                res.raise_for_status()
                out = res.json()

            # --- read values from API (robust to either key name) ---
                predicted = out.get("predicted_next_day_high", out.get("predicted_high_next_day"))
                if predicted is None:
                    raise KeyError("predicted_next_day_high")

                predicted = float(predicted)
                features_used = out.get("features_used", {})
                pred_day = out.get("prediction_for_day_utc")  # e.g., "2025-11-04"

            # show features
                # st.json(features_used)
                if pred_day:
                    st.success(f"✅ Predicted Next-Day HIGH for {pred_day}: **${predicted:,.2f} USD**")
                else:
                    st.success(f"✅ Predicted Next-Day HIGH: **${predicted:,.2f} USD**")

            # Pull recent history and plot with prediction marker on the API's prediction day
                now_ts = int(datetime.now(timezone.utc).timestamp())
                data = self.fetch_eth(limit=60, to_ts=now_ts)
                df = pd.DataFrame(data)
                if df.empty:
                    st.warning("No historical data to plot.")
                    return

                df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], unit="s", utc=True)

            # Use the API's prediction date if provided; otherwise fall back to last + 1 day
                if pred_day:
                    pred_day_ts = pd.Timestamp(pred_day).tz_localize("UTC")
                else:
                    pred_day_ts = df["TIMESTAMP"].max() + pd.Timedelta(days=1)

                self.draw_chart(
                    df,
                    title="ETH Prediction vs History",
                    predict_point={"date": pred_day_ts, "value": predicted}
                )

                st.caption("Prediction date is UTC from your FastAPI (D+1).")

            except requests.exceptions.RequestException as e:
                st.error(f"❌ API call failed: {e}")
            except KeyError as e:
                st.error(f"⚠️ Missing key in API response: {e}")
            except Exception as e:
                st.error(f"⚠️ Error during prediction: {e}")

    # -----------------------------
    # 🏃‍♀️ Run UI
    # -----------------------------
    def run(self):
        mode = st.radio(
            f"{self.user}, choose mode:",
            ["📈 Historical Data", "🤖 Predict Next-Day HIGH"]
        )

        if mode == "📈 Historical Data":
            self.mode_chart()
        else:
            self.mode_predict()