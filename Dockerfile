FROM python:3.9.6
WORKDIR /app
RUN python3 pip install -r requirements.txt
COPY . .
CMD python -u ./main.py