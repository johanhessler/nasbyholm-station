-- Mart: utplattade tågpassager med läsbara ortnamn, riktning och försening.

with stg as (
    select * from {{ ref('stg_train_announcements') }}
)

select
    train_ident,
    location_signature,
    {{ readable_location('location_signature') }}   as station_name,
    activity_type,

    from_signature,
    {{ readable_location('from_signature') }}        as from_name,
    to_signature,
    {{ readable_location('to_signature') }}          as to_name,

    -- Riktning (2-vägs), härledd från destinationen. Alla ändpunkter ligger
    -- rent på var sin sida om stationerna Sea/Srp/Lmm.
    -- (NULL för Lemmeströ som saknar From/To i källan.)
    case
        when to_signature in ('Y', 'Si')  then 'Mot Ystad/Simrishamn'
        when to_signature in ('Hb', 'Kg') then 'Mot Malmö/Helsingborg'
    end                                              as direction,

    advertised_time,
    estimated_time,
    actual_time,
    coalesce(actual_time, estimated_time)            as effective_time,

    -- Försening i minuter (positiv = sen). Använder faktisk tid om den finns,
    -- annars estimat; NULL innan någon av dem satts.
    case
        when coalesce(actual_time, estimated_time) is not null
        then date_diff('minute', advertised_time, coalesce(actual_time, estimated_time))
    end                                              as delay_minutes,

    track,
    canceled
from stg
