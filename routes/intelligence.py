from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import (db, Prospect, Opportunity, Quote, Order, EmailLog,
                    EmailCampaign, MaintenanceOpportunity, MaintenanceQuote)
from sqlalchemy import func
from datetime import datetime

intelligence_bp = Blueprint('intelligence', __name__, url_prefix='/intelligence')


# ══════════════════════════════════════════════════════════════
#  CLIENT HISTORY — search & full 360° stats
# ══════════════════════════════════════════════════════════════
@intelligence_bp.route('/client-history')
@login_required
def client_history():
    """Landing page — search box only."""
    query  = request.args.get('q', '').strip()
    client = None
    stats  = None

    if query:
        client = Prospect.query.filter_by(company_id=current_user.company_id)\
            .filter(Prospect.company_name.ilike('%' + query + '%'))\
            .order_by(
                (func.lower(Prospect.company_name) == query.lower()).desc()
            ).first()

        if client:
            stats = _build_stats(client)

    if request.args.get('autocomplete'):
        results = Prospect.query.filter_by(company_id=current_user.company_id)\
            .filter(Prospect.company_name.ilike('%' + query + '%'))\
            .limit(8).all()
        return jsonify([{'id': p.id, 'name': p.company_name,
                         'sector': p.sector or '', 'city': p.city or ''} for p in results])

    return render_template('intelligence/client_history.html',
                           query=query, client=client, stats=stats)


def _build_stats(prospect):
    cid = prospect.id
    opps     = Opportunity.query.filter_by(prospect_id=cid).all()
    won_opps = [o for o in opps if o.stage == 'won']
    lost_opps= [o for o in opps if o.stage == 'lost']
    active_opps = [o for o in opps if o.stage not in ('won','lost','delivered')]
    all_quotes = []
    for o in opps:
        all_quotes.extend(o.quotes)
    sent_quotes     = [q for q in all_quotes if q.status in ('sent','accepted')]
    accepted_quotes = [q for q in all_quotes if q.status == 'accepted']
    all_orders    = []
    for o in opps:
        all_orders.extend(o.orders)
    delivered_orders = [o for o in all_orders if o.delivery_status == 'delivered']
    total_won_value  = sum(o.value or 0 for o in won_opps)
    total_order_value= sum(o.amount or 0 for o in all_orders)
    pipeline_value   = sum(o.value or 0 for o in active_opps)
    emails_sent    = EmailLog.query.filter_by(prospect_id=cid).count()
    emails_opened  = EmailLog.query.filter_by(prospect_id=cid).filter(EmailLog.opened_at.isnot(None)).count()
    emails_replied = EmailLog.query.filter_by(prospect_id=cid).filter(EmailLog.replied_at.isnot(None)).count()
    email_logs     = EmailLog.query.filter_by(prospect_id=cid).order_by(EmailLog.sent_at.desc()).all()
    maint_opps   = MaintenanceOpportunity.query.filter_by(prospect_id=cid).all()
    maint_active = [m for m in maint_opps if m.stage in ('won','active')]
    maint_value  = sum(m.value or 0 for m in maint_active)
    conv_rate = round(len(won_opps) / len(opps) * 100, 1) if opps else 0
    timeline = []
    for opp in opps:
        timeline.append({'date': opp.created_at, 'type': 'opportunity',
            'icon': 'fas fa-star', 'color': '#1a56db',
            'label': 'Opportunite creee : ' + opp.title,
            'sub': (str(round(opp.value)) + ' TND') if opp.value else '',
            'stage': opp.stage, 'link_type': 'opp', 'link_id': opp.id})
        for q in opp.quotes:
            timeline.append({'date': q.created_at, 'type': 'quote',
                'icon': 'fas fa-file-alt', 'color': '#7c3aed',
                'label': 'Devis ' + q.quote_number,
                'sub': str(round(q.total_ttc)) + ' TND TTC — ' + q.status,
                'stage': q.status, 'link_type': None})
        for o in opp.orders:
            timeline.append({'date': o.ordered_at, 'type': 'order',
                'icon': 'fas fa-shopping-cart', 'color': '#059669',
                'label': 'Bon de commande ' + o.order_number,
                'sub': str(round(o.amount)) + ' TND — ' + ('Livre' if o.delivery_status == 'delivered' else 'En attente'),
                'stage': o.delivery_status, 'link_type': None})
            if o.delivered_at:
                timeline.append({'date': o.delivered_at, 'type': 'delivery',
                    'icon': 'fas fa-truck', 'color': '#16a34a',
                    'label': 'Livraison confirmee', 'sub': 'BC ' + o.order_number,
                    'stage': 'delivered', 'link_type': None})
    for el in email_logs:
        camp = EmailCampaign.query.get(el.campaign_id)
        timeline.append({'date': el.sent_at, 'type': 'email',
            'icon': 'fas fa-envelope', 'color': '#d97706',
            'label': 'Email : ' + (camp.subject if camp else 'Campagne'),
            'sub': ('Repondu' if el.replied_at else ('Lu' if el.opened_at else 'Envoye')),
            'stage': el.status, 'link_type': None})
    for m in maint_opps:
        timeline.append({'date': m.created_at, 'type': 'maintenance',
            'icon': 'fas fa-tools', 'color': '#0891b2',
            'label': 'Maintenance : ' + m.title,
            'sub': (m.maint_type or '') + ' — ' + m.stage,
            'stage': m.stage, 'link_type': 'maint', 'link_id': m.id})
    timeline.sort(key=lambda x: x['date'] or datetime.min, reverse=True)
    all_dates = [t['date'] for t in timeline if t['date']]
    return {
        'total_opportunities': len(opps), 'won_opportunities': len(won_opps),
        'lost_opportunities': len(lost_opps), 'active_opportunities': len(active_opps),
        'total_quotes': len(all_quotes), 'sent_quotes': len(sent_quotes),
        'accepted_quotes': len(accepted_quotes), 'total_orders': len(all_orders),
        'delivered_orders': len(delivered_orders), 'emails_sent': emails_sent,
        'emails_opened': emails_opened, 'emails_replied': emails_replied,
        'maintenance_opps': len(maint_opps), 'maintenance_active': len(maint_active),
        'total_won_value': total_won_value, 'total_order_value': total_order_value,
        'pipeline_value': pipeline_value, 'maint_value': maint_value,
        'conversion_rate': conv_rate,
        'email_open_rate': round(emails_opened / emails_sent * 100, 1) if emails_sent else 0,
        'email_reply_rate': round(emails_replied / emails_sent * 100, 1) if emails_sent else 0,
        'opportunities': opps, 'quotes': all_quotes, 'orders': all_orders,
        'email_logs': email_logs, 'maintenance_opps_list': maint_opps,
        'timeline': timeline,
        'first_contact': min(all_dates) if all_dates else None,
        'last_contact':  max(all_dates) if all_dates else None,
    }


# ══════════════════════════════════════════════════════════════
#  LINKEDIN COMPANY INTELLIGENCE
# ══════════════════════════════════════════════════════════════
@intelligence_bp.route('/linkedin-search')
@login_required
def linkedin_search():
    return render_template('intelligence/linkedin_search.html')


# ── Helpers ────────────────────────────────────────────────────
def _merge_company_field(entries, field, prefer_non_null=True):
    """Retourne la meilleure valeur pour un champ parmi plusieurs résultats."""
    for e in entries:
        v = e.get(field)
        if v and v not in ('null', 'None', '', []):
            return v
    return entries[0].get(field) if entries else None


def _merge_list_field(entries, field):
    """Fusionne les listes de plusieurs résultats (dédupliquées)."""
    seen = set()
    merged = []
    for e in entries:
        items = e.get(field) or []
        if isinstance(items, list):
            for item in items:
                key = str(item).lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    merged.append(item)
    return merged if merged else None


def _consensus_company(results_by_model):
    """
    Fusionne les analyses de N modèles en une seule fiche entreprise optimale.
    Logique :
      - Champs texte : prend la valeur non-null la plus longue (souvent la plus détaillée)
      - URLs : prend la première URL valide trouvée
      - Listes (produits, services, SWOT) : union de toutes les listes, dédupliquée
      - Contacts : union de tous les contacts avec déduplication par nom
      - Score de confiance : basé sur le nb de modèles qui ont répondu
    """
    import re as _re

    all_company = []
    all_contacts = []

    for model_name, result in results_by_model.items():
        if not isinstance(result, dict):
            continue
        c = result.get('company', result)
        if isinstance(c, dict):
            all_company.append(c)
        contacts = result.get('contacts', [])
        if isinstance(contacts, list):
            all_contacts.extend(contacts)

    if not all_company:
        return None, []

    # ── Fusionner la fiche entreprise ──────────────────────────
    # Pour les champs texte courts : valeur non-null la plus longue
    text_fields = ['name', 'description', 'sector', 'sub_sector', 'country',
                   'city', 'employees_count', 'revenue_estimate',
                   'technologies', 'certifications', 'why_prospect']
    # Pour les URLs : première URL valide
    url_fields  = ['website', 'linkedin_url']
    # Pour les entiers
    int_fields  = ['founded_year', 'relevance_score']

    merged = {}

    for field in text_fields:
        candidates = [
            str(e.get(field) or '').strip()
            for e in all_company
            if e.get(field) and str(e.get(field)).lower() not in ('null','none','')
        ]
        if candidates:
            merged[field] = max(candidates, key=len)  # le plus détaillé
        else:
            merged[field] = None

    for field in url_fields:
        url = None
        for e in all_company:
            v = str(e.get(field) or '').strip()
            if v and v.lower() not in ('null','none','') and v.startswith('http'):
                url = v
                break
        merged[field] = url

    for field in int_fields:
        for e in all_company:
            v = e.get(field)
            if v and str(v).lower() not in ('null','none',''):
                try:
                    merged[field] = int(str(v).split('-')[0].strip())
                    break
                except Exception:
                    pass
        if field not in merged:
            merged[field] = None

    # Listes simples
    for field in ['key_products', 'key_services', 'markets', 'competitors']:
        merged[field] = _merge_list_field(all_company, field) or []

    # SWOT : union de toutes les listes
    swot_keys = ['strengths', 'weaknesses', 'opportunities', 'threats']
    merged['swot'] = {}
    for sk in swot_keys:
        seen = set()
        items = []
        for e in all_company:
            swot = e.get('swot') or {}
            for item in (swot.get(sk) or []):
                key = str(item).lower().strip()[:60]
                if key and key not in seen:
                    seen.add(key)
                    items.append(item)
        merged['swot'][sk] = items[:4]  # max 4 par catégorie

    # ── Fusionner les contacts ─────────────────────────────────
    # Dédupliqués par nom normalisé
    seen_names = {}
    merged_contacts = []
    for contact in all_contacts:
        if not isinstance(contact, dict):
            continue
        name = str(contact.get('name') or '').strip()
        if not name or name.lower() in ('null','none','nom réel trouvé'):
            continue
        norm = _re.sub(r'\s+', ' ', name.lower().strip())
        if norm not in seen_names:
            seen_names[norm] = contact
            merged_contacts.append(contact)
        else:
            # Enrichir l'entrée existante avec les données manquantes
            existing = seen_names[norm]
            for field in ['title', 'department', 'linkedin_url', 'email_guess', 'seniority']:
                if not existing.get(field) and contact.get(field):
                    existing[field] = contact[field]

    # Trier contacts : décideurs en premier
    merged_contacts.sort(key=lambda c: (
        0 if c.get('decision_maker') else 1,
        0 if (c.get('seniority') or '').upper() in ('C-LEVEL', 'C_LEVEL', 'DIRECTOR') else 1
    ))

    return merged, merged_contacts[:8]


@intelligence_bp.route('/linkedin-search/enrich', methods=['POST'])
@login_required
def linkedin_enrich():
    import json as _json
    import re as _re
    import logging
    log = logging.getLogger(__name__)

    # Import sécurisé
    try:
        from utils.groq_ai import ask_groq, _parse_json, CONSENSUS_MODELS
    except Exception as e:
        log.error('Import groq_ai failed: %s', e)
        return jsonify({'error': 'Erreur import: ' + str(e)}), 500

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}

    company_name = (data.get('company_name') or '').strip()
    country      = (data.get('country') or 'Tunisie').strip()
    sector       = (data.get('sector') or '').strip()
    address      = (data.get('address') or '').strip()

    if not company_name:
        return jsonify({'error': 'Nom de societe requis'}), 400

    ctx_parts = ['Societe: ' + company_name]
    if country: ctx_parts.append('Pays: ' + country)
    if address: ctx_parts.append('Ville: ' + address)
    if sector:  ctx_parts.append('Secteur: ' + sector)
    ctx = ', '.join(ctx_parts)

    # ── Etape 1 : Recherche web (adaptée Render vs Local) ───────
    import os as _os_intel
    _on_render = bool(_os_intel.environ.get('RENDER') or _os_intel.environ.get('RENDER_SERVICE_ID'))
    web_data = ''
    if _on_render:
        # Render : 1 seule recherche rapide, timeout 4s
        try:
            from utils.web_research import search, results_to_text
            wc = results_to_text(search(company_name + ' ' + country + ' description secteur', n=3))
            web_data = 'DONNEES WEB :\n' + wc
            log.info('Render: fast web search done')
        except Exception as we:
            log.warning('Web research failed: %s', we)
            web_data = 'Utilise tes connaissances sur cette entreprise.'
    else:
        # Local : recherche complète
        try:
            from utils.web_research import research_company_contacts, search, results_to_text
            wc = results_to_text(search(company_name + ' ' + country + ' site officiel description', n=5))
            wl = results_to_text(search('site:linkedin.com/company "' + company_name + '"', n=3))
            wk = research_company_contacts(company_name, country)
            web_data = 'DONNEES WEB :\n--- Site ---\n' + wc + '\n--- LinkedIn ---\n' + wl + '\n' + wk
        except Exception as we:
            log.warning('Web research failed: %s', we)
            web_data = 'Utilise tes connaissances sur cette entreprise.'

    # ── Etape 2 : Prompt commun ───────────────────────────────
    system = (
        'Tu es un expert en intelligence commerciale B2B. '
        'Tu connais les entreprises tunisiennes et maghrebines. '
        'Reponds UNIQUEMENT en JSON valide pur, sans backtick, sans commentaire.'
    )

    JSON_TEMPLATE = (
        '{"company":{'
        '"name":"nom exact",'
        '"description":"description detaillee 3-4 phrases",'
        '"sector":"secteur principal",'
        '"sub_sector":"sous-secteur",'
        '"country":"' + country + '",'
        '"city":"ville",'
        '"website":null,'
        '"linkedin_url":null,'
        '"founded_year":null,'
        '"employees_count":"estimation",'
        '"revenue_estimate":"estimation",'
        '"technologies":null,'
        '"certifications":null,'
        '"key_products":["produit1","produit2"],'
        '"key_services":["service1","service2"],'
        '"markets":["marche1","marche2"],'
        '"competitors":["concurrent1","concurrent2"],'
        '"swot":{'
        '"strengths":["force1","force2"],'
        '"weaknesses":["faiblesse1"],'
        '"opportunities":["opportunite1"],'
        '"threats":["menace1"]'
        '},'
        '"why_prospect":"pourquoi interessant pour une entreprise HVAC/froid",'
        '"relevance_score":75'
        '},'
        '"contacts":['
        '{"name":"nom reel","title":"titre","department":"dept",'
        '"linkedin_url":null,"email_guess":null,"seniority":"C-Level","decision_maker":true}'
        ']}'
    )

    prompt_parts = [
        'Analyse cette entreprise en detail : ' + ctx,
        '',
        web_data,
        '',
        'REGLES :',
        '- website, linkedin_url : URLs EXACTES des donnees web, sinon null.',
        '- contacts : UNIQUEMENT les personnes dont le nom apparait dans les donnees web. Sinon contacts:[].',
        '- description, swot, produits : utilise tes connaissances si tu connais cette entreprise.',
        '- Tous les champs sont obligatoires (null si inconnu).',
        '',
        'Reponds avec ce JSON exact (sans backtick) :',
        JSON_TEMPLATE
    ]
    prompt = '\n'.join(prompt_parts)

    # ── Etape 3 : Consensus modeles (1 sur Render, 3 en local) ──
    _intel_models = ['llama-3.3-70b-versatile'] if _on_render else CONSENSUS_MODELS
    results_by_model = {}
    for model in _intel_models:
        try:
            log.info('LinkedIn Intel: calling %s', model)
            raw, err = ask_groq(prompt, system, max_tokens=3000, preferred_model=model)
            if err or not raw:
                log.warning('Model %s failed: %s', model, err)
                continue

            # Nettoyer le JSON
            text = raw.strip()
            text = _re.sub(r'^```(?:json)?\s*', '', text, flags=_re.MULTILINE)
            text = _re.sub(r'\s*```\s*$', '', text, flags=_re.MULTILINE)
            # Supprimer les blocs <think> de DeepSeek R1
            text = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL).strip()

            parsed = None
            try:
                parsed = _json.loads(text)
            except Exception:
                m = _re.search(r'\{[\s\S]*\}', text)
                if m:
                    try:
                        parsed = _json.loads(m.group())
                    except Exception:
                        pass

            if parsed:
                if 'company' not in parsed:
                    parsed = {'company': parsed, 'contacts': []}
                results_by_model[model] = parsed
                log.info('LinkedIn Intel: %s OK — %d contacts', model,
                         len(parsed.get('contacts', [])))
            else:
                log.warning('LinkedIn Intel: %s returned unparseable JSON', model)

        except Exception as e:
            log.warning('LinkedIn Intel model %s exception: %s', model, e)
            continue

    if not results_by_model:
        return jsonify({'error': 'Tous les modeles ont echoue. Verifiez GROQ_API_KEY dans .env'}), 500

    # ── Etape 4 : Fusion optimale ──────────────────────────────
    merged_company, merged_contacts = _consensus_company(results_by_model)

    if not merged_company:
        # Fallback : prendre le premier résultat disponible
        first = list(results_by_model.values())[0]
        merged_company = first.get('company', {})
        merged_contacts = first.get('contacts', [])

    # Metadata de confiance
    nb_models = len(results_by_model)
    merged_company['_consensus'] = (
        str(nb_models) + '/3 modeles confirmes'
    )

    log.info('LinkedIn Intel consensus: %d/%d models, %d contacts',
             nb_models, len(CONSENSUS_MODELS), len(merged_contacts))

    return jsonify({
        'success': True,
        'data': {
            'company':  merged_company,
            'contacts': merged_contacts,
        },
        'consensus': {
            'models_used':    list(results_by_model.keys()),
            'models_success': nb_models,
            'models_total':   len(CONSENSUS_MODELS),
        }
    })


@intelligence_bp.route('/linkedin-search/save', methods=['POST'])
@login_required
def linkedin_save():
    """Save enriched company as prospect."""
    from models import Prospect
    data = request.get_json()
    company = data.get('company', {})
    contact = data.get('contact', {})

    name = company.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Nom societe manquant'}), 400

    existing = Prospect.query.filter_by(company_id=current_user.company_id)\
        .filter(db.func.lower(Prospect.company_name) == name.lower()).first()
    if existing:
        return jsonify({'error': '"' + name + '" existe deja dans vos prospects',
                        'existing_id': existing.id}), 409

    prospect = Prospect(
        company_id      = current_user.company_id,
        company_name    = name,
        sector          = company.get('sector', ''),
        sub_sector      = company.get('sub_sector', ''),
        country         = company.get('country', ''),
        city            = company.get('city', ''),
        website         = company.get('website', ''),
        linkedin_url    = company.get('linkedin_url', ''),
        employees_count = company.get('employees_count', ''),
        contact_name    = contact.get('name', ''),
        contact_title   = contact.get('title', ''),
        email           = contact.get('email_guess', ''),
        why_relevant    = company.get('why_prospect', ''),
        relevance_score = company.get('relevance_score', 50),
        notes           = (
            'Trouve via Intelligence LinkedIn\n'
            'Produits: ' + ', '.join(company.get('key_products', [])) + '\n'
            'Services: ' + ', '.join(company.get('key_services', []))
        ),
        source          = 'ai',
        status          = 'new',
    )
    db.session.add(prospect)
    db.session.commit()
    return jsonify({'success': True, 'prospect_id': prospect.id,
                    'message': '"' + name + '" ajoute dans vos prospects'})