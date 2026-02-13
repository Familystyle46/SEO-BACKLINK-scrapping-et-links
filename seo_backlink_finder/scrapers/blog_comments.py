"""Scraper pour trouver des blogs avec commentaires ouverts."""

import logging
from urllib.parse import urlparse

from bs4 import Tag

from .base import BacklinkOpportunity, BaseScraper

logger = logging.getLogger(__name__)


class BlogCommentScraper(BaseScraper):
    """Recherche des blogs avec formulaires de commentaires ouverts."""

    # Requêtes Google spécialisées pour trouver des blogs avec commentaires
    SEARCH_PATTERNS = [
        '"{keyword}" "laisser un commentaire"',
        '"{keyword}" "ajouter un commentaire"',
        '"{keyword}" "leave a comment"',
        '"{keyword}" "poster un commentaire"',
        '"{keyword}" inurl:blog "commentaire"',
        '"{keyword}" "votre adresse e-mail" "commentaire"',
        '"{keyword}" "site web" "commentaire" "e-mail"',
        '"{keyword}" "Cet article vous a plu" commentaire',
        '"{keyword}" WordPress "commentaires"',
        '"{keyword}" blog article commentaire site:.fr',
        '"{keyword}" blog "répondre" "nom" "email"',
    ]

    def _has_comment_form(self, soup) -> bool:
        """Vérifie si la page contient un formulaire de commentaire."""
        # Formulaires WordPress classiques
        if soup.find("form", id="commentform"):
            return True
        if soup.find("textarea", id="comment"):
            return True
        if soup.find("div", id="respond"):
            return True

        # Formulaires génériques
        for form in soup.find_all("form"):
            form_text = form.get_text().lower()
            if any(w in form_text for w in [
                "commentaire", "comment", "laisser un message",
                "votre nom", "your name", "répondre", "reply",
            ]):
                textarea = form.find("textarea")
                if textarea:
                    return True

        # Sections de commentaires
        comment_sections = soup.find_all(
            ["div", "section"],
            class_=lambda c: c and any(
                w in str(c).lower()
                for w in ["comment", "commentaire", "respond", "discussion"]
            ),
        )
        for section in comment_sections:
            if section.find("textarea") or section.find("form"):
                return True

        return False

    def _check_dofollow(self, soup) -> bool:
        """Vérifie si les liens des commentaires sont dofollow."""
        comment_links = soup.select(".comment-content a, .comment-body a, .comments a")
        for link in comment_links:
            rel = link.get("rel", [])
            if isinstance(rel, str):
                rel = rel.split()
            if "nofollow" not in rel:
                return True
        # Si pas de liens dans les commentaires, par défaut nofollow
        return False

    def _extract_page_info(self, soup, url: str) -> dict:
        """Extrait les informations d'une page blog."""
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")

        # Compter les commentaires existants
        comment_count = 0
        comments_section = soup.find_all(
            ["div", "li", "article"],
            class_=lambda c: c and "comment" in str(c).lower(),
        )
        comment_count = len(comments_section)

        # Détecter la plateforme
        platform = "unknown"
        generator = soup.find("meta", attrs={"name": "generator"})
        if generator:
            gen_content = generator.get("content", "").lower()
            if "wordpress" in gen_content:
                platform = "wordpress"
            elif "drupal" in gen_content:
                platform = "drupal"
            elif "joomla" in gen_content:
                platform = "joomla"

        if soup.find("link", href=lambda h: h and "wp-content" in str(h)):
            platform = "wordpress"

        return {
            "title": title,
            "description": description,
            "comment_count": comment_count,
            "platform": platform,
        }

    def _analyze_blog(self, url: str) -> BacklinkOpportunity | None:
        """Analyse une page blog pour les opportunités de commentaires."""
        soup = self.fetch_page(url)
        if not soup:
            return None

        if not self._has_comment_form(soup):
            return None

        domain = urlparse(url).netloc
        info = self._extract_page_info(soup, url)
        dofollow = self._check_dofollow(soup)

        return BacklinkOpportunity(
            url=url,
            domain=domain,
            type="blog_comment",
            title=info["title"],
            description=info["description"],
            dofollow=dofollow,
            comment_form=True,
            registration_required=False,
            language=self.site_config.get("language", "fr"),
            meta={
                "comment_count": info["comment_count"],
                "platform": info["platform"],
            },
        )

    def find_opportunities(self, keywords: list[str]) -> list[BacklinkOpportunity]:
        """Trouve des blogs avec commentaires ouverts dans la thématique."""
        opportunities = []
        seen_domains = set()

        for keyword in keywords:
            for pattern in self.SEARCH_PATTERNS:
                query = pattern.format(keyword=keyword)
                logger.info(f"[BlogComment] Recherche: {query}")

                urls = self.search_google(query, num_results=20)
                for url in urls:
                    domain = urlparse(url).netloc
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    opp = self._analyze_blog(url)
                    if opp:
                        logger.info(f"  -> Trouvé: {opp.domain} (dofollow={opp.dofollow})")
                        opportunities.append(opp)
                    self._respectful_delay()

        return opportunities
