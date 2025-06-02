{{ config(materialized='view') }}

with 

raw_teams as (
    select * from {{ source('public', 'teams') }}
)

select 
    cast(team_id as varchar) as team_id,
    cast(team_activity as varchar) as activity,
    cast(country_code as varchar) as country_code,
    cast(created_at as timestamp) as created_time
from raw_teams