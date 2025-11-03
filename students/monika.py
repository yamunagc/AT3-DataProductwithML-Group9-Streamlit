import os
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, time, date, timezone

# -------------------------------------------------------
# 🔗 API Configuration
# -------------------------------------------------------
API_URL = os.getenv("ETH_API_URL", "https://nextdaycrypto-app.onrender.com/predict/ethereum")

API_KEY = os.getenv(
    "COINDESK_API_KEY",
    "0ca81b617a4bec78667e6b6608ca433e7401719954d66f3415d4d82670272aa6"
)

# -------------------------------------------------------
# 🧠 Ethereum Dashboard
# -------------------------------------------------------
class ETHDashboard:
    def __init__(self, user_name: str = "ETH"):
        self.user = user_name

    # -----------------------------
    # 📊 Fetch Historical Data
    # -----------------------------
    def fetch_eth(self, limit: int, to_ts: int):
        """Fetch daily OHLC + Volume data for ETH-USD from Coindesk."""
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
    # 📈 Candlestick Chart
    # -----------------------------
    def draw_chart(self, df, title="ETH-USD Candlestick Chart", predict_point=None):
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df["TIMESTAMP"],
                    open=df["OPEN"], high=df["HIGH"],
                    low=df["LOW"], close=df["CLOSE"],
                    name="Actual ETH Prices"
                )
            ]
        )

        # Predicted marker (next-day high)
        if predict_point:
            fig.add_trace(go.Scatter(
                x=[predict_point["date"]],
                y=[predict_point["value"]],
                mode="markers+text",
                text=["Predicted Next-Day High"],
                textposition="top center",
                marker=dict(size=14, color="#FF4B4B", symbol="diamond"),
                name="Predicted High"
            ))

        fig.update_layout(
            title=title,
            title_x=0.5,
            yaxis_title="Price (USD)",
            xaxis_rangeslider_visible=False,
            height=550,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig.update_xaxes(tickformat="%Y-%m-%d")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # 📈 Historical Chart Mode
    # -----------------------------
    def mode_chart(self):
        st.subheader("📊 Ethereum Historical Prices")
        st.markdown("View historical **Open-High-Low-Close (OHLC)** data for Ethereum from Coindesk.")

        start_date = st.date_input("Select Start Date", value=date(2025, 8, 26))
        end_date = st.date_input("Select End Date", value=date(2025, 10, 28))

        if st.button("📈 Load Historical Chart"):
            n_days = (end_date - start_date).days + 1
            if n_days <= 0:
                st.error("⚠️ End date must be after start date.")
                return

            end_dt_utc = datetime.combine(end_date, time(0, 0), tzinfo=timezone.utc)
            to_ts = int(end_dt_utc.timestamp())

            data = self.fetch_eth(limit=n_days, to_ts=to_ts)
            df = pd.DataFrame(data or [])
            if df.empty:
                st.warning("No data returned for this date range.")
                return

            df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], unit="s", utc=True)
            self.draw_chart(df)

    # -----------------------------
    # 🤖 Prediction Mode
    # -----------------------------
    def mode_predict(self):
        st.subheader("🤖 Ethereum Next-Day Price Prediction")
        st.markdown("""
        The model predicts **tomorrow’s expected HIGH price** for Ethereum (ETH-USD).  
        It uses hourly data from Kraken, feature engineering, and a trained Ridge Regression model.
        """)

        if st.button("🚀 Run Live Prediction (GET /predict/ethereum)"):
            try:
                res = requests.get(API_URL, timeout=30)
                res.raise_for_status()
                out = res.json()

                predicted = out.get("predicted_next_day_high")
                pred_day = out.get("prediction_for_day_utc")

                if predicted is None:
                    raise KeyError("predicted_next_day_high")

                predicted = float(predicted)

                # ✅ Display prediction in an info box
                st.markdown(
                    f"""
                    <div style='padding:18px; background-color:#1E1E1E; border-radius:10px;'>
                        <h3 style='color:#FFD700; text-align:center;'>💹 Predicted High for {pred_day}</h3>
                        <h2 style='color:#00FFB3; text-align:center;'>${predicted:,.2f} USD</h2>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # 🕒 Fetch historical data for context
                now_ts = int(datetime.now(timezone.utc).timestamp())
                data = self.fetch_eth(limit=60, to_ts=now_ts)
                df = pd.DataFrame(data)
                if df.empty:
                    st.warning("No historical data available to plot.")
                    return

                df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], unit="s", utc=True)
                pred_day_ts = pd.Timestamp(pred_day).tz_localize("UTC")

                # Plot chart with prediction
                self.draw_chart(
                    df,
                    title=f"ETH-USD Price Trend & Next-Day Prediction ({pred_day})",
                    predict_point={"date": pred_day_ts, "value": predicted}
                )

                st.caption("All times and prices shown are in UTC. Data source: Kraken & Coindesk APIs.")

            except requests.exceptions.RequestException as e:
                st.error(f"❌ API connection failed: {e}")
            except KeyError as e:
                st.error(f"⚠️ Missing expected key in API response: {e}")
            except Exception as e:
                st.error(f"⚠️ Unexpected error: {e}")

    # -----------------------------
    # 🏃‍♀️ Run Streamlit App
    # -----------------------------
    def run(self):
        st.set_page_config(page_title="Ethereum Next-Day Predictor", layout="wide")
        st.title("💰 Ethereum (ETH-USD) Dashboard")
        st.markdown("Monitor historical trends and predict tomorrow’s price movement.")

        mode = st.radio(
            f"{self.user}, choose a mode:",
            ["📈 Historical Data", "🤖 Predict Next-Day HIGH"],
            horizontal=True
        )

        if mode == "📈 Historical Data":
            self.mode_chart()
        else:
            self.mode_predict()


# -------------------------------------------------------
# 🧭 Entry point
# -------------------------------------------------------
if __name__ == "__main__":
    dashboard = ETHDashboard()
    dashboard.run()
