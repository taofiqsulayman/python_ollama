# db_connection.py
import psycopg2
from psycopg2 import sql

def create_connection():
    try:
        connection = psycopg2.connect(
            user="root",
            password="pa$$w0rd",
            host="127.0.0.1",
            port="5432",
            database="ollama_db"
        )
        return connection
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
        return None

def close_connection(connection):
    if connection:
        connection.close()
        print("PostgreSQL connection closed")
