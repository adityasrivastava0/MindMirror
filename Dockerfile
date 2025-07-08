# Use official Python image
FROM python:3.10-slim

# Install system dependencies for wkhtmltopdf
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    wkhtmltopdf \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    libjpeg-dev \
    libpng-dev && \
    apt-get clean

# Set working directory inside container
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for wkhtmltopdf path
ENV WKHTMLTOPDF_PATH=/usr/bin/wkhtmltopdf

# Expose port
EXPOSE 5000

# Run the Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
