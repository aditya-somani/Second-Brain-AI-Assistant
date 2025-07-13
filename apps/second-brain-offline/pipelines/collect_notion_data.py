from pathlib import Path

from loguru import logger
from zenml import pipeline

from steps.collect_notion_data import (
    extract_notion_documents,
    extract_notion_documents_metadata,
)

from steps.infrastructure import save_documents_to_disk , uplaod_to_s3

@pipeline
