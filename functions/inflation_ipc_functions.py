import os

import requests
from dotenv import load_dotenv
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import avg, col, lag, regexp_replace, round
from pyspark.sql.functions import sum as spark_sum

load_dotenv()
POSTGRES_JAR = os.getenv("POSTGRES_JAR")
USER_POSTGRES = os.getenv("USER_POSTGRES")
PASSWORD_POSTGRES = os.getenv("PASSWORD_POSTGRES")
URL_POSTGRES = os.getenv("URL_POSTGRES")
IPC_PATH = os.getenv("IPC_PATH")


def create_spark_session():
    return (
        SparkSession.builder.appName("ipc_inflation")
        .config("spark.jars", POSTGRES_JAR)
        .getOrCreate()
    )


def extract():

    spark = None

    try:

        spark = create_spark_session()

        url = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_aperturas.csv"

        response = requests.get(url)

        if response.status_code == 200:

            directory = IPC_PATH

            if directory is None:
                raise ValueError("IPC_PATH is not defined")

            file_name = "serie_ipc_aperturas.csv"

            os.makedirs(directory, exist_ok=True)

            full_path = os.path.join(directory, file_name)

            with open(full_path, "wb") as file:
                file.write(response.content)
            print("CSV successfully downloaded")

            return full_path

        else:

            print("Error downloading the CSV file")

    except Exception as e:

        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()


def transform(**kwargs):

    spark = None

    try:

        spark = create_spark_session()

        ti = kwargs["ti"]

        full_path = ti.xcom_pull(task_ids="extract_and_land")

        if os.path.isfile(full_path):

            df = spark.read.csv(full_path, header=True, sep=";")

            df = df.select("Periodo", "Indice_IPC", "v_m_IPC", "v_i_a_IPC")

            df = (
                df.withColumn(
                    "Indice_IPC",
                    regexp_replace(col("Indice_IPC"), ",", ".").cast("float"),
                )
                .withColumn(
                    "v_m_IPC", regexp_replace(col("v_m_IPC"), ",", ".").cast("float")
                )
                .withColumn(
                    "v_i_a_IPC",
                    regexp_replace(col("v_i_a_IPC"), ",", ".").cast("float"),
                )
            )

            df = df.groupBy("Periodo").agg(
                spark_sum("Indice_IPC").alias("indice_ipc"),
                round(avg("v_m_IPC"), 2).alias("avg_ipc_mensual"),
                round(avg("v_i_a_IPC"), 2).alias("avg_ipc_interanual"),
            )

            ## Window es un módulo que se utiliza para crear objetos de ventana que definen el contexto para las funciones de ventana.
            ## Este módulo permite especificar cómo se deben agrupar y ordenar las filas en un DataFrame.
            ## En otras palabras, genera un contexto o referencia para realizar cálculos en un conjunto específico de filas relacionadas.
            df = df.withColumn(
                "ipc_anterior", lag("indice_ipc").over(Window.orderBy("Periodo"))
            ).withColumn(
                "variacion_mensual",
                round(
                    ((col("indice_ipc") - col("ipc_anterior")) / col("ipc_anterior"))
                    * 100,
                    2,
                ),
            )

            df = df.filter(col("variacion_mensual").isNotNull())

            df = df.select(
                "Periodo", "avg_ipc_mensual", "variacion_mensual", "avg_ipc_interanual"
            ).orderBy("Periodo", ascending=False)

            df.show()

            if IPC_PATH is None:
                raise ValueError("IPC_PATH is not defined")

            df.write.csv(
                os.path.join(IPC_PATH, "promedio_ipc_mensual.csv"),
                header=True,
                mode="overwrite",
            )
        else:
            print(f"{full_path} file not found")

    except Exception as e:

        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()


def load():
    spark = None

    try:

        spark = create_spark_session()

        url = URL_POSTGRES

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver",
        }

        if IPC_PATH is None:
            raise ValueError("IPC_PATH is not defined")

        full_path = os.path.join(IPC_PATH, "promedio_ipc_mensual.csv")

        if os.path.isdir(full_path):

            df = spark.read.csv(full_path, header=True)

            df.write.jdbc(
                url, "promedio_ipc_mensual", mode="overwrite", properties=properties
            )

        else:

            print("promedio_ipc_mensual file not found")

    except Exception as e:

        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()
