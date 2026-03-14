# ============================================================
#  utils/groq_ai.py
#  Intégration API Groq via client OpenAI-compatible
#  Clé gratuite sur : https://console.groq.com → API Keys
# ============================================================

import json
import re
import logging
import os
from flask import current_app

logger = logging.getLogger(__name__)
NL = "\n"  # newline constant for prompt building

# Modèles disponibles sur Groq (confirmés)
GROQ_MODELS = [
    'deepseek-r1-distill-llama-70b',      # Raisonnement — meilleur pour extraction
    'llama-3.3-70b-versatile',             # Rapide et fiable
    'meta-llama/llama-4-scout-17b-16e-instruct',  # Llama 4 Scout — nouvelles connaissances
]

MODEL_RESEARCH  = 'deepseek-r1-distill-llama-70b'
MODEL_FAST      = 'llama-3.3-70b-versatile'
MODEL_SCOUT     = 'meta-llama/llama-4-scout-17b-16e-instruct'

# Les 3 modèles utilisés pour le consensus
# Sur Render free tier (timeout 30s) → 1 seul modèle rapide
# En local → 3 modèles pour le consensus complet
import os as _os
_ON_RENDER = bool(_os.environ.get('RENDER') or _os.environ.get('RENDER_SERVICE_ID') or _os.environ.get('IS_RENDER'))
CONSENSUS_MODELS = (
    # Render free tier (timeout 30s) : 2 modèles rapides ~14-16s total
    # llama-4-scout = connaissance 2025 + rapide
    # llama-3.3    = fiable + rapide
    # DeepSeek R1 exclu sur Render (trop lent ~20-25s seul)
    ['meta-llama/llama-4-scout-17b-16e-instruct',
     'llama-3.3-70b-versatile']
    if _ON_RENDER else
    # Local : consensus 3 modèles complet
    ['deepseek-r1-distill-llama-70b',
     'llama-3.3-70b-versatile',
     'meta-llama/llama-4-scout-17b-16e-instruct',
    ]
)


def _get_client():
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("Installez le package : pip install openai")

    # Priorité : 1) os.environ  2) Flask config  3) clé hardcodée
    api_key = os.environ.get('GROQ_API_KEY', '')
    try:
        api_key = api_key or current_app.config.get('GROQ_API_KEY', '')
    except Exception:
        pass
    # Fallback hardcodé — fonctionne même sans .env ni variable Render
    if not api_key or api_key == 'your-groq-api-key':
        api_key = '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'

    base_url = os.environ.get('GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
    return OpenAI(api_key=api_key, base_url=base_url)


def ask_groq(prompt, system_prompt=None, max_tokens=2000, preferred_model=None):
    """
    Appelle Groq avec fallback automatique entre modeles.
    Ordre : preferred_model -> config GROQ_MODEL -> GROQ_MODELS[0] -> ...
    Gere les modeles de raisonnement (DeepSeek R1, Qwen QwQ).
    """
    REASONING = ('deepseek-r1-distill-llama-70b', 'qwen-qwq-32b')

    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    # Construire l'ordre d'essai
    models_to_try = []
    if preferred_model:
        models_to_try.append(preferred_model)
    try:
        from flask import current_app as _app2
        cfg = _app2.config.get('GROQ_MODEL', '')
        if cfg and cfg not in models_to_try:
            models_to_try.append(cfg)
    except Exception:
        pass
    for m in GROQ_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    client  = _get_client()
    last_err = None

    for model in models_to_try:
        try:
            is_reasoning = model in REASONING
            if is_reasoning:
                # Modeles de raisonnement : temperature=1, pas de role system
                prefix  = ('[Instructions]: ' + system_prompt + '\n\n') if system_prompt else ''
                merged  = [{'role': 'user', 'content': prefix + prompt}]
                resp    = client.chat.completions.create(
                    model=model, messages=merged,
                    temperature=1, max_tokens=max_tokens,
                    timeout=25,
                )
            else:
                resp = client.chat.completions.create(
                    model=model, messages=messages,
                    temperature=0.2, max_tokens=max_tokens,
                    timeout=25,
                )

            raw = resp.choices[0].message.content or ''
            # DeepSeek R1 produit un bloc <think>...</think> a supprimer
            raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            logger.info('Groq OK (%s) - %d chars', model, len(raw))
            return raw, None

        except Exception as e:
            last_err = str(e)
            logger.warning('Groq %s failed: %s', model, e)
            continue

    msg = 'Erreur Groq: ' + str(last_err) if last_err else 'Reponse vide'
    logger.error('All Groq models failed. Last error: %s', last_err)
    return None, msg

def _parse_json(raw):
    if not raw:
        return None, "Réponse vide de l'IA."

    # Supprimer les blocs markdown
    cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip()
    cleaned = re.sub(r'```\s*$', '', cleaned).strip()

    # Parse direct
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError:
        pass

    # Extraire objet JSON
    m = re.search(r'\{[\s\S]*\}', cleaned)
    if m:
        try:
            return json.loads(m.group()), None
        except json.JSONDecodeError:
            pass

    # Extraire tableau JSON
    m = re.search(r'\[[\s\S]*\]', cleaned)
    if m:
        try:
            return json.loads(m.group()), None
        except json.JSONDecodeError:
            pass

    # Réparer virgules trailing
    try:
        repaired = re.sub(r',\s*([}\]])', r'\1', cleaned)
        return json.loads(repaired), None
    except json.JSONDecodeError:
        pass

    logger.error(f"JSON parse FAILED. Raw (300c): {raw[:300]}")
    return None, "Réponse IA non valide (JSON attendu). Réessayez."


# ══════════════════════════════════════════════════════════════
#  MOTEUR DE CONSENSUS MULTI-MODÈLES
#  Chaque modèle génère sa liste indépendamment.
#  Score final = nb de modèles qui citent la même entreprise.
#  Résultat : les entreprises confirmées par 2-3 modèles en tête.
# ══════════════════════════════════════════════════════════════

def _normalize_name(name):
    """Normalise un nom pour comparaison (insensible à la casse/ponctuation)"""
    import unicodedata
    n = name.lower().strip()
    n = unicodedata.normalize('NFD', n)
    n = ''.join(c for c in n if unicodedata.category(c) != 'Mn')  # enlever accents
    n = re.sub(r'[^\w\s]', '', n)
    n = re.sub(r'\b(sarl|sa|sas|llc|ltd|corp|group|groupe|ste|societe)\b', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def _name_similarity(a, b):
    """Similarité Jaccard sur les mots"""
    sa = set(_normalize_name(a).split())
    sb = set(_normalize_name(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _consensus_merge(results_by_model, name_key='name'):
    """
    Fusionne les résultats de N modèles.
    - Groupe les entrées par nom similaire (seuil 0.6)
    - Score = nb de modèles qui citent ce nom
    - Prend les meilleures données disponibles par champ
    - Trie par score décroissant
    """
    # Registre : norm_name → {score, entries, models}
    registry = {}

    for model_name, entries in results_by_model.items():
        for entry in (entries or []):
            if not isinstance(entry, dict):
                continue
            raw_name = (entry.get(name_key) or '').strip()
            if not raw_name:
                continue
            norm = _normalize_name(raw_name)
            if not norm:
                continue

            # Chercher si un nom similaire existe déjà
            matched_key = None
            for existing_norm in registry:
                if _name_similarity(norm, existing_norm) >= 0.6:
                    matched_key = existing_norm
                    break

            key = matched_key or norm
            if key not in registry:
                registry[key] = {'score': 0, 'models': [], 'entries': []}

            registry[key]['score'] += 1
            registry[key]['models'].append(model_name)
            registry[key]['entries'].append(entry)

    # Fusionner les données de chaque groupe
    merged = []
    for norm_key, data in sorted(registry.items(),
                                  key=lambda x: x[1]['score'], reverse=True):
        entries = data['entries']
        score   = data['score']
        models  = data['models']

        # Choisir le nom le plus long (souvent le plus complet)
        best = max(entries, key=lambda e: len((e.get(name_key) or '')))
        result = dict(best)

        # Pour chaque champ : prendre la première valeur non-null trouvée
        for field in list(result.keys()):
            if not result.get(field):
                for e in entries:
                    if e.get(field):
                        result[field] = e[field]
                        break

        # Enrichir avec métadonnées du consensus
        result['_consensus_score']  = score
        result['_consensus_models'] = models
        result['_credibility'] = (
            '🥇 Confirmé par %d modèles' % score if score >= 2
            else '🔵 Suggéré par 1 modèle'
        )
        merged.append(result)

    return merged


def _ask_model_for_list(model, prompt, system, max_tokens, list_key):
    """Lance ask_groq sur un modèle spécifique et parse la liste"""
    raw, err = ask_groq(prompt, system, max_tokens=max_tokens, preferred_model=model)
    if err or not raw:
        logger.warning('Model %s failed: %s', model, err)
        return []
    data, parse_err = _parse_json(raw)
    if parse_err or not data:
        return []
    if isinstance(data, dict):
        data = data.get(list_key, data.get('data', []))
    if not isinstance(data, list):
        return []
    return data



# ── Analyse du profil entreprise ──────────────────────────────
def analyze_company_profile(description, country):
    system = "Tu es un expert en stratégie marketing B2B. Réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après."
    prompt = f"""Pays : {country}
Description entreprise : {description}

Retourne UNIQUEMENT ce JSON (pas de backticks, pas d'explication) :
{{
  "sector": "secteur principal",
  "sub_sector": "sous-secteur",
  "keywords": ["mot1", "mot2", "mot3", "mot4", "mot5"],
  "products_summary": "résumé en une phrase",
  "icp": {{
    "company_sizes": ["PME", "ETI"],
    "sectors": ["secteur1", "secteur2", "secteur3"],
    "roles": ["DG", "Directeur technique"],
    "pain_points": ["problème 1", "problème 2"]
  }},
  "value_proposition": "proposition de valeur en une phrase"
}}"""

    raw, err = ask_groq(prompt, system, max_tokens=700)
    if err:
        return None, err
    return _parse_json(raw)




# ── Génération de concurrents ─────────────────────────────────
def generate_competitors(company_name, description, country, sector, keywords, count=10):
    """CONSENSUS 3 MODELES + TRIANGULATION WEB"""
    from utils.web_research import triangulate
    count  = min(count, 10)
    kw_str = ", ".join(keywords) if keywords else sector

    try:
        if _ON_RENDER:
            # Render: triangulation légère — 2 sources rapides seulement
            web_hits = triangulate_fast(sector, country, keywords or [])
        else:
            web_hits = triangulate(sector, country, keywords or [], is_prospect=False, limit=20)
    except Exception as e:
        logger.warning("Triangulation failed: %s", e)
        web_hits = []

    web_lines = []
    if web_hits:
        web_lines.append("DONNEES WEB VERIFIEES :")
        for r in web_hits[:12]:
            li = ("| linkedin: " + r["linkedin_url"]) if r.get("linkedin_url") else ""
            ws = ("| site: " + r["website"]) if r.get("website") else ""
            web_lines.append("- %s [%d src] %s %s" % (r["name"], r.get("score", 1), li, ws))
    web_ctx = NL.join(web_lines) if web_lines else ("Utilise tes connaissances sur les vraies entreprises en " + country)

    system = ("Tu es expert en veille concurrentielle B2B. Tu connais les entreprises tunisiennes "
              "froid industriel, climatisation, HVAC. Reponds UNIQUEMENT en JSON tableau valide, "
              "sans backtick, sans commentaire.")

    prompt_parts = [
        "Identifie %d concurrents reels de \"%s\" (%s, %s). Mots-cles: %s" % (count, company_name, sector, country, kw_str),
        web_ctx,
        "REGLES :",
        "- Priorite aux entreprises des donnees web (URLs exactes si disponibles).",
        "- Complete avec tes connaissances des vraies entreprises en " + country + ".",
        "- linkedin_url / website : URL exacte des donnees web, sinon null.",
        "- employees_count, revenue_estimate : estimation raisonnable.",
        "- Varie les villes : Tunis, Sfax, Sousse, Monastir, Nabeul, Bizerte...",
        "",
        "Retourne UNIQUEMENT ce tableau JSON :",
        "[",
        "  {",
        "    \"name\": \"Nom reel\",",
        "    \"website\": null,",
        "    \"country\": \"%s\"," % country,
        "    \"city\": \"ville\",",
        "    \"sector\": \"%s\"," % sector,
        "    \"activities\": \"activite\",",
        "    \"products\": \"produits\",",
        "    \"services\": \"services\",",
        "    \"employees_count\": \"10-50\",",
        "    \"founded_year\": 2005,",
        "    \"linkedin_url\": null,",
        "    \"google_rating\": null,",
        "    \"similarity_score\": 80,",
        "    \"revenue_estimate\": \"1M-5M TND\",",
        "    \"swot_analysis\": \"\"",
        "  }",
        "]"
    ]
    prompt = NL.join(prompt_parts)

    results_by_model = {}
    last_model_error = None
    for model in CONSENSUS_MODELS:
        try:
            logger.info("Consensus: running %s", model)
            _max_tok = 2000 if _ON_RENDER else 4000
            raw, err = ask_groq(prompt, system, max_tokens=_max_tok, preferred_model=model)
            if err:
                last_model_error = err
                logger.warning("Consensus model %s error: %s", model, err)
                continue
            data, perr = _parse_json(raw)
            if perr or not data:
                last_model_error = perr or "JSON vide"
                logger.warning("Consensus model %s parse error: %s", model, perr)
                continue
            if isinstance(data, dict):
                data = data.get("competitors", data.get("data", []))
            if isinstance(data, list) and data:
                results_by_model[model] = data
                logger.info("Consensus: %s -> %d", model, len(data))
        except Exception as e:
            last_model_error = str(e)
            logger.warning("Consensus model %s failed: %s", model, e)

    if not results_by_model:
        return [], ("Tous les modeles ont echoue. Derniere erreur: " + str(last_model_error))

    merged = _consensus_merge(results_by_model, name_key="name")
    final = []
    for item in merged[:count]:
        cs = item.pop("_consensus_score", 1)
        item.pop("_consensus_models", None)
        item.pop("_credibility", None)
        item["similarity_score"] = min(100, int(item.get("similarity_score") or 75) + (cs - 1) * 5)
        if item.get("name"):
            final.append(item)
    logger.info("Consensus competitors final: %d", len(final))
    return final, None


# ── Generation de prospects ───────────────────────────────────
def generate_prospects(company_name, description, country, sector, icp_profile, count=10):
    """CONSENSUS 3 MODELES + TRIANGULATION WEB"""
    from utils.web_research import triangulate
    count = min(count, 10)

    icp_sectors = []
    icp_sizes   = []
    if isinstance(icp_profile, dict):
        icp_sectors = icp_profile.get("sectors", [])
        icp_sizes   = icp_profile.get("company_sizes", [])

    icp_str   = ("Secteurs cibles : " + ", ".join(icp_sectors) + ".") if icp_sectors else ""
    sizes_str = ("Tailles : " + ", ".join(icp_sizes) + ".") if icp_sizes else ""
    kw_targets = icp_sectors[:3] if icp_sectors else [sector]

    try:
        if _ON_RENDER:
            web_hits = triangulate_fast(" ".join(kw_targets[:2]), country, kw_targets)
        else:
            web_hits = triangulate(" ".join(kw_targets[:2]), country, kw_targets, is_prospect=True, limit=20)
    except Exception as e:
        logger.warning("Triangulation failed: %s", e)
        web_hits = []

    web_lines = []
    if web_hits:
        web_lines.append("ENTREPRISES CLIENTES POTENTIELLES TROUVEES :")
        for r in web_hits[:12]:
            li = ("| linkedin: " + r["linkedin_url"]) if r.get("linkedin_url") else ""
            ws = ("| site: " + r["website"]) if r.get("website") else ""
            web_lines.append("- %s [%d src] %s %s" % (r["name"], r.get("score", 1), li, ws))
    web_ctx = NL.join(web_lines) if web_lines else ("Utilise tes connaissances sur les vraies entreprises en " + country)

    system = ("Tu es expert en prospection B2B. Tu connais les entreprises tunisiennes "
              "industrie, agroalimentaire, logistique, hotellerie, distribution, GMS, sante. "
              "Reponds UNIQUEMENT en JSON tableau valide, sans backtick, sans commentaire.")

    prompt_parts = [
        "Identifie %d clients potentiels B2B reels en %s pour \"%s\" (%s). %s %s" % (count, country, company_name, sector, icp_str, sizes_str),
        web_ctx,
        "REGLES :",
        "- Priorite aux entreprises des donnees web (URLs exactes si disponibles).",
        "- Complete avec des entreprises reelles en " + country + ".",
        "- contact_name / email / phone : null sauf si connu publiquement.",
        "- Varie les secteurs et les villes.",
        "",
        "Retourne UNIQUEMENT ce tableau JSON :",
        "[",
        "  {",
        "    \"company_name\": \"Nom reel\",",
        "    \"sector\": \"secteur\",",
        "    \"sub_sector\": \"sous-secteur\",",
        "    \"country\": \"%s\"," % country,
        "    \"city\": \"ville\",",
        "    \"size\": \"PME\",",
        "    \"employees_count\": \"50-200\",",
        "    \"contact_name\": null,",
        "    \"contact_title\": null,",
        "    \"email\": null,",
        "    \"phone\": null,",
        "    \"website\": null,",
        "    \"linkedin_url\": null,",
        "    \"why_relevant\": \"Raison courte\",",
        "    \"relevance_score\": 80",
        "  }",
        "]"
    ]
    prompt = NL.join(prompt_parts)

    results_by_model = {}
    last_model_error = None
    for model in CONSENSUS_MODELS:
        try:
            logger.info("Consensus prospects: running %s", model)
            _max_tok = 2000 if _ON_RENDER else 4000
            raw, err = ask_groq(prompt, system, max_tokens=_max_tok, preferred_model=model)
            if err:
                last_model_error = err
                logger.warning("Consensus model %s error: %s", model, err)
                continue
            data, perr = _parse_json(raw)
            if perr or not data:
                last_model_error = perr or "JSON vide"
                continue
            if isinstance(data, dict):
                data = data.get("prospects", data.get("data", []))
            if isinstance(data, list) and data:
                results_by_model[model] = data
                logger.info("Consensus: %s -> %d", model, len(data))
        except Exception as e:
            last_model_error = str(e)
            logger.warning("Consensus model %s failed: %s", model, e)

    if not results_by_model:
        return [], ("Tous les modeles ont echoue. Derniere erreur: " + str(last_model_error))

    merged = _consensus_merge(results_by_model, name_key="company_name")
    final = []
    for item in merged[:count]:
        cs = item.pop("_consensus_score", 1)
        item.pop("_consensus_models", None)
        item.pop("_credibility", None)
        item["relevance_score"] = min(100, int(item.get("relevance_score") or 75) + (cs - 1) * 5)
        if item.get("company_name"):
            final.append(item)
    logger.info("Consensus prospects final: %d", len(final))
    return final, None


# ── Génération de template email ──────────────────────────────
def generate_email_template(company_name, product_desc, prospect_sector, prospect_name=None):
    system = "Tu es un expert en copywriting B2B. Réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après."
    prompt = f"""Email de prospection B2B en français.
Expéditeur : {company_name} — {product_desc}
Secteur prospect : {prospect_sector}

Retourne UNIQUEMENT ce JSON (pas de backticks) :
{{
  "subject": "Objet accrocheur (max 80 caractères)",
  "body": "<p>Bonjour,</p><p>Corps court (max 80 mots). Call-to-action clair.</p><p>Cordialement,<br>{company_name}</p>"
}}"""

    raw, err = ask_groq(prompt, system, max_tokens=500)
    if err:
        return None, err
    return _parse_json(raw)


# ── Génération d'analyse SWOT ─────────────────────────────────
def generate_swot(competitor_name, competitor_data, our_company):
    system = "Tu es un expert en analyse stratégique. Réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après."
    activities = competitor_data.get('activities', '') if isinstance(competitor_data, dict) else ''

    prompt = f"""SWOT de "{competitor_name}" face à "{our_company}". Activités : {activities}

Retourne UNIQUEMENT ce JSON (pas de backticks) :
{{
  "strengths":     ["Force 1", "Force 2", "Force 3"],
  "weaknesses":    ["Faiblesse 1", "Faiblesse 2"],
  "opportunities": ["Opportunité 1", "Opportunité 2"],
  "threats":       ["Menace 1", "Menace 2"]
}}"""

    raw, err = ask_groq(prompt, system, max_tokens=500)
    if err:
        return None, err
    return _parse_json(raw)