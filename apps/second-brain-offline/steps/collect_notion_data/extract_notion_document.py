#What is the purpose of this file?
#This code defines a ZenML pipeline step that extracts content from multiple Notion documents by transforming document 
#metadata into fully-populated document objects with their actual content.

from typing_extensions import Annotated
from zenml import get_step_context, step

from src.second_brain_offline.domain import Document, DocumentMetadata
from steps.infrastructure.notion import NotionDocumentClient

#The code is structured as a decorated function rather than a class because it represents a single, 
#stateless transformation step in a larger pipeline.

@step #zenml decorator to mark the function as a step in the pipeline
# Transform a collection of document metadata objects into fully-populated document objects with extracted content from Notion.
def extract_notion_documents(
    document_metadata: list[DocumentMetadata],
) -> Annotated[list[Document],'notion_documents']: 
    # The "notion_documents" annotation allows ZenML to track this specific output artifact, 
    # enabling downstream steps to reference it explicitly and providing better lineage tracking

    """Extract content from multiple Notion documents.

    Args:
        documents_metadata: List of document metadata to extract content from.

    Returns:
        list[Document]: List of documents with their extracted content.
    """

    client = NotionDocumentClient()
    documents = []
    # The client is created fresh for each step execution rather than being reused, which might seem inefficient but serves 
    # several purposes: ensures fresh authentication tokens, avoids connection state issues in distributed pipeline execution, 
    # and keeps the step stateless. The empty list initialization follows a clear accumulator pattern for the upcoming loop.

    # Iterates through each metadata object and extracts the corresponding document content, accumulating results in the list.
    for document_metadata in document_metadata:
        documents.append(client.extract_document(document_metadata))

        # Retrieves the ZenML step execution context and attaches metadata about the operation's results.
        step_context = get_step_context()
        step_context.add_output_metadata(
            output_name = 'notion_documents',
            metadata = {
                'len_documents': len(documents), 
            }
        )

        return documents

