"""Scraper pour trouver des forums dans la thématique."""

import logging
from urllib.parse import urlparse

from .base import BacklinkOpportunity, BaseScraper

logger = logging.getLogger(__name__)


class ForumScraper(BaseScraper):
    """Recherche des forums où poster dans la thématique."""

    SEARCH_PATTERNS = [
        '"{keyword}" forum',
        '"{keyword}" "forum" site:.fr',
        '"{keyword}" "rejoindre la discussion"',
        '"{keyword}" "inscription gratuite" forum',
        '"{keyword}" inurl:forum',
        '"{keyword}" inurl:viewtopic',
        '"{keyword}" inurl:showthread',
        '"{keyword}" "powered by phpBB"',
        '"{keyword}" "powered by vBulletin"',
        '"{keyword}" "powered by SMF"',
        '"{keyword}" "powered by XenForo"',
        '"{keyword}" "powered by Discourse"',
        '"{keyword}" "créer un sujet" OR "nouveau sujet"',
        '"{keyword}" forum discussion communauté',
        '"{keyword}" "s\'inscrire" forum santé',
    ]

    FORUM_INDICATORS = [
        "forum", "viewtopic", "showthread", "viewforum",
        "phpbb", "vbulletin", "xenforo", "discourse",
        "community", "communaute", "discussion",
    ]

    FORUM_PLATFORMS = {
        "phpBB": ["phpbb", "powered by phpbb", "viewtopic.php"],
        "vBulletin": ["vbulletin", "powered by vbulletin", "showthread.php"],
        "XenForo": ["xenforo", "powered by xenforo"],
        "SMF": ["simple machines", "powered by smf"],
        "Discourse": ["discourse", "powered by discourse"],
        "MyBB": ["mybb", "powered by mybb"],
        "Invision": ["invision", "powered by invision", "ips community"],
    }

    def _is_forum(self, soup, url: str) -> bool:
        """Vérifie si la page est un forum."""
        url_lower = url.lower()
        if any(ind in url_lower for ind in self.FORUM_INDICATORS):
            return True

        page_text = soup.get_text().lower()
        forum_signals = [
            "forum", "sujet", "topic", "thread", "répondre", "reply",
            "message", "post", "membre", "member", "inscription", "register",
        ]
        signal_count = sum(1 for s in forum_signals if s in page_text)
        return signal_count >= 3

    def _detect_platform(self, soup, url: str) -> str:
        """Détecte la plateforme du forum."""
        page_html = str(soup).lower()
        for platform, indicators in self.FORUM_PLATFORMS.items():
            if any(ind in page_html for ind in indicators):
                return platform
        return "unknown"

    def _check_registration(self, soup) -> bool:
        """Vérifie si une inscription est requise pour poster."""
        page_text = soup.get_text().lower()
        reg_signals = [
            "inscription", "register", "s'inscrire", "créer un compte",
            "sign up", "connectez-vous pour répondre",
            "vous devez être inscrit", "you must be logged in",
        ]
        return any(s in page_text for s in reg_signals)

    def _check_dofollow_links(self, soup) -> bool:
        """Vérifie si les liens des posts sont dofollow."""
        post_areas = soup.select(
            ".post-content a, .message-body a, .postbody a, "
            ".post_body a, .entry-content a, article a"
        )
        for link in post_areas:
            rel = link.get("rel", [])
            if isinstance(rel, str):
                rel = rel.split()
            if "nofollow" not in rel and link.get("href", "").startswith("http"):
                return True
        return False

    def _count_activity(self, soup) -> dict:
        """Estime l'activité du forum."""
        page_text = soup.get_text()

        # Chercher des indicateurs de nombre de sujets/messages
        topics = 0
        members = 0

        stats = soup.find(["div", "ul", "p"], class_=lambda c: c and "stat" in str(c).lower())
        if stats:
            import re
            numbers = re.findall(r"(\d[\d\s,.]*)", stats.get_text())
            if len(numbers) >= 1:
                topics = int(numbers[0].replace(" ", "").replace(",", "").replace(".", ""))

        return {"estimated_topics": topics, "estimated_members": members}

    def _analyze_forum(self, url: str) -> BacklinkOpportunity | None:
        """Analyse une page pour déterminer si c'est un forum intéressant."""
        soup = self.fetch_page(url)
        if not soup:
            return None

        if not self._is_forum(soup, url):
            return None

        domain = urlparse(url).netloc
        platform = self._detect_platform(soup, url)
        registration_required = self._check_registration(soup)
        dofollow = self._check_dofollow_links(soup)
        activity = self._count_activity(soup)

        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")

        return BacklinkOpportunity(
            url=url,
            domain=domain,
            type="forum",
            title=title,
            description=description,
            dofollow=dofollow,
            comment_form=True,
            registration_required=registration_required,
            language=self.site_config.get("language", "fr"),
            meta={
                "platform": platform,
                **activity,
            },
        )

    def find_opportunities(self, keywords: list[str]) -> list[BacklinkOpportunity]:
        """Trouve des forums dans la thématique."""
        opportunities = []
        seen_domains = set()

        for keyword in keywords:
            for pattern in self.SEARCH_PATTERNS:
                query = pattern.format(keyword=keyword)
                logger.info(f"[Forum] Recherche: {query}")

                urls = self.search_google(query, num_results=20)
                for url in urls:
                    domain = urlparse(url).netloc
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    opp = self._analyze_forum(url)
                    if opp:
                        logger.info(f"  -> Forum trouvé: {opp.domain} ({opp.meta.get('platform', '?')})")
                        opportunities.append(opp)
                    self._respectful_delay()

        return opportunities
