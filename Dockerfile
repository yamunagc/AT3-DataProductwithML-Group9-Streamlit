FROM python:3.11.4

# Create working directory
WORKDIR /app

# Copy dependency files first for build caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Streamlit configuration for Render
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=$PORT

EXPOSE $PORT

CMD ["sh", "-c", "streamlit run app/main.py --server.port=$PORT --server.address=0.0.0.0"]