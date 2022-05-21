from datetime import timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.utils.dates import datetime
from airflow.utils.dates import timedelta

DAG_ID = "project_level_dbt_dag"
DAG_OWNER = "luciano.naveiro"

DBT_PROJECT_PATH = "/opt/dbt/jaffle_shop"

default_args = {
    "owner": DAG_OWNER,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}


with DAG(
    DAG_ID,
    start_date=datetime(2021, 12, 23),
    description="An Airflow DAG to invoke simple dbt commands",
    schedule_interval=timedelta(days=1),
    default_args=default_args,
    catchup=False,
) as dag:

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"""
        dbt run --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"""
        dbt test --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """,
    )

    dbt_run >> dbt_test
