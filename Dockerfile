FROM mongo:7

# Install Python 3 and pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py db.py auth.py api_users.py api_applications.py utils.py ./
COPY static/ static/

# Create directories
RUN mkdir -p /app/applications /data/db

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8900

ENTRYPOINT []
CMD ["/entrypoint.sh"]
