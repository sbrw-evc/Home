FROM python:3.12-alpine
WORKDIR /app
COPY app.py .
COPY static ./static
EXPOSE 8088
HEALTHCHECK CMD wget -qO- http://127.0.0.1:8088/health || exit 1
CMD ["python", "-u", "app.py"]
