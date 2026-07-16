-- Staging: en rad per tågpassage, med From/To utplattade från barntabellerna.
-- Tiderna är redan TIMESTAMP WITH TIME ZONE (Europe/Stockholm) från källan.

with announcements as (
    select * from {{ source('raw', 'train_announcements') }}
),

-- From/To är arrayer men i praktiken enkel-element (prio 1, order 0).
-- Vi tar första elementet (_dlt_list_idx = 0).
from_location as (
    select _dlt_parent_id, location_name
    from {{ source('raw', 'train_announcements__from_location') }}
    where _dlt_list_idx = 0
),

to_location as (
    select _dlt_parent_id, location_name
    from {{ source('raw', 'train_announcements__to_location') }}
    where _dlt_list_idx = 0
)

select
    a.advertised_train_ident        as train_ident,
    a.location_signature,
    a.activity_type,
    f.location_name                 as from_signature,
    t.location_name                 as to_signature,
    a.advertised_time_at_location   as advertised_time,
    a.estimated_time_at_location    as estimated_time,
    a.time_at_location              as actual_time,
    a.track_at_location             as track,
    a.canceled
from announcements a
left join from_location f on f._dlt_parent_id = a._dlt_id
left join to_location   t on t._dlt_parent_id = a._dlt_id
