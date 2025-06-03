{{ config(
    materialized='incremental', 
    unique_key=['event_id', 'responded_date'],
    
) }}

with 

stg_event_rsvps as (
    select * 
    from {{ ref('stg_event_rsvps') }}
    {% if is_incremental() %}
        where responded_date >= (select max(responded_date) from {{ this }})
    {% endif %}
)

select 
    -- DIMENSIONS
    event_rsvp.event_id,
    event_rsvp.responded_date,
    -- MEASURES
    sum(
        case when event_rsvp.rsvp_status_code = 0 then 1 else 0 end
    ) as num_unanswered_event_rsvps,
    sum(
        case when event_rsvp.rsvp_status_code = 1 then 1 else 0 end
    ) as num_accepted_event_rsvps,
    sum(
        case when event_rsvp.rsvp_status_code = 2 then 1 else 0 end
    ) as num_declined_event_rsvps,
    count(distinct
        case when event_rsvp.rsvp_status_code = 0 then event_rsvp.membership_id else null end
    ) as unique_members_with_unanswered_event_rsvps,
    count(distinct
        case when event_rsvp.rsvp_status_code = 1 then event_rsvp.membership_id else null end
    ) as unique_members_with_accepted_event_rsvps,
    count(distinct
        case when event_rsvp.rsvp_status_code = 2 then event_rsvp.membership_id else null end
    ) as unique_members_with_declined_event_rsvps
    
from stg_event_rsvps as event_rsvp
group by 
    event_rsvp.event_id,
    event_rsvp.responded_date