"""Kör dlt-pipelinen: hämta TrainAnnouncement och ladda in i DuckLake (raw-schema).

    python run_pipeline.py

Destinationen (ducklake-katalog + Azure Blob) konfigureras via .dlt/config.toml
och .dlt/secrets.toml.
"""
import dlt

import dlt_win_patch  # noqa: F401  — måste importeras före pipeline.run() (se modulen)
from trainlake_source import train_announcements


def run() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="trainlake",
        destination="ducklake",
        dataset_name="raw",
    )
    info = pipeline.run(train_announcements())
    print(info)


if __name__ == "__main__":
    run()
