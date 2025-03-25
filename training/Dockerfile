# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY training/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY training .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the training script
CMD ["python", "training_pipeline.py"]