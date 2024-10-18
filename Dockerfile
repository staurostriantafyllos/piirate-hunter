FROM python:3.11

WORKDIR /app

COPY requirements.txt .

# Install Tesseract and necessary dependencies
RUN apt-get update
RUN apt-get install -y tesseract-ocr libtesseract-dev
RUN rm -rf /var/lib/apt/lists/*

RUN pip install -U pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
