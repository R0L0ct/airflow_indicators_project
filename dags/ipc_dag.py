from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from functions.inflation_ipc_functions import extract, load, transform

default_args = {"owner": "rolo", "retries": 5, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="ipc_inflation_v03",
    default_args=default_args,
    start_date=datetime(2024, 10, 28),
    schedule_interval="0 0 * * *",
) as dag:

    tasks = []

    functions_dictionary = {
        "extract_and_land": extract,
        "transform": transform,
        "load_and_sink": load,
    }

    for task_id, function in functions_dictionary.items():
        ipc_inflation = PythonOperator(task_id=task_id, python_callable=function)
        tasks.append(ipc_inflation)

    for i in range(len(tasks) - 1):
        tasks[i] >> tasks[i + 1]
