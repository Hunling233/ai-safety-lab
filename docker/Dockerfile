# Use Python 3.9 as base image
FROM python:3.9

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the entire project
COPY . .

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start both FastAPI server and Streamlit app
CMD echo "Starting AI Safety Lab..." && \
    python server/api.py &> /logs/server.log & \
    streamlit run ui/app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true &> /logs/streamlit.log & \
    wait
