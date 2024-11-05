import os

import requests
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

load_dotenv()
POSTGRES_JAR = os.getenv("POSTGRES_JAR")
COVID_PATH = os.getenv("COVID_PATH")
USER_POSTGRES = os.getenv("USER_POSTGRES")
URL_POSTGRES = os.getenv("URL_POSTGRES")
PASSWORD_POSTGRES = os.getenv("PASSWORD_POSTGRES")

def create_spark_session():
    return (
        SparkSession.builder.appName("Covid_Indicators")
        .config("spark.jars", POSTGRES_JAR)
        .getOrCreate()
    )

def extract():

    try:

        if COVID_PATH is None:
            raise ValueError("COVID_PATH not found!")

        os.makedirs(COVID_PATH, exist_ok=True)

        url = "https://raw.githubusercontent.com/owid/covid-19-data/refs/heads/master/public/data/owid-covid-data.csv"

        response = requests.get(url)

        if response.status_code == 200:
            data_path = os.path.join(COVID_PATH, 'covid-19-data.csv')

            with open(data_path, "wb") as file:
                file.write(response.content)
        else:

            print(f"{response.status_code}")

    except Exception as e:
        print(f'Error: {e}')


def transform():
    spark = None

    try:
        spark = create_spark_session()

        if COVID_PATH is None:
            raise ValueError("COVID_PATH not found!")

        data_path = os.path.join(COVID_PATH,"covid-19-data.csv")

        df = spark.read.csv(data_path, header=True)

        df = df.select("location", "date", "total_cases", "new_cases")

        df = df.filter(~(df['total_cases'].isNull() & df['new_cases'].isNull()))

        df = df.orderBy("date", ascending=False)

        # df = df.dropna(subset=[])

        df.show(n=200)

        transformed_data = os.path.join(COVID_PATH, 'covid-19-data-transformed.csv')

        df.write.csv(transformed_data, header=True, mode="overwrite")

        return transformed_data

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if spark:
            spark.stop()

def load(**kwargs):

    spark = None

    ti = kwargs['ti']

    transformed_data = ti.xcom_pull(task_ids="transform")

    url = URL_POSTGRES

    try:

        spark = create_spark_session()

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver"
        }

        df = spark.read.csv(transformed_data, header=True)

        df.write.jdbc(url, 'covid_indicators', mode="overwrite", properties=properties)

    except Exception as e:
        print(f'Error: {e}')
    finally:
        if spark:
            spark.stop()
