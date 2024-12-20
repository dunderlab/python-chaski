import os
import sqlite3
import time
import json
from platformdirs import user_data_dir
from typing import Any, Optional


########################################################################
class PersistentStorage:
    """
    A class for persistent storage using SQLite.

    Parameters
    ----------
    app_name : str, optional
        The name of the application (default is "chaski-confluent").
    filename : str, optional
        The name of the SQLite database file (default is "persistent_storage.db").
    default_ttl : Optional[int], optional
        Default time-to-live (TTL) for stored items in seconds.

    Examples
    --------
    >>> storage = PersistentStorage()
    >>> storage.set("key1", {"value": 123}, ttl=60)
    >>> value = storage.get("key1")
    >>> print(value)
    {'value': 123}
    """

    def __init__(
        self,
        app_name: str = "chaski-confluent",
        filename: str = "persistent_storage.db",
        default_ttl: Optional[int] = 3600,
    ):
        self.default_ttl = default_ttl
        self.storage_path = os.path.join(user_data_dir(app_name), filename)
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        self.conn = sqlite3.connect(self.storage_path)
        self._initialize_table()

    # ----------------------------------------------------------------------
    def _initialize_table(self) -> None:
        """Initialize the SQLite table if it does not already exist."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS storage (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expires_at REAL
                )
                """
            )

    # ----------------------------------------------------------------------
    def _cleanup_expired(self) -> None:
        """Remove expired entries from the storage."""
        current_time = time.time()
        with self.conn:
            self.conn.execute(
                "DELETE FROM storage WHERE expires_at IS NOT NULL AND expires_at < ?",
                (current_time,),
            )

    # ----------------------------------------------------------------------
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value with an optional expiration time.

        Parameters
        ----------
        key : str
            The key to associate with the value.
        value : Any
            The value to store.
        ttl : Optional[int], optional
            Time-to-live in seconds. If None, the default TTL is used.
        """
        if not isinstance(key, str):
            raise TypeError("Key must be a string.")
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl if ttl is not None else None
        value_json = json.dumps(value)
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO storage (key, value, expires_at) VALUES (?, ?, ?)",
                (key, value_json, expires_at),
            )

    # ----------------------------------------------------------------------
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Retrieve a value by its key.

        Parameters
        ----------
        key : str
            The key to look up.
        default : Optional[Any], optional
            The default value to return if the key is not found.

        Returns
        -------
        Any
            The stored value, or the default value if the key is not found or expired.
        """
        if not isinstance(key, str):
            raise TypeError("Key must be a string.")
        self._cleanup_expired()
        cursor = self.conn.execute(
            "SELECT value, expires_at FROM storage WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row is None:
            return default

        value, expires_at = row
        if expires_at is not None and expires_at < time.time():
            self.delete(key)
            return default
        return json.loads(value)

    # ----------------------------------------------------------------------
    def pop(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Retrieve and delete a value by its key.

        Parameters
        ----------
        key : str
            The key to look up.
        default : Optional[Any], optional
            The default value to return if the key is not found.

        Returns
        -------
        Any
            The stored value, or the default value if the key is not found.
        """
        value = self.get(key, default=default)
        if self.exists(key):
            self.delete(key)
        return value

    # ----------------------------------------------------------------------
    def delete(self, key: str) -> None:
        """
        Delete a value by its key.

        Parameters
        ----------
        key : str
            The key to delete.

        Raises
        ------
        KeyError
            If the key is not found.
        """
        with self.conn:
            cursor = self.conn.execute("DELETE FROM storage WHERE key = ?", (key,))
        if cursor.rowcount == 0:
            raise KeyError(f"Key '{key}' not found in PersistentStorage.")

    # ----------------------------------------------------------------------
    def exists(self, key: str) -> bool:
        """
        Check if a key exists.

        Parameters
        ----------
        key : str
            The key to check.

        Returns
        -------
        bool
            True if the key exists, False otherwise.
        """
        if not isinstance(key, str):
            raise TypeError("Key must be a string.")
        self._cleanup_expired()
        cursor = self.conn.execute("SELECT 1 FROM storage WHERE key = ?", (key,))
        return cursor.fetchone() is not None

    # ----------------------------------------------------------------------
    def keys(self) -> list[str]:
        """
        Retrieve all keys in the storage.

        Returns
        -------
        list[str]
            A list of keys.
        """
        self._cleanup_expired()
        cursor = self.conn.execute("SELECT key FROM storage")
        return [row[0] for row in cursor]

    # ----------------------------------------------------------------------
    def clear(self) -> None:
        """Remove all keys and values from the storage."""
        with self.conn:
            self.conn.execute("DELETE FROM storage")

    # ----------------------------------------------------------------------
    def close(self) -> None:
        """Close the SQLite connection."""
        self.conn.close()
