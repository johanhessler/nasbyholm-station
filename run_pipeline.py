"""Kör dlt-pipelinen mot DuckLake (raw-schema).

    python run_pipeline.py                          # tågannonseringar, default-fönster
    python run_pipeline.py stations                 # stationsdimension (sällan)
    python run_pipeline.py all                      # båda

Parametriserat fönster (endast announcements) — för catch-up om en körning
missats. OBS: API:t behåller bara ~3 dygn, så äldre datum ger tomt:

    python run_pipeline.py --from 2026-07-14 --to 2026-07-16
    python run_pipeline.py --days-back 2

Destinationen (ducklake-katalog + Azure Blob) konfigureras via .dlt/config.toml
och .dlt/secrets.toml.
"""
import argparse

import dlt

import dlt_win_patch  # noqa: F401  — måste importeras före pipeline.run() (se modulen)
from trainlake_source import (
    train_announcements,
    train_stations,
    window_days_back,
    window_from_dates,
)


def run(what: str = "announcements", window: tuple[str, str] | None = None) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="trainlake",
        destination="ducklake",
        dataset_name="raw",
    )
    start, end = window if window else (None, None)
    ann = train_announcements(start=start, end=end)
    resources = {
        "announcements": [ann],
        "stations": [train_stations()],
        "all": [ann, train_stations()],
    }[what]
    info = pipeline.run(resources)
    print(info)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("what", nargs="?", default="announcements",
                   choices=["announcements", "stations", "all"],
                   help="vad som ska hämtas (default: announcements)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--days-back", type=int, metavar="N",
                   help="hämta N dygn bakåt t.o.m. imorgon (catch-up)")
    p.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD",
                   help="startdatum (inklusivt), kräver --to")
    p.add_argument("--to", dest="to_date", metavar="YYYY-MM-DD",
                   help="slutdatum (inklusivt), kräver --from")
    args = p.parse_args()

    if bool(args.from_date) != bool(args.to_date):
        p.error("--from och --to måste anges tillsammans")
    if args.from_date and args.days_back is not None:
        p.error("ange antingen --from/--to eller --days-back, inte båda")

    window = None
    if args.from_date:
        window = window_from_dates(args.from_date, args.to_date)
    elif args.days_back is not None:
        window = window_days_back(args.days_back)

    run(args.what, window)


if __name__ == "__main__":
    main()
