FROM apache/airflow:2.10.2


USER root

# Limpiar listas de paquetes y actualizar
# Dichas listas contienen información sobre los paquetes disponibles en los repositorios
# Luego, al realizar un update, volvemos a descargarlas 
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get update && \
    apt-get install -y default-jdk && \
    apt-get clean

# Configurar JAVA_HOME
ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64
ENV PATH $JAVA_HOME/bin:$PATH

# Cambiar de nuevo al usuario airflow
USER airflow

COPY requirements.txt /requirements.txt
RUN pip install  --upgrade pip
RUN pip install --no-cache-dir  -r /requirements.txt



