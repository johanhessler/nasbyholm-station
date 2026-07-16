"""Kör dlt-pipelinen mot DuckLake (raw-schema).

    python run_pipeline.py                # tågannonseringar (frekvent)
    python run_pipeline.py stations       # stationsdimension (sällan)
    python run_pipeline.py all            # båda

Destinationen (ducklake-katalog + Azure Blob) konfigureras via .dlt/config.toml
och .dlt/secrets.toml.
"""
import sys

import dlt

import dlt_win_patch  # noqa: F401  — måste importeras före pipeline.run() (se modulen)
from trainlake_source import train_announcements, train_stations


def run(what: str = "announcements") -> None:
    pipeline = dlt.pipeline(
        pipeline_name="trainlake",
        destination="ducklake",
        dataset_name="raw",
    )
    resources = {
        "announcements": [train_announcements()],
        "stations": [train_stations()],
        "all": [train_announcements(), train_stations()],
    }[what]
    info = pipeline.run(resources)
    print(info)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "announcements")
