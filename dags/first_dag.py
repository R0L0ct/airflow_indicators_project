from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from functions.indicators_functions import extract_and_land, transform, load_and_sink

default_args = {"owner": "rolo", "retries": 5, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="indices_argentina_v08",
    default_args=default_args,
    start_date=datetime(2024, 10, 25),
    schedule_interval="0 0 * * *",
) as dag:

    extract_task = PythonOperator(
        task_id="extract_and_land",
        python_callable=extract_and_land,
    )

    transform_task = PythonOperator(task_id="transform", python_callable=transform)

    load_task = PythonOperator(task_id="load", python_callable=load_and_sink)

    extract_task >> transform_task >> load_task
