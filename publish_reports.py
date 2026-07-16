"""Publicera dbt-modellerna till en lokal DuckDB-fil för Evidence.

    python publish_reports.py

Körs efter `dbt build`. Kopierar mart/staging-tabellerna från DuckLake (Azure)
till en lokal reports/trains.duckdb. Evidence läser bara den lokala filen —
ingen Azure, inga secrets, ingen ducklake-attach i Node-lagret.
"""
import pathlib
import tomllib

import duckdb

REPORTS_DB = pathlib.Path("reports/trains.duckdb")

# Tabeller att publicera: (schema, tabell)
SOURCES = [
    ("mart", "fct_train_passages"),
    ("mart", "agg_passages_daily"),
    ("mart", "dim_trains"),
    ("staging", "stg_train_stations"),
]


def main() -> None:
    with open(".dlt/secrets.toml", "rb") as f:
        creds = tomllib.load(f)["destination"]["ducklake"]["credentials"]["storage"]["credentials"]

    REPORTS_DB.parent.mkdir(exist_ok=True)
    con = duckdb.connect(str(REPORTS_DB))
    con.execute("INSTALL ducklake; LOAD ducklake; INSTALL azure; LOAD azure;")
    # Default-transport: curl hittar inte CA-certet (Windows-certlager / GHA-runner).
    con.execute("SET azure_transport_option_type = 'default';")
    con.execute(
        "CREATE OR REPLACE SECRET s (TYPE AZURE, CONNECTION_STRING "
        f"'AccountName={creds['azure_storage_account_name']};"
        f"AccountKey={creds['azure_storage_account_key']}', SCOPE 'az://trainlake/');"
    )
    con.execute("ATTACH 'ducklake:trains_catalog.ducklake' AS trainlake;")
    for schema, table in SOURCES:
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM trainlake.{schema}.{table}"
        )
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n} rader")
    con.execute("DETACH trainlake;")
    con.close()
    print(f"Klart -> {REPORTS_DB}")


if __name__ == "__main__":
    main()
