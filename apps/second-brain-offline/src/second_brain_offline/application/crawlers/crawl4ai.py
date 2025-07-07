import asyncio
import os

import psutil
from crawl4ai import AsyncWebCrawler, CacheMode
from loguru import logger

# from second_brain_offline import utils
# from second_brain_offline.domain import Document, DocumentMetadata

class Crawl4AICrawler:
    """A crawler implemetation using crawl4ai for concurrent crawling
    Attributes:
        max_concurrent_requests : Maximum number of concurrent HTTP requests allowed"""
    
    def __init__(self, max_concurrent_requests: int = 10) -> None:
        """Intializes the crawler with the maximum number of concurrent requests"""

        self.max_concurrent_requests = max_concurrent_requests

    def __call__(self, pages: list[Document]) -> list[Document]:
        """Crawl Multiple child pages in parallel.

        Args : takes in a list of pages containing child urls  
        Output : a list of new documents from child urls """

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.__crawl_batch(pages))
        else:
            return loop.run_until_complete(self.__crawl_batch(pages))
    
    async def __crawl_batch(self, pages: list[Document]) -> list[Document]:
         """Asynchronously crawl all child URLs of multiple documents.

        Args: List of documents containing child URLs to crawl.

        Output: list[Document]: List of new documents created from successfully crawled URLs.
        """