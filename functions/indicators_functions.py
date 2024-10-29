import os

import requests
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import date_format, month, year


load_dotenv()
POSTGRES_JAR = os.getenv('POSTGRES_JAR') 
INDICE_ANUAL = os.getenv('INDICE_ANUAL') 
INDICE_MENSUAL = os.getenv('INDICE_MENSUAL') 
RIESGO_PAIS = os.getenv('RIESGO_PAIS') 
INDICE_JOINED = os.getenv('INDICE_JOINED') 
URL_POSTGRES = os.getenv('URL_POSTGRES') 
USER_POSTGRES = os.getenv('USER_POSTGRES') 
PASSWORD_POSTGRES = os.getenv('PASSWORD_POSTGRES') 

def create_spark_session():

    if not POSTGRES_JAR:
        raise ValueError("POSTGRES_JAR not found")

    return (
        SparkSession.builder.appName("indices_argentina")
        .config("spark.jars", POSTGRES_JAR)
        .getOrCreate()
    )



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
        data_riesgo_pais = requests.get(
            "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/"
        )

        data_inflacion_mensual.raise_for_status()
        data_inflacion_anual.raise_for_status()
        data_riesgo_pais.raise_for_status()

        data_mensual = data_inflacion_mensual.json()
        data_anual = data_inflacion_anual.json()
        data_riesgo = data_riesgo_pais.json()

        data_mensual = [
            {"fecha": item["fecha"], "valor": float(item["valor"])}
            for item in data_mensual
        ]
        data_anual = [
            {"fecha": item["fecha"], "valor": float(item["valor"])}
            for item in data_anual
        ]

        data_riesgo = [
            {"fecha": item["fecha"], "valor": int(item["valor"])}
            for item in data_riesgo
        ]

        df_m = spark.createDataFrame(data_mensual)
        df_a = spark.createDataFrame(data_anual)
        df_r = spark.createDataFrame(data_riesgo)

        # df_m.printSchema()
        # df_a.printSchema()

        df_m.write.csv(
            INDICE_MENSUAL,
            header=True,
            mode="overwrite",
        )

        df_a.write.csv(
            INDICE_ANUAL,
            header=True,
            mode="overwrite",
        )

        df_r.write.csv(
            RIESGO_PAIS,
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

        # Dataframe Inflacion mensual 
        df_mensual = spark.read.csv(
            INDICE_MENSUAL, header=True
        ).withColumnRenamed("valor", "valor_mensual").withColumnRenamed("fecha", "fecha_inflacion")

        df_mensual = df_mensual.withColumn(
            "fecha_inflacion", df_mensual["fecha_inflacion"].cast("timestamp")
        )

        # Dataframe Inflacion interanual
        df_anual = spark.read.csv(
            INDICE_ANUAL, header=True
        ).withColumnRenamed("valor", "valor_anual").withColumnRenamed("fecha", "fecha_inflacion")

        df_anual = df_anual.withColumn("fecha_inflacion", df_anual["fecha_inflacion"].cast("timestamp"))

        # Dataframe riesgo pais
        df_riesgo = spark.read.csv(
            RIESGO_PAIS, header=True
        ).withColumnRenamed("valor", "valor_riesgo").withColumnRenamed("fecha", "fecha_riesgo")

        df_riesgo = df_riesgo.withColumn("fecha_riesgo", df_riesgo["fecha_riesgo"].cast("timestamp"))

        df_joined = df_mensual.join(df_anual, on="fecha_inflacion", how="inner")

        df_second_join = df_joined.join(
            df_riesgo,
            (
                (year(df_joined["fecha_inflacion"]) == year(df_riesgo["fecha_riesgo"]))
                & (month(df_joined["fecha_inflacion"]) == month(df_riesgo["fecha_riesgo"]))
            ),
            how="inner",
        )

        df_sorted = df_second_join.orderBy("fecha_inflacion", ascending=False) \
            .withColumn("fecha_inflacion", date_format("fecha_inflacion", "yyyy-MM-dd")) \
            .withColumn("fecha_riesgo", date_format("fecha_riesgo", "yyyy-MM-dd"))

        df_sorted.show()

        df_sorted.write.csv(
            INDICE_JOINED,
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
            INDICE_JOINED, header=True
        )

        url = URL_POSTGRES 

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver",
        }

        df_transformed.write.jdbc(
            url, "indices", mode="overwrite", properties=properties
        )

    except Exception as e:

        print(f"Error: {e}")

    finally:

        if spark:
            spark.stop()
