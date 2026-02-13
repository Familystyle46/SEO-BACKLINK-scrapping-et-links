"""Moteur principal qui orchestre tous les scrapers et l'analyse."""

import logging

from .scrapers.blog_comments import BlogCommentScraper
from .scrapers.forums import ForumScraper
from .scrapers.directories import DirectoryScraper
from .scrapers.web2_profiles import Web2ProfileScraper
from .scrapers.base import BacklinkOpportunity
from .analyzers.scorer import OpportunityScorer
from .exporters.exporter import ResultExporter

logger = logging.getLogger(__name__)


SCRAPER_CLASSES = {
    "blogs": BlogCommentScraper,
    "forums": ForumScraper,
    "directories": DirectoryScraper,
    "web2": Web2ProfileScraper,
}


def run_scan(config: dict, sources: list[str] | None = None,
             keywords: list[str] | None = None) -> dict:
    """Lance un scan complet de recherche de backlinks.

    Args:
        config: Configuration chargée.
        sources: Liste des types de sources à scanner.
                 Valeurs possibles: blogs, forums, directories, web2.
                 Si None, scanne toutes les sources.
        keywords: Mots-clés à utiliser. Si None, utilise ceux de la config.

    Returns:
        Dictionnaire avec les résultats, le résumé et les fichiers exportés.
    """
    if sources is None:
        sources = list(SCRAPER_CLASSES.keys())

    if keywords is None:
        keywords = config.get("site", {}).get("keywords", [])

    if not keywords:
        raise ValueError("Aucun mot-clé configuré. Ajoutez des mots-clés dans la config ou via --keywords.")

    all_opportunities: list[BacklinkOpportunity] = []
    interrupted = False

    # Exécuter chaque scraper
    for source_name in sources:
        if source_name not in SCRAPER_CLASSES:
            logger.warning(f"Source inconnue: {source_name}, ignorée.")
            continue

        scraper_class = SCRAPER_CLASSES[source_name]
        logger.info(f"=== Démarrage du scan: {source_name.upper()} ===")

        try:
            scraper = scraper_class(config)
            opportunities = scraper.find_opportunities(keywords)
            logger.info(f"  {source_name}: {len(opportunities)} opportunités trouvées")
            all_opportunities.extend(opportunities)
        except KeyboardInterrupt:
            logger.warning(f"  Interruption pendant {source_name} - sauvegarde des résultats partiels...")
            interrupted = True
            break
        except Exception as e:
            logger.error(f"  Erreur sur {source_name}: {e}")

    # Scoring et déduplication (même partiels)
    if interrupted:
        logger.info("=== Sauvegarde partielle des résultats ===")
    else:
        logger.info("=== Analyse et scoring ===")

    scorer = OpportunityScorer(config)
    all_opportunities = scorer.score_all(all_opportunities)
    all_opportunities = scorer.filter_duplicates(all_opportunities)
    summary = scorer.get_summary(all_opportunities)
    if interrupted:
        summary["interrupted"] = True

    # Export
    logger.info("=== Export des résultats ===")
    exporter = ResultExporter(config)
    exported_files = exporter.export_all(all_opportunities, summary)

    return {
        "opportunities": all_opportunities,
        "summary": summary,
        "exported_files": exported_files,
    }
