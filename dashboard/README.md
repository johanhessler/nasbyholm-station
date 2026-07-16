# Dashboard (Evidence)

Lokal Evidence-dashboard som visualiserar tågpassagerna förbi Näsbyholm.

## Datakälla

Läser **enbart** den lokala filen `../reports/trains.duckdb` (se
`sources/trains/connection.yaml`). Ingen Azure, inga secrets, ingen DuckLake-attach
i Node-lagret — filen produceras av `publish_reports.py`.

Käll-tabeller (varje `.sql` i `sources/trains/` blir en tabell):
- `trains.passages` → `fct_train_passages`
- `trains.daily` → `agg_passages_daily`

## Sidor

- `/` **Näsbyholm station** — avgångstavla från Skurup + dygnssiffror
- `/tag-per-dygn` — antal tåg/dygn per riktning
- `/punktlighet` — andel i tid, snittförsening, förseningsfördelning

Alla siffror räknas på **Skurup** (`Srp`) som proxy för Näsbyholm — grannstationen
sydost om huset med annonserad trafik. Lemmeströ undviks (magra, opålitliga poster).

## Köra

Engångs: `npm install`

Utveckla lokalt:
```bash
npm run dev        # http://localhost:3000
```

Statisk build:
```bash
npm run build      # -> build/
```

## Fullt dygnsflöde

Kör från projektroten (uppdaterar datat dashboarden läser):

```bash
python run_pipeline.py          # 1. hämta från Trafikverket -> DuckLake
dbt build --profiles-dir .      # 2. staging + mart
python publish_reports.py       # 3. publicera -> reports/trains.duckdb
```

Efter steg 3 visar `npm run dev` / `npm run build` det nya datat automatiskt
(kör om `npm run sources` om en dev-server redan står och du vill tvinga omläsning).
