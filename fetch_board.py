"""Lättviktig, timvis avgångstavla — hämtar direkt från Trafikverket.

Fristående från den tunga historik-pipelinen (dlt/DuckLake/dbt). Kör varje
timme och gör bara två API-anrop (Skurup i ett smalt fönster + stationsnamn),
skriver departures.json och publicerar den till data-grenen. Mobiltavlan hämtar
filen klientsidan (raw.githubusercontent, CORS-öppen).

Enda beroendet är `requests` — medvetet ingen dlt/duckdb här. Riktnings- och
tågslagslogiken speglar mart-modellerna (fct_train_passages / dim_trains) så att
tavlan visar samma sak som dashboarden.
"""
import datetime as dt
import json
import os
import pathlib
import tomllib
from zoneinfo import ZoneInfo

import requests

TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
TZ = ZoneInfo("Europe/Stockholm")

STATION_SIGNATURE = "Srp"      # Skurup — Näsbyholm-proxy
STATION_NAME = "Skurup"
SKANE_COUNTY_NO = "12"         # samma dimension som train_stations-resursen
WINDOW_BACK_HOURS = 2          # visas i klienten (filtreras mot besökarens klocka)
WINDOW_FWD_HOURS = 4
OUT = pathlib.Path("departures.json")


def _api_key() -> str:
    key = os.environ.get("TRAFIKVERKET_API_KEY")
    if key:
        return key
    with open(".dlt/secrets.toml", "rb") as f:
        return tomllib.load(f)["sources"]["trainlake_source"]["api_key"]


def _post(body: str) -> dict:
    resp = requests.post(
        TRAFIKVERKET_URL,
        data=body.encode("utf-8"),
        headers={"Content-Type": "text/xml"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["RESPONSE"]["RESULT"][0]


def _window() -> tuple[str, str]:
    # Generöst fönster (nu −3h … +8h) så klientens exakta −2/+4 täcks även när
    # datan hunnit bli en timme gammal.
    now = dt.datetime.now(TZ)
    start = now - dt.timedelta(hours=3)
    end = now + dt.timedelta(hours=8)
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


def _announcements(api_key: str, start: str, end: str) -> list[dict]:
    body = f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="TrainAnnouncement" schemaversion="1.9" orderby="AdvertisedTimeAtLocation">
    <FILTER>
      <AND>
        <EQ name="LocationSignature" value="{STATION_SIGNATURE}" />
        <EQ name="ActivityType" value="Avgang" />
        <GTE name="AdvertisedTimeAtLocation" value="{start}" />
        <LT name="AdvertisedTimeAtLocation" value="{end}" />
      </AND>
    </FILTER>
  </QUERY>
</REQUEST>"""
    return _post(body).get("TrainAnnouncement", [])


def _station_names(api_key: str) -> dict[str, str]:
    body = f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="TrainStation" schemaversion="1.0">
    <FILTER><EQ name="CountyNo" value="{SKANE_COUNTY_NO}" /></FILTER>
    <INCLUDE>LocationSignature</INCLUDE>
    <INCLUDE>AdvertisedLocationName</INCLUDE>
  </QUERY>
</REQUEST>"""
    rows = _post(body).get("TrainStation", [])
    return {r["LocationSignature"]: r.get("AdvertisedLocationName") for r in rows}


def _to_epoch(s: str | None) -> int | None:
    # Trafikverkets tider är ISO8601 med offset (t.ex. ...+02:00).
    return int(dt.datetime.fromisoformat(s).timestamp()) if s else None


def _direction(to_sig: str | None) -> str | None:
    # Spegel av fct_train_passages: härledd från destinationssignaturen.
    if to_sig in ("Y", "Si"):
        return "Mot Ystad/Simrishamn"
    if to_sig in ("Hb", "Kg"):
        return "Mot Malmö/Helsingborg"
    return None


def _train_type(product: str | None, traffic: str | None, operator: str | None) -> str:
    # Spegel av dim_trains.train_type.
    p, t, o = (product or "").lower(), (traffic or "").lower(), (operator or "").lower()
    if "pågatåg" in p:
        return "Pågatåg"
    if "öresund" in p:
        return "Öresundståg"
    if "gods" in t or "cargo" in o:
        return "Godståg"
    return product or "Övrigt"


def main() -> None:
    api_key = _api_key()
    start, end = _window()
    anns = _announcements(api_key, start, end)
    names = _station_names(api_key)

    deps = []
    for a in anns:
        to = a.get("ToLocation") or []
        to_sig = to[0].get("LocationName") if to else None
        direction = _direction(to_sig)
        if direction is None:
            continue  # tavlan grupperar på riktning; hoppa okända
        product = (a.get("ProductInformation") or [{}])[0].get("Description")
        traffic = (a.get("TypeOfTraffic") or [{}])[0].get("Description")

        adv = _to_epoch(a.get("AdvertisedTimeAtLocation"))
        eff = (_to_epoch(a.get("TimeAtLocation"))
               or _to_epoch(a.get("EstimatedTimeAtLocation"))
               or adv)
        delay = round((eff - adv) / 60) if (adv and eff) else None

        deps.append({
            "train_ident": a.get("AdvertisedTrainIdent"),
            "direction": direction,
            "train_type": _train_type(product, traffic, a.get("Operator")),
            "to_name": names.get(to_sig, to_sig),
            "track": a.get("TrackAtLocation"),
            "canceled": bool(a.get("Canceled")),
            "delay_minutes": delay or None,   # 0 = i tid → ingen badge
            "advertised_epoch": adv,
            "effective_epoch": eff,
        })
    deps.sort(key=lambda d: d["advertised_epoch"] or 0)

    payload = {
        "generated_epoch": int(dt.datetime.now(dt.timezone.utc).timestamp()),
        "station": STATION_NAME,
        "window_back_hours": WINDOW_BACK_HOURS,
        "window_fwd_hours": WINDOW_FWD_HOURS,
        "departures": deps,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Klart -> {OUT} ({len(deps)} avgångar i fönstret {start} … {end})")


if __name__ == "__main__":
    main()
