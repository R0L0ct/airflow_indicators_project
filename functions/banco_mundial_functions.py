import os
import re
import zipfile

import requests
from functools import reduce
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType

load_dotenv()
POSTGRES_JAR = os.getenv("POSTGRES_JAR")
USER_POSTGRES = os.getenv("USER_POSTGRES")
URL_POSTGRES = os.getenv("URL_POSTGRES")
PASSWORD_POSTGRES = os.getenv("PASSWORD_POSTGRES")
BANCO_MUNDIAL_PATH = os.getenv("BANCO_MUNDIAL_PATH")


def create_spark_session():
    return (
        SparkSession.builder.appName("banco_mundial_indicators")
        .config("spark.jars", POSTGRES_JAR)
        .getOrCreate()
    )


def extract():

    try:

        if BANCO_MUNDIAL_PATH is None:
            raise ValueError("BANCO_MUNDIAL_PATH not found!")

        os.makedirs(BANCO_MUNDIAL_PATH, exist_ok=True)

        url_list = {
            "poblacion_total": "https://api.worldbank.org/v2/es/indicator/SP.POP.TOTL?downloadformat=csv",
            "pbi": "https://api.worldbank.org/v2/es/indicator/NY.GDP.MKTP.CD?downloadformat=csv",
            "pbi_percapita": "https://api.worldbank.org/v2/es/indicator/NY.GDP.PCAP.CD?downloadformat=csv",
            "inversion_extranjera": "https://api.worldbank.org/v2/es/indicator/BM.KLT.DINV.WD.GD.ZS?downloadformat=csv",
        }

        response_list = {}

        for key, url in url_list.items():
            response = requests.get(url)
            response_list[key] = response

        if all(response.status_code == 200 for response in response_list.values()):
            for key, response in response_list.items():

                zip_path = os.path.join(BANCO_MUNDIAL_PATH, f"temp_{key}.zip")

                with open(zip_path, "wb") as temp_zip:
                    temp_zip.write(response.content)

                with zipfile.ZipFile(zip_path, "r") as zip_r:
                    zip_r.extractall(BANCO_MUNDIAL_PATH)

                    for file_name in zip_r.namelist():
                        file_path = os.path.join(BANCO_MUNDIAL_PATH, file_name)
                        if file_name.startswith("API"):
                            new_file_name = f"{key}.csv"
                            new_file_path = os.path.join(
                                BANCO_MUNDIAL_PATH, new_file_name
                            )
                            os.rename(file_path, new_file_path)
                        else:
                            os.remove(file_path)

                os.remove(zip_path)

    except Exception as e:
        print(f"Error: {e}")


def transform():

    spark = None

    try:
        spark = create_spark_session()

        if BANCO_MUNDIAL_PATH is None:
            raise ValueError("BANCO_MUNDIAL_PATH not found!")

        file_list = {}

        for file_name in os.listdir(BANCO_MUNDIAL_PATH):
            file_path = os.path.join(BANCO_MUNDIAL_PATH, file_name)
            if os.path.isfile(file_path):
                file_list[file_name] = file_path

        dataframes = []
        for file_name, file_path in file_list.items():
            try:

                rdd = spark.sparkContext.textFile(file_path)

                filter_rdd = (
                    rdd.zipWithIndex().filter(lambda x: x[1] >= 4).map(lambda x: x[0])
                )

                def split_with_quotes(row):
                    return re.findall(r'(?:[^,"]|"(?:\\.|[^"])*")+', row)

                filter_rdd = filter_rdd.map(split_with_quotes)

                header_line = filter_rdd.first()

                header = [col.replace('"', "").strip() for col in header_line]

                data_rdd = filter_rdd.filter(lambda x: x != header_line)

                data_rdd = data_rdd.map(
                    lambda x: [value.replace('"', "").strip() for value in x]
                )

                df = spark.createDataFrame(data_rdd, schema=header)

                df = (
                    df.select("Country Name","2023")
                    .withColumn("2023", df["2023"].cast(FloatType()))
                    .withColumn(
                        "2023",
                        F.when(F.col("2023").isNull(), 0).otherwise(F.col("2023")),
                    )
                    .withColumnRenamed("2023", f"{file_name.split(".")[0]} 2023")
                )

                df = df.filter(df["Country Name"] != "")

                dataframes.append(df)

            except Exception as e:
                print(f"Error procesando el archivo {file_path}: {e}")

        # df_pbi = dataframes[0]
        # df_poblacion = dataframes[1]
        # df_pbi_percapita = dataframes[2]
        # df_inversion = dataframes[3]

        df = reduce(lambda df1, df2: df1.join(df2, on="Country Name", how="inner"), dataframes)

        df = df.orderBy("Country Name")

        df.show(n=100)

        df.write.csv(os.path.join(BANCO_MUNDIAL_PATH, "banco_mundial_transformed.csv"), header=True, mode="overwrite")

        # df_pbi.write.csv(
        #     os.path.join(BANCO_MUNDIAL_PATH, "pbi_transformed.csv"), header=True, mode="overwrite"
        # )
        # df_pbi_percapita.write.csv(
        #     os.path.join(BANCO_MUNDIAL_PATH, "pbi_percapita_transformed.csv"),
        #     header=True, mode="overwrite"
        # )
        # df_inversion.write.csv(
        #     os.path.join(BANCO_MUNDIAL_PATH, "inversion_transformed.csv"), header=True, mode="overwrite"
        # )
        # df_poblacion.write.csv(
        #     os.path.join(BANCO_MUNDIAL_PATH, "poblacion_transformed.csv"), header=True, mode="overwrite"
        # )

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

        if BANCO_MUNDIAL_PATH is None:
            raise ValueError("BANCO_MUNDIAL_PATH not found!")

        file_path = os.path.join(BANCO_MUNDIAL_PATH, "banco_mundial_transformed.csv")

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver"
        }

        if os.path.isdir(file_path):

            df = spark.read.csv(file_path, header=True)

            df.write.jdbc(url, "banco_mundial_indicators", mode="overwrite", properties=properties)

        else:
            print("csv not found")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if spark:
            spark.stop()
