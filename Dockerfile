# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variables
ENV PORT=80 \
    GOOGLE_API_KEY="AIzaSyCzO8pBeFspmHU0_QztnFe5cBDlD0p86w4" \
    PINECONE_API_KEY="7caa4ebc-006a-4934-964f-d8ca99b6533d" \
    LANGCHAIN_API_KEY="ls__f7a4bd725d8d4e709bd5a82a346623b6" \
    LANGCHAIN_TRACING_V2="true" \
    LANGCHAIN_ENDPOINT="https://api.smith.langchain.com" \
    MONGODB_URI="mongodb+srv://reeturaj:lgpIvrf6EMQNSbKR@reetupersonal.u7wxg.mongodb.net/" \
    CUSTOM_TOKEN="f47ac10b-58cc-4372-a567-0e02b2c3d479"     

# Run app.py when the container launches
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
