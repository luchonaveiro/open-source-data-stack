FROM python:3.7-slim

COPY . /app

WORKDIR /app

RUN pip install pandas==1.2.3
RUN pip install psycopg2-binary==2.9.1

CMD python3 db/scripts/create_db_insert_data.py