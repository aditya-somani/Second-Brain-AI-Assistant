# What it is: This code defines the NotionDocumentClient class, a specialized tool for fetching the complete content of a single Notion page. 
# It recursively traverses all of a page's content blocks (like headings, text, lists, and even sub-pages) and converts them into a clean, 
# flat Markdown string while also extracting all embedded URLs.

# The Core Problem: This code solves the problem of deep content extraction and transformation. 
# A Notion page isn't a single document but a hierarchical tree of "blocks." The API returns this raw, nested JSON structure. 
# This client's job is to navigate this tree, make additional API calls for nested content, and transform the complex block-based data into a simple, 
# standardized Markdown format that other systems can easily process.


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
            self, blocks: list[dict], depth: int = 0
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
                
            # Handle Notion paragraph and quote blocks
            elif block_type in {
                "paragraph",
                "quote",
            }:
                # Convert rich_text to plain/markdown text and add newline
                content += f"{self.__parse_rich_text(block[block_type].get('rich_text', []))}\n"
                # Collect any URLs in this text
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))

            # Handle bulleted and numbered list items
            elif block_type in {"bulleted_list_item", "numbered_list_item"}:
                # Format as markdown list item (e.g., "- item")
                content += f"- {self.__parse_rich_text(block[block_type].get('rich_text', []))}\n"
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))

            # Handle to-do items (checkbox-style tasks)
            elif block_type == "to_do":
                # Format as markdown to-do with empty checkbox (can be extended to track completion)
                content += f"[] {self.__parse_rich_text(block['to_do'].get('rich_text', []))}\n"
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))

            # Handle code blocks
            elif block_type == "code":
                # Wrap content in Markdown code block syntax (```
                content += f"```\n{self.__parse_rich_text(block['code'].get('rich_text', []))}\n```"
                urls.extend(self.__extract_urls(block[block_type].get("rich_text", [])))

            # Handle image blocks (external image links)
            elif block_type == "image":
                # Safely extract image URL, fallback to "No URL" if missing
                content += f"[Image]({block['image'].get('external', {}).get('url', 'No URL')})\n"

            # Handle divider blocks (horizontal rule)
            elif block_type == "divider":
                # Render a markdown horizontal rule
                content += "---\n\n"

            # Handle sub-pages only if recursion depth is shallow enough
            elif block_type == "child_page" and depth < 3:
                child_id = block["id"]  # Extract child page ID for retrieval
                # Get the title of the child page; fallback to placeholder if missing
                child_title = block.get("child_page", {}).get("title", "Untitled")
                
                # Add metadata line and start content section for the sub-page
                content += f"\n\n<child_page>\n# {child_title}\n\n"
                
                # Recursively retrieve and parse the child page content
                child_blocks = self.__retrieve_child_blocks(child_id)
                child_content, child_urls = self.__parse_blocks(child_blocks, depth + 1)
                
                # Add parsed child content and mark end of child page
                content += child_content + "\n</child_page>\n\n"
                urls += child_urls

            # Handle link previews (visual/inline link cards)
            elif block_type == "link_preview":
                url = block.get("link_preview", {}).get("url", "")
                # Display the preview as a markdown link
                content += f"[Link Preview]({url})\n"
                # Normalize and collect for downstream crawling
                urls.append(self.__normalize_url(url))

            # Catch any unrecognized block types for logging/debugging
            else:
                logger.warning(f"Unknown block type: {block_type}")

            # Check if this block (but not a full child_page) has nested children
            # Usually applies to bullet lists, toggles, etc.
            if (
                block_type != "child_page"
                and "has_children" in block
                and block["has_children"]
            ):
                # Recursively retrieve and parse nested blocks ("children")
                child_blocks = self.__retrieve_child_blocks(block_id)
                child_content, child_urls = self.__parse_blocks(child_blocks, depth + 1)

                # Indent each line of child content to reflect hierarchy (visual tab)
                content += (
                    "\n".join("\t" + line for line in child_content.split("\n"))
                    + "\n\n"
                )
                urls += child_urls

            # Deduplicate all collected URLs before returning
            urls = list(set(urls))

            # Return cleaned content and list of links
            return content.strip("\n "), urls
        
    # Purpose: To extract URLs from the rich text blocks of the Notion API.
    def __extract_urls(self,rich_text: list[dict]) -> list[str]:
        """Extract URLs from Notion rich text blocks.

        Args:
            rich_text: List of Notion rich text objects to extract URLs from.

        Returns:
            list[str]: List of normalized URLs found in the rich text.
        """
        urls = []
        for text in rich_text: #iterating through each text object in the rich_text list
            url = None
            if text.get('href'): #using .get() to safely access the 'href' key without raising an error if it doesn't exist it returns None
                url = text['href']
            elif text.get('annotations',{}):
                url = text['annotations']['url']

            if url:
                urls.append(self.__normalize_url(url)) #append adds one element to the end of list whereas extend adds element from an iterable -> go see this right now
        
        return urls
    
    def __normalize_url(self, url: str) -> str:
        """Normalize a URL by ensuring it ends with a forward slash.

        Args:
            url: URL to normalize.

        Returns:
            str: Normalized URL with trailing slash.
        """
        if not url.endswith('/'):
            url += '/'
        return url



