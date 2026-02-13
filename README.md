# SEO Backlink Finder

Outil de recherche automatique de backlinks dans votre thématique. Trouve des opportunités sur :
- **Blogs** avec commentaires ouverts
- **Forums** dans votre niche
- **Annuaires** web et thématiques
- **Plateformes Web 2.0** et guest posts

Conçu pour être utilisé avec **plusieurs sites** via un système de configuration YAML.

## Installation

```bash
pip install -r requirements.txt
```

Ou en mode développement :

```bash
pip install -e .
```

## Utilisation rapide

### 1. Scanner avec la config par défaut (pharmacie-provencale.com)

```bash
python run.py scan
```

### 2. Scanner avec une config spécifique

```bash
python run.py scan --config pharmacie-provencale.yaml
```

### 3. Scanner uniquement certaines sources

```bash
# Seulement les blogs et forums
python run.py scan --sources blogs,forums

# Seulement les annuaires
python run.py scan --sources directories
```

### 4. Utiliser des mots-clés personnalisés

```bash
python run.py scan --keywords "pharmacie,parapharmacie,cosmétiques bio"
```

### 5. Mode verbeux

```bash
python run.py scan -v
```

## Multi-sites

### Créer une config pour un nouveau site

```bash
python run.py new-site \
  --name "Mon Autre Site" \
  --url "https://mon-autre-site.com" \
  --keywords "mot-clé 1,mot-clé 2,mot-clé 3"
```

### Lister les configs disponibles

```bash
python run.py list
```

### Scanner avec la config d'un autre site

```bash
python run.py scan --config mon-autre-site.yaml
```

## Configuration

Les fichiers de configuration sont dans `configs/`. Chaque site a son propre fichier YAML :

```yaml
site:
  url: "https://mon-site.com"
  name: "Mon Site"
  keywords:
    - "mot-clé 1"
    - "mot-clé 2"
  language: "fr"
  country: "FR"
```

Le fichier `configs/default.yaml` contient les paramètres globaux (délais, scoring, export).

## Exports

Les résultats sont exportés dans le dossier `output/` en 3 formats :

| Format | Description |
|--------|-------------|
| **CSV** | Import dans Excel/Google Sheets |
| **JSON** | Exploitation programmatique |
| **HTML** | Rapport visuel interactif avec filtres et tri |

## Architecture

```
seo_backlink_finder/
├── cli.py                  # Interface ligne de commande
├── config.py               # Gestion des configurations multi-sites
├── runner.py               # Orchestrateur principal
├── scrapers/
│   ├── base.py             # Classe de base + recherche Google
│   ├── blog_comments.py    # Détection blogs avec commentaires ouverts
│   ├── forums.py           # Recherche de forums
│   ├── directories.py      # Recherche d'annuaires
│   └── web2_profiles.py    # Plateformes Web 2.0 + guest posts
├── analyzers/
│   └── scorer.py           # Scoring et déduplication
└── exporters/
    └── exporter.py         # Export CSV/JSON/HTML
```

## Scoring

Chaque opportunité reçoit un score de 0 à 100 basé sur :

| Critère | Poids par défaut |
|---------|-----------------|
| Pertinence thématique | 30% |
| Autorité du domaine (estimée) | 25% |
| DoFollow / NoFollow | 20% |
| Accessibilité (commentaire ouvert, etc.) | 15% |
| Type de source | 10% |
