FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir . \
    && useradd --no-create-home --shell /bin/false appuser
COPY app/ app/
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["teams-mcp"]
