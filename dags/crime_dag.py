from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from functions.crime_data_functions import extract, transform, load

default_args = {"owner": "rolo", "retries": 5, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="crime_data_v02",
    default_args=default_args,
    start_date=datetime(2024, 11, 4),
    schedule_interval="0 0 * * *",
) as dag:
    function_dictionary = {
        'extract_and_land': extract,
        'transform': transform,
        'load_and_sink': load
    }

    tasks = []

    for task_id, function in function_dictionary.items():
        crime_task = PythonOperator(
            task_id = task_id,
            python_callable = function
        )
        tasks.append(crime_task)

    for i in range(len(tasks) - 1):
        tasks[i] >> tasks[i + 1]

    # tasks
