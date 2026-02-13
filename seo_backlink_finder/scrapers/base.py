"""Classe de base pour tous les scrapers."""

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


@dataclass
class BacklinkOpportunity:
    """Représente une opportunité de backlink trouvée."""

    url: str
    domain: str
    type: str  # "blog_comment", "forum", "directory", "guest_post", "web2.0"
    title: str = ""
    description: str = ""
    relevance_score: float = 0.0
    dofollow: bool = False
    comment_form: bool = False
    registration_required: bool = False
    language: str = ""
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "domain": self.domain,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "relevance_score": round(self.relevance_score, 2),
            "dofollow": self.dofollow,
            "comment_form": self.comment_form,
            "registration_required": self.registration_required,
            "language": self.language,
            **self.meta,
        }


class BaseScraper(ABC):
    """Classe abstraite pour les scrapers de backlinks."""

    def __init__(self, config: dict):
        self.config = config
        self.search_config = config.get("search", {})
        self.site_config = config.get("site", {})
        self.delay = self.search_config.get("delay_between_requests", 5)
        self.timeout = self.search_config.get("request_timeout", 15)
        self.max_results = self.search_config.get("max_results_per_query", 30)
        self.google_delay_min = self.search_config.get("google_delay_min", 8)
        self.google_delay_max = self.search_config.get("google_delay_max", 15)
        self.max_retries = self.search_config.get("max_retries_on_429", 3)
        self._ua = UserAgent(fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": f"{self.site_config.get('language', 'fr')},en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        return session

    def _get_headers(self) -> dict:
        return {"User-Agent": self._ua.random}

    def _respectful_delay(self):
        """Attend entre les requêtes pour ne pas surcharger les serveurs."""
        time.sleep(self.delay)

    def _google_delay(self):
        """Délai randomisé plus long entre les requêtes Google."""
        delay = random.uniform(self.google_delay_min, self.google_delay_max)
        logger.debug(f"Pause Google: {delay:.1f}s")
        time.sleep(delay)

    def fetch_page(self, url: str) -> BeautifulSoup | None:
        """Récupère et parse une page web.

        Returns:
            BeautifulSoup object ou None si erreur.
        """
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            logger.debug(f"Erreur fetch {url}: {e}")
            return None

    def search_google(self, query: str, num_results: int = 30) -> list[str]:
        """Effectue une recherche Google et retourne les URLs des résultats.

        Utilise le scraping direct de Google Search avec retry et backoff
        exponentiel en cas de rate-limiting (429).
        """
        urls = []
        lang = self.site_config.get("language", "fr")
        country = self.site_config.get("country", "FR")
        consecutive_429 = 0

        for start in range(0, min(num_results, self.max_results), 10):
            search_url = (
                f"https://www.google.com/search"
                f"?q={requests.utils.quote(query)}"
                f"&hl={lang}&gl={country}&start={start}&num=10"
            )

            success = False
            for retry in range(self.max_retries + 1):
                try:
                    response = self.session.get(
                        search_url,
                        headers=self._get_headers(),
                        timeout=self.timeout,
                    )

                    if response.status_code == 429:
                        consecutive_429 += 1
                        backoff = min(30 + (2 ** retry) * 15, 120)
                        jitter = random.uniform(0, backoff * 0.3)
                        wait = backoff + jitter
                        logger.warning(
                            f"Google 429 (tentative {retry + 1}/{self.max_retries + 1}) "
                            f"- pause de {wait:.0f}s avant retry"
                        )
                        time.sleep(wait)

                        if consecutive_429 >= 3:
                            logger.warning(
                                "Trop de 429 consécutifs - arrêt de cette recherche "
                                "pour éviter un blocage prolongé"
                            )
                            return urls[:num_results]
                        continue

                    response.raise_for_status()
                    consecutive_429 = 0
                    soup = BeautifulSoup(response.text, "lxml")

                    for link in soup.select("div.g a[href]"):
                        href = link.get("href", "")
                        if href.startswith("http") and "google.com" not in href:
                            if href not in urls:
                                urls.append(href)

                    # Fallback: chercher dans tous les liens
                    if not urls:
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            if href.startswith("/url?q="):
                                clean = href.split("/url?q=")[1].split("&")[0]
                                if clean.startswith("http") and "google.com" not in clean:
                                    if clean not in urls:
                                        urls.append(clean)

                    success = True
                    break

                except requests.RequestException as e:
                    if retry < self.max_retries:
                        backoff = (2 ** retry) * 10
                        logger.warning(
                            f"Erreur recherche Google (start={start}, "
                            f"tentative {retry + 1}): {e} - retry dans {backoff}s"
                        )
                        time.sleep(backoff)
                    else:
                        logger.warning(
                            f"Erreur recherche Google (start={start}): {e} "
                            f"- abandon après {self.max_retries + 1} tentatives"
                        )

            if success:
                self._google_delay()

            if len(urls) >= num_results:
                break

        return urls[:num_results]

    @abstractmethod
    def find_opportunities(self, keywords: list[str]) -> list[BacklinkOpportunity]:
        """Cherche des opportunités de backlinks.

        Args:
            keywords: Mots-clés de la thématique.

        Returns:
            Liste d'opportunités trouvées.
        """
        ...
