---
title: Punktlighet
description: Förseningar och andel i tid vid Skurup
---

Punktlighet mätt på **Skurup**. Ett tåg räknas som i tid om det är högst 5 minuter
sent. Bara passager med en uppmätt eller estimerad tid ingår.

```sql punctuality
select
    operating_day,
    count(*) filter (where delay_minutes is not null) as n_matta,
    round(avg(delay_minutes), 1) as snitt_forsening,
    round(avg((delay_minutes <= 5)::int) filter (where delay_minutes is not null), 3) as andel_i_tid
from trains.passages
where station_name = 'Skurup'
group by operating_day
order by operating_day
```

```sql overall
select
    round(avg(delay_minutes), 1) as snitt_forsening,
    round(avg((delay_minutes <= 5)::int), 3) as andel_i_tid,
    max(delay_minutes) as varsta_forsening
from trains.passages
where station_name = 'Skurup' and delay_minutes is not null
```

<BigValue data={overall} value=andel_i_tid title="Andel i tid" fmt="0%"/>
<BigValue data={overall} value=snitt_forsening title="Snittförsening (min)" fmt="#,##0.0"/>
<BigValue data={overall} value=varsta_forsening title="Värsta försening (min)" fmt="#,##0"/>

<LineChart
    data={punctuality}
    x=operating_day
    y=andel_i_tid
    title="Andel i tid per dygn"
    yAxisTitle="Andel i tid"
    yFmt="0%"
    yMax=1
/>

## Förseningsfördelning

```sql delay_dist
select
    case
        when delay_minutes <= 0 then 'I tid / före'
        when delay_minutes <= 5 then '1–5 min'
        when delay_minutes <= 10 then '6–10 min'
        else '> 10 min'
    end as intervall,
    count(*) as n
from trains.passages
where station_name = 'Skurup' and delay_minutes is not null
group by intervall
```

<BarChart
    data={delay_dist}
    x=intervall
    y=n
    title="Passager per förseningsintervall"
    yAxisTitle="Antal passager"
    sort=false
/>

<DataTable data={punctuality} rows=all>
    <Column id=operating_day title="Driftdag" fmt="yyyy-mm-dd"/>
    <Column id=n_matta title="Mätta passager"/>
    <Column id=snitt_forsening title="Snittförsening (min)"/>
    <Column id=andel_i_tid title="Andel i tid" fmt="0%"/>
</DataTable>
