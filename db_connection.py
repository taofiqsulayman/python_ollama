import psycopg2
from psycopg2 import sql

def create_connection():
    try:
        connection = psycopg2.connect(
            user="root",
            password="pa$$w0rd",
            port="54320",
            host="127.0.0.1",
            database="ollama_db"
        )
        print("PostgreSQL connection successful")
        return connection
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
        return None

def close_connection(connection):
    if connection:
        connection.close()
        print("PostgreSQL connection closed")
# DB_URL=jdbc:postgresql://165.22.118.43:5431/psa-stage-api
# DB_USER=postgres
# DB_PASSWORD=969e66b69c6adc8d9f