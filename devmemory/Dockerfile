FROM python:3.13-slim
ARG BUILD_ARCH
ARG BUILD_VERSION=0.3.0
LABEL io.hass.name="DevMemory" io.hass.description="Local-first development memory" io.hass.type="app" io.hass.version="$BUILD_VERSION" io.hass.arch="$BUILD_ARCH"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DEVMEMORY_DATA=/data DEVMEMORY_HOST=0.0.0.0 DEVMEMORY_MODE=ingress
WORKDIR /app
COPY server.py github_sync.py index.html app.js style.css ./
EXPOSE 8099
CMD ["python", "server.py"]
