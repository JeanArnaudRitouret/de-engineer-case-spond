import pandas as pd
from sqlalchemy import create_engine
from settings import POSTGRES_SETTINGS
from pathlib import Path
from logger import get_logger

"""
    This script uploads the data from the csv files to the postgres database.
    Not required by the case but it's making it easier to replicate the behvaviour of an actual application.
"""

logger = get_logger(__name__)

user = POSTGRES_SETTINGS['user']
password = POSTGRES_SETTINGS['password']
host = POSTGRES_SETTINGS['host']
port = POSTGRES_SETTINGS['port']
dbname = POSTGRES_SETTINGS['dbname']


def get_csv_files_to_upload() -> list[tuple[str, str]]:
    """
        Get the files to upload from the local data directory.

        Returns:
            list[tuple[str, str]]: List of tuples containing the filepath and the tablename
    """
    # Get project root (2 levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / 'data'
    
    files = list(data_dir.glob('*.csv'))
    files_to_upload = [
        (str(file), file.stem) 
        for file in files
    ]
    logger.info(f"Found {len(files_to_upload)} files to upload: {files_to_upload}")
    return files_to_upload


def upload_csv_to_postgres(filepath: str, tablename: str) -> None:
    """
        Upload a csv file to the postgres database.

        Args:
            filepath: Path to the csv file
            tablename: Name of the table to upload the data to
    """
    logger.info(f"Uploading {filepath} to {tablename} in Postgres...")
    df = pd.read_csv(filepath)
    engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{dbname}")
    df.to_sql(tablename, engine, if_exists='replace', index=False)
    logger.info(f"...Upload of {filepath} to {tablename} in Postgres completed")


def main() -> None:
    """
        Main function to:
        - get the files to upload
        - upload the data to the postgres database
        - send a confirmation of the upload when it is completedd
    """
    logger.info("Starting upload to Postgres")
    try:
        files_to_upload = get_csv_files_to_upload()
        for filepath, tablename in files_to_upload:
            upload_csv_to_postgres(filepath, tablename)
        logger.info("Upload to Postgres completed")
    except KeyboardInterrupt:
        logger.warning("Upload interrupted.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()