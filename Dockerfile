FROM python:slim
COPY . /app
WORKDIR /app
RUN apt-get update && apt-get install -y cron chromium chromium-driver \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt 
ENV DOCKER=1
CMD ["sh", "docker.sh"]