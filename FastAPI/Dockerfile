FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the application code and model files
COPY *.py /app/
COPY *.pkl /app/
COPY static/ /app/static/

# Expose the port
EXPOSE 8888

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]