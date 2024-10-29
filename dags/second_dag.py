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
    dag_id="indices_provincias_v01",
    default_args=default_args,
    start_date=datetime(2024, 10, 27),
    schedule_interval="0 0 * * *",
) as dag:

    inflacion_parana = PythonOperator(
        task_id="inflacion_parana",
        python_callable=parana_inflation,
    )

    inflacion_santafe = PythonOperator(
        task_id="inflacion_santafe", python_callable=santafe_inflation
    )

    inflacion_cordoba = PythonOperator(
        task_id="inflacion_cordoba", python_callable=cordoba_inflation
    )
