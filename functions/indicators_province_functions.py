import os

import requests
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import (date_format, first, month, round, to_date,
                                   year)

load_dotenv()

INDICE_JOINED = os.getenv("INDICE_JOINED")
INDICE_PARANA = os.getenv("INDICE_PARANA")
INDICE_SANTAFE = os.getenv("INDICE_SANTAFE")
INDICE_CORDOBA = os.getenv("INDICE_CORDOBA")
POSTGRES_JAR = os.getenv("POSTGRES_JAR")
USER_POSTGRES = os.getenv("USER_POSTGRES")
PASSWORD_POSTGRES = os.getenv("PASSWORD_POSTGRES")
URL_POSTGRES = os.getenv("URL_POSTGRES")


def create_spark_session():

    if not POSTGRES_JAR:
        raise ValueError("POSTGRES_JAR not found")

    return (
        SparkSession.builder.appName("indices_argentina")
        .config("spark.jars", POSTGRES_JAR)
        .getOrCreate()
    )


def parana_inflation():
    spark = None

    try:

        spark = create_spark_session()

        data_inflacion_general = spark.read.csv(INDICE_JOINED, header=True)

        data_inflacion_parana = data_inflacion_general \
            .withColumn("fecha_inflacion", data_inflacion_general["fecha_inflacion"] ) \
            .withColumn("valor_mensual", round(data_inflacion_general["valor_mensual"] * 0.1, 2)) \
            .withColumn("valor_anual", round(data_inflacion_general["valor_anual"] * 0.1, 2)) \
            .drop("fecha_riesgo") \
            .drop("valor_riesgo")


        data_inflacion_parana = data_inflacion_parana.dropDuplicates(["fecha_inflacion"])

        data_inflacion_parana.write.csv(INDICE_PARANA, header=True, mode="overwrite")

        data_inflacion_parana.show()

        url = URL_POSTGRES

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver",
        }

        data_inflacion_parana.write.jdbc(
            url, "indices_parana", mode="overwrite", properties=properties
        )

    except Exception as e:
        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()


def santafe_inflation():

    spark = None

    try:

        spark = create_spark_session()

        data_inflacion_general = spark.read.csv(INDICE_JOINED, header=True)

        data_inflacion_santafe = data_inflacion_general \
            .withColumn("fecha_inflacion", data_inflacion_general["fecha_inflacion"] ) \
            .withColumn("valor_mensual", round(data_inflacion_general["valor_mensual"] * 0.2, 2)) \
            .withColumn("valor_anual", round(data_inflacion_general["valor_anual"] * 0.2, 2)) \
            .drop("fecha_riesgo") \
            .drop("valor_riesgo")

        data_inflacion_santafe = data_inflacion_santafe.dropDuplicates(["fecha_inflacion"])

        data_inflacion_santafe.write.csv(INDICE_SANTAFE, header=True, mode="overwrite")

        data_inflacion_santafe.show()

        url = URL_POSTGRES

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver",
        }

        data_inflacion_santafe.write.jdbc(
            url, "indices_santafe", mode="overwrite", properties=properties
        )

    except Exception as e:
        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()


def cordoba_inflation():

    spark = None

    try:

        spark = create_spark_session()

        data_inflacion_general = spark.read.csv(INDICE_JOINED, header=True, inferSchema=True)

        data_inflacion_cordoba = data_inflacion_general \
            .withColumn("fecha_inflacion", data_inflacion_general["fecha_inflacion"] ) \
            .withColumn("valor_mensual", round(data_inflacion_general["valor_mensual"] * 0.3, 2)) \
            .withColumn("valor_anual", round(data_inflacion_general["valor_anual"] * 0.3, 2)) \
            .drop("fecha_riesgo") \
            .drop("valor_riesgo")

        data_inflacion_cordoba = data_inflacion_cordoba.dropDuplicates(["fecha_inflacion"])

        data_inflacion_cordoba.write.csv(INDICE_CORDOBA, header=True, mode="overwrite")

        data_inflacion_cordoba.show()

        url = URL_POSTGRES

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver",
        }

        data_inflacion_cordoba.write.jdbc(
            url, "indices_cordoba", mode="overwrite", properties=properties
        )

    except Exception as e:
        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()

