"""Ladda ner/upp DuckLake-katalogfilen till Azure Blob.

DuckLake-katalogen (`trains_catalog.ducklake`) är en lokal DuckDB-fil som håller
lakets metadata. På en efemär GHA-runner måste den överleva mellan körningar →
vi speglar den i blob (`az://trainlake/catalog/`). Bara EN skrivare (cronen), så
ingen låsning behövs.

    python blob_catalog.py download   # före pipeline/dbt
    python blob_catalog.py upload     # efter dbt (katalogen är då uppdaterad)

Nyckeln läses från env AZURE_STORAGE_ACCOUNT_KEY (GHA-secret), annars från
.dlt/secrets.toml (lokal körning/migrering).
"""
import os
import pathlib
import sys

from azure.storage.blob import BlobClient

ACCOUNT = "nasbyholmstation"
CONTAINER = "trainlake"
BLOB = "catalog/trains_catalog.ducklake"
LOCAL = pathlib.Path("trains_catalog.ducklake")


def _account_key() -> str:
    key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
    if key:
        return key
    import tomllib
    creds = tomllib.load(open(".dlt/secrets.toml", "rb"))[
        "destination"]["ducklake"]["credentials"]["storage"]["credentials"]
    return creds["azure_storage_account_key"]


def _client() -> BlobClient:
    conn = (
        f"DefaultEndpointsProtocol=https;AccountName={ACCOUNT};"
        f"AccountKey={_account_key()};EndpointSuffix=core.windows.net"
    )
    return BlobClient.from_connection_string(conn, CONTAINER, BLOB)


def download() -> None:
    c = _client()
    if not c.exists():
        print("Ingen katalog i blob än — hoppar (första körningen skapar den lokalt).")
        return
    with open(LOCAL, "wb") as f:
        f.write(c.download_blob().readall())
    print(f"Katalog nedladdad -> {LOCAL} ({LOCAL.stat().st_size} bytes)")


def upload() -> None:
    if not LOCAL.exists():
        raise SystemExit(f"Saknar {LOCAL} — inget att ladda upp.")
    c = _client()
    with open(LOCAL, "rb") as f:
        c.upload_blob(f, overwrite=True)
    print(f"Katalog uppladdad {LOCAL} ({LOCAL.stat().st_size} bytes) -> blob {BLOB}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    {"download": download, "upload": upload}.get(action, lambda: sys.exit(
        "Ange 'download' eller 'upload'"))()
