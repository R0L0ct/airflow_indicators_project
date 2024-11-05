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
CRIME_PATH = os.getenv("CRIME_PATH")


def create_spark_session():
    return (
        SparkSession.builder.appName("crime_data")
        .config("spark.jars", POSTGRES_JAR)
        .getOrCreate()
    )


def extract():

    url = "https://data.lacity.org/api/views/2nrs-mtv8/rows.csv?accessType=DOWNLOAD"

    try:
        if CRIME_PATH is None:
            raise ValueError("CRIME_PATH not found!")

        os.makedirs(CRIME_PATH, exist_ok=True)

        response = requests.get(url)

        data_path = os.path.join(CRIME_PATH, "crime_data.csv")

        if response.status_code == 200:

            with open(data_path, "wb") as file:
                file.write(response.content)

            return data_path
        else:

            print(f"{response.status_code}")

    except Exception as e:
        print(f"Error: {e}")


def transform(**kwargs):

    ti = kwargs["ti"]

    data_path = ti.xcom_pull(task_ids="extract_and_land")

    spark = None

    try:

        spark = create_spark_session()

        if CRIME_PATH is None:
            raise ValueError("CRIME_PATH not found!")

        transformed_data = os.path.join(CRIME_PATH, "crime_data_transformed.csv")

        df = spark.read.csv(data_path, header=True)

        exclude_columns = [
            "DR_NO",
            "Date Rptd",
            "Rpt Dist No",
            "Mocodes",
            "Crm Cd 1",
            "Crm Cd 2",
            "Crm Cd 3",
            "Crm Cd 4",
            "Premis Cd",
        ]

        df = df.select([col for col in df.columns if col not in exclude_columns])

        df.write.csv(transformed_data, header=True, mode="overwrite")

        df.show(n=100)

        return transformed_data

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if spark:
            spark.stop()


def load(**kwargs):

    spark = None

    ti = kwargs["ti"]

    transformed_data = ti.xcom_pull(task_ids="transform")

    try:

        spark = create_spark_session()

        properties = {
            "user": USER_POSTGRES,
            "password": PASSWORD_POSTGRES,
            "driver": "org.postgresql.Driver",
        }

        url = URL_POSTGRES

        df = spark.read.csv(transformed_data, header=True)

        df.write.jdbc(url, "crime_data", mode="overwrite", properties=properties)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if spark:
            spark.stop()


## https://data.gov/
