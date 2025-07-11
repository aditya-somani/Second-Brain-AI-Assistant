from .crawl4ai import Crawl4AICrawler

#__all__ is a list of all the wildcard classes and functions that are being exported from the module
#That is when you use import * from second_brain_offline.application.crawlers this will be the list of classes and functions that are being exported
#__init__.py is a special file that tells Python that the directory should be treated as a package so making __all__ is not compulsory
# and does not changes anything expect what I said above
__all__ = ['Crawl4AICrawler']