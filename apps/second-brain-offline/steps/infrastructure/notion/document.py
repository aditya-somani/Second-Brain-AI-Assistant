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
    def __retrive_child_blocks( #__ is a convention to indicate that the method is private or for internal use only
            self, block_id: str , page_size: int = 100
    ) -> list[dict]:
        """Retrieve child blocks from a Notion block.

        Args:
            block_id: The ID of the block to retrieve children from.
            page_size: Number of blocks to retrieve per request.

        Returns:
            list[dict]: List of block data.
        """
        # 1. Construct the URL for the API request
        blocks_url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size={page_size}"

        # 2. Set up the headers for the API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
        }
        # wrapping in try except to handle errors
        try:
            # 1. Make the API request
            blocks_response = requests.get(blocks_url, headers=headers,timeout=10) 
            # 2. Raise an error if the request was not successful
            blocks_response.raise_for_status()
            # 3. Parse the response and return the results
            blocks_data = blocks_response.json()
            return blocks_data.get('results',[])
        # 4. Handle errors
        # It catches any exception that is a subclass of RequestException. 
        # This includes a wide range of network-related problems like connection timeouts, DNS failures, or receiving an invalid HTTP response. 
        # It aliases the caught exception object as e so it can be inspected.
        except requests.exceptions.RequestException as e:
            error_message = f"Error: Failed to retrieve Notion page content. {e}"
            #So why check if the attribute exists or not before checking the value?
            #Because the exception object might not have a response attribute if the error is like ConnectionError or HTTPError , 
            #Hence checking value before will lead to an AttributeError that is why we check if the attribute exists or not before checking the value.
            if hasattr(e,'response') and e is not None:
                error_message += f'Status code: {e.response.status_code}, Response: {e.response.text}'
            #Why use logger.exception() instead of logger.error()?
            #When called from within an except block, logger.exception() automatically includes the full exception traceback in the log. 
            #This provides the complete context of where the error occurred in the code, which is invaluable for debugging.
            logger.exception(error_message)
            return [] #return empty list if the request fails
        # Handle other exceptions which are not related to the request like JSONDecodeError, KeyError, etc.
        except Exception as e:
            logger.exception("Error retrieving Notion page content")
            return []
        
    # Purpose: It's where the raw, proprietary Notion format is translated into the clean, standardized Markdown that the rest of the AI pipeline relies on
    def __parse_blocks(
            self, blocks: list[dict], indepth: int = 0
    ) -> tuple[str, list[str]]:
        """Parse Notion blocks into text content and extract URLs.

        Args:
            blocks: List of Notion block objects to parse.
            depth: Current recursion depth for parsing nested blocks.
                This is the recursion counter. It tracks how deep the parser is in the document tree. It defaults to 0 for the initial call. 
                This is a crucial safety mechanism to prevent infinite loops.

        Returns:
            tuple[str, list[str]]: A tuple containing:
                - Parsed text content as a string
                - List of extracted URLs
        """
        # The core strategy is to iterate through each block, identify its type, and apply a specific formatting rule. 
        # To handle nested content (like toggles or sub-pages), the function calls itself, creating a recursive loop that can traverse the entire document tree.
        
        content = ""
        urls = []
        for block in blocks:
            block_type = block.get('type') #using .get() to safely access the 'type' key without raising an error if it doesn't exist it returns None
            block_id = block.get('id')

            if block_type in {
                'heading_1','heading_2','heading_3',
            }:
                #It prepends a # to create a Markdown heading. \n\n adds a blank line after the heading for better readability, a standard Markdown practice
                content += f"# {self.__parse_rich_text(block[block_type].get('rich_text', []))}\n\n"
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))

            # This pattern repeats for paragraph, quote, bulleted_list_item, to_do, and code, 
            # each applying the appropriate Markdown syntax (e.g., - for lists, [] for to-do items, ``` for code blocks).
                
            elif block_type in {
                "paragraph",
                "quote",
            }:
                content += f"{self.__parse_rich_text(block[block_type].get('rich_text', []))}\n"
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))
            elif block_type in {"bulleted_list_item", "numbered_list_item"}:
                content += f"- {self.__parse_rich_text(block[block_type].get('rich_text', []))}\n"
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))
            elif block_type == "to_do":
                content += f"[] {self.__parse_rich_text(block['to_do'].get('rich_text', []))}\n"
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))
            elif block_type == "code":
                content += f"```\n{self.__parse_rich_text(block['code'].get('rich_text', []))}\n````\n"
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))
            elif block_type == "image":
                content += f"[Image]({block['image'].get('external', {}).get('url', 'No URL')})\n"
            elif block_type == "divider":
                content += "---\n\n"
            elif block_type == "child_page" and depth < 3:
                child_id = block["id"]
                child_title = block.get("child_page", {}).get("title", "Untitled")
                content += f"\n\n<child_page>\n# {child_title}\n\n"

                child_blocks = self.__retrieve_child_blocks(child_id)
                child_content, child_urls = self.__parse_blocks(child_blocks, depth + 1)
                content += child_content + "\n</child_page>\n\n"
                urls += child_urls

            elif block_type == "link_preview":
                url = block.get("link_preview", {}).get("url", "")
                content += f"[Link Preview]({url})\n"

                urls.append(self.__normalize_url(url))
            else:
                logger.warning(f"Unknown block type: {block_type}")

            # Parse child pages that are bullet points, toggles or similar structures.
            # Subpages (child_page) are parsed individually as a block.
            if (
                block_type != "child_page"
                and "has_children" in block
                and block["has_children"]
            ):
                child_blocks = self.__retrieve_child_blocks(block_id)
                child_content, child_urls = self.__parse_blocks(child_blocks, depth + 1)
                content += (
                    "\n".join("\t" + line for line in child_content.split("\n"))
                    + "\n\n"
                )
                urls += child_urls

        urls = list(set(urls))

        return content.strip("\n "), urls



