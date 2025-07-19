# The code solves the problem of translating complex API data into a usable format. 
# The Notion API returns data in a deeply nested and verbose JSON structure. This client abstracts away the complexity of making HTTP requests, 
# handling authentication, and, most importantly, parsing the raw Notion data into clean, flattened Python objects (DocumentMetadata).

import json
from typing import Any

import requests
from loguru import logger

from src.second_brain_offline import settings
from src.second_brain_offline.domain import DocumentMetadata

# Purpose: To manage the connection and interaction with the Notion API, acting as the primary object for fetching database data.
class NotionDatabaseClient:
    """Client for interacting with Notion databases.

    This class provides methods to query Notion databases and process the returned data.

    Attributes:
        api_key: The Notion API secret key used for authentication.
    """

    def __init__(self, api_key: str|None = settings.NOTION_SECRET_KEY) -> None:
        """Initialize the NotionDatabaseClient.

        Args:
            api_key: Optional Notion API key. If not provided, will use settings.NOTION_SECRET_KEY.
        """
        # assert statement implements a fail-fast design. It checks for the API key immediately, providing a clear, actionable error message if it's missing, 
        # rather than allowing the program to fail later with a more cryptic authentication error from the API server.
        assert api_key is not None, (
            "NOTION_SECRET_KEY environment variable is required. Set it in your .env file."
        )

        self.api_key = api_key

        # Its job is to orchestrate the query process: build the request, send it, handle any errors, and format the results.
        def notion_query_database(
                self, database_id: str, query_json: str|None = None
        ) -> list[DocumentMetadata]:
            """Query a Notion database and return its results.

            Args:
                database_id: The ID of the Notion database to query.
                query_json: Optional JSON string containing query parameters.

            Returns:
                A list of dictionaries containing the query results.
            """

            # This block constructs the API endpoint URL and the required HTTP headers for the request.
            url = f'https://api.notion.com/v1/databases/{database_id}/query'
            headers = {
                'Authorization': f'Bearer {self.api_key}', #This is all according to the Notion API documentation.Read the docs to understand this.
                'Content-Type': 'application/json',
                'Notion-Version': '2022-06-28',
            }

            query_payload = {}
            if query_json and query_json.strip(): #This is a check to see if the query_json is not empty.
                try:
                    query_payload = json.loads(query_json) # This is a check to see if the query_json is valid JSON.
                except json.JSONDecodeError:
                    # this captures the stack trace for debugging without halting execution.
                    # Instead of crashing, the function exits early with an empty list [] — graceful error handling.
                    logger.opt(exception=True).debug(f"Invalid JSON format for query") 
                    # .debug(...) is a non-intrusive log level, meaning:
                    # It won't show up in production unless debugging is turned on.
                    # But it's invaluable in development and testing when tracing bugs.
                    return []
                
            try:
                response = requests.post(
                    url, headers=headers, json=query_payload, timeout=10
                )
                response.raise_for_status() # A best practice in requests lib, it automatically checks if the HTTP response was successful or not 
                # and raises exception if it was not successful which is then caught by the except block.
                results = response.json()
                results = results['results']
            except requests.exceptions.RequestException as e:
                logger.opt(exception=True).debug(f"Error querying Notion database")
                return []
            except KeyError:
                logger.opt(exception=True).debug(f"Unexpected response format from Notion API")
                return []
            except Exception:
                logger.opt(exception=True).debug(f"Error querying Notion database")
                return []

            return [self.__build_page_metadata(page) for page in results]
        
    # Purpose: To convert a single, raw page object from the Notion API into a structured DocumentMetadata object.
    def __build_page_metadata(self, page: dict[str, Any]) -> DocumentMetadata: # This is a private method, so it's not exposed to the outside world.
        """Build a PageMetadata object from a Notion page dictionary.

        Args:
            page: Dictionary containing Notion page data.

        Returns:
            A PageMetadata object containing the processed page data.
        """

        # calls another helper, __flatten_properties, to simplify the nested properties dictionary.
        properties = self.__flatten_properties(page.get('properties', {})) # safely handles cases where a page might not have properties. 
        # It then extracts the "Name" property to use as the title
        title = properties.pop('Name') # pop to avoid duplication of the title in the properties dictionary.

        if page.get('parent'):
            properties['parent'] = {
                'id': page['parent']['database_id'],
                'url': '',
                'title': '',
                'properties': {},
            }

        return DocumentMetadata(
            id=page['id'], url=page['url'], title=title, properties=properties
        )
    
    # Purpose: This utility method's sole responsibility is to transform the complex, nested Notion properties dictionary into a simple, flat key-value dictionary.
    def __flatten_properties(self, properties: dict) -> dict:
        """Flatten Notion properties dictionary into a simpler key-value format.

        Args:
            properties: Dictionary of Notion properties to flatten.

        Returns:
            A flattened dictionary with simplified key-value pairs.

        Example:
            Input: {
                'Type': {'type': 'select', 'select': {'name': 'Leaf'}},
                'Name': {'type': 'title', 'title': [{'plain_text': 'Merging'}]}
            }
            Output: {
                'Type': 'Leaf',
                'Name': 'Merging'
            }
        """
        # Extra:
        # The Notion API uses a different nested structure for every property type (select, multi_select, title, etc.). 
        # This method centralizes the parsing logic for all of them. Any other part of the system that needs a property's value can now 
        # simply access properties['Type'] and get 'Leaf', instead of needing to know how to parse {'type': 'select', 'select': {'name': 'Leaf'}}.

        flattened = {}
        # Iterating over the properties and for each one checks the type and then how to parse it.
        for key, value in properties.items():
            prop_type = value.get('type')

            if prop_type == "select":
                select_value = value.get("select", {}) or {}
                flattened[key] = select_value.get("name")
            elif prop_type == "multi_select":
                flattened[key] = [
                    item.get("name") for item in value.get("multi_select", [])
                ]
            elif prop_type == "title":
                flattened[key] = "\n".join(
                    item.get("plain_text", "") for item in value.get("title", [])
                )
            elif prop_type == "rich_text":
                flattened[key] = " ".join(
                    item.get("plain_text", "") for item in value.get("rich_text", [])
                )
            elif prop_type == "number":
                flattened[key] = value.get("number")
            elif prop_type == "checkbox":
                flattened[key] = value.get("checkbox")
            elif prop_type == "date":
                date_value = value.get("date", {})
                if date_value:
                    flattened[key] = {
                        "start": date_value.get("start"),
                        "end": date_value.get("end"),
                    }
            elif prop_type == "database_id":
                flattened[key] = value.get("database_id")
            else:
                flattened[key] = value

        return flattened


            

