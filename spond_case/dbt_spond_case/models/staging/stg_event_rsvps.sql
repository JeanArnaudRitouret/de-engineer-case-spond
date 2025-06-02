{{ config(materialized='view') }}

with 

raw_event_rsvps as (
    select * from {{ source('public', 'event_rsvps') }}
)

select 
    cast(event_rsvp_id as varchar) as event_rsvp_id,
    cast(event_id as varchar) as event_id,
    cast(membership_id as varchar) as membership_id,
    cast(rsvp_status as integer) as rsvp_status_code,
    cast(responded_at as timestamp) as responded_time,
    date(responded_time) as responded_date
from raw_event_rsvps