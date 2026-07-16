-- Staging: stationsdimension. Signatur -> namn (+ koordinater ur WGS84-punkten).

with stations as (
    select * from {{ source('raw', 'train_stations') }}
    where not deleted
)

select
    location_signature,
    advertised_location_name                                              as station_name,
    advertised                                                            as is_advertised,
    -- Geometry.WGS84 kommer som "POINT (lon lat)"
    try_cast(regexp_extract(geometry__wgs84, 'POINT \(([-0-9.]+) ', 1) as double)  as longitude,
    try_cast(regexp_extract(geometry__wgs84, ' ([-0-9.]+)\)', 1) as double)        as latitude
from stations
