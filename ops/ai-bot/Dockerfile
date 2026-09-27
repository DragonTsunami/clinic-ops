FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv/bot
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
EXPOSE 9500
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9500/health', timeout=3).status==200 else 1)"]
CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "9500"]
