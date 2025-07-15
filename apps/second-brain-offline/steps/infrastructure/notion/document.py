import requests
from loguru import logger

from src.second_brain_offline.config import settings
from src.second_brain_offline.domain import Document, DocumentMetadata

class NotionDocumentClient:
    """Client for interacting with Notion API to extract document content.

    This class handles retrieving and parsing Notion pages, including their blocks,
    rich text content, and embedded URLs.
    """

    def __init__(self, api_key: str|None = settings.NOTION_SECRET_KEY):
        """Initialize the Notion client.

        Args:
            api_key: The Notion API key to use for authentication.
        """
        #pre checking - It ensures the client cannot be created without a valid API key.
        assert api_key is not None, (
            "Notion API key is not set. Please set the NOTION_SECRET_KEY environment variable."
        )

        self.api_key = api_key

    # Purpose: To take a document's metadata and return a fully populated Document object. - primary method that ties everything together
    def extract_document(self,document_metadata: DocumentMetadata) -> Document:
        """Extract content from a Notion document.

        Args:
            document_metadata: Metadata about the document to extract.

        Returns:
            Document: A Document object containing the extracted content and metadata.
        """
        # 1. Fetch raw data from the source (Notion)
        blocks = self.__retrieve_child_blocks(document_metadata.id)
        
        # 2. Transform raw data into standardized format and extract key information
        content, urls = self.__parse_blocks(blocks)

        # 3. Handle and structure hierarchical metadata (parent-child relationships)
        parent_metadata = document_metadata.properties.pop("parent", None)
        if parent_metadata:
            parent_metadata = DocumentMetadata(
                id=parent_metadata["id"],
                url=parent_metadata["url"],
                title=parent_metadata["title"],
                properties=parent_metadata["properties"],
            )

        # 4. Assemble the final, structured object
        return Document(
            id=document_metadata.id,
            metadata=document_metadata,
            parent_metadata=parent_metadata,
            content=content,
            child_urls=urls,
        )
    
    # Purpose: To fetch content blocks from the Notion API for a given page or block ID.
    def __retrive_child_blocks(
            slef, block_id: str , page_size: int = 100
    ) -> list[dict]:
        """Retrieve child blocks from a Notion block.

        Args:
            block_id: The ID of the block to retrieve children from.
            page_size: Number of blocks to retrieve per request.

        Returns:
            list[dict]: List of block data.
        """



