# db_connection.py
import psycopg2
from psycopg2 import sql

def create_connection():
    try:
        connection = psycopg2.connect(
            user="your_username",
            password="your_password",
            host="localhost",
            port="5432",
            database="your_database"
        )
        return connection
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
        return None

def close_connection(connection):
    if connection:
        connection.close()
        print("PostgreSQL connection closed")
