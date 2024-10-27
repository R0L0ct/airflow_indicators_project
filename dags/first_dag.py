from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from pyspark.sql import SparkSession


def create_spark_session():
    return (
        SparkSession.builder.appName("indices_argentina")
        .config("spark.jars", "/opt/airflow/data/postgres/postgresql-42.7.4.jar")
        .getOrCreate()
    )


default_args = {"owner": "rolo", "retries": 5, "retry_delay": timedelta(minutes=2)}


# extract + landing
def extract_and_land():

    spark = None

    try:

        spark = create_spark_session()

        data_inflacion_mensual = requests.get(
            "https://api.argentinadatos.com/v1/finanzas/indices/inflacion/"
        )
        data_inflacion_anual = requests.get(
            "https://api.argentinadatos.com/v1/finanzas/indices/inflacionInteranual/"
        )
        data_inflacion_mensual.raise_for_status()
        data_inflacion_anual.raise_for_status()

        data_mensual = data_inflacion_mensual.json()
        data_anual = data_inflacion_anual.json()

        data_mensual = [
            {"fecha": item["fecha"], "valor": float(item["valor"])}
            for item in data_mensual
        ]
        data_anual = [
            {"fecha": item["fecha"], "valor": float(item["valor"])}
            for item in data_anual
        ]

        df_m = spark.createDataFrame(data_mensual)
        df_a = spark.createDataFrame(data_anual)

        # df_m.printSchema()
        # df_a.printSchema()

        df_m.write.csv(
            "/opt/airflow/data/indice_mensual.csv",
            header=True,
            mode="overwrite",
        )

        df_a.write.csv(
            "/opt/airflow/data/indice_anual.csv",
            header=True,
            mode="overwrite",
        )

    except Exception as e:

        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()


def transform():

    spark = None

    try:

        spark = create_spark_session()

        df_mensual = spark.read.csv(
            "/opt/airflow/data/indice_mensual.csv", header=True
        ).withColumnRenamed("valor", "valor_mensual")

        df_anual = spark.read.csv(
            "/opt/airflow/data/indice_anual.csv", header=True
        ).withColumnRenamed("valor", "valor_anual")

        df_joined = df_mensual.join(df_anual, on="fecha", how="inner")

        df_sorted = df_joined.orderBy("fecha", ascending=False)

        df_sorted.show()

        df_sorted.write.csv(
            "/opt/airflow/data/indice_joined.csv",
            header=True,
            mode="overwrite",
        )

    except Exception as e:

        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()


def load_and_sink():

    spark = None

    try:

        spark = create_spark_session()

        df_transformed = spark.read.csv(
            "/opt/airflow/data/indice_joined.csv", header=True
        )

        url = "jdbc:postgresql://postgres:5432/indices_argentina"

        properties = {
            "user": "airflow",
            "password": "airflow",
            "driver": "org.postgresql.Driver",
        }

        df_transformed.write.jdbc(url, "indices", mode="overwrite", properties=properties)

    except Exception as e:

        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()


with DAG(
    dag_id="indices_argentina_v04",
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


