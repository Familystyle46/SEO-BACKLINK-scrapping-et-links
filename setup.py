"""Package setup pour SEO Backlink Finder."""

from setuptools import setup, find_packages

setup(
    name="seo-backlink-finder",
    version="1.0.0",
    description="Outil SEO de recherche de backlinks multi-sites",
    author="Familystyle46",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "fake-useragent>=1.4.0",
        "rich>=13.7.0",
        "pyyaml>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "seo-backlinks=seo_backlink_finder.cli:main",
        ],
    },
)
