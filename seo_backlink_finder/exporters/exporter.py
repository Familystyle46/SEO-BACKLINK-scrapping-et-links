"""Module d'export des résultats en CSV, JSON et HTML."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from seo_backlink_finder.scrapers.base import BacklinkOpportunity

logger = logging.getLogger(__name__)


class ResultExporter:
    """Exporte les résultats de recherche de backlinks."""

    def __init__(self, config: dict):
        self.config = config
        self.output_dir = Path(config.get("export", {}).get("output_dir", "output"))
        self.site_name = config.get("site", {}).get("name", "unknown")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _make_filename(self, extension: str) -> Path:
        """Génère un nom de fichier avec horodatage."""
        safe_name = self.site_name.lower().replace(" ", "-").replace(".", "-")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"backlinks_{safe_name}_{timestamp}.{extension}"

    def export_csv(self, opportunities: list[BacklinkOpportunity],
                   summary: dict) -> Path:
        """Exporte en CSV."""
        filepath = self._make_filename("csv")

        fieldnames = [
            "score", "type", "url", "domain", "title",
            "dofollow", "comment_form", "registration_required",
            "language", "description",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for opp in opportunities:
                row = opp.to_dict()
                row["score"] = opp.relevance_score
                writer.writerow(row)

        logger.info(f"CSV exporté: {filepath}")
        return filepath

    def export_json(self, opportunities: list[BacklinkOpportunity],
                    summary: dict) -> Path:
        """Exporte en JSON."""
        filepath = self._make_filename("json")

        data = {
            "metadata": {
                "site": self.site_name,
                "url": self.config.get("site", {}).get("url", ""),
                "generated_at": datetime.now().isoformat(),
                "total_results": len(opportunities),
            },
            "summary": summary,
            "opportunities": [
                {**opp.to_dict(), "score": opp.relevance_score}
                for opp in opportunities
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON exporté: {filepath}")
        return filepath

    def export_html(self, opportunities: list[BacklinkOpportunity],
                    summary: dict) -> Path:
        """Exporte en rapport HTML interactif."""
        filepath = self._make_filename("html")

        type_labels = {
            "blog_comment": "Blog (Commentaire)",
            "forum": "Forum",
            "directory": "Annuaire",
            "guest_post": "Guest Post",
            "web2.0": "Web 2.0",
        }

        type_colors = {
            "blog_comment": "#3498db",
            "forum": "#2ecc71",
            "directory": "#e67e22",
            "guest_post": "#9b59b6",
            "web2.0": "#1abc9c",
        }

        rows_html = ""
        for opp in opportunities:
            score_color = (
                "#27ae60" if opp.relevance_score >= 70
                else "#f39c12" if opp.relevance_score >= 40
                else "#e74c3c"
            )
            type_color = type_colors.get(opp.type, "#95a5a6")
            dofollow_badge = (
                '<span class="badge dofollow">DoFollow</span>'
                if opp.dofollow
                else '<span class="badge nofollow">NoFollow</span>'
            )
            access_badge = ""
            if opp.comment_form and not opp.registration_required:
                access_badge = '<span class="badge open">Accès libre</span>'
            elif opp.registration_required:
                access_badge = '<span class="badge reg">Inscription</span>'

            rows_html += f"""
            <tr data-type="{opp.type}" data-dofollow="{str(opp.dofollow).lower()}">
                <td><strong style="color:{score_color}">{opp.relevance_score}</strong></td>
                <td><span class="type-badge" style="background:{type_color}">{type_labels.get(opp.type, opp.type)}</span></td>
                <td><a href="{opp.url}" target="_blank" rel="noopener">{opp.domain}</a></td>
                <td class="title-cell">{opp.title[:80]}</td>
                <td>{dofollow_badge}</td>
                <td>{access_badge}</td>
            </tr>"""

        by_type_html = ""
        for t, count in summary.get("by_type", {}).items():
            color = type_colors.get(t, "#95a5a6")
            label = type_labels.get(t, t)
            by_type_html += f'<div class="stat-item"><span class="stat-label" style="border-left:4px solid {color};padding-left:8px">{label}</span><span class="stat-value">{count}</span></div>'

        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Backlinks - {self.site_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; color: #2c3e50; line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        header {{ background: linear-gradient(135deg, #2c3e50, #3498db); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        header h1 {{ font-size: 1.8em; margin-bottom: 5px; }}
        header p {{ opacity: 0.9; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); text-align: center; }}
        .summary-card .number {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .summary-card .label {{ color: #7f8c8d; font-size: 0.9em; }}
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
        .stats-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
        .stats-box h3 {{ margin-bottom: 10px; color: #2c3e50; }}
        .stat-item {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #ecf0f1; }}
        .stat-value {{ font-weight: bold; }}
        .filters {{ background: white; padding: 15px 20px; border-radius: 10px; margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
        .filters label {{ font-weight: 600; margin-right: 5px; }}
        .filters select, .filters input {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
        th {{ background: #2c3e50; color: white; padding: 12px 15px; text-align: left; font-weight: 600; cursor: pointer; }}
        th:hover {{ background: #34495e; }}
        td {{ padding: 10px 15px; border-bottom: 1px solid #ecf0f1; }}
        tr:hover {{ background: #f8f9fa; }}
        .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }}
        .dofollow {{ background: #d4efdf; color: #27ae60; }}
        .nofollow {{ background: #fadbd8; color: #e74c3c; }}
        .open {{ background: #d5f5e3; color: #1e8449; }}
        .reg {{ background: #fdebd0; color: #e67e22; }}
        .type-badge {{ color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }}
        .title-cell {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .footer {{ text-align: center; color: #95a5a6; margin-top: 20px; padding: 15px; }}
        @media (max-width: 768px) {{ .stats-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>Rapport Backlinks</h1>
        <p>{self.site_name} - {self.config.get("site", {}).get("url", "")} | {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
    </header>

    <div class="summary">
        <div class="summary-card"><div class="number">{summary.get("total", 0)}</div><div class="label">Opportunit&eacute;s trouv&eacute;es</div></div>
        <div class="summary-card"><div class="number">{summary.get("dofollow_count", 0)}</div><div class="label">DoFollow</div></div>
        <div class="summary-card"><div class="number">{summary.get("open_access", 0)}</div><div class="label">Acc&egrave;s libre</div></div>
        <div class="summary-card"><div class="number">{summary.get("average_score", 0)}</div><div class="label">Score moyen</div></div>
    </div>

    <div class="stats-grid">
        <div class="stats-box"><h3>Par type</h3>{by_type_html}</div>
        <div class="stats-box"><h3>Acc&egrave;s</h3>
            <div class="stat-item"><span class="stat-label">Acc&egrave;s libre</span><span class="stat-value">{summary.get("open_access", 0)}</span></div>
            <div class="stat-item"><span class="stat-label">Inscription requise</span><span class="stat-value">{summary.get("needs_registration", 0)}</span></div>
            <div class="stat-item"><span class="stat-label">DoFollow</span><span class="stat-value">{summary.get("dofollow_count", 0)}</span></div>
            <div class="stat-item"><span class="stat-label">NoFollow</span><span class="stat-value">{summary.get("nofollow_count", 0)}</span></div>
        </div>
    </div>

    <div class="filters">
        <label>Type:</label>
        <select id="filterType" onchange="filterTable()">
            <option value="all">Tous</option>
            <option value="blog_comment">Blog (Commentaire)</option>
            <option value="forum">Forum</option>
            <option value="directory">Annuaire</option>
            <option value="guest_post">Guest Post</option>
            <option value="web2.0">Web 2.0</option>
        </select>
        <label>Lien:</label>
        <select id="filterDofollow" onchange="filterTable()">
            <option value="all">Tous</option>
            <option value="true">DoFollow</option>
            <option value="false">NoFollow</option>
        </select>
        <label>Recherche:</label>
        <input type="text" id="searchInput" placeholder="Filtrer..." oninput="filterTable()">
    </div>

    <table id="resultsTable">
        <thead>
            <tr>
                <th onclick="sortTable(0)">Score</th>
                <th onclick="sortTable(1)">Type</th>
                <th onclick="sortTable(2)">Domaine</th>
                <th onclick="sortTable(3)">Titre</th>
                <th onclick="sortTable(4)">Lien</th>
                <th onclick="sortTable(5)">Acc&egrave;s</th>
            </tr>
        </thead>
        <tbody>{rows_html}
        </tbody>
    </table>

    <div class="footer">
        <p>G&eacute;n&eacute;r&eacute; par SEO Backlink Finder v1.0</p>
    </div>
</div>
<script>
function filterTable() {{
    const type = document.getElementById('filterType').value;
    const dofollow = document.getElementById('filterDofollow').value;
    const search = document.getElementById('searchInput').value.toLowerCase();
    const rows = document.querySelectorAll('#resultsTable tbody tr');
    rows.forEach(row => {{
        const matchType = type === 'all' || row.dataset.type === type;
        const matchDofollow = dofollow === 'all' || row.dataset.dofollow === dofollow;
        const matchSearch = !search || row.textContent.toLowerCase().includes(search);
        row.style.display = matchType && matchDofollow && matchSearch ? '' : 'none';
    }});
}}
let sortDir = {{}};
function sortTable(col) {{
    const table = document.getElementById('resultsTable');
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    sortDir[col] = !sortDir[col];
    rows.sort((a, b) => {{
        let aVal = a.cells[col].textContent.trim();
        let bVal = b.cells[col].textContent.trim();
        if (!isNaN(aVal) && !isNaN(bVal)) {{ aVal = parseFloat(aVal); bVal = parseFloat(bVal); }}
        if (aVal < bVal) return sortDir[col] ? -1 : 1;
        if (aVal > bVal) return sortDir[col] ? 1 : -1;
        return 0;
    }});
    const tbody = table.querySelector('tbody');
    rows.forEach(row => tbody.appendChild(row));
}}
</script>
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"HTML exporté: {filepath}")
        return filepath

    def export_all(self, opportunities: list[BacklinkOpportunity],
                   summary: dict) -> dict[str, Path]:
        """Exporte dans tous les formats configurés."""
        formats = self.config.get("export", {}).get("formats", ["csv", "json", "html"])
        results = {}

        export_methods = {
            "csv": self.export_csv,
            "json": self.export_json,
            "html": self.export_html,
        }

        for fmt in formats:
            if fmt in export_methods:
                results[fmt] = export_methods[fmt](opportunities, summary)

        return results
