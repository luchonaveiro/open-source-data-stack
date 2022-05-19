from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.dates import datetime, timedelta
from dbt_dag_parser_v2 import DbtDagParser

DAG_ID = 'model_level_dbt_dag'
DAG_OWNER = 'luciano.naveiro'

DBT_PROJECT_PATH = '/opt/dbt/jaffle_shop'
DBT_GLOBAL_CLI_FLAGS = "--no-write-json"
DBT_TARGET = "dev"

default_args = {
    "owner": DAG_OWNER,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}


with DAG(
    DAG_ID,
    start_date=datetime(2021, 12, 23),
    description="A dbt wrapper for Airflow using a utility class to map the dbt DAG to Airflow tasks",
    schedule_interval=timedelta(days=1),
    default_args=default_args,
    catchup=False,
) as dag:

    # Define DummyOperator
    start_dummy = DummyOperator(task_id="start")
    end_dummy = DummyOperator(task_id="end")
    start_run_dbt_dummy = DummyOperator(task_id="start_run_dbt")
    start_test_dbt_dummy = DummyOperator(task_id="start_test_dbt")

    # Validate taskgroups
    validate_taskgroup = TaskGroup('dbt_validate')
    # dbt_debug = BashOperator(
    #     task_id='dbt_debug',
    #     task_group=validate_taskgroup,
    #     bash_command=f"""
    #     dbt debug --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
    #     """)

    dbt_parse = BashOperator(
        task_id='dbt_parse',
        task_group=validate_taskgroup,
        bash_command=f"""
        dbt parse --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """)

    dbt_compile = BashOperator(
        task_id='dbt_compile',
        task_group=validate_taskgroup,
        bash_command=f"""
        dbt compile --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """)

    start_dummy >> dbt_parse >> dbt_compile >> start_run_dbt_dummy

    # The parser parses out a dbt manifest.json file and dynamically creates tasks for "dbt run" and "dbt test"
    # commands for each individual model. It groups them into task groups which we can retrieve and use in the DAG.
    dag_parser = DbtDagParser(
        dbt_global_cli_flags=DBT_GLOBAL_CLI_FLAGS,
        dbt_project_dir=DBT_PROJECT_PATH,
        dbt_profiles_dir=DBT_PROJECT_PATH,
        dbt_target=DBT_TARGET,
    )
    dbt_run_group = dag_parser.get_dbt_run_group()
    dbt_test_group = dag_parser.get_dbt_test_group()

    start_run_dbt_dummy >> dbt_run_group >> start_test_dbt_dummy >> dbt_test_group 

    dbt_docs = BashOperator(
        task_id='dbt_docs',
        bash_command=f"""
        dbt docs generate --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """)

    dbt_test_group >> dbt_docs >> end_dummy


