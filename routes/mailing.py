from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from models import db, EmailCampaign, EmailLog, Prospect
from utils.groq_ai import generate_email_template
from datetime import datetime

mailing_bp = Blueprint('mailing', __name__, url_prefix='/mailing')

@mailing_bp.route('/')
@login_required
def index():
    cid = current_user.company_id
    campaigns = EmailCampaign.query.filter_by(company_id=cid)\
        .order_by(EmailCampaign.created_at.desc()).all()
    return render_template('mailing/index.html', campaigns=campaigns)


@mailing_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    cid = current_user.company_id
    if request.method == 'POST':
        campaign = EmailCampaign(
            company_id = cid,
            name       = request.form.get('name'),
            subject    = request.form.get('subject'),
            body_html  = request.form.get('body_html'),
            body_text  = request.form.get('body_text'),
            status     = 'draft'
        )
        scheduled = request.form.get('scheduled_at')
        if scheduled:
            campaign.scheduled_at = datetime.strptime(scheduled, '%Y-%m-%dT%H:%M')
            campaign.status = 'scheduled'

        db.session.add(campaign)
        db.session.commit()
        flash('Campagne créée.', 'success')
        return redirect(url_for('mailing.view', id=campaign.id))

    # Get available prospects with emails
    prospects = Prospect.query.filter_by(company_id=cid)\
        .filter(Prospect.email != None, Prospect.email != '').all()
    return render_template('mailing/create.html', prospects=prospects)


@mailing_bp.route('/<int:id>')
@login_required
def view(id):
    campaign = EmailCampaign.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    logs = EmailLog.query.filter_by(campaign_id=id).all()
    return render_template('mailing/view.html', campaign=campaign, logs=logs)


@mailing_bp.route('/<int:id>/send', methods=['POST'])
@login_required
def send_campaign(id):
    from app import mail
    campaign = EmailCampaign.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()

    # Get target prospects
    target = request.form.get('target', 'all')
    sector = request.form.get('sector', '')

    # Emails à exclure (séparés par virgule ou retour ligne)
    exclude_raw = request.form.get('exclude_emails', '')
    excluded = [e.strip().lower() for e in exclude_raw.replace(',', chr(10)).split() if e.strip()]

    query = Prospect.query.filter_by(company_id=current_user.company_id)\
        .filter(Prospect.email != None, Prospect.email != '')
    if target == 'sector' and sector:
        query = query.filter(Prospect.sector.ilike(f'%{sector}%'))
    elif target == 'specific':
        ids = request.form.getlist('prospect_ids[]')
        query = query.filter(Prospect.id.in_(ids))

    prospects = [p for p in query.all() if p.email.lower() not in excluded]
    sent_count = 0

    for prospect in prospects:
        try:
            msg = Message(
                subject    = campaign.subject,
                recipients = [prospect.email],
                html       = campaign.body_html.replace('{{name}}', prospect.contact_name or '')
                                               .replace('{{company}}', prospect.company_name or ''),
                body       = campaign.body_text or ''
            )
            mail.send(msg)

            log = EmailLog(
                campaign_id = campaign.id,
                prospect_id = prospect.id,
                email_to    = prospect.email,
                status      = 'sent',
                sent_at     = datetime.utcnow()
            )
            db.session.add(log)

            if prospect.status == 'new':
                prospect.status = 'contacted'

            sent_count += 1
        except Exception as e:
            current_app.logger.error(f"Email send error to {prospect.email}: {e}")

    campaign.status    = 'sent'
    campaign.sent_at   = datetime.utcnow()
    campaign.total_sent += sent_count
    db.session.commit()

    flash(f'Campagne envoyée à {sent_count} prospects.', 'success')
    return redirect(url_for('mailing.view', id=id))


@mailing_bp.route('/send-individual', methods=['POST'])
@login_required
def send_individual():
    from app import mail
    prospect_id = request.form.get('prospect_id', type=int)
    prospect = Prospect.query.filter_by(id=prospect_id, company_id=current_user.company_id).first_or_404()

    subject   = request.form.get('subject')
    body_html = request.form.get('body_html')

    try:
        msg = Message(
            subject    = subject,
            recipients = [prospect.email],
            html       = body_html
        )
        mail.send(msg)

        log = EmailLog(
            prospect_id = prospect_id,
            email_to    = prospect.email,
            status      = 'sent',
            sent_at     = datetime.utcnow()
        )
        db.session.add(log)

        if prospect.status == 'new':
            prospect.status = 'contacted'

        db.session.commit()
        flash(f'Email envoyé à {prospect.email}.', 'success')
    except Exception as e:
        flash(f'Erreur envoi email : {str(e)}', 'error')

    return redirect(url_for('prospects.view', id=prospect_id))


@mailing_bp.route('/generate-template', methods=['POST'])
@login_required
def generate_template():
    """Generate email template using Grok AI."""
    company = current_user.company
    sector  = request.json.get('sector', '')
    contact = request.json.get('contact', '')

    template, error = generate_email_template(
        company.name,
        company.description or '',
        sector,
        contact
    )
    if error:
        return jsonify({'error': error}), 400
    return jsonify(template)


@mailing_bp.route('/log/<int:id>/replied', methods=['POST'])
@login_required
def mark_replied(id):
    log = EmailLog.query.filter_by(id=id).first_or_404()
    log.status     = 'replied'
    log.replied_at = datetime.utcnow()
    if log.prospect:
        log.prospect.status = 'replied'
    if log.campaign:
        log.campaign.total_replied += 1
    db.session.commit()
    flash('Réponse enregistrée. Créez une opportunité pour ce prospect.', 'info')
    return redirect(request.referrer or url_for('mailing.index'))
