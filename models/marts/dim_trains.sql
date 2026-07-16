-- Dimension: ett tåg per driftdag, med härlett tågslag.
-- Byggs från de annonserade posterna (som har produkt/operatör). Lemmeströs
-- magra poster saknar metadata men delar train_ident + dag → kan berikas
-- härifrån i fct.

with rich as (
    select
        train_ident,
        advertised_time::date as operating_day,
        operator,
        train_owner,
        product_name,
        traffic_type
    from {{ ref('stg_train_announcements') }}
    where product_name is not null or operator is not null
),

-- Garantera en rad per (tåg, dag) så joinen i fct förblir 1:1.
per_train as (
    select
        train_ident,
        operating_day,
        any_value(operator)     as operator,
        any_value(train_owner)  as train_owner,
        any_value(product_name) as product_name,
        any_value(traffic_type) as traffic_type
    from rich
    group by train_ident, operating_day
)

select
    train_ident,
    operating_day,
    operator,
    train_owner,
    product_name,
    traffic_type,
    case
        when product_name ilike '%pågatåg%'                          then 'Pågatåg'
        when product_name ilike '%öresund%'                          then 'Öresundståg'
        when traffic_type ilike '%gods%' or operator ilike '%cargo%' then 'Godståg'
        when product_name is not null                                then product_name
        else 'Övrigt'
    end as train_type
from per_train
