from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from functions.indicators_province_functions import (
    cordoba_inflation,
    parana_inflation,
    santafe_inflation,
)

default_args = {"owner": "rolo", "retries": 5, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="indices_provincias_v05",
    default_args=default_args,
    start_date=datetime(2024, 10, 27),
    schedule_interval="0 0 * * *",
) as dag:

    functions_dictionary = {
        "inflacion_parana": parana_inflation,
        "inflacion_santafe": santafe_inflation,
        "inflacion_cordoba": cordoba_inflation
    } 

    tasks = [] 

    for task_id, function in functions_dictionary.items():
        inflacion_provincias = PythonOperator(
            task_id=task_id,
            python_callable=function,
        )

        tasks.append(inflacion_provincias)

    # Sequential Tasks
    # for i in range(len(tasks) - 1):
    #     tasks[i] >> tasks[i + 1]

    # Parallel Tasks
    tasks

