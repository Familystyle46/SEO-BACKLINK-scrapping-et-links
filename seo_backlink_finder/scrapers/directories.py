"""Scraper pour trouver des annuaires et sites de soumission."""

import logging
from urllib.parse import urlparse

from .base import BacklinkOpportunity, BaseScraper

logger = logging.getLogger(__name__)


class DirectoryScraper(BaseScraper):
    """Recherche des annuaires web, annuaires thématiques et sites de soumission."""

    SEARCH_PATTERNS = [
        '"{keyword}" annuaire',
        '"{keyword}" "soumettre un site"',
        '"{keyword}" "proposer un site"',
        '"{keyword}" "ajouter un site"',
        '"{keyword}" "inscrire un site"',
        '"{keyword}" annuaire gratuit',
        '"{keyword}" "référencement gratuit"',
        '"{keyword}" annuaire site:.fr',
        '"{keyword}" "submit your site"',
        '"{keyword}" "add your site"',
        '"{keyword}" directory listing',
        '"annuaire" "{keyword}" "inscription"',
        '"annuaire santé" OR "annuaire pharmacie" OR "annuaire bien-être"',
        '"annuaire professionnel" "{keyword}"',
    ]

    # Annuaires francophones connus
    KNOWN_DIRECTORIES = [
        "dmoz.org", "webrankinfo.com", "gralon.net", "1annuaire.com",
        "toplien.fr", "costaud.net", "el-annuaire.com", "net-liens.com",
        "yakeo.com", "dicoweb.com", "annuaire-gratuit.net",
        "indexa.fr", "coodoeil.fr", "netgo.fr", "prolinkr.com",
        "annuaire-web-france.com", "tagbox.fr", "compare-le-net.com",
    ]

    DIRECTORY_INDICATORS = [
        "annuaire", "directory", "soumettre", "submit",
        "proposer un site", "ajouter un site", "inscrire",
        "catégorie", "category", "référencer",
    ]

    def _is_directory(self, soup, url: str) -> bool:
        """Vérifie si le site est un annuaire."""
        domain = urlparse(url).netloc.lower()
        if any(known in domain for known in self.KNOWN_DIRECTORIES):
            return True

        url_lower = url.lower()
        if any(ind in url_lower for ind in ["annuaire", "directory", "submit"]):
            return True

        page_text = soup.get_text().lower()
        score = sum(1 for ind in self.DIRECTORY_INDICATORS if ind in page_text)
        return score >= 2

    def _has_submission_form(self, soup) -> bool:
        """Vérifie si le site a un formulaire de soumission."""
        # Chercher des liens ou formulaires de soumission
        submit_links = soup.find_all("a", href=True)
        for link in submit_links:
            text = link.get_text().lower()
            href = link.get("href", "").lower()
            if any(w in text for w in [
                "soumettre", "proposer", "ajouter", "inscrire",
                "submit", "add site", "suggest",
            ]) or any(w in href for w in [
                "submit", "soumettre", "proposer", "ajouter", "inscription",
            ]):
                return True

        # Chercher des formulaires
        for form in soup.find_all("form"):
            form_text = form.get_text().lower()
            if any(w in form_text for w in [
                "url", "site web", "website", "titre", "description",
                "catégorie", "category",
            ]):
                return True

        return False

    def _check_free_submission(self, soup) -> bool:
        """Vérifie si la soumission est gratuite."""
        page_text = soup.get_text().lower()
        paid_signals = ["payant", "premium", "paiement", "tarif", "€", "prix"]
        free_signals = ["gratuit", "free", "sans frais"]

        has_free = any(s in page_text for s in free_signals)
        has_paid = any(s in page_text for s in paid_signals)

        # Si gratuit mentionné ou si rien de payant mentionné
        return has_free or not has_paid

    def _detect_categories(self, soup) -> list[str]:
        """Détecte les catégories disponibles dans l'annuaire."""
        categories = []
        cat_links = soup.find_all("a", href=True)
        health_keywords = [
            "santé", "pharmacie", "médecine", "bien-être", "beauté",
            "cosmétique", "health", "wellness", "beauty", "medical",
            "parapharmacie", "nutrition", "fitness",
        ]
        for link in cat_links:
            text = link.get_text(strip=True).lower()
            if any(kw in text for kw in health_keywords):
                categories.append(link.get_text(strip=True))

        return list(set(categories))[:10]

    def _analyze_directory(self, url: str) -> BacklinkOpportunity | None:
        """Analyse un site pour déterminer si c'est un annuaire intéressant."""
        soup = self.fetch_page(url)
        if not soup:
            return None

        if not self._is_directory(soup, url):
            return None

        domain = urlparse(url).netloc
        has_form = self._has_submission_form(soup)
        is_free = self._check_free_submission(soup)
        categories = self._detect_categories(soup)

        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")

        # Vérifier dofollow sur les liens de l'annuaire
        dofollow = False
        external_links = soup.find_all("a", href=True)
        for link in external_links:
            href = link.get("href", "")
            if href.startswith("http") and domain not in href:
                rel = link.get("rel", [])
                if isinstance(rel, str):
                    rel = rel.split()
                if "nofollow" not in rel:
                    dofollow = True
                    break

        return BacklinkOpportunity(
            url=url,
            domain=domain,
            type="directory",
            title=title,
            description=description,
            dofollow=dofollow,
            comment_form=has_form,
            registration_required=not is_free,
            language=self.site_config.get("language", "fr"),
            meta={
                "free_submission": is_free,
                "has_submission_form": has_form,
                "relevant_categories": categories,
            },
        )

    def find_opportunities(self, keywords: list[str]) -> list[BacklinkOpportunity]:
        """Trouve des annuaires dans la thématique."""
        opportunities = []
        seen_domains = set()

        for keyword in keywords:
            for pattern in self.SEARCH_PATTERNS:
                query = pattern.format(keyword=keyword)
                logger.info(f"[Directory] Recherche: {query}")

                urls = self.search_google(query, num_results=15)
                for url in urls:
                    domain = urlparse(url).netloc
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    opp = self._analyze_directory(url)
                    if opp:
                        logger.info(f"  -> Annuaire trouvé: {opp.domain} (gratuit={opp.meta.get('free_submission')})")
                        opportunities.append(opp)
                    self._respectful_delay()

        return opportunities
