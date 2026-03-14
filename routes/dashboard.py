from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import db, Prospect, Opportunity, MaintenanceOpportunity, EmailCampaign
from sqlalchemy import func
from datetime import datetime, timedelta, date

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    cid = current_user.company_id

    # ── Date filter ──────────────────────────────────────────
    date_from_str = request.args.get('date_from', '')
    date_to_str   = request.args.get('date_to', '')

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else None
    except ValueError:
        date_from = None
    try:
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23,minute=59,second=59) if date_to_str else None
    except ValueError:
        date_to = None

    # Preset labels
    today = date.today()
    preset = request.args.get('preset', '')
    if preset == '7d':
        date_from = datetime.combine(today - timedelta(days=7), datetime.min.time())
        date_to   = datetime.now()
    elif preset == '30d':
        date_from = datetime.combine(today - timedelta(days=30), datetime.min.time())
        date_to   = datetime.now()
    elif preset == '90d':
        date_from = datetime.combine(today - timedelta(days=90), datetime.min.time())
        date_to   = datetime.now()
    elif preset == 'year':
        date_from = datetime(today.year, 1, 1)
        date_to   = datetime.now()

    # ── Base queries with optional date filter ───────────────
    def apply_date(q, model, field='created_at'):
        col = getattr(model, field)
        if date_from: q = q.filter(col >= date_from)
        if date_to:   q = q.filter(col <= date_to)
        return q

    p_base = Prospect.query.filter_by(company_id=cid)
    o_base = Opportunity.query.filter_by(company_id=cid)

    total_prospects = apply_date(p_base, Prospect).count()
    contacted       = apply_date(p_base.filter_by(status='contacted'), Prospect).count()
    replied         = apply_date(p_base.filter_by(status='replied'), Prospect).count()
    opportunities   = apply_date(o_base, Opportunity, 'created_at').count()
    won             = apply_date(o_base.filter_by(stage='won'), Opportunity, 'updated_at').count()
    lost            = apply_date(o_base.filter_by(stage='lost'), Opportunity, 'updated_at').count()

    # Pipeline value (no date filter — current state)
    pipeline_value = db.session.query(func.sum(Opportunity.value)).filter(
        Opportunity.company_id == cid,
        Opportunity.stage.notin_(['won', 'lost'])
    ).scalar() or 0

    won_q = o_base.filter_by(stage='won')
    if date_from: won_q = won_q.filter(Opportunity.updated_at >= date_from)
    if date_to:   won_q = won_q.filter(Opportunity.updated_at <= date_to)
    won_value = db.session.query(func.sum(Opportunity.value)).filter(
        Opportunity.company_id == cid, Opportunity.stage == 'won',
        *(([Opportunity.updated_at >= date_from] if date_from else []) +
          ([Opportunity.updated_at <= date_to]   if date_to   else []))
    ).scalar() or 0

    # Maintenance revenue
    maint_value = db.session.query(func.sum(MaintenanceOpportunity.value)).filter(
        MaintenanceOpportunity.company_id == cid,
        MaintenanceOpportunity.stage.in_(['won', 'active'])
    ).scalar() or 0

    # Expiring maintenance contracts
    in_30_days = datetime.utcnow() + timedelta(days=30)
    from models import MaintenanceContract
    expiring_contracts = MaintenanceContract.query.filter(
        MaintenanceContract.company_id == cid,
        MaintenanceContract.end_date <= in_30_days,
        MaintenanceContract.end_date >= datetime.utcnow(),
        MaintenanceContract.status == 'active'
    ).count()

    conversion_rate = round((won / opportunities * 100) if opportunities > 0 else 0, 1)

    # Stage funnel
    stages = ['new', 'contacted', 'replied', 'interested', 'quoted', 'won']
    stage_labels = ['Nouveau', 'Contacté', 'A répondu', 'Intéressé', 'Devis envoyé', 'Gagné']
    stage_counts = [apply_date(p_base.filter_by(status=s), Prospect).count() for s in stages]

    # Monthly revenue trend (last 6 months, ignore date filter for trend)
    months, monthly_won = [], []
    for i in range(5, -1, -1):
        dt = datetime.now().replace(day=1) - timedelta(days=i*30)
        m_start = dt.replace(day=1, hour=0, minute=0, second=0)
        if dt.month == 12:
            m_end = dt.replace(year=dt.year+1, month=1, day=1)
        else:
            m_end = dt.replace(month=dt.month+1, day=1)
        val = db.session.query(func.sum(Opportunity.value)).filter(
            Opportunity.company_id == cid,
            Opportunity.stage == 'won',
            Opportunity.updated_at >= m_start,
            Opportunity.updated_at < m_end,
        ).scalar() or 0
        months.append(m_start.strftime('%b %Y'))
        monthly_won.append(round(val, 0))

    # Stage distribution for donut
    stage_dist_labels = ['Prospecté', 'Devis', 'Gagné', 'Perdu', 'Livré']
    stage_dist_vals = [
        Opportunity.query.filter_by(company_id=cid, stage='replied').count() +
        Opportunity.query.filter_by(company_id=cid, stage='interested').count(),
        Opportunity.query.filter_by(company_id=cid, stage='quoted').count(),
        Opportunity.query.filter_by(company_id=cid, stage='won').count(),
        Opportunity.query.filter_by(company_id=cid, stage='lost').count(),
        Opportunity.query.filter_by(company_id=cid, stage='delivered').count(),
    ]

    recent_opps      = Opportunity.query.filter_by(company_id=cid).order_by(Opportunity.updated_at.desc()).limit(5).all()
    recent_prospects = apply_date(p_base, Prospect, 'created_at').order_by(Prospect.created_at.desc()).limit(5).all()

    return render_template('dashboard/index.html',
        total_prospects=total_prospects, contacted=contacted, replied=replied,
        opportunities=opportunities, won=won, lost=lost,
        pipeline_value=pipeline_value, won_value=won_value,
        maint_value=maint_value,
        expiring_contracts=expiring_contracts,
        conversion_rate=conversion_rate,
        stage_labels=stage_labels, stage_counts=stage_counts,
        monthly_labels=months, monthly_won=monthly_won,
        stage_dist_labels=stage_dist_labels, stage_dist_vals=stage_dist_vals,
        recent_opps=recent_opps, recent_prospects=recent_prospects,
        date_from=date_from_str or (date_from.strftime('%Y-%m-%d') if date_from else ''),
        date_to=date_to_str or (date_to.strftime('%Y-%m-%d') if date_to else ''),
        preset=preset,
    )
