import os
from itertools import chain
from typing import Any, Callable, Dict, List, Optional, Union

import mysql.connector

from grai_source_mysql.models import Column, ColumnID, Edge, EdgeQuery, MysqlNode, Table


def get_from_env(label: str, default: Optional[Any] = None, validator: Callable = None):
    env_key = f"GRAI_MYSQL_{label.upper()}"
    result = os.getenv(env_key, default)
    if result is None:
        message = (
            f"Establishing mysql connection requires a {label}. "
            f"Either pass a value explicitly or set a {env_key} environment value."
        )
        raise Exception(message)
    return result if validator is None else validator(result)


class MySQLConnector:
    def __init__(
        self,
        dbname: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[Union[str, int]] = None,
        namespace: Optional[str] = None,
    ):
        self.host = host if host is not None else get_from_env("host", "localhost")
        self.port = port if port is not None else get_from_env("port", "3306", str)
        self.dbname = dbname if dbname is not None else get_from_env("dbname")
        self.user = user if user is not None else get_from_env("user")
        self.password = password if password is not None else get_from_env("password")
        self.namespace = namespace if namespace is not None else get_from_env("namespace", "default")
        self._connection = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def connection_dict(self) -> dict:
        return {
            "host": self.host,
            "database": self.dbname,
            "user": self.user,
            "password": self.password,
            "port": self.port,
        }

    def connect(self):
        if self._connection is None:
            self._connection = mysql.connector.connect(**self.connection_dict)
        return self

    @property
    def connection(self):
        if self._connection is None:
            raise Exception("Not connected, call `.connect()")
        return self._connection

    def close(self) -> None:
        self.connection.close()
        self._connection = None

    def query_runner(self, query: str, param_dict: Dict = {}) -> List[Dict]:
        dict_cursor = self.connection.cursor(dictionary=True)
        dict_cursor.execute(query, param_dict)
        result = dict_cursor.fetchall()
        return [dict(item) for item in result]

    def get_tables(self) -> List[Table]:
        """
        Create and return a list of dictionaries with the
        schemas and names of tables in the database
        connected to by the connection argument.
        """

        query = """
	    SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema != 'information_schema'
		    AND table_schema != 'performance_schema'
            ORDER BY table_schema, table_name
        """
        res = ({k.lower(): v for k, v in result.items()} for result in self.query_runner(query))
        return [Table(**result, namespace=self.namespace) for result in res]

    def get_columns(self, table: Table) -> List[Column]:
        """
        Creates and returns a list of dictionaries for the specified
        schema.table in the database connected to.
        """

        query = f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = '{table.table_schema}'
            AND table_name = '{table.name}'
            ORDER BY ordinal_position
        """

        res = ({k.lower(): v for k, v in result.items()} for result in self.query_runner(query))

        addtl_args = {
            "namespace": table.namespace,
            "schema": table.table_schema,
            "table": table.name,
        }
        return [Column(**result, **addtl_args) for result in res]

    def get_foreign_keys(self) -> List[Edge]:
        """This needs to be tested / evaluated
        :param connection:
        :param table:
        :return:
        """
        # Only need constraint_types == 'f' for foreign keys but the others might be useful someday.
        # Removed schemas, no schemas in mysql
        query = """
        select
            tc.CONSTRAINT_NAME as constraint_name,
            case when tc.CONSTRAINT_TYPE='PRIMARY KEY' then 'p'
                when tc.CONSTRAINT_TYPE='FOREIGN KEY' then 'f' end as constraint_type,
            tc.TABLE_schema as "self_schema",
            tc.TABLE_NAME as "self_table",
            GROUP_CONCAT(kcu.COLUMN_NAME SEPARATOR ',') "self_columns",
            kcu.TABLE_schema as "foreign_schema",
            kcu.REFERENCED_TABLE_NAME as "foreign_table",
            GROUP_CONCAT(kcu.REFERENCED_COLUMN_NAME SEPARATOR ',') as "foreign_columns",
            CONCAT(tc.CONSTRAINT_TYPE, ' (', GROUP_CONCAT(kcu.COLUMN_NAME), ')', (case when tc.CONSTRAINT_TYPE = 'FOREIGN KEY' then CONCAT(' REFERENCES ',kcu.REFERENCED_TABLE_NAME,'(',GROUP_CONCAT(kcu.REFERENCED_COLUMN_NAME),')') else '' end) ) as "definition"
        from
            information_schema.TABLE_CONSTRAINTS tc
        join information_schema.KEY_COLUMN_USAGE kcu on
            (kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
            or kcu.REFERENCED_TABLE_SCHEMA = tc.TABLE_SCHEMA)
            and (kcu.TABLE_NAME = tc.TABLE_NAME
            or kcu.REFERENCED_TABLE_NAME = tc.TABLE_NAME)
            and kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
        group by
            tc.CONSTRAINT_NAME,
            tc.CONSTRAINT_TYPE,
            tc.TABLE_NAME,
            tc.TABLE_schema,
            kcu.TABLE_schema,
            kcu.REFERENCED_TABLE_NAME
        """
        addtl_args = {
            "namespace": self.namespace,
        }

        res = self.query_runner(query)

        for item in res:
            item["self_columns"] = list(item["self_columns"].split(",")) if item["self_columns"] else []
            item["foreign_columns"] = list(item["foreign_columns"].split(",")) if item["foreign_columns"] else []

        res = ({k.lower(): v for k, v in result.items()} for result in res)

        filtered_results = (result for result in res if result["constraint_type"] == "f")

        return [EdgeQuery(**fk, **addtl_args).to_edge() for fk in filtered_results]

    def get_nodes(self) -> List[MysqlNode]:
        def get_nodes():
            for table in self.get_tables():
                table.columns = self.get_columns(table)
                yield [table]
                yield table.columns

        return list(chain(*get_nodes()))

    # TODO need to push edges between table -> columns

    def get_nodes_and_edges(self):
        tables = self.get_tables()
        edges = []
        for table in tables:
            table.columns = self.get_columns(table)

        edges = list(chain(*[t.get_edges() for t in tables], self.get_foreign_keys()))

        nodes = list(chain(tables, *[t.columns for t in tables]))
        return nodes, edges
