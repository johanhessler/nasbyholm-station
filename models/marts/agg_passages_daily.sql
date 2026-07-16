-- Aggregat: passager per driftdag, station, riktning och tågslag.
-- Driver dygnsräkning och punktlighet i dashboarden.

with p as (
    select * from {{ ref('fct_train_passages') }}
)

select
    operating_day,
    location_signature,
    station_name,
    direction,
    train_type,
    count(distinct train_ident)                                   as n_trains,
    count(*)                                                      as n_passages,
    count(distinct case when canceled then train_ident end)       as n_cancelled,
    round(avg(delay_minutes), 1)                                  as avg_delay_min,
    -- Andel i tid (<= 5 min) bland passager som har en uppmätt/estimerad tid.
    round(avg(case when delay_minutes is not null
                   then (delay_minutes <= 5)::int end), 3)        as pct_on_time
from p
group by operating_day, location_signature, station_name, direction, train_type
