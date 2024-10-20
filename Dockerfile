# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variables
ENV PORT=80
ENV GOOGLE_API_KEY=""
ENV PINECONE_API_KEY=""
ENV LANGCHAIN_API_KEY=""
ENV LANGCHAIN_TRACING_V2=""
ENV LANGCHAIN_ENDPOINT=""
ENV MONGODB_URI=""
ENV CUSTOM_TOKEN=""

# Run app.py when the container launches
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
