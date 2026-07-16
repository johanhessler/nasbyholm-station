"""dlt-källa för Trafikverkets TrainAnnouncement (Ystadbanan: Sea, Srp, Lmm).

Kör direkt (`python trainlake_source.py`) för att bara skriva ut några poster
och verifiera att API-anropet ger rätt data — INNAN destinationen kopplas på.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import dlt
import requests

TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

# All tidtabell rapporteras i svensk tid; vi räknar dygnsgränser DST-korrekt.
TZ = ZoneInfo("Europe/Stockholm")

# Verifierade stationssignaturer (mot TrainStation-API:t)
STATIONS = ["Sea", "Srp", "Lmm"]  # Svedala, Skurup, Lemmeströ

# Vi utelämnar INCLUDE medvetet → API:t returnerar ALLA fält för
# TrainAnnouncement (EL-troget). dlt normaliserar array-fälten till barntabeller;
# vi formar det vi behöver i dbt. Merge-nyckeln nedan finns alltid med.


def _day_window() -> tuple[str, str]:
    """Absoluta dygnsgränser: igår 00:00 → imorgon 24:00 (3 kalenderdygn).

    Halvöppet intervall [start, end). Brett + överlappande så en missad
    körning läker sig själv; merge-nyckeln dedupar överlappet.
    """
    today = datetime.now(TZ).date()
    start = datetime.combine(today - timedelta(days=1), time.min, TZ)  # igår 00:00
    end = datetime.combine(today + timedelta(days=2), time.min, TZ)    # imorgon 24:00
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


def _build_query(api_key: str) -> str:
    """Bygg XML-request-bodyn med absoluta dygnsgränser (svensk tid). Ingen
    INCLUDE → alla fält returneras."""
    stations = "\n          ".join(
        f'<EQ name="LocationSignature" value="{s}" />' for s in STATIONS
    )
    start, end = _day_window()
    return f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="TrainAnnouncement" schemaversion="1.9" orderby="AdvertisedTimeAtLocation">
    <FILTER>
      <AND>
        <OR>
          {stations}
        </OR>
        <GTE name="AdvertisedTimeAtLocation" value="{start}" />
        <LT name="AdvertisedTimeAtLocation" value="{end}" />
      </AND>
    </FILTER>
  </QUERY>
</REQUEST>"""


def _post(body: str) -> dict:
    """POST:a en XML-query och returnera första RESULT-objektet."""
    resp = requests.post(
        TRAFIKVERKET_URL,
        data=body.encode("utf-8"),
        headers={"Content-Type": "text/xml"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["RESPONSE"]["RESULT"][0]


@dlt.resource(
    name="train_announcements",
    write_disposition="merge",
    primary_key=[
        "advertised_train_ident",
        "location_signature",
        "activity_type",
        "advertised_time_at_location",
    ],
)
def train_announcements(api_key: str = dlt.secrets.value):
    """Yield:ar en post per tågannonsering. dlt normaliserar From/To-arrayerna
    till barntabeller automatiskt."""
    result = _post(_build_query(api_key))
    yield from result.get("TrainAnnouncement", [])


# Skåne = län 12. Statisk dimension — körs sällan (namn ändras nästan aldrig).
SKANE_COUNTY_NO = "12"


@dlt.resource(
    name="train_stations",
    write_disposition="merge",
    primary_key=["location_signature"],
)
def train_stations(api_key: str = dlt.secrets.value):
    """Stationsdimension: signatur -> namn (+ koordinater), alla stationer i Skåne.
    Ersätter hårdkodade namn — nya ändpunkter får namn automatiskt."""
    body = f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="TrainStation" schemaversion="1.0">
    <FILTER>
      <EQ name="CountyNo" value="{SKANE_COUNTY_NO}" />
    </FILTER>
    <INCLUDE>LocationSignature</INCLUDE>
    <INCLUDE>AdvertisedLocationName</INCLUDE>
    <INCLUDE>Geometry.WGS84</INCLUDE>
    <INCLUDE>Advertised</INCLUDE>
    <INCLUDE>Deleted</INCLUDE>
  </QUERY>
</REQUEST>"""
    result = _post(body)
    yield from result.get("TrainStation", [])


if __name__ == "__main__":
    # Snabbtest: skriv ut antal + de första posterna, utan att ladda någonstans.
    import json

    records = list(train_announcements())
    print(f"Hämtade {len(records)} poster\n")
    for rec in records[:5]:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        print("-" * 40)
