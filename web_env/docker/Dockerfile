ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir --no-deps -e .
USER 65532:65532
ENTRYPOINT ["provtrust"]
CMD ["serve", "--host", "127.0.0.1", "--port", "18080"]
