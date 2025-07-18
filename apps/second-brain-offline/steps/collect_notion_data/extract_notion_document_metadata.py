from loguru import logger
from typing_extensions import Annotated
from zenml import get_step_context, step

from src.second_brain_offline.domain import DocumentMetadata
from steps.infrastructure.notion import NotionDatabaseClient

@step
#It queries a Notion database by ID and extracts metadata for all documents within it, returning a list of metadata objects.
# Purpose: Fetch and compile metadata for documents in a given Notion database, serving as an initial discovery step in a data pipeline.
def extract_notion_document_metadata(
    database_id: str,
) -> Annotated[list[DocumentMetadata],'notion_document_metadata']:
    """Extract metadata from Notion documents in a specified database.

    Args:
        database_id: The ID of the Notion database to query.

    Returns:
        A list of DocumentMetadata objects containing the extracted information.
    """

    client = NotionDocumentClient()
    document_metadata = client.query_notion_database(database_id)