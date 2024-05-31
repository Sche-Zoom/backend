# database.py

import psycopg2
from psycopg2 import Error

class Database:
    _connection = None

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            cls.connect()
        return cls._connection

    @classmethod
    def connect(cls):
        try:
            cls._connection = psycopg2.connect(
                dbname='user',
                user='user1',
                password='user1!',
                host='0.0.0.0',
                port=5432
            )
        except Error as e:
            print(f"Error connecting to PostgreSQL: {e}")

    @classmethod
    def close_connection(cls):
        if cls._connection is not None:
            cls._connection.close()
            cls._connection = None
