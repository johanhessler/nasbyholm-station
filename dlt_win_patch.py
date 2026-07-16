"""Windows-workaround för dlt:s ducklake/azure-destination.

När dlt skapar DuckDB-secreten för Azure Blob kör den hårdkodat
`SET azure_transport_option_type = 'curl'`. Curl-transporten kan inte verifiera
TLS-certet mot Windows certifikatlager här och faller med curl error 60
("SSL peer certificate or SSH remote key was not OK"). DuckDB:s default-transport
(schannel/WinHTTP) fungerar felfritt mot samma blob — verifierat.

Denna patch byter 'curl' mot 'default' i secret-satserna. Importera modulen
INNAN pipeline.run(). Ta bort när dlt gör transporten konfigurerbar uppströms.
"""
from dlt.destinations.impl.duckdb.sql_client import DuckDbSqlClient

_orig_build = DuckDbSqlClient._build_secret_statements


def _build_secret_statements_default_transport(*args, **kwargs):
    stmts = _orig_build(*args, **kwargs)
    return [s.replace("'curl'", "'default'") for s in stmts]


DuckDbSqlClient._build_secret_statements = staticmethod(
    _build_secret_statements_default_transport
)
