"""Module de scoring et d'analyse des opportunités de backlinks."""

import logging
from urllib.parse import urlparse

from seo_backlink_finder.scrapers.base import BacklinkOpportunity

logger = logging.getLogger(__name__)


class OpportunityScorer:
    """Calcule un score pour chaque opportunité de backlink trouvée."""

    def __init__(self, config: dict):
        self.config = config
        weights = config.get("scoring", {}).get("weights", {})
        self.w_authority = weights.get("domain_authority", 25)
        self.w_relevance = weights.get("relevance", 30)
        self.w_dofollow = weights.get("dofollow", 20)
        self.w_comment = weights.get("comment_open", 15)
        self.w_age = weights.get("page_age", 10)
        self.keywords = config.get("site", {}).get("keywords", [])

    def _score_relevance(self, opp: BacklinkOpportunity) -> float:
        """Score de pertinence basé sur les mots-clés dans le titre/description."""
        text = f"{opp.title} {opp.description}".lower()
        if not self.keywords:
            return 50.0

        matched = 0
        for kw in self.keywords:
            kw_words = kw.lower().split()
            if any(word in text for word in kw_words):
                matched += 1

        ratio = matched / len(self.keywords) if self.keywords else 0
        return min(ratio * 150, 100)  # Bonus si beaucoup de mots-clés matchent

    def _score_domain(self, opp: BacklinkOpportunity) -> float:
        """Score basé sur la qualité estimée du domaine."""
        domain = opp.domain.lower()
        score = 50.0  # Score de base

        # Bonus pour les extensions de confiance
        trust_tlds = [".gov", ".edu", ".org", ".fr", ".eu"]
        if any(domain.endswith(tld) for tld in trust_tlds):
            score += 20

        # Bonus pour les domaines connus
        high_authority = [
            "medium.com", "quora.com", "wordpress.com", "tumblr.com",
            "slideshare.net", "scoop.it", "pearltrees.com",
        ]
        if any(ha in domain for ha in high_authority):
            score += 25

        # Malus pour les domaines suspects
        spam_signals = [
            "free", "cheap", "buy-link", "seo-", "backlink",
            "link-exchange", "spam",
        ]
        if any(s in domain for s in spam_signals):
            score -= 30

        return max(0, min(score, 100))

    def _score_type(self, opp: BacklinkOpportunity) -> float:
        """Score selon le type d'opportunité."""
        type_scores = {
            "blog_comment": 60,
            "forum": 65,
            "directory": 50,
            "guest_post": 85,
            "web2.0": 55,
        }
        return type_scores.get(opp.type, 50)

    def score_opportunity(self, opp: BacklinkOpportunity) -> float:
        """Calcule le score global d'une opportunité (0-100).

        Le score est une combinaison pondérée de:
        - Autorité du domaine (estimée)
        - Pertinence thématique
        - Dofollow vs nofollow
        - Accessibilité (formulaire ouvert, inscription, etc.)
        - Type d'opportunité
        """
        relevance = self._score_relevance(opp)
        domain_score = self._score_domain(opp)
        type_score = self._score_type(opp)
        dofollow_score = 100 if opp.dofollow else 30
        access_score = 80 if opp.comment_form and not opp.registration_required else (
            50 if opp.comment_form else 30
        )

        total = (
            (domain_score * self.w_authority / 100)
            + (relevance * self.w_relevance / 100)
            + (dofollow_score * self.w_dofollow / 100)
            + (access_score * self.w_comment / 100)
            + (type_score * self.w_age / 100)
        )

        return round(min(total, 100), 1)

    def score_all(self, opportunities: list[BacklinkOpportunity]) -> list[BacklinkOpportunity]:
        """Score et trie toutes les opportunités."""
        for opp in opportunities:
            opp.relevance_score = self.score_opportunity(opp)

        # Trier par score décroissant
        opportunities.sort(key=lambda o: o.relevance_score, reverse=True)
        return opportunities

    def filter_duplicates(self, opportunities: list[BacklinkOpportunity]) -> list[BacklinkOpportunity]:
        """Supprime les doublons basés sur le domaine."""
        seen_domains = {}
        unique = []

        for opp in opportunities:
            domain = opp.domain
            if domain in seen_domains:
                # Garder celui avec le meilleur score
                existing = seen_domains[domain]
                if opp.relevance_score > existing.relevance_score:
                    unique.remove(existing)
                    unique.append(opp)
                    seen_domains[domain] = opp
            else:
                seen_domains[domain] = opp
                unique.append(opp)

        return unique

    def get_summary(self, opportunities: list[BacklinkOpportunity]) -> dict:
        """Génère un résumé des opportunités trouvées."""
        if not opportunities:
            return {"total": 0}

        by_type = {}
        for opp in opportunities:
            by_type.setdefault(opp.type, []).append(opp)

        dofollow_count = sum(1 for o in opportunities if o.dofollow)
        avg_score = sum(o.relevance_score for o in opportunities) / len(opportunities)

        return {
            "total": len(opportunities),
            "by_type": {t: len(ops) for t, ops in by_type.items()},
            "dofollow_count": dofollow_count,
            "nofollow_count": len(opportunities) - dofollow_count,
            "average_score": round(avg_score, 1),
            "top_score": opportunities[0].relevance_score if opportunities else 0,
            "needs_registration": sum(1 for o in opportunities if o.registration_required),
            "open_access": sum(1 for o in opportunities if o.comment_form and not o.registration_required),
        }
