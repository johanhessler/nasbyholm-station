# Överlämning: Trainlake-pipeline (hobbyprojekt)

Kontext för Claude Code att fortsätta ett projekt som startats i Claude Desktop. Läs hela detta dokument först — det innehåller alla beslut, verifierade fakta och nästa steg.

## Vad projektet gör

Johan bor i ett gammalt stationshus vid Malmö–Ystad-järnvägen (Ystadbanan) och vill veta vilka tåg som passerar. Projektet hämtar tågdata från Trafikverkets öppna API, lagrar i en DuckLake (DuckDB-katalog + Parquet i Azure Blob), och ska så småningom visualiseras. Hobbyprojekt — **får kosta minimalt**, helst inget som rullar dygnet runt.

## Arkitektur (beslutad)

```
Trafikverket API (TrainAnnouncement, XML in / JSON ut)
        │  dlt (ducklake-destination, auto-normalisering)
        ▼
DuckLake  (raw-schema)
  - katalog: lokal DuckDB-fil (trains_catalog.ducklake)
  - storage: Azure Blob, container "trainlake", data_path abfs://trainlake/lake/
        │  dbt (plain SQL, snake_case) — staging + mart
        ▼
fct_train_passages  (utplattad, riktning, förseningsberäkning)
        │
        ▼
Visualisering (senare — DuckDB UI ad hoc nu; MotherDuck Dive eller Streamlit/Evidence senare)
```

Framtida steg: paketera hämtningen i en Azure Function (Timer + HTTP-trigger) för schemalagd + on-demand-hämtning. Ej börjat.

## Miljö

- Windows, **inget WSL** (kör nativt på Windows)
- Git Bash som default shell i VS Code:s integrerade terminal
- Projektmapp önskas under `C:\dev\` (utanför OneDrive — undvik sync/fillås)
- Python venv i `.venv`
- dbt Power User-extension finns i VS Code
- Föredrar plain SQL framför dbt-makron; snake_case genomgående
- Föredrar steg-för-steg, inte stora block på en gång

## Verifierade fakta (viktigt — dessa är kontrollerade mot verkligheten)

**Stationssignaturer (verifierade mot TrainStation-API:t):**
- Svedala = `Sea`
- Skurup = `Srp`
- Lemmeströ = `Lmm` (driftplats utan persontrafik — se nedan)

**Trafikverket API:**
- Endpoint: `https://api.trafikinfo.trafikverket.se/v2/data.json` (JSON ut)
- Request-body är ALLTID XML (deras query-språk). Response-format styrs av `.json`/`.xml`-suffix.
- Content-Type: `text/xml`
- Objekt: `TrainAnnouncement`, schemaversion `1.9`
- Johan har en fungerande API-nyckel (lagras säkert, INTE i git — använd .env / dlt secrets)

**Datastruktur (bekräftad från riktigt svar):**
- Varje passage har `ActivityType` (`Avgang`/`Ankomst`), `AdvertisedTrainIdent`, `LocationSignature`, `AdvertisedTimeAtLocation`, ofta `EstimatedTimeAtLocation`, `TimeAtLocation`, `TrackAtLocation`, `Canceled`.
- `FromLocation` och `ToLocation` är **arrayer av objekt**: `[{"LocationName":"Si","Priority":1,"Order":0}]`. dlt normaliserar dessa till barntabeller automatiskt — det är önskat (EL troget, forma med dbt sedan).
- **Lemmeströ (Lmm) rapporterar magert**: bara ActivityType, tid, tågnummer, Canceled, signatur, TimeAtLocation. INGEN From/To/Estimated. Väntat — driftplats utan persontrafik.
- `EstimatedTimeAtLocation` är glest — sätts först närmare avgång. Kolumner måste tillåta NULL.
- Riktning avgörs via From/To (`Y`=Ystad, `Si`=Simrishamn, `Hb`, `Kg` m.fl.), INTE via tågnummer-paritet.

**Merge-nyckel (för dedup vid upprepade hämtningar):**
`advertised_train_ident + location_signature + activity_type + advertised_time_at_location`

## Status just nu — var vi är

KLART:
- DuckDB CLI v1.5.4 installerat på Windows (via winget-sökväg men v1.5.4-binär)
- Extensions `ui`, `ducklake`, `azure` installerade och cachade lokalt
  - OBS: VPN blockerar `http`-vägen till extensions.duckdb.org (503-fel). Installera extensions med VPN NEDKOPPLAD. När cachade fungerar de med VPN på.
- DuckDB UI fungerar (`duckdb -ui` → localhost:4213)
- DuckLake uppsatt och testad med påhittad data:
  - `create secret azure_trains (type azure, connection_string '...')`
  - `attach 'ducklake:trains_catalog.ducklake' as trainlake (data_path 'abfs://trainlake/lake/')`
  - Azure-container `trainlake` skapad (behövdes manuellt — 404 "filesystem does not exist" tills den fanns)
  - Testdata skrevs, verifierades, flushades till Parquet (`call ducklake_flush_inlined_data('trainlake')`) — låg först inlinad i katalogen (data inlining), file_count=0 tills flush
  - Auth: connection string (kan bytas till managed identity när det körs i Azure Function senare)
- API verifierat: både TrainStation-uppslag och TrainAnnouncement-hämtning ger korrekt data

PÅBÖRJAT (nästa konkreta steg):
- dlt-pipeline lokalt. Johan skulle just skapa projektmappen och installera dlt när överlämningen skedde.

## NÄSTA STEG (fortsätt här)

### Steg 1 — projektuppsättning (om ej klart)
```bash
mkdir C:/dev/trainlake-pipeline && cd C:/dev/trainlake-pipeline
python -m venv .venv
source .venv/Scripts/activate   # git bash-syntax på Windows
pip install "dlt[duckdb]" requests
dlt --version
```

### Steg 2 — bygg dlt-pipelinen
- dlt har en INBYGGD `ducklake`-destination (verifierat, aktuellt). Använd den — hacka INTE in egen duckdb-connection.
- Destinationen konfigureras via `secrets.toml`/`config.toml`: catalog = DuckDB-fil (`trains_catalog.ducklake`), storage = Azure Blob (`abfs://trainlake/lake/`).
- VIKTIGT: peka dlt på SAMMA katalogfil och SAMMA container som den redan uppsatta `trainlake`, så allt landar i samma DuckLake. Ta reda på var `trains_catalog.ducklake` ligger på disk (mappen där Johan körde `duckdb -ui`).
- Ladda till ett `raw`-schema (dataset_name t.ex. `raw`).
- Källa: en `@dlt.resource` som POST:ar XML-bodyn (se nedan) till API:t, parsar JSON-svaret, och yield:ar posterna ur `RESPONSE.RESULT[0].TrainAnnouncement`. Låt dlt normalisera From/To-arrayerna automatiskt.
- Write disposition: `merge` med primary_key motsvarande merge-nyckeln ovan.
- API-nyckeln via dlt secrets / env-variabel, ALDRIG hårdkodad.
- Ta det i småbitar: få API-anropet att yield:a rätt data FÖRST (skriv ut några poster), koppla sedan på ducklake-destinationen.

XML-body (byt nyckel via secret; fönster -1h till +6h):
```xml
<REQUEST>
  <LOGIN authenticationkey="{key}" />
  <QUERY objecttype="TrainAnnouncement" schemaversion="1.9" orderby="AdvertisedTimeAtLocation">
    <FILTER>
      <AND>
        <OR>
          <EQ name="LocationSignature" value="Sea" />
          <EQ name="LocationSignature" value="Srp" />
          <EQ name="LocationSignature" value="Lmm" />
        </OR>
        <GT name="AdvertisedTimeAtLocation" value="$dateadd(-01:00:00)" />
        <LT name="AdvertisedTimeAtLocation" value="$dateadd(06:00:00)" />
      </AND>
    </FILTER>
    <INCLUDE>ActivityType</INCLUDE>
    <INCLUDE>AdvertisedTrainIdent</INCLUDE>
    <INCLUDE>LocationSignature</INCLUDE>
    <INCLUDE>AdvertisedTimeAtLocation</INCLUDE>
    <INCLUDE>EstimatedTimeAtLocation</INCLUDE>
    <INCLUDE>TimeAtLocation</INCLUDE>
    <INCLUDE>ToLocation</INCLUDE>
    <INCLUDE>FromLocation</INCLUDE>
    <INCLUDE>TrackAtLocation</INCLUDE>
    <INCLUDE>Canceled</INCLUDE>
  </QUERY>
</REQUEST>
```

### Steg 3 — dbt ovanpå (plain SQL, snake_case)
- staging-modell: platta ut From/To barntabeller till enkla `from_location`/`to_location`-kolumner, normalisera tidszoner.
- mart: `fct_train_passages` med riktning (härledd från from/to) och förseningsberäkning (estimated/actual minus advertised).
- dbt-duckdb-adaptern pekar på samma DuckLake-katalog i `profiles.yml`.

### Steg 4 — Azure Function (senare)
- Timer-trigger (t.ex. var 5:e min, 05–23) + HTTP-trigger (on-demand-koll mitt på dagen).
- Compute ryms i Functions gratis-grant. Byt connection string mot managed identity där.
- Överväg `ducklake_merge_adjacent_files` / flush med jämna mellanrum (small files problem vid frekventa skrivningar).

## Pollningsfrekvens (beslutat resonemang)
- Tidtabell: 1 gång/dag räcker (statisk per dag).
- Realtid (förseningar/inställda): var 5:e min gott och väl. Ystadbanan död på natten → schemalägg 05–23.

## Fallgropar att komma ihåg
- VPN blockerar extension-nedladdning (http 503). Koppla ner vid install.
- DuckLake data inlining: små skrivningar syns inte som Parquet-filer förrän flush. Inte ett fel.
- Azure "filesystem does not exist" = containern finns inte. Skapa den.
- `abfs://` förutsätter ev. HNS aktiverat; annars `az://`. (Fungerade med abfs:// hittills.)
- Kvalificera skrivningar i UI:t med `trainlake.main.` — `use` fastnar inte alltid mellan celler.
- Hemligheter (API-nyckel, Azure connection string) ALDRIG i git.
```
