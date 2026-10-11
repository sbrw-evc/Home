FROM python:3.12-alpine
ARG VERSION=dev
ENV APP_VERSION=$VERSION
LABEL org.opencontainers.image.title="home" \
      org.opencontainers.image.description="Стартовая страница с сайтами из Nginx Proxy Manager" \
      org.opencontainers.image.source="https://github.com/sbrw-evc/Home" \
      org.opencontainers.image.version=$VERSION
WORKDIR /app
COPY app.py .
COPY static ./static
EXPOSE 8088
HEALTHCHECK CMD wget -qO- http://127.0.0.1:8088/health || exit 1
CMD ["python", "-u", "app.py"]
