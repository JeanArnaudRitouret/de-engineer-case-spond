import os

POSTGRES_SETTINGS = {
    "host": os.environ["PGHOST"],
    "port": 5432,
    "dbname": os.environ["PGDATABASE"],
    "user": os.environ["PGUSER"],
    "password": os.environ["PGPASSWORD"],
}

REDSHIFT_SETTINGS = {
    "host": os.environ["REDSHIFT_HOST"],
    "port": 5439,   
    "dbname": os.environ["REDSHIFT_DB"],
    "user": os.environ["REDSHIFT_USER"],
    "password": os.environ["REDSHIFT_PASSWORD"],
}

DMS_SETTINGS = {
    "region_name": os.environ["AWS_DEFAULT_REGION"],
    "task_arn": os.environ["TASK_ARN"],
    "source_endpoint_arn": os.environ["SOURCE_ENDPOINT_ARN"],
    "target_endpoint_arn": os.environ["TARGET_ENDPOINT_ARN"],
    "replication_instance_arn": os.environ["REPLICATION_INSTANCE_ARN"],
}