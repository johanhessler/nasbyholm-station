---
title: Tåg per dygn
description: Antal tåg förbi Näsbyholm per driftdag och riktning
---

Antal distinkta tåg som passerar **Skurup** (proxy för Näsbyholm) per driftdag,
uppdelat på riktning.

```sql per_day
select
    operating_day,
    count(distinct train_ident) as n_trains,
    count(distinct case when direction = 'Mot Ystad/Simrishamn' then train_ident end) as mot_ystad,
    count(distinct case when direction = 'Mot Malmö/Helsingborg' then train_ident end) as mot_malmo
from trains.passages
where station_name = 'Skurup'
group by operating_day
order by operating_day
```

```sql avg_day
select round(avg(n_trains), 0) as snitt from ${per_day}
```

<BigValue data={avg_day} value=snitt title="Snitt tåg/dygn" fmt="#,##0"/>

```sql per_day_dir
select operating_day, 'Mot Ystad/Simrishamn' as riktning, mot_ystad as n_trains from ${per_day}
union all
select operating_day, 'Mot Malmö/Helsingborg' as riktning, mot_malmo as n_trains from ${per_day}
```

<BarChart
    data={per_day_dir}
    x=operating_day
    y=n_trains
    series=riktning
    title="Tåg per dygn och riktning"
    yAxisTitle="Antal tåg"
/>

<DataTable data={per_day} rows=all>
    <Column id=operating_day title="Driftdag" fmt="yyyy-mm-dd"/>
    <Column id=n_trains title="Totalt tåg"/>
    <Column id=mot_ystad title="Mot Ystad/Simrishamn"/>
    <Column id=mot_malmo title="Mot Malmö/Helsingborg"/>
</DataTable>
