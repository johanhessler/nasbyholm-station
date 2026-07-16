-- Mart: utplattade tågpassager med stationsnamn (från dimensionen), riktning och försening.

with stg as (
    select * from {{ ref('stg_train_announcements') }}
),

stations as (
    select location_signature, station_name from {{ ref('stg_train_stations') }}
)

select
    a.train_ident,
    a.location_signature,
    station.station_name                             as station_name,
    a.activity_type,

    a.from_signature,
    from_st.station_name                             as from_name,
    a.to_signature,
    to_st.station_name                               as to_name,

    -- Riktning (2-vägs), härledd från destinationen. Alla ändpunkter ligger
    -- rent på var sin sida om stationerna Sea/Srp/Lmm.
    -- (NULL för Lemmeströ som saknar From/To i källan.)
    case
        when a.to_signature in ('Y', 'Si')  then 'Mot Ystad/Simrishamn'
        when a.to_signature in ('Hb', 'Kg') then 'Mot Malmö/Helsingborg'
    end                                              as direction,

    a.advertised_time,
    a.estimated_time,
    a.actual_time,
    coalesce(a.actual_time, a.estimated_time)        as effective_time,

    -- Försening i minuter (positiv = sen). Använder faktisk tid om den finns,
    -- annars estimat; NULL innan någon av dem satts.
    case
        when coalesce(a.actual_time, a.estimated_time) is not null
        then date_diff('minute', a.advertised_time, coalesce(a.actual_time, a.estimated_time))
    end                                              as delay_minutes,

    a.track,
    a.canceled
from stg a
left join stations station on station.location_signature = a.location_signature
left join stations from_st on from_st.location_signature = a.from_signature
left join stations to_st   on to_st.location_signature   = a.to_signature
