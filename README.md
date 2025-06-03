# Hot To Set Up

This project uses:
- `pyenv` to manage python versions (the local version set for this project is 3.13)
- `Poetry` to manage dependencies. Run `poetry install` to install the dependencies.
- `direnv` for variables, the file `.env.template` is given as a model for required variables
    - copy paste the content into a `.env` or `.envrc` file and fill it with your own values


# Tech choices

### PostgreSQL
As per the case, I have used PostgreSQL as the source database. I have developed a script to upload the data from the csv files to the postgres database outside of the porject directory, since it was not required by the case but make it easier to replicate the behaviour of an actual production application.
- in order to replicate, run `poetry run python -m spond_case.upload.upload_to_postgres`


### AWS DMS (PostgreSQL -> Redshift Serverless)
Data has been loaded from PostgreSQL to Redshift Serverless using AWS Data Migration Service (DMS). This is a quick load migration, no validation happens yet at this stage.
here's how to replicate:
- Set up a Migration DMS Project which indludes creating 2 data providers, one for PostgreSQL (Source) and one for Redshift Serverless (Target). In the process, you also need to set up a replication Instance. All these should be in the same VPC security group as the source and target.
- Set up 2 endpoints, one for the source and one for the target. You can test that the connections are working properly by running Test conncetions on the UI. 
    - When setting up the source endpoint, it's important to follow these instructions https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.PostgreSQL.html#CHAP_Source.PostgreSQL.Endpoint
    - When setting up the target endpoint, it's important to follow these instructions https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.Redshift.html#CHAP_Target.Redshift.RSServerless 
        - Documentation is unclear on the following point: it is needed to create a IAM policy role specifically named `dms-access-for-endpoint` with a trusted entity of Redshift to be able to attach it to the Redshift Serverless Namespace, in order for the connection to work.
- Once the project, replication instance, data providers and endpoints have been set up 
    - run the script `poetry run python -m spond_case.ingestion.migrate_postgres_to_redshift`  in order to create a databbase migration task and start it until the data is fully loaded and a confirmation is received
    - This will start the migration from all tables in postgres into redshift
- For this project, a simple full load is enough to migrate the data. 
    - However in a production-grade pipeline, I would have used the change data capture (CDC) mode whiwh would capture ongoing changes after the initial migration (as new rows) in order to keep the data sync and to capture a more precise time of changes if we want to build a SCD type 2 table.


### Amazon Redshift Serverless
- I used only Redshift Serverless for both staging and transformed layers, since:
    - it makes the pipleline simpler to set up and manage
    - it removes cost from other services and you pay only what you use
    - it has a good performance for analytics queries
    - it can auto-scale compute and concurrency
- In production, I might consider a raw data lake in S3 
    - it would ensure immutable records useful for data recovery
    - it would separate the ingestion process from the transformation process
    - it offers one place to also potentially non-structured data or from other data sources


### DBT
Transformations from staging and further layers are run with dbt. Validation tests for the staging layer and further layers are also run with dbt.

Here's how to run the dbt models/tests:
- Variables set in the `spond_case/dbt_spond_case/profiles.yml` should be the same environment variables set in the `.env`/`.envrc` file and used in `settings.py`
- Go into the `spond_case/dbt_spond_case` directory
- Run the models with full refresh the first time `poetry run dbt run --full-refresh`
- Run the models with incremental refresh `poetry run dbt run`
- Run the tests with `poetry run dbt test`




# Data Modelling

## Design choices
- Staging layer is a 1-1 copy of the source data. Only some minor transformations like renaming or casting, models are materialized as view to keep the warehouse lean
- I am running data validation tests on fields on staging to ensure foreign keys exist, data types are correct, timestamp can be converted correctly, data isn't null or duplicated when it shouldn't be
- I am running a few tests on the serve layer to ensure the data is correct and to check for potential data issues. More custom tests could be run to verify that numbers add up, especially compared to other serve models.


## Analytics Requirements
2 business questions can be easily answered within the same reporting table, which I have created:
- **RSVP summary:**: can be answered through a reporting table for event_rsvps (`rbt_event_rsvps_daily`), by counting distinct members for different status codes
- **Attendance rate:** can be answered with the same reporting table for event_rsvps (`rbt_event_rsvps_daily`), by suming the event_rsvps for different status codes and dividing
- `rbt_event_rsvps_daily` is materialized as incremental, in order to reduce the running costs. We query the data including from the previous run in case some data was added since, we could extend the backfill to previous runs if there is a risk that historicaldata is modified after the initial migration.

2 question could be answered with the previous table and some transformations or by creating its own table to reduce complexity:
- **Events hosted per region:** can be answered with the same reporting table for event_rsvps (`rbt_event_rsvps_daily`) with a previous transformation to get the region of each event, done either in an intm_ table or by creating a dim_events table if that information can be re-used.
- **New vs. returning members**: 
    - we could add a level of aggregation which would be member_id and compare the week of event_rsvp of the member with the week of joining
    - alternatively, we could create a separate table where for each member, we could aggregate each week where this member had an activity like joining or having an event_rsvp accepted or declined, and compare to the joining week to know if they were joining or returning. Especially useful if we are interested in more activities than just event_rsvp. 

1 question would require a bit of transformation before to be fully answered:
- **Daily active teams:** I assume that a team is considered active on a given date if it hosts an event whose start and end times fall within that date. To achieve this, it is necessary to join with a date spine and create a model at a daily granularity.
    - It would be more difficult right now to answer: *How many distinct teams updated events each day?* since we only have a timestamp for the creation of the event, not the update. 
        - It would be possible to create a snapshot table of the events that would check when a column has changed value and which would be keep both the previous version of the row and the new version, and the time of the detection of the change.
            - This is NOT my favourite solution, because the valid_from / valid_to timestamps would depend on the time when the model is run. Moreover snapshot are hard to maintain and data can be lost.
            - Instead, I would prefer to use the CDC from AWS DMS to keep track of changes and their timestamp, in order to build a SCD type 2 table upstream. The sync would happen nearly in real-time and the source data wouldn't have to be approximately recreated by a snapshot. 
            - Ideally, change data could be generated directly from the source and already stored as such in postgres if this is strategic for the business. This would be the best solution in terms of data quality. Storage and tracking of data would be probably the most expensive in that case.


## Data quality issues
- `memberships` table seems to be missing a member_id column, as I would understand membership as a member joining a team?
- Multiple tests are failing that shouldbe investigated to see if the source data is missing or if the test is to be removed:

```
19:17:00  Failure in test not_null_stg_event_rsvps_membership_id (models/staging/staging_schema.yml)
19:17:00    Got 102 results, configured to fail if != 0
19:17:00
19:17:00    compiled code at target/compiled/dbt_spond_case/models/staging/staging_schema.yml/not_null_stg_event_rsvps_membership_id.sql
19:17:00
19:17:00    Database Error in test not_null_stg_events_membership_id (models/staging/staging_schema.yml)
  column "membership_id" does not exist in stg_events
  compiled code at target/run/dbt_spond_case/models/staging/staging_schema.yml/not_null_stg_events_membership_id.sql
19:17:00
19:17:00  Failure in test not_null_stg_events_longitude (models/staging/staging_schema.yml)
19:17:00    Got 8853 results, configured to fail if != 0
19:17:00
19:17:00    compiled code at target/compiled/dbt_spond_case/models/staging/staging_schema.yml/not_null_stg_events_longitude.sql
19:17:00
19:17:00  Failure in test not_null_stg_events_latitude (models/staging/staging_schema.yml)
19:17:00    Got 8853 results, configured to fail if != 0
19:17:00
19:17:00    compiled code at target/compiled/dbt_spond_case/models/staging/staging_schema.yml/not_null_stg_events_latitude.sql
19:17:00
19:17:00  Failure in test relationships_stg_event_rsvps_event_id__event_id__ref_stg_events_ (models/staging/staging_schema.yml)
19:17:00    Got 21 results, configured to fail if != 0
19:17:00
19:17:00    compiled code at target/compiled/dbt_spond_case/models/staging/staging_schema.yml/relationships_stg_event_rsvps_88609d4ccdd88bd95f1e85ef4f870049.sql
19:17:00
19:17:00  Failure in test relationships_stg_event_rsvps_membership_id__membership_id__ref_stg_memberships_ (models/staging/staging_schema.yml)
19:17:00    Got 15294 results, configured to fail if != 0
19:17:00
19:17:00    compiled code at target/compiled/dbt_spond_case/models/staging/staging_schema.yml/relationships_stg_event_rsvps_bf3e51c613a264e479578fec66c66738.sql
19:17:00
19:17:00  Failure in test relationships_stg_memberships_team_id__team_id__ref_stg_teams_ (models/staging/staging_schema.yml)
19:17:00    Got 313 results, configured to fail if != 0
19:17:00
19:17:00    compiled code at target/compiled/dbt_spond_case/models/staging/staging_schema.yml/relationships_stg_memberships_team_id__team_id__ref_stg_teams_.sql
```

