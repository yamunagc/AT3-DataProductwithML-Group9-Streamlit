import streamlit as st
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, timezone


class TRONDashboard:
    """TradingView-style dashboard for TRON (TRX-USD) prediction & analysis."""

    def __init__(self):
        self.API_URL = "https://at3-fast-api-4b7s.onrender.com/predict/TRON"
        self.COIN_API_URL = "https://data-api.coindesk.com/index/cc/v1/historical/days"
        self.MARKET = "cadli"
        self.SYMBOL = "TRX-USD"
        self.df = None
        self.pred_data = None
        self.pred_point = None

    # ======================================================
    # 1️⃣ DATA FETCHING
    # ======================================================
    @st.cache_data(ttl=3600)
    def fetch_data(_self):
        """Fetch TRON OHLC data from CoinDesk API."""
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)
        n_days = (end_date.date() - start_date.date()).days + 1
        to_ts = int(end_date.timestamp())

        url = (
            f"{_self.COIN_API_URL}?market={_self.MARKET}&instrument={_self.SYMBOL}"
            f"&limit={n_days}&to_ts={to_ts}"
            "&fill=true&apply_mapping=true&response_format=JSON&groups=OHLC,VOLUME"
        )

        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json().get("Data", [])
        df = pd.DataFrame(data or [])
        df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], unit="s", utc=True)
        return df

    @st.cache_data(ttl=3600)
    def fetch_prediction(_self):
        """Fetch predicted high price from FastAPI."""
        try:
            res = requests.get(_self.API_URL, timeout=300)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.ReadTimeout:
            st.error("⏱️ Render server is waking up. Please wait 3–5 minutes.")
            return None
        except Exception as e:
            st.error(f"❌ Failed to fetch prediction: {e}")
            return None

    # ======================================================
    # 2️⃣ INDICATORS
    # ======================================================
    def calc_ma(self, df, windows=[9, 20, 50]):
        for w in windows:
            df[f"MA{w}"] = df["CLOSE"].rolling(window=w).mean()
        return df

    def calc_bollinger(self, df, window=20):
        df["BB_mid"] = df["CLOSE"].rolling(window=window).mean()
        df["BB_std"] = df["CLOSE"].rolling(window=window).std()
        df["BB_upper"] = df["BB_mid"] + (2 * df["BB_std"])
        df["BB_lower"] = df["BB_mid"] - (2 * df["BB_std"])
        return df

    def calc_rsi(self, df, period=14):
        delta = df["CLOSE"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))
        return df

    def calc_macd(self, df, short=12, long=26, signal=9):
        df["EMA_short"] = df["CLOSE"].ewm(span=short, adjust=False).mean()
        df["EMA_long"] = df["CLOSE"].ewm(span=long, adjust=False).mean()
        df["MACD"] = df["EMA_short"] - df["EMA_long"]
        df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
        return df

    def compute_all_indicators(self):
        """Compute all indicators on df."""
        self.df = self.calc_ma(self.df)
        self.df = self.calc_bollinger(self.df)
        self.df = self.calc_rsi(self.df)
        self.df = self.calc_macd(self.df)

    # ======================================================
    # 3️⃣ CHART DRAWING
    # ======================================================
    def draw_chart(self, indicators=None):
        indicators = indicators or []
        df = self.df
        fig = go.Figure()

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df["TIMESTAMP"],
                open=df["OPEN"],
                high=df["HIGH"],
                low=df["LOW"],
                close=df["CLOSE"],
                name="TRX Price",
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350",
            )
        )

        # Moving Averages
        for ma in [9, 20, 50]:
            if f"MA{ma}" in indicators:
                fig.add_trace(
                    go.Scatter(
                        x=df["TIMESTAMP"],
                        y=df[f"MA{ma}"],
                        mode="lines",
                        name=f"MA{ma}",
                        line=dict(width=1.5),
                    )
                )

        # Bollinger Bands
        if "Bollinger 20" in indicators:
            fig.add_trace(
                go.Scatter(
                    x=df["TIMESTAMP"],
                    y=df["BB_upper"],
                    line=dict(width=1, color="gray"),
                    name="BB Upper",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df["TIMESTAMP"],
                    y=df["BB_lower"],
                    line=dict(width=1, color="gray"),
                    fill="tonexty",
                    fillcolor="rgba(200,200,200,0.2)",
                    name="BB Lower",
                )
            )

        if "Bollinger 50" in indicators:
            bb50_mid = df["CLOSE"].rolling(50).mean()
            bb50_std = df["CLOSE"].rolling(50).std()
            fig.add_trace(
                go.Scatter(
                    x=df["TIMESTAMP"],
                    y=bb50_mid + 2 * bb50_std,
                    line=dict(width=1, color="lightblue"),
                    name="BB50 Upper",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df["TIMESTAMP"],
                    y=bb50_mid - 2 * bb50_std,
                    line=dict(width=1, color="lightblue"),
                    fill="tonexty",
                    fillcolor="rgba(173,216,230,0.2)",
                    name="BB50 Lower",
                )
            )

        # Predicted point
        if self.pred_point:
            fig.add_trace(
                go.Scatter(
                    x=[self.pred_point["date"]],
                    y=[self.pred_point["value"]],
                    mode="markers+text",
                    text=[f"Predicted High\n({self.pred_point['value']:.5f})"],
                    textposition="top center",
                    marker=dict(size=12, color="red", symbol="circle"),
                    name="Prediction",
                )
            )

        fig.update_layout(
            title="📈 TRON (TRX-USD) Price Chart",
            title_x=0.5,
            xaxis=dict(title="Date", rangeslider_visible=False),
            yaxis=dict(title="Price (USD)", side="right"),
            height=700,
            hovermode="x unified",
            showlegend=False,  # hide legend
        )

        st.plotly_chart(fig, use_container_width=True)

    # ======================================================
    # 4️⃣ INDICATOR DISPLAY
    # ======================================================
    def display_indicators(self, selected):
        """Show selected subcharts (RSI, MACD, Volume)."""
        df = self.df.set_index("TIMESTAMP")

        if "RSI" in selected:
            st.subheader("RSI (14)")
            st.line_chart(df["RSI"])

        if "MACD" in selected:
            st.subheader("MACD (12,26,9)")
            st.line_chart(df[["MACD", "Signal"]])

        if "Volume" in selected:
            st.subheader("Volume")
            st.bar_chart(df["VOLUME"])

    # ======================================================
    # 5️⃣ MAIN RUN
    # ======================================================
    def run(self):
        st.set_page_config(page_title="TRON Prediction Dashboard", layout="wide")
        st.title("💎 TRON (TRX-USD) TradingView-style Dashboard")

        with st.spinner("📡 Fetching TRON data..."):
            self.df = self.fetch_data()

        self.compute_all_indicators()

        with st.spinner("🤖 Fetching prediction..."):
            self.pred_data = self.fetch_prediction()

        if self.pred_data:
            self.pred_point = {
                "date": pd.to_datetime(self.pred_data["predicted_for"]),
                "value": self.pred_data["predicted_high"],
            }
            st.markdown("### 🔍 Prediction Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Last Data Date", self.pred_data["last_data_date"])
            col2.metric("Predicted For", self.pred_data["predicted_for"])
            col3.metric("Predicted High (USD)", f"{self.pred_data['predicted_high']:.5f}")
        else:
            self.pred_point = None
            st.warning("⚠️ Prediction not available yet.")

        st.markdown("### 📊 Select Technical Indicators")
        selected = st.multiselect(
            "Choose indicators to display:",
            ["RSI", "MACD", "Volume", "Bollinger 20", "Bollinger 50", "MA9", "MA20", "MA50"],
            default=["MA9", "MA20", "MA50", "Bollinger 20"],
        )

        self.draw_chart(selected)
        self.display_indicators(selected)

        st.caption("⚙️ Data source: CoinDesk API | Prediction: FastAPI (Render)")


# ======================================================
# ENTRY POINT
# ======================================================
if __name__ == "__main__":
    app = TRONDashboard()
    app.run()
