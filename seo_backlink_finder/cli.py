"""Interface en ligne de commande pour SEO Backlink Finder."""

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from . import __version__
from .config import load_config, list_configs, create_config
from .runner import run_scan, SCRAPER_CLASSES

console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_scan(args):
    """Commande principale: lancer un scan."""
    config = load_config(args.config)

    # Override des mots-clés si fournis en CLI
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]

    # Sources à scanner
    sources = None
    if args.sources:
        sources = [s.strip() for s in args.sources.split(",")]

    console.print(Panel(
        f"[bold]SEO Backlink Finder v{__version__}[/bold]\n"
        f"Site: {config['site']['name']} ({config['site']['url']})\n"
        f"Sources: {', '.join(sources or SCRAPER_CLASSES.keys())}\n"
        f"Mots-clés: {len(keywords or config['site']['keywords'])} configurés",
        title="Configuration du scan",
        border_style="blue",
    ))

    try:
        with console.status("[bold green]Scan en cours..."):
            results = run_scan(config, sources=sources, keywords=keywords)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interruption - aucun résultat à sauvegarder.[/bold yellow]")
        return

    # Afficher le résumé
    summary = results["summary"]
    if summary.get("interrupted"):
        console.print(Panel(
            "[bold yellow]Scan interrompu par l'utilisateur (Ctrl+C)[/bold yellow]\n"
            "Les résultats partiels ont été sauvegardés.",
            border_style="yellow",
        ))
    console.print()
    console.print(Panel(
        f"Total: [bold]{summary['total']}[/bold] opportunités\n"
        f"DoFollow: [green]{summary['dofollow_count']}[/green] | "
        f"NoFollow: [red]{summary['nofollow_count']}[/red]\n"
        f"Accès libre: [green]{summary['open_access']}[/green] | "
        f"Inscription: [yellow]{summary['needs_registration']}[/yellow]\n"
        f"Score moyen: [bold]{summary['average_score']}[/bold]",
        title="Résumé",
        border_style="green",
    ))

    # Tableau par type
    if summary.get("by_type"):
        type_table = Table(title="Par type de source")
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Nombre", justify="right", style="bold")
        type_labels = {
            "blog_comment": "Blogs (Commentaires)",
            "forum": "Forums",
            "directory": "Annuaires",
            "guest_post": "Guest Posts",
            "web2.0": "Web 2.0",
        }
        for t, count in summary["by_type"].items():
            type_table.add_row(type_labels.get(t, t), str(count))
        console.print(type_table)

    # Top 20 des opportunités
    opportunities = results["opportunities"][:20]
    if opportunities:
        table = Table(title=f"Top {len(opportunities)} opportunités")
        table.add_column("Score", justify="right", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Domaine", style="blue")
        table.add_column("DoFollow", justify="center")
        table.add_column("Accès", justify="center")
        table.add_column("Titre", max_width=50)

        type_labels = {
            "blog_comment": "Blog",
            "forum": "Forum",
            "directory": "Annuaire",
            "guest_post": "Guest",
            "web2.0": "Web2.0",
        }

        for opp in opportunities:
            score_style = (
                "green" if opp.relevance_score >= 70
                else "yellow" if opp.relevance_score >= 40
                else "red"
            )
            dofollow = "[green]YES[/green]" if opp.dofollow else "[red]no[/red]"
            access = (
                "[green]Libre[/green]"
                if opp.comment_form and not opp.registration_required
                else "[yellow]Inscr.[/yellow]" if opp.registration_required
                else "-"
            )
            table.add_row(
                f"[{score_style}]{opp.relevance_score}[/{score_style}]",
                type_labels.get(opp.type, opp.type),
                opp.domain[:40],
                dofollow,
                access,
                opp.title[:50] if opp.title else "",
            )
        console.print(table)

    # Fichiers exportés
    if results["exported_files"]:
        console.print()
        console.print("[bold]Fichiers exportés:[/bold]")
        for fmt, path in results["exported_files"].items():
            console.print(f"  [{fmt.upper()}] {path}")


def cmd_list_configs(args):
    """Liste les configurations disponibles."""
    configs = list_configs()
    if not configs:
        console.print("[yellow]Aucune configuration de site trouvée.[/yellow]")
        console.print("Créez-en une avec: seo-backlinks new-site --name 'Mon Site' --url 'https://...'")
        return

    table = Table(title="Configurations disponibles")
    table.add_column("Nom", style="cyan")
    for c in configs:
        table.add_row(c)
    console.print(table)


def cmd_new_site(args):
    """Crée une nouvelle configuration de site."""
    keywords = [k.strip() for k in args.keywords.split(",")]
    filepath = create_config(
        name=args.name,
        url=args.url,
        keywords=keywords,
        language=args.language,
        country=args.country,
    )
    console.print(f"[green]Configuration créée: {filepath}[/green]")
    console.print(f"Utilisez-la avec: seo-backlinks scan --config {filepath.stem}.yaml")


def main():
    parser = argparse.ArgumentParser(
        prog="seo-backlinks",
        description="SEO Backlink Finder - Trouvez des opportunités de backlinks dans votre thématique",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Mode verbeux (debug)")

    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")

    # Commande scan
    scan_parser = subparsers.add_parser("scan", help="Lancer un scan de backlinks")
    scan_parser.add_argument(
        "-c", "--config",
        help="Fichier de configuration du site (ex: pharmacie-provencale.yaml)",
    )
    scan_parser.add_argument(
        "-s", "--sources",
        help="Sources à scanner, séparées par des virgules (blogs,forums,directories,web2)",
    )
    scan_parser.add_argument(
        "-k", "--keywords",
        help="Mots-clés séparés par des virgules (override la config)",
    )

    # Commande list
    subparsers.add_parser("list", help="Lister les configurations disponibles")

    # Commande new-site
    new_parser = subparsers.add_parser("new-site", help="Créer une nouvelle configuration de site")
    new_parser.add_argument("--name", required=True, help="Nom du site")
    new_parser.add_argument("--url", required=True, help="URL du site")
    new_parser.add_argument(
        "--keywords", required=True,
        help="Mots-clés séparés par des virgules",
    )
    new_parser.add_argument("--language", default="fr", help="Code langue (défaut: fr)")
    new_parser.add_argument("--country", default="FR", help="Code pays (défaut: FR)")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "list":
        cmd_list_configs(args)
    elif args.command == "new-site":
        cmd_new_site(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
