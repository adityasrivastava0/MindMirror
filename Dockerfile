# Use official Python image
FROM python:3.10-slim

# Install system dependencies for wkhtmltopdf
RUN apt-get update && \
    apt-get install -y \
    wkhtmltopdf \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    libjpeg-dev \
    libpng-dev && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy everything
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 5000

# Start the Flask app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
