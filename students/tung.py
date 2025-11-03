import streamlit as st
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, time, date, timezone

API_URL = "https://at3-xrp-fastapi-25608516.onrender.com/predict/xrp"
API_KEY = "c62e1a5b4597376b78386f97a7f188f87d462dd7bd8c02de1561d0d4c6dab60c"

class XRPDashboard:
    def __init__(self, user_name:str = "XRP"):
        self.user = user_name
        self.chart_area = None

    def fetch_xrp(self, limit: int, to_ts: int):
        url = (
            "https://data-api.coindesk.com/index/cc/v1/historical/days"
            f"?market=cadli"
            f"&instrument=XRP-USD"
            f"&limit={limit}"
            f"&to_ts={to_ts}"
            "&fill=true&apply_mapping=true&response_format=JSON&groups=OHLC,VOLUME"
        )
        headers = {"X-CoinAPI-Key": API_KEY}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get("Data", [])

    def draw_chart(self, df, title="XRP-USD Candlestick Chart", predict_point=None):
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df["TIMESTAMP"],
                    open=df["OPEN"], high=df["HIGH"],
                    low=df["LOW"], close=df["CLOSE"],
                    name="XRP Actual"
                )
            ]
        )

        if predict_point:
            fig.add_trace(go.Scatter(
                x=[predict_point["date"]],
                y=[predict_point["value"]],
                mode="markers+text",
                name="Prediction",
                text=["Predicted High"],
                textposition="top center",
                marker=dict(size=13, color="red", symbol="circle")
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

    # 📈 CHART MODE
    def mode_chart(self):
        st.subheader(f"📈 {self.user}'s Chart Mode")

        start_date = st.date_input("Start Date", value=date(2025, 8, 26), key=f"{self.user}_start")
        end_date   = st.date_input("End Date", value=date(2025, 10, 28), key=f"{self.user}_end")

        if st.button("📊 Load Chart", key=f"{self.user}_chart_btn"):

            # days count inclusive
            n_days = (end_date - start_date).days + 1
            if n_days <= 0:
                st.error("End date must be after start date.")
                return

            # `to_ts` = end date midnight UTC
            end_dt_utc = datetime.combine(end_date, time(0, 0), tzinfo=timezone.utc)
            to_ts = int(end_dt_utc.timestamp())

            data = self.fetch_xrp(limit=n_days, to_ts=to_ts)
            df = pd.DataFrame(data or [])
            if df.empty:
                st.warning("No data returned for the selected range.")
                return

            df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], unit="s", utc=True).dt.tz_convert("UTC")
            self.draw_chart(df)

    def mode_predict(self):
        st.subheader(f"{self.user}'s Prediction Mode")

        if st.button("🚀 Predict Next High", key=f"{self.user}_predict_btn"):

            with st.spinner("Render server is waking up... It may take up to 1 minute..."):
            
                res = requests.get(API_URL).json()
                predicted = float(res["predicted_high_next_day"])

                now_ts = int(datetime.now(timezone.utc).timestamp())

                data = self.fetch_xrp(limit=90, to_ts=now_ts)
                df = pd.DataFrame(data)
                df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], unit="s")

                next_date = df["TIMESTAMP"].max() + pd.Timedelta(days=1)

                # Draw chart with predicted point
                self.draw_chart(
                    df,
                    title="XRP Prediction vs History",
                    predict_point={"date": next_date, "value": predicted}
                )

                st.success(f"✅ Predicted next-day HIGH: **{predicted:.4f} USD**")

    def run(self):
        if self.chart_area is None:
            self.chart_area = st.empty()  # container to control clearing

        mode = st.radio(
            f"{self.user}, choose mode:",
            ["📈 Load Chart", "🤖 Predict"],
            key=f"{self.user}_mode"
        )

        # ✅ Clear chart when switching mode
        self.chart_area.empty()

        if mode == "📈 Load Chart":
            self.mode_chart()
        else:
            self.mode_predict()