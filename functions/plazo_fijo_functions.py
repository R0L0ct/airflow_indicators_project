import csv
import os

import requests
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

load_dotenv()
POSTGRES_JAR = os.getenv("POSTGRES_JAR")
USER_POSTGRES = os.getenv("USER_POSTGRES")
URL_POSTGRES = os.getenv("URL_POSTGRES")
PASSWORD_POSTGRES = os.getenv("PASSWORD_POSTGRES")
PLAZO_FIJO_PATH = os.getenv("PLAZO_FIJO_PATH")


def create_spark_session():
    return (
        SparkSession.builder.appName("plazo_fijo_app")
        .config("spark.jars", POSTGRES_JAR)
        .getOrCreate()
    )


def extract():
    try:
        url_plazo = "https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo/"
        url_deposito = (
            "https://api.argentinadatos.com/v1/finanzas/tasas/depositos30Dias/"
        )

        url_dictionary = {"plazo_fijo": url_plazo, "depositos30Dias": url_deposito}

        if PLAZO_FIJO_PATH is None:
            raise ValueError("PLAZO_FIJO_PATH not found!")

        os.makedirs(PLAZO_FIJO_PATH, exist_ok=True)

        for key, url in url_dictionary.items():
            data_path = os.path.join(PLAZO_FIJO_PATH, f"{key}.csv")
            response = requests.get(url)
            data = response.json()

            with open(data_path, "w", newline="") as file:
                if isinstance(data, list) and len(data) > 0:
                    headers = data[0].keys()
                    writer = csv.DictWriter(file, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(data)

    except Exception as e:
        print(f"Error: {e}")


def transform():
    spark = None

    try:
        spark = create_spark_session()

        if PLAZO_FIJO_PATH is None:
            raise ValueError("PLAZO_FIJO_PATH not found!")

        path_plazo = os.path.join(PLAZO_FIJO_PATH, "plazo_fijo.csv")
        path_deposito = os.path.join(PLAZO_FIJO_PATH, "depositos30Dias.csv")

        path_plazo_transformed = os.path.join(
            PLAZO_FIJO_PATH, "plazo_fijo_transformed.csv"
        )
        path_deposito_transformed = os.path.join(
            PLAZO_FIJO_PATH, "depositos30Dias_transformed.csv"
        )

        df_plazo = spark.read.csv(path_plazo, header=True)
        df_deposito = spark.read.csv(path_deposito, header=True)

        exclude_columns = ["logo", "enlace"]

        df_plazo = df_plazo.select(
            [col for col in df_plazo.columns if col not in exclude_columns]
        )

        df_plazo.write.csv(path_plazo_transformed, header=True, mode="overwrite")
        df_deposito.write.csv(path_deposito_transformed, header=True, mode="overwrite")

        df_plazo.show()
        df_deposito.show()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if spark:
            spark.stop()


def load():

    spark = None

    try:
        spark = create_spark_session()

        if PLAZO_FIJO_PATH is None:
            raise ValueError("PLAZO_FIJO_PATH not found!")

        path_plazo_transformed = os.path.join(
            PLAZO_FIJO_PATH, "plazo_fijo_transformed.csv"
        )
        path_deposito_transformed = os.path.join(
            PLAZO_FIJO_PATH, "depositos30Dias_transformed.csv"
        )

        df_plazo = spark.read.csv(path_plazo_transformed, header=True)
        df_deposito = spark.read.csv(path_deposito_transformed, header=True)

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver",
        }

        df_plazo.write.jdbc(
            URL_POSTGRES, "plazo_fijo", mode="overwrite", properties=properties
        )
        df_deposito.write.jdbc(
            URL_POSTGRES, "deposito_30_dias", mode="overwrite", properties=properties
        )

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if spark:
            spark.stop()
