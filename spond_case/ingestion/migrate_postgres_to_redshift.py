import boto3
import json
import time
from settings import DMS_SETTINGS
from logger import get_logger

"""
    This script migrates the data from PostgreSQL to Redshift Serverless using AWS Data Migration Service (DMS).
    It is a quick load migration, no validation happens yet at this stage.
    - First a task is created and waits until it is ready.
    - Then the task is started and waits until it is complete.
    - Then a confirmation is logged.

    This process requires to create beforehand (more info in README.md): 
    - A migration project
    - A replication instance
    - 2 data providers for source (PostgreSQL) and target (Redshift Serverless)  
    - 2 endpoints for source (PostgreSQL) and target (Redshift Serverless)
"""

logger = get_logger(__name__)

task_name = "postgres-to-redshift-task-6"
replication_instance_arn = DMS_SETTINGS["replication_instance_arn"]
source_endpoint_arn = DMS_SETTINGS["source_endpoint_arn"]
target_endpoint_arn = DMS_SETTINGS["target_endpoint_arn"]


def wait_until_task_created(
        dms: boto3.client, 
        task_arn: str, 
        max_wait_time: int = 300,
        check_interval: int = 10
) -> None:
    """
        Wait for the migration task to be created.

        Args:
            dms: boto3 client for DMS
            task_arn: ARN of the migration task
            max_wait_time: maximum amount of time to wait for the task to be created
            check_interval: interval to check if the task is created
    """

    logger.info("Waiting for replication task to be ready...")
    start_time = time.time()
    
    while True:
        try:
            response = dms.describe_replication_tasks(
                Filters=[
                    {
                        'Name': 'replication-task-arn',
                        'Values': [task_arn]
                    }
                ]
            )
            
            task = response['ReplicationTasks'][0]
            status = task['Status']
            logger.info(f"Current task status: {status}")
            
            if status == 'ready':
                logger.info("Task is ready to start")
                return
            elif status in ['failed', 'stopped']:
                last_failure_message = task.get('LastFailureMessage', 'No failure message available')
                raise Exception(f"Task is in {status} state and cannot be started. Failure message: {last_failure_message}")
            
            if time.time() - start_time > max_wait_time:
                raise Exception(f"Timeout passed. Current status: {status}")
            
            time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error while checking task status: {e}")
            raise


def create_migration_task(
        dms: boto3.client, 
        task_name: str, 
        source_endpoint_arn: str, 
        target_endpoint_arn: str, 
        replication_instance_arn: str
) -> str:
    """
    Create a DMS migration task and wait for it to be ready.
    
    Returns:
        str: The ARN of the created task
    
    Args:
        dms: boto3 client for DMS
        task_name: name of the migration task
        source_endpoint_arn: ARN of the source endpoint
        target_endpoint_arn: ARN of the target endpoint
        replication_instance_arn: ARN of the replication instance
        
    Raises:
        Exception: If task creation fails or task doesn't become ready
    """
    
    # The table mappings define which tables and schemas to include or exclude in the migration.
    #  IN that case, all tables in the "public" schema are included.
    table_mappings = {
        "rules": [
            {
                "rule-type": "selection",
                "rule-id": "1",
                "rule-name": "select-all",
                "object-locator": {
                    "schema-name": "public",
                    "table-name": "%"
                },
                "rule-action": "include"
            }
        ]
    }

    try:
        # Create the replication task
        response = dms.create_replication_task(
            ReplicationTaskIdentifier=task_name,
            SourceEndpointArn=source_endpoint_arn,
            TargetEndpointArn=target_endpoint_arn,
            ReplicationInstanceArn=replication_instance_arn,
            MigrationType='full-load', 
            TableMappings=json.dumps(table_mappings),
            ReplicationTaskSettings=json.dumps({}),
            Tags=[
                {'Key': 'Project', 'Value': 'SpondMigration'}
            ]
        )
        
        task_arn = response['ReplicationTask']['ReplicationTaskArn']
        logger.info(f"Migration task creation started: {task_arn}")
        
        wait_until_task_created(dms, task_arn)
        logger.info(f"Migration task created successfully: {task_arn}")
        
        return task_arn
        
    except Exception as e:
        logger.error(f"Error in migration task creation process: {e}")
        raise


def wait_until_migration_complete(
        dms: boto3.client, 
        task_arn: str, 
        max_wait_time: int = 3600,
        check_interval: int = 20
) -> None:
    """
    Wait for the migration task to complete (that is when the full load is finished).

    Args:
        dms: boto3 client for DMS
        task_arn: ARN of the migration task
        max_wait_time: maximum time to wait for completion 
        check_interval: interval between status checks
        
    Raises:
        Exception: If task fails or times out
    """
    
    logger.info("Waiting for migration task to complete...")
    start_time = time.time()
    
    while True:
        try:
            response = dms.describe_replication_tasks(
                Filters=[
                    {
                        'Name': 'replication-task-arn',
                        'Values': [task_arn]
                    }
                ]
            )
            
            task = response['ReplicationTasks'][0]['Status']
            status = task
            logger.info(f"Migration status: {status}")
            
            if status == 'stopped':
                logger.info("Migration completed successfully!")
                return
            elif status == 'failed':
                failure_message = task.get('LastFailureMessage', 'No failure message available')
                raise Exception(f"Migration failed: {failure_message}")
            elif status in ['running']:
                logger.info("Migration is running...")
            
            if time.time() - start_time > max_wait_time:
                raise Exception(f"Timeout passed. Current status: {status}")
            
            time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error while waiting for migration task completion: {e}")
            raise


def start_migration_task(dms: boto3.client, task_arn: str) -> None:
    """
    Start the migration task and wait for it to complete.
    
    Args:
        dms: boto3 DMS client
        task_arn: ARN of the task to start
            
    Raises:
        Exception: If task fails to start or complete
    """
    try:
        # Start the task
        start_response = dms.start_replication_task(
            ReplicationTaskArn=task_arn,
            StartReplicationTaskType='start-replication'
        )
        logger.info(f"Task started successfully. Status: {start_response['ReplicationTask']['Status']}")
        
        wait_until_migration_complete(dms, task_arn)
        logger.info(f"Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in migration process: {e}")
        raise


def main() -> None:
    """
        Main function to:
        - create a migration task
        - wait until it is ready
        - start the migration task
        - wait until the migration is complete
        - send a confirmation of the completed migration
    """
    
    try:
        dms = boto3.client('dms', region_name=DMS_SETTINGS["region_name"])
        logger.info(f"Connected to DMS")
        
        task_arn = create_migration_task(
            dms=dms, 
            task_name=task_name, 
            source_endpoint_arn=source_endpoint_arn, 
            target_endpoint_arn=target_endpoint_arn, 
            replication_instance_arn=replication_instance_arn
        )
        
        start_migration_task(dms, task_arn)
        
        logger.info("Migration process completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Migration process interrupted")
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        raise


if __name__ == "__main__":
    main()