# Use Python base image
FROM python:3.10-slim
 
# Set the working directory inside the container
WORKDIR /app
 
# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy the entire backend folder into the container
COPY ./backend /app/backend
 
# Copy .env file to ensure environment variables are loaded
COPY .env /app/.env
 
# Set PYTHONPATH so Python can find the backend module
ENV PYTHONPATH=/app
 
# Expose port 8080 for FastAPI
EXPOSE 8080
 
# Start FastAPI with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]