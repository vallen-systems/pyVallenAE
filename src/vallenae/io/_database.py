import sqlite3
from ast import literal_eval
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Set, Tuple, Union

from ._sql import insert_from_dict, read_sql_generator, update_from_dict


def require_write_access(func):
    @wraps(func)
    def wrapper(self: "Database", *args, **kwargs):
        if self.readonly:
            raise ValueError(
                "Can not write to database in read-only mode. Open database with mode='rw'"
            )
        return func(self, *args, **kwargs)
    return wrapper


class Database:
    """Database base class for pridb, tradb and trfdb."""

    def __init__(
        self,
        filename: str,
        mode: str = "ro",
        *,
        table_prefix: str,
        required_file_ext: Optional[str] = None,
    ):
        # forced str conversion (e.g. for pathlib.Path)
        self._filename: str = str(filename)

        # check mode
        valid_modes = ("ro", "rw", "rwc")
        if mode not in valid_modes:
            raise ValueError(f"Invalid access mode '{mode}', use: {valid_modes}")
        if mode == "rwc":
            raise NotImplementedError("Database creation not implemented yet")
        self._readonly: bool = (mode == "ro")

        if required_file_ext is not None:
            file_ext = Path(self._filename).suffix[1:]
            if file_ext.lower() != required_file_ext.lower():
                raise ValueError(f"File extension '{file_ext}' must match '{required_file_ext}'")

        self._connected: bool = False
        self._connection = sqlite3.connect(
            f"file:{self._filename}?mode={mode}",
            uri=True,
            check_same_thread=(not self._readonly),  # allow multithreading in read-only mode
        )
        self._connected = True

        # set pragmas for write-mode
        if not self._readonly:
            self._connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA locking_mode = EXCLUSIVE;
                PRAGMA synchronous = OFF;
                """
            )

        self._table_prefix: str = table_prefix
        self._table_main: str = f"{table_prefix}_data"
        self._table_fieldinfo: str = f"{table_prefix}_fieldinfo"
        self._table_globalinfo: str = f"{table_prefix}_globalinfo"
        self._table_params: str = f"{table_prefix}_params"

        # check if required tables exist
        for table in (self._table_main, self._table_fieldinfo, self._table_globalinfo):
            if table not in self.tables():
                raise ValueError(f"Required table {table} not found in database")

        # cached results
        self._parameter_table_cached: Dict[int, Dict[str, Any]] = {}

    @property
    def filename(self) -> str:
        """Filename of database."""
        return self._filename

    @property
    def readonly(self) -> bool:
        """Read-only mode for database connection."""
        return self._readonly

    @property
    def connected(self) -> bool:
        """Check if connected to SQLite database."""
        return self._connected

    def connection(self) -> sqlite3.Connection:
        """
        Get SQLite connection object.

        Raises:
            RuntimeError: If connection is closed
        """
        if not self._connected:
            raise RuntimeError("Not connected to SQLite database")
        return self._connection

    def rows(self) -> int:
        """Number of rows in data table."""
        con = self.connection()
        cur = con.execute(f"SELECT COUNT(*) FROM {self._table_main}")
        return cur.fetchone()[0]

    def _columns(self, table: str) -> Tuple[str, ...]:
        """Columns of specified table."""
        con = self.connection()
        cur = con.execute(f"SELECT * FROM {table} LIMIT 0")  # empty dummy query
        return tuple(str(column[0]) for column in cur.description)

    def columns(self) -> Tuple[str, ...]:
        """Columns of data table."""
        return self._columns(self._table_main)

    @require_write_access
    def _add_columns(
        self,
        table: str,
        columns: Union[str, Set[str], Sequence[str]],
        dtype: Optional[str] = None,
    ):
        """Add columns to specified table."""
        if dtype is None:
            dtype = ""
        con = self.connection()
        columns_create = set(columns) - set(self._columns(table))
        for column in columns_create:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")

    def tables(self) -> Set[str]:
        """Get table names."""
        con = self.connection()
        cur = con.execute("SELECT name FROM sqlite_master WHERE type == 'table'")
        tables = {result[0] for result in cur.fetchall()}
        return tables

    def fieldinfo(self) -> Dict[str, Dict[str, Any]]:
        """
        Read fieldinfo table.

        The fieldinfo table stores informations about columns of the data table (like units).

        Returns:
            Dict of column names and informations (again a dict)
        """
        con = self.connection()
        query = f"SELECT * FROM {self._table_fieldinfo}"
        return {row.pop("field"): row for row in read_sql_generator(con, query)}

    @require_write_access
    def write_fieldinfo(self, field: str, info: Dict[str, Any]):
        """
        Write to fieldinfo table.

        Args:
            field: Column name of data table
            info: Dict of properties and values, e.g. {"Unit": "[Hz]"}

        Raises:
            ValueError: If field is not a column of data table
        """
        if field not in self.columns():
            raise ValueError(f"Field {field} must be a column of data table")

        con = self.connection()
        row_dict = info
        row_dict["field"] = field
        try:
            if field in self.fieldinfo().keys():
                update_from_dict(con, self._table_fieldinfo, row_dict, "field")
            else:
                insert_from_dict(con, self._table_fieldinfo, row_dict)
        except sqlite3.OperationalError:  # missing column(s)
            self._add_columns(self._table_fieldinfo, set(row_dict.keys()))
            self.write_fieldinfo(field, info)  # try again

    def globalinfo(self) -> Dict[str, Any]:
        """Read globalinfo table."""
        def try_convert_string(value: str) -> Any:
            try:
                return literal_eval(value)
            except SyntaxError:
                return str(value)
        con = self.connection()
        cur = con.execute(f"SELECT Key, Value FROM {self._table_globalinfo}")
        return {
            row[0]: try_convert_string(str(row[1])) for row in cur.fetchall()
        }

    @require_write_access
    def _update_globalinfo(self):
        """Update globalinfo after writes."""
        keys = self.globalinfo().keys()
        if "ValidSets" in keys:
            self.connection().execute(
                """
                UPDATE {prefix}_globalinfo
                SET Value = (SELECT MAX(rowid) FROM {prefix}_data)
                WHERE Key == "ValidSets"
                """.format(prefix=self._table_prefix)
            )
        if "TRAI" in keys:
            self.connection().execute(
                """
                UPDATE {prefix}_globalinfo
                SET Value = (SELECT MAX(TRAI) FROM {prefix}_data)
                WHERE Key == "TRAI";
                """.format(prefix=self._table_prefix)
            )

    def _parameter_table(self) -> Dict[int, Dict[str, Any]]:
        """Read *_params table to dict."""
        def parameter_by_id():
            for row in read_sql_generator(
                self.connection(),
                f"SELECT * FROM {self._table_params}",
            ):
                param_id = row.pop("ID")
                yield (param_id, row)

        if not self._parameter_table_cached:
            self._parameter_table_cached = dict(parameter_by_id())
        return self._parameter_table_cached

    def _parameter(self, param_id: int) -> Dict[str, Any]:
        """Read parameters from *_params by ID."""
        try:
            return self._parameter_table()[param_id]
        except KeyError:
            raise ValueError(
                f"Parameter ID {param_id} not found in {self._table_params}"
            )

    def close(self):
        """Close database connection."""
        if self._connected:
            if not self._readonly:
                self._update_globalinfo()
                self._connection.commit()  # commit remaining changes
            self._connection.close()
            self._connected = False

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.close()
