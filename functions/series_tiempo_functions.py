import os
import zipfile

import requests
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

load_dotenv()
POSTGRES_JAR = os.getenv("POSTGRES_JAR")
USER_POSTGRES = os.getenv("USER_POSTGRES")
URL_POSTGRES = os.getenv("URL_POSTGRES")
PASSWORD_POSTGRES = os.getenv("PASSWORD_POSTGRES")
SERIES_TIEMPO_PATH = "/opt/airflow/data/series_tiempo"


def create_spark_session():
    return (
        SparkSession.builder.appName("series_tiempo")
        .config("spark.jars", POSTGRES_JAR)
        .getOrCreate()
    )


def extract():

    try:
        url = "https://apis.datos.gob.ar/series/api/dump/series-tiempo-csv.zip"

        if SERIES_TIEMPO_PATH is None:
            raise ValueError("SERIES_TIEMPO_PATH not found")

        os.makedirs(SERIES_TIEMPO_PATH, exist_ok=True)

        response = requests.get(url)

        zip_path = os.path.join(SERIES_TIEMPO_PATH, "series_tiempo.zip")

        data_path = ""

        if response.status_code == 200:

            with open(zip_path, "wb") as file:
                file.write(response.content)

            with zipfile.ZipFile(zip_path, "r") as zip:
                zip.extractall(SERIES_TIEMPO_PATH)
                for file_name in zip.namelist():
                    original_file_path = os.path.join(SERIES_TIEMPO_PATH, file_name)
                    new_file_path = os.path.join(
                        SERIES_TIEMPO_PATH, "series_tiempo.csv"
                    )
                    os.rename(original_file_path, new_file_path)
                    data_path = new_file_path

            os.remove(zip_path)

            return data_path

    except Exception as e:
        print(f"Error: {e}")


def transform(**kwargs):
    spark = None

    ti = kwargs["ti"]
    data_path = ti.xcom_pull(task_ids="extract_and_land")

    try:
        spark = create_spark_session()

        if SERIES_TIEMPO_PATH is None:
            raise ValueError("SERIES_TIEMPO_PATH not found")

        transformed_data_path = os.path.join(
            SERIES_TIEMPO_PATH, "series_tiempo_transformed.csv"
        )

        df = spark.read.csv(data_path, header=True)

        exclude_columns = ["catalogo_id", "serie_id", "dataset_id", "distribucion_id"]

        df = df.select([col for col in df.columns if col not in exclude_columns])

        df = df.groupBy(
            "serie_titulo",
            "serie_unidades",
            "serie_descripcion",
            "distribucion_descripcion",
            "dataset_responsable",
            "dataset_titulo",
        ).agg(F.round(F.avg("valor"), 2).alias("promedio_x_serie"))

        df.show(n=100, truncate=False)

        df.write.csv(transformed_data_path, header=True, mode="overwrite")

        return transformed_data_path

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if spark:
            spark.stop()


def load(**kwargs):
    spark = None
    ti = kwargs["ti"]
    tranformed_data_path = ti.xcom_pull(task_ids="transform")

    try:
        spark = create_spark_session()

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver",
        }

        df = spark.read.csv(tranformed_data_path, header=True)

        df.write.jdbc(
            URL_POSTGRES, "series_tiempo", mode="overwrite", properties=properties
        )

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if spark:
            spark.stop()


## https://series-tiempo-ar-api.readthedocs.io/es/latest/dumps/#links-de-descarga
