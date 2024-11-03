from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from functions.banco_mundial_functions import extract, load, transform

default_args = {"owner": "rolo", "retries": 5, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="banco_mundial_indicators_v02",
    default_args=default_args,
    start_date=datetime(2024, 10, 30),
    schedule_interval="0 0 * * *",
) as dag:

    functions_dictionary = {"extract": extract, "transform": transform, "load": load}

    tasks = []

    for task_id, function in functions_dictionary.items():
        banco_mundial_task = PythonOperator(task_id=task_id, python_callable=function)
        tasks.append(banco_mundial_task)

    for i in range(len(tasks) - 1):
        tasks[i] >> tasks[i + 1]

    # tasks
