"""dlt-källa för Trafikverkets TrainAnnouncement (Ystadbanan: Sea, Srp, Lmm).

Kör direkt (`python trainlake_source.py`) för att bara skriva ut några poster
och verifiera att API-anropet ger rätt data — INNAN destinationen kopplas på.
"""
from __future__ import annotations

import dlt
import requests

TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

# Verifierade stationssignaturer (mot TrainStation-API:t)
STATIONS = ["Sea", "Srp", "Lmm"]  # Svedala, Skurup, Lemmeströ

# Fält vi hämtar (INCLUDE i queryn)
_INCLUDES = [
    "ActivityType",
    "AdvertisedTrainIdent",
    "LocationSignature",
    "AdvertisedTimeAtLocation",
    "EstimatedTimeAtLocation",
    "TimeAtLocation",
    "ToLocation",
    "FromLocation",
    "TrackAtLocation",
    "Canceled",
]


def _build_query(api_key: str) -> str:
    """Bygg XML-request-bodyn. Fönster: -1h till +6h."""
    stations = "\n          ".join(
        f'<EQ name="LocationSignature" value="{s}" />' for s in STATIONS
    )
    includes = "\n    ".join(f"<INCLUDE>{f}</INCLUDE>" for f in _INCLUDES)
    return f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="TrainAnnouncement" schemaversion="1.9" orderby="AdvertisedTimeAtLocation">
    <FILTER>
      <AND>
        <OR>
          {stations}
        </OR>
        <GT name="AdvertisedTimeAtLocation" value="$dateadd(-01:00:00)" />
        <LT name="AdvertisedTimeAtLocation" value="$dateadd(06:00:00)" />
      </AND>
    </FILTER>
    {includes}
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
