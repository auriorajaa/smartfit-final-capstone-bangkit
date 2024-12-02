# Gunakan official Python image sebagai base
FROM python:3.9-slim

# Set working directory di dalam container
WORKDIR /usr/src/app

# Salin semua file ke dalam container
COPY . .

# Install dependencies yang diperlukan
RUN python -m pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port yang akan digunakan oleh aplikasi (App Engine membutuhkan port 8080)
EXPOSE 8080

# Jalankan aplikasi menggunakan gunicorn (bukan flask run)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
