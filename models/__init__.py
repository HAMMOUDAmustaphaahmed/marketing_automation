from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ─────────────────────────────────────────
# USER & COMPANY
# ─────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False)
    email           = db.Column(db.String(150), unique=True, nullable=False)
    password        = db.Column(db.String(255), nullable=False)
    company_id      = db.Column(db.Integer, db.ForeignKey('companies.id'))
    role            = db.Column(db.String(20), default='member')  # admin | member
    # Granular permissions (1=yes, 0=no)
    can_read        = db.Column(db.Boolean, default=True)
    can_create      = db.Column(db.Boolean, default=True)
    can_edit        = db.Column(db.Boolean, default=True)
    can_delete      = db.Column(db.Boolean, default=False)
    is_active       = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime)
    company         = db.relationship('Company', back_populates='users')

class Company(db.Model):
    __tablename__ = 'companies'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(200), nullable=False)
    logo            = db.Column(db.String(255))
    country         = db.Column(db.String(100))
    sector          = db.Column(db.String(200))
    description     = db.Column(db.Text)           # Description produits/services (analysée par Grok)
    keywords        = db.Column(db.Text)           # Mots-clés extraits par Grok
    icp_profile     = db.Column(db.Text)           # Profil client idéal généré par Grok
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    users           = db.relationship('User', back_populates='company')
    competitors     = db.relationship('Competitor', back_populates='company')
    prospects       = db.relationship('Prospect', back_populates='company')

# ─────────────────────────────────────────
# COMPETITORS
# ─────────────────────────────────────────
class Competitor(db.Model):
    __tablename__ = 'competitors'
    id              = db.Column(db.Integer, primary_key=True)
    company_id      = db.Column(db.Integer, db.ForeignKey('companies.id'))
    name            = db.Column(db.String(200), nullable=False)
    logo            = db.Column(db.String(255))
    website         = db.Column(db.String(255))
    country         = db.Column(db.String(100))
    city            = db.Column(db.String(100))
    founded_year    = db.Column(db.Integer)
    sector          = db.Column(db.String(200))
    activities      = db.Column(db.Text)
    products        = db.Column(db.Text)
    services        = db.Column(db.Text)
    employees_count = db.Column(db.String(50))
    linkedin_url    = db.Column(db.String(255))
    facebook_url    = db.Column(db.String(255))
    instagram_url   = db.Column(db.String(255))
    twitter_url     = db.Column(db.String(255))
    google_rating   = db.Column(db.Float)
    trustpilot_rating = db.Column(db.Float)
    technologies    = db.Column(db.Text)
    key_contacts    = db.Column(db.Text)        # JSON string
    revenue_estimate = db.Column(db.String(100))
    similarity_score = db.Column(db.Integer)    # % de similarité avec l'entreprise
    swot_analysis   = db.Column(db.Text)        # Généré par Grok
    notes           = db.Column(db.Text)
    source          = db.Column(db.String(20), default='ai')  # ai ou manual
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    company         = db.relationship('Company', back_populates='competitors')

# ─────────────────────────────────────────
# PROSPECTS / CLIENTS POTENTIELS
# ─────────────────────────────────────────
class Prospect(db.Model):
    __tablename__ = 'prospects'
    id              = db.Column(db.Integer, primary_key=True)
    company_id      = db.Column(db.Integer, db.ForeignKey('companies.id'))
    company_name    = db.Column(db.String(200), nullable=False)
    sector          = db.Column(db.String(200))
    sub_sector      = db.Column(db.String(200))
    country         = db.Column(db.String(100))
    city            = db.Column(db.String(100))
    size            = db.Column(db.String(50))          # TPE, PME, ETI, GE
    employees_count = db.Column(db.String(50))
    contact_name    = db.Column(db.String(150))
    contact_title   = db.Column(db.String(150))
    email           = db.Column(db.String(150))
    phone           = db.Column(db.String(50))
    website         = db.Column(db.String(255))
    linkedin_url    = db.Column(db.String(255))
    why_relevant    = db.Column(db.Text)                # Explication IA pourquoi ce prospect
    relevance_score = db.Column(db.Integer)             # Score 1-100
    status          = db.Column(db.String(30), default='new')
    # new | contacted | replied | opportunity | interested | quoted | won | lost | delivered | maintenance
    notes           = db.Column(db.Text)
    source          = db.Column(db.String(20), default='ai')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    company         = db.relationship('Company', back_populates='prospects')
    opportunities   = db.relationship('Opportunity', back_populates='prospect')
    email_logs      = db.relationship('EmailLog', back_populates='prospect')

# ─────────────────────────────────────────
# MAILING CAMPAIGNS
# ─────────────────────────────────────────
class EmailCampaign(db.Model):
    __tablename__ = 'email_campaigns'
    id              = db.Column(db.Integer, primary_key=True)
    company_id      = db.Column(db.Integer, db.ForeignKey('companies.id'))
    name            = db.Column(db.String(200), nullable=False)
    subject         = db.Column(db.String(300))
    body_html       = db.Column(db.Text)
    body_text       = db.Column(db.Text)
    status          = db.Column(db.String(20), default='draft')  # draft, scheduled, sent
    scheduled_at    = db.Column(db.DateTime)
    sent_at         = db.Column(db.DateTime)
    total_sent      = db.Column(db.Integer, default=0)
    total_opened    = db.Column(db.Integer, default=0)
    total_clicked   = db.Column(db.Integer, default=0)
    total_replied   = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    logs            = db.relationship('EmailLog', back_populates='campaign')

class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    id              = db.Column(db.Integer, primary_key=True)
    campaign_id     = db.Column(db.Integer, db.ForeignKey('email_campaigns.id'))
    prospect_id     = db.Column(db.Integer, db.ForeignKey('prospects.id'))
    email_to        = db.Column(db.String(150))
    status          = db.Column(db.String(20), default='sent')  # sent, opened, clicked, replied, bounced
    sent_at         = db.Column(db.DateTime, default=datetime.utcnow)
    opened_at       = db.Column(db.DateTime)
    replied_at      = db.Column(db.DateTime)
    campaign        = db.relationship('EmailCampaign', back_populates='logs')
    prospect        = db.relationship('Prospect', back_populates='email_logs')

# ─────────────────────────────────────────
# PIPELINE CRM
# ─────────────────────────────────────────
class Opportunity(db.Model):
    __tablename__ = 'opportunities'
    id              = db.Column(db.Integer, primary_key=True)
    company_id      = db.Column(db.Integer, db.ForeignKey('companies.id'))
    prospect_id     = db.Column(db.Integer, db.ForeignKey('prospects.id'))
    title           = db.Column(db.String(200), nullable=False)
    product_service = db.Column(db.String(200))
    value           = db.Column(db.Float)
    currency        = db.Column(db.String(10), default='TND')
    probability     = db.Column(db.Integer, default=50)  # %
    stage           = db.Column(db.String(30), default='replied')
    # replied | interested | quoted | won | lost | delivered | maintenance
    assigned_to     = db.Column(db.Integer, db.ForeignKey('users.id'))
    next_followup   = db.Column(db.DateTime)
    lost_reason     = db.Column(db.String(200))
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    prospect        = db.relationship('Prospect', back_populates='opportunities')
    quotes          = db.relationship('Quote', back_populates='opportunity')
    orders          = db.relationship('Order', back_populates='opportunity')

class Quote(db.Model):
    __tablename__ = 'quotes'
    id              = db.Column(db.Integer, primary_key=True)
    opportunity_id  = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    quote_number    = db.Column(db.String(50), unique=True)
    source          = db.Column(db.String(20), default='internal')  # internal | uploaded
    file_path       = db.Column(db.String(255))   # si uploadé
    total_ht        = db.Column(db.Float)
    tva             = db.Column(db.Float, default=19.0)
    total_ttc       = db.Column(db.Float)
    status          = db.Column(db.String(20), default='sent')  # sent | accepted | refused
    sent_at         = db.Column(db.DateTime)
    valid_until     = db.Column(db.DateTime)
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    opportunity     = db.relationship('Opportunity', back_populates='quotes')
    items           = db.relationship('QuoteItem', back_populates='quote')

class QuoteItem(db.Model):
    __tablename__ = 'quote_items'
    id              = db.Column(db.Integer, primary_key=True)
    quote_id        = db.Column(db.Integer, db.ForeignKey('quotes.id'))
    description     = db.Column(db.String(300))
    quantity        = db.Column(db.Float, default=1)
    unit_price      = db.Column(db.Float)
    discount        = db.Column(db.Float, default=0)
    total           = db.Column(db.Float)
    quote           = db.relationship('Quote', back_populates='items')

class Order(db.Model):
    __tablename__ = 'orders'
    id              = db.Column(db.Integer, primary_key=True)
    opportunity_id  = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    order_number    = db.Column(db.String(50), unique=True)
    source          = db.Column(db.String(20), default='internal')
    file_path       = db.Column(db.String(255))
    amount          = db.Column(db.Float)
    status          = db.Column(db.String(20), default='pending')
    # pending | confirmed | delivered | cancelled
    ordered_at      = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at    = db.Column(db.DateTime)
    delivery_status = db.Column(db.String(20))  # pending | delivered | issue
    client_satisfaction = db.Column(db.String(20))  # satisfied | unsatisfied | pv_uploaded
    pv_file_path    = db.Column(db.String(255))
    delivery_notes  = db.Column(db.Text)
    opportunity     = db.relationship('Opportunity', back_populates='orders')
    maintenance     = db.relationship('MaintenanceContract', back_populates='order', uselist=False)

class MaintenanceContract(db.Model):
    __tablename__ = 'maintenance_contracts'
    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey('orders.id'))
    company_id      = db.Column(db.Integer, db.ForeignKey('companies.id'))
    contract_number = db.Column(db.String(50), unique=True)
    file_path       = db.Column(db.String(255))
    start_date      = db.Column(db.DateTime)
    end_date        = db.Column(db.DateTime)
    annual_value    = db.Column(db.Float)
    currency        = db.Column(db.String(10), default='TND')
    status          = db.Column(db.String(20), default='active')  # active | expired | renewed | cancelled
    renewal_alert_sent = db.Column(db.Boolean, default=False)
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    order           = db.relationship('Order', back_populates='maintenance')


# ─────────────────────────────────────────
# MAINTENANCE CRM (module séparé)
# ─────────────────────────────────────────
class MaintenanceOpportunity(db.Model):
    """
    Opportunité de vente de contrats de maintenance.
    Indépendant du pipeline commercial classique.
    Types : préventive (planifiée) ou curative (dépannage).
    Parcs : matériel industriel, informatique, froid, CVC, etc.
    """
    __tablename__ = 'maintenance_opportunities'
    id              = db.Column(db.Integer, primary_key=True)
    company_id      = db.Column(db.Integer, db.ForeignKey('companies.id'))
    prospect_id     = db.Column(db.Integer, db.ForeignKey('prospects.id'), nullable=True)
    title           = db.Column(db.String(200), nullable=False)
    # Type de maintenance
    maint_type      = db.Column(db.String(20), default='preventive')
    # preventive | curative | both
    # Type de parc
    park_type       = db.Column(db.String(100))
    # park_materiel | park_informatique | park_froid | park_cvc | park_electrique | autre
    park_description = db.Column(db.Text)     # Description détaillée du parc
    nb_equipments   = db.Column(db.Integer)   # Nombre d'équipements
    site_address    = db.Column(db.String(300)) # Adresse du site
    # Valeur & durée
    value           = db.Column(db.Float)
    currency        = db.Column(db.String(10), default='TND')
    contract_duration = db.Column(db.Integer, default=12)  # mois
    visits_per_year = db.Column(db.Integer, default=4)     # Nb visites préventives/an
    # Pipeline
    stage           = db.Column(db.String(30), default='prospecting')
    # prospecting | quoted | negotiating | won | active | expired | lost
    probability     = db.Column(db.Integer, default=50)
    next_visit      = db.Column(db.DateTime)
    next_followup   = db.Column(db.DateTime)
    lost_reason     = db.Column(db.String(200))
    notes           = db.Column(db.Text)
    assigned_to     = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relations
    prospect        = db.relationship('Prospect', foreign_keys=[prospect_id])
    quotes          = db.relationship('MaintenanceQuote', back_populates='opportunity', cascade='all, delete-orphan')


class MaintenanceQuote(db.Model):
    """Devis associé à une opportunité de maintenance."""
    __tablename__ = 'maintenance_quotes'
    id              = db.Column(db.Integer, primary_key=True)
    opportunity_id  = db.Column(db.Integer, db.ForeignKey('maintenance_opportunities.id'))
    quote_number    = db.Column(db.String(50), unique=True)
    total_ht        = db.Column(db.Float)
    tva             = db.Column(db.Float, default=19.0)
    total_ttc       = db.Column(db.Float)
    status          = db.Column(db.String(20), default='draft')
    # draft | sent | accepted | refused
    valid_until     = db.Column(db.DateTime)
    notes           = db.Column(db.Text)
    file_path       = db.Column(db.String(255))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    opportunity     = db.relationship('MaintenanceOpportunity', back_populates='quotes')

# ─────────────────────────────────────────
# ACTIVITY LOG
# ─────────────────────────────────────────
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id              = db.Column(db.Integer, primary_key=True)
    company_id      = db.Column(db.Integer, db.ForeignKey('companies.id'))
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'))
    entity_type     = db.Column(db.String(50))   # prospect, opportunity, competitor...
    entity_id       = db.Column(db.Integer)
    action          = db.Column(db.String(100))  # created, updated, emailed, won...
    description     = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
