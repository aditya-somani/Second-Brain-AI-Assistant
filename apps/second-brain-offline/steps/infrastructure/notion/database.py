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

            

