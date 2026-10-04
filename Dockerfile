FROM python:3.12

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY configs ./configs
COPY data ./data

ENV AEGIS_HOME=/app
EXPOSE 8000
CMD ["aegis", "serve"]
