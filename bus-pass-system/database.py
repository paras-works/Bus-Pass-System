import mysql.connector
import config


class Database:
    """A small wrapper around a MySQL connection."""

    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """Open a connection to MySQL using the settings in config.py."""
        self.connection = mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
        )

    def _ensure_connected(self):
        """Reconnect automatically if the connection dropped (e.g. MySQL
        timed out an idle connection)."""
        if self.connection is None or not self.connection.is_connected():
            self.connect()

    def run(self, query, params=None):
        """
        Run an INSERT / UPDATE / DELETE statement.
        Returns the last inserted row id (useful right after an INSERT).

        IMPORTANT: `params` is always passed separately from the query
        string (parameterized query). This is what prevents SQL
        injection - user input is NEVER glued directly into the SQL
        text with string formatting.
        """
        self._ensure_connected()
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            self.connection.commit()
            return cursor.lastrowid
        finally:
            cursor.close()

    def fetch_one(self, query, params=None):
        """Run a SELECT and return a single row as a dictionary, or None."""
        self._ensure_connected()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchone()
        finally:
            cursor.close()

    def fetch_all(self, query, params=None):
        """Run a SELECT and return every matching row as a list of dicts."""
        self._ensure_connected()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
