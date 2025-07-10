import asyncio
import os

import psutil
from crawl4ai import AsyncWebCrawler, CacheMode
from loguru import logger

# from second_brain_offline import utils
# from second_brain_offline.domain import Document, DocumentMetadata

#Crawl4AICrawler is a class that allows you to crawl the web asynchronously.
class Crawl4AICrawler:
    """A crawler implemetation using crawl4ai for concurrent crawling
    Attributes:
        max_concurrent_requests : Maximum number of concurrent HTTP requests allowed"""
    
    #__init__ is a special method in Python that is used to initialize an object.
    def __init__(self, max_concurrent_requests: int = 10) -> None:
        """Intializes the crawler with the maximum number of concurrent requests"""

        self.max_concurrent_requests = max_concurrent_requests

    #__call__ is a special method in Python that makes an object callable.
    #It is used to define the behavior of the object when it is called as a function.
    #In this case, the object is a Crawl4AICrawler instance and the function is called __call__.
    #The function takes in a list of pages containing child urls and returns a list of new documents from child urls.
    def __call__(self, pages: list[Document]) -> list[Document]:
        """Crawl Multiple child pages in parallel.

        Args : takes in a list of pages containing child urls  
        Output : a list of new documents from child urls """

        #get_running_loop is a function that returns the current event loop.
        #If no event loop is running, it raises a RuntimeError.
        #If an event loop is running, it returns the current event loop.
        #In this case, the event loop is the asyncio event loop.
        #The event loop is used to schedule and execute coroutines.
        try:
            loop = asyncio.get_running_loop()
        #If no event loop is running, it raises a RuntimeError.
        except RuntimeError:
            #If no event loop is running, it runs the __crawl_batch function asynchronously.
            #asyncio.run is a function that runs the given coroutine and returns the result.
            #In this case, the coroutine is the __crawl_batch function.
            #The __crawl_batch function is run asynchronously.
            return asyncio.run(self.__crawl_batch(pages))
        else:
            #If an event loop is running, it runs the __crawl_batch function synchronously.
            #run_until_complete is a function that runs the given coroutine and returns the result.
            #In this case, the coroutine is the __crawl_batch function.
            #The __crawl_batch function is run synchronously.
            return loop.run_until_complete(self.__crawl_batch(pages))
    
    #__crawl_batch is a coroutine function that crawls all child URLs of multiple documents.
    async def __crawl_batch(self, pages: list[Document]) -> list[Document]:

        #Extra(Name Mangling):
        #a function name as __crawl_batch is a deliberate choice to make it a class-private method, primarily to prevent it from being 
        #accidentally overwritten in any child classes that might extend its functionality.

        """Asynchronously crawl all child URLs of multiple documents.

        Args: List of documents containing child URLs to crawl.

        Output: list[Document]: List of new documents created from successfully crawled URLs.
        """
         
        process = psutil.Process(os.getpid()) #memory logging for process #process ki unique id nikalne ke liye
        start_mem = process.memory_info().rss #memory usage in bytes #rss = resident set size
        logger.info(
            f"Starting crawl batch with {self.max_concurrent_requests} concurrent requests. "
            f"Current process memory usage: {start_mem // (1024 * 1024)} MB"
        )

        #A semaphore is a synchronization primitive that allows a limited number of concurrent tasks to run.
        #It is used to control the number of concurrent operations that can be performed.
        #In this case, it is used to limit the number of concurrent HTTP requests that can be made.
        #This is useful to avoid overwhelming the server with requests and to avoid rate limiting.
        #This is also useful to avoid overwhelming the memory and CPU of the process.
        semaphor = asyncio.Semaphore(self.max_concurrent_requests)
        
        all_results = [] #list to store the results of the crawling

        #AsyncWebCrawler is a class that allows you to crawl the web asynchronously.
        #CacheMode.BYPASS is a class that allows you to bypass the cache.
        #By bypassing the cache, you can avoid the overhead of caching and the need to store the results in the cache.
        async with AsyncWebCrawler(cache_mode=CacheMode.BYPASS) as crawler:
            #crawl all child urls in parallel
            for page in pages:
                #This create a list of coroutines objects which are waiting to be executed
                tasks = [
                    self.__crawl_page(crawler, page ,url ,semaphor)
                    for url in page.child_urls
                ]
                #asyncio.gather: This function takes one or more awaitables (our list of tasks) and schedules them to run concurrently.
                # *tasks: The asterisk * unpacks the tasks list, passing each task as a separate argument to gather.
                # await: This keyword pauses the __crawl_batch function right here. 
                        # The asyncio event loop now takes over, juggling all the __crawl_url tasks.
                        # It sends a request, and while waiting for a response, it starts another, and so on, up to the semaphore's limit. 
                # The __crawl_batch function will only resume once all the tasks passed to gather have finished.
                #results is a list of documents that are returned by the __crawl_page function
                results = await asyncio.gather(*tasks)
                all_results.extend(results)

        #memory logging for process(crawling)
        end_mem = process.memory_info().rss
        crawling_memory_diff = end_mem - start_mem
        logger.debug(
            f"Crawl batch completed. "
            f"Final process memory usage: {end_mem // (1024 * 1024)} MB, "
            f"Crawling memory diff: {crawling_memory_diff // (1024 * 1024)} MB"
        )

        #storing the successful results in a list and removing the None values
        successful_results = [result for result in all_results if result is not None]

        success_count = len(successful_results)
        failed_count = len(all_results) - success_count
        total_count = len(all_results)
        logger.info(
            f"Crawling completed: "
            f"{success_count}/{total_count} succeeded ✓ | "
            f"{failed_count}/{total_count} failed ✗"
        )
            
        return successful_results
    
    async def __crawl_url(
            self,
            crawler: AsyncWebCrawler,
            page: Document,
            url: str,
            semaphor: asyncio.Semaphore,
    ) -> Document | None:
        """Crawl a single URL asynchronously.

        Args:
            crawler: AsyncWebCrawler instance to use for crawling.
            page: Parent document containing the URL.
            url: URL to crawl.
            semaphore: Semaphore for controlling concurrent requests.

        Returns:
            Document | None: New document if crawl was successful, None otherwise.
        """

        async with semaphor:

            