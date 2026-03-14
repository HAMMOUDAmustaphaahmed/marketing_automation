# ============================================================
#  utils/web_research.py  — v2  TRIANGULATION MULTI-SOURCES
#  Algorithme de cross-validation :
#    1. Cherche sur N sources indépendantes (LinkedIn via Google,
#       Google Maps, annuaires, Facebook, presse)
#    2. Extrait les noms d'entreprises de chaque source
#    3. Score = nombre de sources où le nom apparaît
#    4. Les noms présents dans 2+ sources = haute crédibilité
#    5. Retourne une liste triée par crédibilité à Groq
# ============================================================

import re
import os
import time
import logging
import requests
from collections import defaultdict
from urllib.parse import unquote

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
TIMEOUT = 7


# ══════════════════════════════════════════════════════════════
#  COUCHE RECHERCHE
# ══════════════════════════════════════════════════════════════

def _serper(query: str, n: int = 8) -> list[dict]:
    """Google Search via Serper.dev (gratuit 2500/mois)"""
    key = os.environ.get('SERPER_API_KEY', '')
    if not key:
        return []
    try:
        r = requests.post(
            'https://google.serper.dev/search',
            headers={'X-API-KEY': key, 'Content-Type': 'application/json'},
            json={'q': query, 'gl': 'tn', 'hl': 'fr', 'num': n},
            timeout=TIMEOUT,
        )
        return [{'title': x.get('title',''), 'snippet': x.get('snippet',''),
                 'url': x.get('link','')} for x in r.json().get('organic', [])[:n]]
    except Exception as e:
        logger.debug(f"Serper: {e}")
        return []


def _ddg(query: str, n: int = 8) -> list[dict]:
    """DuckDuckGo HTML — gratuit, sans clé"""
    try:
        r = requests.post('https://html.duckduckgo.com/html/',
                          data={'q': query, 'kl': 'fr-fr'},
                          headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        results = []
        if BS4_OK:
            soup = BeautifulSoup(r.text, 'html.parser')
            for item in soup.select('.result')[:n]:
                ta = item.select_one('.result__a')
                ts = item.select_one('.result__snippet')
                if not ta:
                    continue
                href = ta.get('href', '')
                m = re.search(r'uddg=([^&]+)', href)
                url = unquote(m.group(1)) if m else ''
                results.append({'title': ta.text.strip(),
                                 'snippet': ts.text.strip() if ts else '',
                                 'url': url})
        else:
            titles   = re.findall(r'class="result__a"[^>]*>([^<]+)</a>', r.text)
            snippets = re.findall(r'class="result__snippet"[^>]*>([^<]+)', r.text)
            urls_raw = re.findall(r'uddg=([^&"]+)', r.text)
            for i in range(min(n, len(titles))):
                results.append({'title': titles[i].strip(),
                                 'snippet': snippets[i].strip() if i < len(snippets) else '',
                                 'url': unquote(urls_raw[i]) if i < len(urls_raw) else ''})
        return results
    except Exception as e:
        logger.debug(f"DDG: {e}")
        return []


def search(query: str, n: int = 8) -> list[dict]:
    """Serper si disponible, sinon DuckDuckGo"""
    r = _serper(query, n)
    return r if r else _ddg(query, n)


def _text(result: dict) -> str:
    return f"{result.get('title','')} {result.get('snippet','')} {result.get('url','')}"


# ══════════════════════════════════════════════════════════════
#  EXTRACTION DE NOMS D'ENTREPRISES
# ══════════════════════════════════════════════════════════════

# Suffixes légaux communs Tunisie / Maghreb / international
_LEGAL = r'(?:SARL|SA|SAS|SASU|SNC|GIE|LLC|Ltd|Corp|S\.A|S\.A\.R\.L|Group|Groupe|International|Intl|Holding|Industries|Industry|Industrie|Trading|Services|Solutions|Technologies|Tech|Systems|Systèmes|Engineering|Ingénierie|Construction|Distribution|Commerce|Import|Export|Consulting|Conseil)?'

_STOPWORDS = {
    'linkedin', 'facebook', 'google', 'maps', 'page', 'pages', 'company',
    'companies', 'entreprise', 'entreprises', 'tunisie', 'tunisian', 'maroc',
    'algerie', 'france', 'tunis', 'sfax', 'sousse', 'monastir', 'nabeul',
    'result', 'results', 'search', 'site', 'web', 'http', 'https', 'www',
    'profile', 'profil', 'emploi', 'job', 'jobs', 'work', 'career',
    'the', 'les', 'des', 'une', 'pour', 'dans', 'avec', 'sur', 'par',
    'and', 'or', 'of', 'in', 'at', 'to', 'for', 'is', 'are',
    'voir', 'plus', 'voir plus', 'suivre', 'about', 'about us',
}


def _extract_names(results: list[dict], source_label: str) -> list[tuple[str, str, str]]:
    """
    Extrait les noms d'entreprises depuis les résultats de recherche.
    Retourne: [(nom_normalisé, nom_original, url), ...]
    """
    extracted = []
    for r in results:
        title   = r.get('title', '')
        snippet = r.get('snippet', '')
        url     = r.get('url', '')

        # Source LinkedIn company page → le titre EST le nom
        if 'linkedin.com/company' in url:
            # Ex: "COGEPAM | LinkedIn" → "COGEPAM"
            name = re.split(r'\s*[|\-–]\s*', title)[0].strip()
            if name and len(name) > 2:
                extracted.append((_normalize(name), name, url))
            continue

        # Source Google Maps → titre souvent = nom
        if 'maps.google' in url or 'goo.gl/maps' in url:
            name = re.split(r'\s*[|\-–·]\s*', title)[0].strip()
            if name and len(name) > 2:
                extracted.append((_normalize(name), name, url))
            continue

        # Source générale : chercher des patterns de noms d'entreprises
        text = f"{title} {snippet}"
        # Pattern: Majuscule(s) + suffixe légal OU acronymes
        patterns = [
            r'\b([A-Z][A-Z\s&]{2,30}(?:' + _LEGAL[3:] + r'))\b',
            r'"([^"]{3,40})"',       # Entre guillemets
            r'«([^»]{3,40})»',       # Entre guillemets français
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b',  # Noms propres
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                name = m.group(1).strip()
                words = name.lower().split()
                if (len(name) > 3 and
                    not any(w in _STOPWORDS for w in words) and
                    not name.isdigit()):
                    extracted.append((_normalize(name), name, url))

    return extracted


def _normalize(name: str) -> str:
    """Normalise un nom pour comparaison : minuscules, sans ponctuation"""
    n = name.lower().strip()
    n = re.sub(r'[^\w\s]', '', n)
    n = re.sub(r'\s+', ' ', n)
    # Supprimer suffixes légaux pour comparaison
    n = re.sub(r'\b(sarl|sa|sas|llc|ltd|corp|group|groupe|international|holding)\b', '', n).strip()
    return n


# ══════════════════════════════════════════════════════════════
#  ALGORITHME DE TRIANGULATION
# ══════════════════════════════════════════════════════════════

class TriangulationResult:
    def __init__(self, name: str, original: str, score: int,
                 sources: list[str], linkedin_url: str | None,
                 website: str | None, snippet: str):
        self.name         = name          # nom normalisé
        self.original     = original      # nom original le plus long
        self.score        = score         # nb de sources distinctes
        self.sources      = sources       # liste des sources
        self.linkedin_url = linkedin_url
        self.website      = website
        self.snippet      = snippet

    def to_dict(self) -> dict:
        return {
            'name':         self.original,
            'score':        self.score,
            'sources':      self.sources,
            'linkedin_url': self.linkedin_url,
            'website':      self.website,
            'snippet':      self.snippet,
            'credibility':  '⭐⭐⭐' if self.score >= 3 else ('⭐⭐' if self.score >= 2 else '⭐'),
        }


def triangulate(sector: str, country: str, keywords: list[str],
                is_prospect: bool = False, limit: int = 30) -> list[dict]:
    """
    Algorithme principal de triangulation :
    1. Lance 5-6 recherches sur sources différentes
    2. Extrait les noms de chaque source
    3. Score = nb de sources où le nom apparaît
    4. Retourne les N meilleurs triés par score décroissant
    """
    kw = ' '.join(keywords[:3]) if keywords else sector
    city_hint = 'Tunisie Tunis Sfax Sousse' if country == 'Tunisie' else country

    # ── Sources de recherche ──────────────────────────────────
    SOURCES = {
        'linkedin':   f'site:linkedin.com/company {sector} {country}',
        'linkedin2':  f'site:linkedin.com/company "{kw}" {country}',
        'gmaps':      f'{sector} entreprises {city_hint} site:maps.google.com OR site:google.com/maps',
        'annuaire':   f'{sector} {country} annuaire entreprises',
        'facebook':   f'{sector} {country} site:facebook.com/pages OR site:facebook.com',
        'presse':     f'"{sector}" entreprise {country} société -offre -emploi -recrutement',
        'kompass':    f'site:kompass.com {sector} {country}',
        'industrie':  f'{kw} industriel {country} fabricant fournisseur',
    }

    if is_prospect:
        SOURCES['prospect1'] = f'{kw} client {country} acheteur {sector}'
        SOURCES['prospect2'] = f'agroalimentaire industrie logistique {country} site:linkedin.com/company'

    # ── Collecte des résultats par source ────────────────────
    # nom_normalisé → {score, sources, best_original, linkedin_url, website, snippets}
    registry: dict[str, dict] = defaultdict(lambda: {
        'score': 0, 'sources': [], 'originals': [], 'linkedin_url': None,
        'website': None, 'snippets': []
    })

    for source_name, query in SOURCES.items():
        logger.info(f"[triangulate] source={source_name} query={query[:60]}")
        results = search(query, n=8)
        time.sleep(0.4)

        extracted = _extract_names(results, source_name)
        seen_this_source = set()

        for norm, original, url in extracted:
            if not norm or len(norm) < 3:
                continue
            if norm in seen_this_source:
                continue
            seen_this_source.add(norm)

            entry = registry[norm]
            entry['score'] += 1
            entry['sources'].append(source_name)
            entry['originals'].append(original)

            # Conserver la meilleure URL LinkedIn trouvée
            if 'linkedin.com/company' in url and not entry['linkedin_url']:
                entry['linkedin_url'] = url

            # Conserver un site web non-LinkedIn
            if url and 'linkedin' not in url and 'google' not in url \
               and 'facebook' not in url and not entry['website'] \
               and url.startswith('http'):
                entry['website'] = url

            # Garder le snippet le plus long
            for r in results:
                if original.lower() in _text(r).lower() and r.get('snippet'):
                    entry['snippets'].append(r['snippet'][:150])
                    break

    # ── Trier par score décroissant ──────────────────────────
    sorted_entries = sorted(
        [(norm, data) for norm, data in registry.items() if data['score'] > 0],
        key=lambda x: x[1]['score'],
        reverse=True
    )

    # ── Construire le résultat ───────────────────────────────
    output = []
    seen_final = set()
    for norm, data in sorted_entries[:limit]:
        # Choisir le nom original le plus long (souvent le plus complet)
        best_original = max(data['originals'], key=len) if data['originals'] else norm.title()

        # Dédupliquer les noms très similaires
        if any(_similarity(norm, s) > 0.8 for s in seen_final):
            continue
        seen_final.add(norm)

        snippet = ' '.join(data['snippets'][:2])
        output.append({
            'name':         best_original,
            'score':        data['score'],
            'sources':      list(set(data['sources'])),
            'linkedin_url': data['linkedin_url'],
            'website':      data['website'],
            'snippet':      snippet[:300],
            'credibility':  '⭐⭐⭐' if data['score'] >= 3 else ('⭐⭐' if data['score'] >= 2 else '⭐'),
        })

    logger.info(f"[triangulate] {len(output)} companies found, "
                f"top score={output[0]['score'] if output else 0}")
    return output


def _similarity(a: str, b: str) -> float:
    """Similarité simple entre deux chaînes (Jaccard sur mots)"""
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ══════════════════════════════════════════════════════════════
#  RECHERCHE CONTACTS
# ══════════════════════════════════════════════════════════════

def research_company_contacts(company_name: str, country: str) -> str:
    """Cherche les vrais contacts publics d'une entreprise"""
    queries = [
        f'site:linkedin.com/in "{company_name}" directeur OR manager OR responsable OR PDG',
        f'"{company_name}" {country} directeur général PDG contact équipe',
        f'"{company_name}" direction management {country}',
    ]
    all_results = []
    seen = set()
    for q in queries:
        for r in search(q, n=5):
            url = r.get('url', '')
            if url not in seen:
                seen.add(url)
                all_results.append(r)
        time.sleep(0.3)

    if not all_results:
        return ""

    lines = [f"=== CONTACTS TROUVÉS POUR {company_name} ==="]
    li_profiles = [r for r in all_results if 'linkedin.com/in' in r.get('url', '')]
    others      = [r for r in all_results if r not in li_profiles]

    if li_profiles:
        lines.append("-- Profils LinkedIn --")
        for r in li_profiles[:5]:
            lines.append(f"• {r['title']} | {r['snippet']} | {r['url']}")
    if others:
        lines.append("-- Autres sources --")
        for r in others[:3]:
            lines.append(f"• {r['title']} | {r['snippet']}")
    return '\n'.join(lines)


def results_to_text(results: list[dict]) -> str:
    lines = []
    for r in results:
        lines.append(f"• {r.get('title','')} | {r.get('snippet','')} | {r.get('url','')}")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════
#  TRIANGULATION RAPIDE — Pour Render free tier (timeout 30s)
#  2 sources seulement, timeout 4s chacune, max 5 résultats
# ══════════════════════════════════════════════════════════════
def triangulate_fast(sector: str, country: str, keywords: list) -> list:
    """
    Version allégée de triangulate() pour environnements avec timeout court.
    - 2 sources au lieu de 8 (LinkedIn + annuaire)
    - Timeout 4s par source
    - Max 5 résultats
    Durée totale : ~4-6s
    """
    kw = ' '.join(keywords[:2]) if keywords else sector

    FAST_SOURCES = {
        'linkedin': 'site:linkedin.com/company ' + sector + ' ' + country,
        'annuaire': sector + ' entreprise ' + country + ' annuaire',
    }

    registry = {}
    for source_name, query in FAST_SOURCES.items():
        try:
            results = []
            # Serper si dispo (plus rapide), sinon DDG avec timeout réduit
            key = os.environ.get('SERPER_API_KEY', '')
            if key:
                import requests as _req
                r = _req.post(
                    'https://google.serper.dev/search',
                    headers={'X-API-KEY': key, 'Content-Type': 'application/json'},
                    json={'q': query, 'gl': 'tn', 'hl': 'fr', 'num': 5},
                    timeout=4,
                )
                results = [{'title': x.get('title',''), 'snippet': x.get('snippet',''),
                            'url': x.get('link','')} for x in r.json().get('organic', [])[:5]]
            else:
                import requests as _req
                r = _req.post('https://html.duckduckgo.com/html/',
                              data={'q': query, 'kl': 'fr-fr'},
                              headers=HEADERS, timeout=4)
                if BS4_OK:
                    from bs4 import BeautifulSoup as _BS
                    soup = _BS(r.text, 'html.parser')
                    for item in soup.select('.result')[:5]:
                        ta = item.select_one('.result__a')
                        ts = item.select_one('.result__snippet')
                        if ta:
                            results.append({'title': ta.text.strip(),
                                            'snippet': ts.text.strip() if ts else '',
                                            'url': ''})

            extracted = _extract_names(results, source_name)
            for norm, original, url in extracted:
                if not norm or len(norm) < 3:
                    continue
                if norm not in registry:
                    registry[norm] = {'score': 0, 'originals': [], 'linkedin_url': None, 'website': None, 'snippets': []}
                registry[norm]['score'] += 1
                registry[norm]['originals'].append(original)
                if 'linkedin.com/company' in url and not registry[norm]['linkedin_url']:
                    registry[norm]['linkedin_url'] = url
                elif url and 'linkedin' not in url and url.startswith('http') and not registry[norm]['website']:
                    registry[norm]['website'] = url

        except Exception as e:
            logger.debug('triangulate_fast source %s failed: %s', source_name, e)

    output = []
    for norm, data in sorted(registry.items(), key=lambda x: x[1]['score'], reverse=True)[:5]:
        best_original = max(data['originals'], key=len) if data['originals'] else norm.title()
        output.append({
            'name': best_original,
            'score': data['score'],
            'sources': [],
            'linkedin_url': data['linkedin_url'],
            'website': data['website'],
            'snippet': '',
            'credibility': '⭐⭐' if data['score'] >= 2 else '⭐',
        })

    logger.info('triangulate_fast: %d results for %s/%s', len(output), sector, country)
    return output