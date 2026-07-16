-- Staging: en rad per tågpassage, med From/To och produkt/typ utplattade från
-- barntabellerna. Tiderna är redan TIMESTAMP WITH TIME ZONE (Europe/Stockholm).

with announcements as (
    select * from {{ source('raw', 'train_announcements') }}
),

-- From/To/produkt/typ är arrayer men i praktiken enkel-element (idx 0).
from_location as (
    select _dlt_parent_id, location_name
    from {{ source('raw', 'train_announcements__from_location') }}
    where _dlt_list_idx = 0
),

to_location as (
    select _dlt_parent_id, location_name
    from {{ source('raw', 'train_announcements__to_location') }}
    where _dlt_list_idx = 0
),

product as (
    select _dlt_parent_id, description as product_name
    from {{ source('raw', 'train_announcements__product_information') }}
    where _dlt_list_idx = 0
),

traffic as (
    select _dlt_parent_id, description as traffic_type
    from {{ source('raw', 'train_announcements__type_of_traffic') }}
    where _dlt_list_idx = 0
)

select
    a.advertised_train_ident        as train_ident,
    a.location_signature,
    a.activity_type,
    a.advertised                    as is_advertised,
    a.operator,
    a.train_owner,
    p.product_name,
    tr.traffic_type,
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
left join product       p on p._dlt_parent_id = a._dlt_id
left join traffic      tr on tr._dlt_parent_id = a._dlt_id
