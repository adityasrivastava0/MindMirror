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
    libfreetype6 \
    libjpeg-dev \
    libpng-dev && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for Flask
EXPOSE 5000

# Run the app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
