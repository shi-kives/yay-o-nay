FROM python:3.11

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

# Run your app (adjust this)
#CMD ["python", "main.py"]