{{ config(materialized='view') }}

with 

raw_events as (
    select * from {{ source('public', 'events') }}
)

select 
    cast(event_id as varchar) as event_id,
    cast(team_id as varchar) as team_id,
    cast(event_start as timestamp) as event_start_time,
    cast(event_end as timestamp) as event_end_time,
    cast(latitude as float) as latitude,
    cast(longitude as float) as longitude,
    cast(created_at as timestamp) as created_time
from raw_events