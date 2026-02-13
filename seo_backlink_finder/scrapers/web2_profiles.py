"""Scraper pour trouver des plateformes Web 2.0 et profils pour backlinks."""

import logging
from urllib.parse import urlparse

from .base import BacklinkOpportunity, BaseScraper

logger = logging.getLogger(__name__)


class Web2ProfileScraper(BaseScraper):
    """Recherche des plateformes Web 2.0 et profils pour créer des backlinks."""

    # Plateformes Web 2.0 connues pour le link building
    WEB2_PLATFORMS = [
        {
            "name": "Medium",
            "domain": "medium.com",
            "type": "blogging",
            "dofollow": False,
            "url": "https://medium.com",
        },
        {
            "name": "Tumblr",
            "domain": "tumblr.com",
            "type": "blogging",
            "dofollow": True,
            "url": "https://www.tumblr.com",
        },
        {
            "name": "WordPress.com",
            "domain": "wordpress.com",
            "type": "blogging",
            "dofollow": False,
            "url": "https://wordpress.com",
        },
        {
            "name": "Blogger/Blogspot",
            "domain": "blogspot.com",
            "type": "blogging",
            "dofollow": False,
            "url": "https://www.blogger.com",
        },
        {
            "name": "About.me",
            "domain": "about.me",
            "type": "profile",
            "dofollow": True,
            "url": "https://about.me",
        },
        {
            "name": "Gravatar",
            "domain": "gravatar.com",
            "type": "profile",
            "dofollow": True,
            "url": "https://gravatar.com",
        },
        {
            "name": "Issuu",
            "domain": "issuu.com",
            "type": "document",
            "dofollow": False,
            "url": "https://issuu.com",
        },
        {
            "name": "SlideShare",
            "domain": "slideshare.net",
            "type": "document",
            "dofollow": False,
            "url": "https://www.slideshare.net",
        },
        {
            "name": "Scoop.it",
            "domain": "scoop.it",
            "type": "curation",
            "dofollow": True,
            "url": "https://www.scoop.it",
        },
        {
            "name": "Pearltrees",
            "domain": "pearltrees.com",
            "type": "curation",
            "dofollow": True,
            "url": "https://www.pearltrees.com",
        },
        {
            "name": "Diigo",
            "domain": "diigo.com",
            "type": "bookmarking",
            "dofollow": False,
            "url": "https://www.diigo.com",
        },
        {
            "name": "Pinterest",
            "domain": "pinterest.com",
            "type": "social",
            "dofollow": False,
            "url": "https://www.pinterest.fr",
        },
        {
            "name": "Quora",
            "domain": "quora.com",
            "type": "qa",
            "dofollow": False,
            "url": "https://fr.quora.com",
        },
    ]

    SEARCH_PATTERNS = [
        '"{keyword}" site:medium.com',
        '"{keyword}" site:quora.com',
        '"{keyword}" site:scoop.it',
        '"{keyword}" "guest post" OR "article invité"',
        '"{keyword}" "write for us" OR "écrire pour nous"',
        '"{keyword}" "contributeur" OR "contributor"',
        '"{keyword}" "publiez votre article"',
    ]

    def _find_guest_post_opportunities(self, keywords: list[str]) -> list[BacklinkOpportunity]:
        """Cherche des opportunités de guest posting."""
        opportunities = []
        seen_domains = set()

        for keyword in keywords[:5]:
            for pattern in self.SEARCH_PATTERNS:
                query = pattern.format(keyword=keyword)
                logger.info(f"[Web2.0] Recherche: {query}")

                urls = self.search_google(query, num_results=10)
                for url in urls:
                    domain = urlparse(url).netloc
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    soup = self.fetch_page(url)
                    if not soup:
                        continue

                    title = ""
                    title_tag = soup.find("title")
                    if title_tag:
                        title = title_tag.get_text(strip=True)

                    description = ""
                    meta_desc = soup.find("meta", attrs={"name": "description"})
                    if meta_desc:
                        description = meta_desc.get("content", "")

                    opp = BacklinkOpportunity(
                        url=url,
                        domain=domain,
                        type="guest_post",
                        title=title,
                        description=description,
                        dofollow=True,
                        comment_form=False,
                        registration_required=True,
                        language=self.site_config.get("language", "fr"),
                        meta={"source": "guest_post_search"},
                    )
                    opportunities.append(opp)
                    self._respectful_delay()

        return opportunities

    def find_opportunities(self, keywords: list[str]) -> list[BacklinkOpportunity]:
        """Trouve des plateformes Web 2.0 et guest posts."""
        opportunities = []

        # Ajouter les plateformes Web 2.0 connues
        for platform in self.WEB2_PLATFORMS:
            opp = BacklinkOpportunity(
                url=platform["url"],
                domain=platform["domain"],
                type="web2.0",
                title=platform["name"],
                description=f"Plateforme {platform['type']} - {platform['name']}",
                dofollow=platform["dofollow"],
                comment_form=False,
                registration_required=True,
                language="multi",
                meta={
                    "platform_type": platform["type"],
                    "platform_name": platform["name"],
                },
            )
            opportunities.append(opp)

        # Chercher des opportunités de guest posting
        guest_posts = self._find_guest_post_opportunities(keywords)
        opportunities.extend(guest_posts)

        return opportunities
