-- Täckningskontroll: flaggar signaturer som förekommer i passagerna (station,
-- from eller to) men saknar post i stationsdimensionen. Rader = saknade
-- signaturer → dags att bredda stationsladdningen (t.ex. tåg som vänt utanför Skåne).

with used as (
    select location_signature as signature from {{ ref('fct_train_passages') }}
    union
    select from_signature from {{ ref('fct_train_passages') }}
    union
    select to_signature from {{ ref('fct_train_passages') }}
)

select signature
from used
where signature is not null
  and signature not in (select location_signature from {{ ref('stg_train_stations') }})
