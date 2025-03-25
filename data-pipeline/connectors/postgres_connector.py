import logging
import pandas as pd
import psycopg2

logger = logging.getLogger(__name__)

def read_from_postgres(connection_string: str, query: str) -> pd.DataFrame:
    """Reads data from a PostgreSQL database using the provided query."""
    try:
        conn = psycopg2.connect(connection_string)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Error reading from PostgreSQL: {e}")
        raise e