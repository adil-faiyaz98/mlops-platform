FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Example CMD for running the pipeline (adjust as needed)
CMD ["python", "pipelines/simple_pipeline.py", "input.csv", "output.csv"]