{{ config(materialized='view') }}

with 

raw_memberships as (
    select * from {{ source('public', 'memberships') }}
)

select 
    cast(membership_id as varchar) as membership_id,
    cast(group_id as varchar) as team_id,
    cast(role_title as varchar) as role_title,
    cast(joined_at as timestamp) as joined_time,
    date(joined_time) as joined_date
from raw_memberships