{#-
  Använd det custom schema-namnet (+schema) rakt av, utan target-prefix.
  Ger rena scheman: staging, mart — istället för main_staging osv.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
