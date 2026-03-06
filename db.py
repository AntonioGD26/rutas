import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', ''),
            'database': os.getenv('DB_NAME', ''),
            'user': os.getenv('DB_USER', ''),
            'password': os.getenv('DB_PASSWORD', ''),
            'port': os.getenv('DB_PORT', '')
        }

    def get_connection(self):
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            st.error(f"Error de conexión: {str(e)}")
            return None

    def execute_query(self, query, params=None, fetch=True):
        conn = self.get_connection()
        if not conn:
            return None

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                if fetch:
                    if query.strip().upper().startswith(('SELECT', 'WITH')):
                        return cursor.fetchall()
                    elif query.strip().upper().startswith('INSERT'):
                        return cursor.fetchone()
                conn.commit()
                return None
        except Exception as e:
            st.error(f"Error en consulta: {str(e)}")
            return None
        finally:
            conn.close()

    def get_user(self, username):
        query = "SELECT id, username, password_hash, nombre, rol FROM usuarios WHERE username = %s AND activo = TRUE"
        result = self.execute_query(query, (username,))
        return result[0] if result else None

db = Database()