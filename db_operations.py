# db_operations.py
from db_connection import create_connection, close_connection

def create_table():
    connection = create_connection()
    if connection is None:
        return

    # try:
    #     cursor = connection.cursor()
    #     create_table_query = '''CREATE TABLE IF NOT EXISTS employees (
    #                                 ID INT PRIMARY KEY,
    #                                 NAME TEXT NOT NULL,
    #                                 AGE INT NOT NULL,
    #                                 SALARY REAL);'''
    #     cursor.execute(create_table_query)
    #     connection.commit()
    #     print("Table created successfully")
    # except (Exception, psycopg2.Error) as error:
    #     print("Error while creating table", error)
    # finally:
    #     cursor.close()
    #     close_connection(connection)

def insert_employee(employee_id, name, age, salary):
    connection = create_connection()
    if connection is None:
        return

    try:
        cursor = connection.cursor()
        insert_query = '''INSERT INTO employees (ID, NAME, AGE, SALARY) 
                          VALUES (%s, %s, %s, %s)'''
        cursor.execute(insert_query, (employee_id, name, age, salary))
        connection.commit()
        print("Employee inserted successfully")
    except (Exception, psycopg2.Error) as error:
        print("Error while inserting into table", error)
    finally:
        cursor.close()
        close_connection(connection)

def fetch_employees():
    connection = create_connection()
    if connection is None:
        return

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM employees")
        rows = cursor.fetchall()

        for row in rows:
            print(row)
    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data", error)
    finally:
        cursor.close()
        close_connection(connection)
