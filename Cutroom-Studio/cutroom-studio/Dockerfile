FROM python:3.13-slim-trixie
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 CUTROOM_DATA=/var/lib/cutroom CUTROOM_MODELS=/opt/cutroom-models
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates ffmpeg libgomp1 fontconfig fonts-dejavu-core fonts-liberation fonts-noto-core fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
RUN groupadd -g 10001 cutroom && useradd -u 10001 -g cutroom -m cutroom && mkdir -p /var/lib/cutroom /opt/cutroom-models && chown cutroom:cutroom /var/lib/cutroom /opt/cutroom-models
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY cutroom cutroom
COPY scripts scripts
COPY web web
COPY samples samples
USER cutroom
RUN python -m scripts.bootstrap_models
EXPOSE 3000
CMD ["python","-m","uvicorn","cutroom.api:app","--host","0.0.0.0","--port","3000","--proxy-headers"]
