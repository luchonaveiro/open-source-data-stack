from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.dates import datetime, timedelta
from dbt_dag_parser_v2 import DbtDagParser
from great_expectations_provider.operators.great_expectations import (
    GreatExpectationsOperator,
)

DAG_ID = "model_level_dbt_great_expectations_dag"
DAG_OWNER = "luciano.naveiro"

DBT_PROJECT_PATH = "/opt/dbt/jaffle_shop"
DBT_GLOBAL_CLI_FLAGS = "--no-write-json"
DBT_TARGET = "dev"

GREAT_EXPECTATIONS_PATH = "/opt/great_expectations"
GREAT_EXPECTATIONS_SOURCE_CHECKPOINTS = [
    "sources.jaffle_shop__customers",
    "sources.jaffle_shop__orders",
    "sources.stripe__payment",
]
GREAT_EXPECTATIONS_TARGET_CHECKPOINTS = [
    "targets.dev__fct_customer_orders",
]

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
    concurrency=4,
    max_active_tasks=4,
) as dag:

    # Define DummyOperator
    start_dummy = DummyOperator(task_id="start")
    end_dummy = DummyOperator(task_id="end")
    start_run_dbt_dummy = DummyOperator(task_id="start_run_dbt")
    start_test_dbt_dummy = DummyOperator(task_id="start_test_dbt")
    start_ge_sources_dummy = DummyOperator(task_id="start_ge_sources")
    finish_ge_sources_dummy = DummyOperator(task_id="finish_ge_sources")
    start_ge_targets_dummy = DummyOperator(task_id="start_ge_targets")
    finish_ge_targets_dummy = DummyOperator(task_id="finish_ge_targets")

    # Great Expectations Source Tables
    ge_sources_taskgroup = TaskGroup("great_expectations_sources")
    ge_sources_tasks = []
    for checkpoint in GREAT_EXPECTATIONS_SOURCE_CHECKPOINTS:
        ge_source_validation = GreatExpectationsOperator(
            task_id=checkpoint,
            task_group=ge_sources_taskgroup,
            data_context_root_dir=GREAT_EXPECTATIONS_PATH,
            checkpoint_name=checkpoint,
        )
        ge_sources_tasks.append(ge_source_validation)

    start_dummy >> start_ge_sources_dummy >> ge_sources_tasks >> finish_ge_sources_dummy

    # dbt Validate taskgroups
    validate_taskgroup = TaskGroup("dbt_validate")
    dbt_debug = BashOperator(
        task_id="dbt_debug",
        task_group=validate_taskgroup,
        bash_command=f"""
        dbt debug --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """,
    )

    dbt_parse = BashOperator(
        task_id="dbt_parse",
        task_group=validate_taskgroup,
        bash_command=f"""
        dbt parse --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """,
    )

    dbt_compile = BashOperator(
        task_id="dbt_compile",
        task_group=validate_taskgroup,
        bash_command=f"""
        dbt compile --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """,
    )

    (
        finish_ge_sources_dummy
        >> dbt_debug
        >> dbt_parse
        >> dbt_compile
        >> start_run_dbt_dummy
    )

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

    # Great Expectations Target Tables
    ge_targets_taskgroup = TaskGroup("great_expectations_targets")
    ge_targets_tasks = []
    for checkpoint in GREAT_EXPECTATIONS_TARGET_CHECKPOINTS:
        ge_target_validation = GreatExpectationsOperator(
            task_id=checkpoint,
            task_group=ge_targets_taskgroup,
            data_context_root_dir=GREAT_EXPECTATIONS_PATH,
            checkpoint_name=checkpoint,
        )
        ge_targets_tasks.append(ge_target_validation)

    (
        dbt_test_group
        >> start_ge_targets_dummy
        >> ge_targets_tasks
        >> finish_ge_targets_dummy
    )

    dbt_docs = BashOperator(
        task_id="dbt_docs",
        bash_command=f"""
        dbt docs generate --profiles-dir {DBT_PROJECT_PATH} --project-dir {DBT_PROJECT_PATH}
        """,
    )

    finish_ge_targets_dummy >> dbt_docs >> end_dummy
