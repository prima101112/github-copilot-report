FROM python:3.12.9-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY permonth.py .

EXPOSE 8501

CMD ["streamlit", "run", "permonth.py"]
