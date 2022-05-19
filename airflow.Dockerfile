FROM apache/airflow:2.2.2

RUN pip install dbt-postgres==1.1.0
RUN pip install airflow-provider-great-expectations>=0.1.0
RUN pip install great_expectations==0.15.5