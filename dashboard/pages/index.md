---
title: Näsbyholm station
description: Tåg som passerar huset på Ystadbanan
---

Näsbyholm rapporterar inte i Trafikverkets data, så vi mäter på grannstationen
**Skurup** (`Srp`) — närmaste annonserade station sydost om huset. Varje tåg som
passerar Näsbyholm passerar även Skurup.

```sql days
select distinct operating_day
from trains.passages
order by operating_day desc
```

<Dropdown data={days} name=day value=operating_day defaultValue={days[0]?.operating_day}>
    <DropdownOption value="%" valueLabel="Alla dygn"/>
</Dropdown>

```sql today_count
select
    count(distinct train_ident) as n_trains,
    count(distinct case when direction = 'Mot Ystad/Simrishamn' then train_ident end) as mot_ystad,
    count(distinct case when direction = 'Mot Malmö/Helsingborg' then train_ident end) as mot_malmo
from trains.passages
where station_name = 'Skurup'
  and operating_day::varchar like '${inputs.day.value}'
```

<BigValue data={today_count} value=n_trains title="Tåg förbi Näsbyholm" fmt="#,##0"/>
<BigValue data={today_count} value=mot_ystad title="Mot Ystad/Simrishamn" fmt="#,##0"/>
<BigValue data={today_count} value=mot_malmo title="Mot Malmö/Helsingborg" fmt="#,##0"/>

## Avgångstavla — Skurup

```sql board
select
    advertised_time,
    train_ident,
    direction,
    to_name as slutstation,
    track as spar,
    delay_minutes,
    canceled
from trains.passages
where station_name = 'Skurup'
  and activity_type = 'Avgang'
  and operating_day::varchar like '${inputs.day.value}'
order by advertised_time
```

<DataTable data={board} rows=all search=true>
    <Column id=advertised_time title="Tid" fmt="hh:mm"/>
    <Column id=train_ident title="Tåg"/>
    <Column id=direction title="Riktning"/>
    <Column id=slutstation title="Mot"/>
    <Column id=spar title="Spår" align=center/>
    <Column id=delay_minutes title="Försening (min)" align=center/>
    <Column id=canceled title="Inställt"/>
</DataTable>
