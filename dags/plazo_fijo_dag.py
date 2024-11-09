from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from functions.plazo_fijo_functions import extract, load, transform

default_args = {"owner": "rolo", "retries": 5, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="plazo_fijo_v01",
    default_args=default_args,
    start_date=datetime(2024, 11, 7),
    schedule_interval="0 0 * * *",
) as dag:
    functions_dictionary = {
        "extract_and_land": extract,
        "transform": transform,
        "load_and_sink": load,
    }

    tasks = []

    for task_id, function in functions_dictionary.items():
        plazo_task = PythonOperator(task_id=task_id, python_callable=function)
        tasks.append(plazo_task)

    for i in range(len(tasks) - 1):
        tasks[i] >> tasks[i + 1]
