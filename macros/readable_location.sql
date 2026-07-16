{#-
  Översätt Trafikverkets stationssignaturer till läsbara ortnamn.
  Verifierade signaturer för Ystadbanan + ändpunkter.
-#}
{% macro readable_location(col) -%}
case {{ col }}
    when 'Hb'  then 'Helsingborg'
    when 'Kg'  then 'Kävlinge'
    when 'Sea' then 'Svedala'
    when 'Srp' then 'Skurup'
    when 'Lmm' then 'Lemmeströ'
    when 'Y'   then 'Ystad'
    when 'Si'  then 'Simrishamn'
    else {{ col }}
end
{%- endmacro %}
