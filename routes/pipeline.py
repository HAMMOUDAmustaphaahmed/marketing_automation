from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from models import db, Opportunity, Quote, QuoteItem, Order, MaintenanceContract, Prospect
from utils.pdf_generator import generate_quote_pdf
from datetime import datetime
import os, uuid
from werkzeug.utils import secure_filename

pipeline_bp = Blueprint('pipeline', __name__, url_prefix='/pipeline')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, subfolder='uploads'):
    from flask import current_app
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    return os.path.join('uploads', subfolder, filename)


# ─── PIPELINE KANBAN ─────────────────────────────────────────────────────────
@pipeline_bp.route('/')
@login_required
def index():
    cid = current_user.company_id
    stages = {
        'replied':    {'label': 'A répondu',     'color': 'blue',   'icon': '💬'},
        'interested': {'label': 'Intéressé',      'color': 'yellow', 'icon': '⭐'},
        'quoted':     {'label': 'Devis envoyé',   'color': 'purple', 'icon': '📄'},
        'won':        {'label': 'Gagné',          'color': 'green',  'icon': '🏆'},
        'lost':       {'label': 'Perdu',          'color': 'red',    'icon': '❌'},
        'delivered':  {'label': 'Livré',          'color': 'teal',   'icon': '🚚'},
    }

    pipeline = {}
    for stage, info in stages.items():
        opps = Opportunity.query.filter_by(company_id=cid, stage=stage)\
            .order_by(Opportunity.updated_at.desc()).all()
        pipeline[stage] = {'info': info, 'opportunities': opps}

    return render_template('pipeline/index.html', pipeline=pipeline)


# ─── OPPORTUNITIES ────────────────────────────────────────────────────────────
@pipeline_bp.route('/opportunity/create/<int:prospect_id>', methods=['GET', 'POST'])
@login_required
def create_opportunity(prospect_id):
    prospect = Prospect.query.filter_by(id=prospect_id, company_id=current_user.company_id).first_or_404()
    if request.method == 'POST':
        opp = Opportunity(
            company_id      = current_user.company_id,
            prospect_id     = prospect_id,
            title           = request.form.get('title'),
            product_service = request.form.get('product_service'),
            value           = request.form.get('value') or None,
            currency        = request.form.get('currency', 'TND'),
            probability     = request.form.get('probability', 50),
            stage           = 'replied',
            assigned_to     = current_user.id,
            notes           = request.form.get('notes'),
        )
        db.session.add(opp)
        prospect.status = 'replied'
        db.session.commit()
        flash('Opportunité créée avec succès !', 'success')
        return redirect(url_for('pipeline.index'))
    return render_template('pipeline/create_opportunity.html', prospect=prospect)


@pipeline_bp.route('/opportunity/<int:id>')
@login_required
def view_opportunity(id):
    opp = Opportunity.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    return render_template('pipeline/opportunity.html', opp=opp)


@pipeline_bp.route('/opportunity/<int:id>/stage', methods=['POST'])
@login_required
def update_stage(id):
    opp = Opportunity.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    new_stage = request.form.get('stage')
    valid_stages = ['replied', 'interested', 'quoted', 'won', 'lost', 'delivered']
    if new_stage in valid_stages:
        opp.stage = new_stage
        opp.prospect.status = new_stage
        if new_stage == 'lost':
            opp.lost_reason = request.form.get('lost_reason', '')
        db.session.commit()
        flash(f'Opportunité mise à jour : {new_stage}', 'success')
    return redirect(request.referrer or url_for('pipeline.index'))


# ─── QUOTES ──────────────────────────────────────────────────────────────────
@pipeline_bp.route('/opportunity/<int:opp_id>/quote/create', methods=['GET', 'POST'])
@login_required
def create_quote(opp_id):
    opp = Opportunity.query.filter_by(id=opp_id, company_id=current_user.company_id).first_or_404()

    if request.method == 'POST':
        source = request.form.get('source', 'internal')

        # Generate quote number
        count = Quote.query.filter_by(opportunity_id=opp_id).count()
        quote_number = f"DV-{datetime.now().year}-{opp_id:04d}-{count+1:02d}"

        quote = Quote(
            opportunity_id = opp_id,
            quote_number   = quote_number,
            source         = source,
            tva            = float(request.form.get('tva', 19)),
            notes          = request.form.get('notes'),
            sent_at        = datetime.utcnow(),
            valid_until    = datetime.strptime(request.form.get('valid_until'), '%Y-%m-%d') if request.form.get('valid_until') else None,
        )

        if source == 'uploaded':
            file = request.files.get('quote_file')
            if file and allowed_file(file.filename):
                quote.file_path = save_upload(file, 'quotes')
            quote.total_ht  = float(request.form.get('total_ht', 0))
            quote.total_ttc = float(request.form.get('total_ttc', 0))
        else:
            # Internal quote with line items
            descriptions = request.form.getlist('item_description[]')
            quantities   = request.form.getlist('item_quantity[]')
            prices       = request.form.getlist('item_price[]')
            discounts    = request.form.getlist('item_discount[]')

            db.session.add(quote)
            db.session.flush()  # get quote.id

            total_ht = 0
            for i, desc in enumerate(descriptions):
                if desc.strip():
                    qty      = float(quantities[i]) if quantities[i] else 1
                    price    = float(prices[i]) if prices[i] else 0
                    discount = float(discounts[i]) if discounts[i] else 0
                    total    = qty * price * (1 - discount/100)
                    total_ht += total
                    item = QuoteItem(
                        quote_id    = quote.id,
                        description = desc,
                        quantity    = qty,
                        unit_price  = price,
                        discount    = discount,
                        total       = total
                    )
                    db.session.add(item)

            quote.total_ht  = total_ht
            quote.total_ttc = total_ht * (1 + quote.tva / 100)

        db.session.add(quote)
        opp.stage = 'quoted'
        opp.prospect.status = 'quoted'
        db.session.commit()
        flash(f'Devis {quote_number} créé avec succès.', 'success')
        return redirect(url_for('pipeline.view_opportunity', id=opp_id))

    return render_template('pipeline/create_quote.html', opp=opp)


@pipeline_bp.route('/quote/<int:id>/pdf')
@login_required
def quote_pdf(id):
    quote = Quote.query.filter_by(id=id).first_or_404()
    if quote.opportunity.company_id != current_user.company_id:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('pipeline.index'))
    buffer = generate_quote_pdf(quote, current_user.company)
    filename = f"devis_{quote.quote_number}.pdf"
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)


# ─── ORDERS ──────────────────────────────────────────────────────────────────
@pipeline_bp.route('/opportunity/<int:opp_id>/order/create', methods=['GET', 'POST'])
@login_required
def create_order(opp_id):
    opp = Opportunity.query.filter_by(id=opp_id, company_id=current_user.company_id).first_or_404()

    if request.method == 'POST':
        count = Order.query.filter_by(opportunity_id=opp_id).count()
        order_number = f"BC-{datetime.now().year}-{opp_id:04d}-{count+1:02d}"

        order = Order(
            opportunity_id = opp_id,
            order_number   = order_number,
            source         = request.form.get('source', 'internal'),
            amount         = float(request.form.get('amount', 0)),
            status         = 'confirmed',
        )

        file = request.files.get('order_file')
        if file and allowed_file(file.filename):
            order.file_path = save_upload(file, 'orders')

        db.session.add(order)
        opp.stage = 'won'
        opp.prospect.status = 'won'
        db.session.commit()
        flash(f'Bon de commande {order_number} créé. Opportunité marquée comme GAGNÉE !', 'success')
        return redirect(url_for('pipeline.view_opportunity', id=opp_id))

    return render_template('pipeline/create_order.html', opp=opp)


@pipeline_bp.route('/order/<int:id>/deliver', methods=['POST'])
@login_required
def deliver_order(id):
    order = Order.query.filter_by(id=id).first_or_404()
    if order.opportunity.company_id != current_user.company_id:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('pipeline.index'))

    order.delivered_at       = datetime.utcnow()
    order.delivery_status    = 'delivered'
    order.client_satisfaction = request.form.get('satisfaction', 'satisfied')
    order.delivery_notes     = request.form.get('delivery_notes', '')
    order.opportunity.stage  = 'delivered'
    order.opportunity.prospect.status = 'delivered'

    pv_file = request.files.get('pv_file')
    if pv_file and allowed_file(pv_file.filename):
        order.pv_file_path = save_upload(pv_file, 'pv')
        order.client_satisfaction = 'pv_uploaded'

    db.session.commit()
    flash('Livraison confirmée !', 'success')
    return redirect(url_for('pipeline.view_opportunity', id=order.opportunity_id))


# ─── MAINTENANCE ─────────────────────────────────────────────────────────────
@pipeline_bp.route('/order/<int:order_id>/maintenance/create', methods=['GET', 'POST'])
@login_required
def create_maintenance(order_id):
    order = Order.query.filter_by(id=order_id).first_or_404()
    if order.opportunity.company_id != current_user.company_id:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('pipeline.index'))

    if request.method == 'POST':
        count = MaintenanceContract.query.filter_by(company_id=current_user.company_id).count()
        contract_number = f"MT-{datetime.now().year}-{count+1:04d}"

        mc = MaintenanceContract(
            order_id        = order_id,
            company_id      = current_user.company_id,
            contract_number = contract_number,
            start_date      = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d'),
            end_date        = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d'),
            annual_value    = float(request.form.get('annual_value', 0)),
            currency        = request.form.get('currency', 'TND'),
            notes           = request.form.get('notes'),
            status          = 'active'
        )
        file = request.files.get('contract_file')
        if file and allowed_file(file.filename):
            mc.file_path = save_upload(file, 'contracts')

        db.session.add(mc)
        order.opportunity.stage = 'maintenance'
        order.opportunity.prospect.status = 'maintenance'
        db.session.commit()
        flash(f'Contrat de maintenance {contract_number} créé.', 'success')
        return redirect(url_for('pipeline.view_opportunity', id=order.opportunity_id))

    return render_template('pipeline/create_maintenance.html', order=order)


@pipeline_bp.route('/maintenance')
@login_required
def maintenance_list():
    contracts = MaintenanceContract.query.filter_by(company_id=current_user.company_id)\
        .order_by(MaintenanceContract.end_date.asc()).all()
    return render_template("pipeline/maintenance_list.html", contracts=contracts, now=__import__("datetime").datetime.utcnow())


# ─── CREATE OPPORTUNITY DIRECT (depuis Pipeline) ─────────────────────────────
@pipeline_bp.route('/opportunity/new', methods=['GET', 'POST'])
@login_required
def new_opportunity():
    """Créer une opportunité directement depuis le pipeline avec sélecteur de prospect."""
    cid = current_user.company_id
    prospects = Prospect.query.filter_by(company_id=cid)        .order_by(Prospect.company_name.asc()).all()

    if request.method == 'POST':
        prospect_id = request.form.get('prospect_id', type=int)
        prospect = Prospect.query.filter_by(id=prospect_id, company_id=cid).first() if prospect_id else None

        opp = Opportunity(
            company_id      = cid,
            prospect_id     = prospect_id,
            title           = request.form.get('title'),
            product_service = request.form.get('product_service'),
            value           = request.form.get('value') or None,
            currency        = request.form.get('currency', 'TND'),
            probability     = request.form.get('probability', 50),
            stage           = request.form.get('stage', 'replied'),
            assigned_to     = current_user.id,
            notes           = request.form.get('notes'),
        )
        nf = request.form.get('next_followup')
        if nf:
            opp.next_followup = datetime.strptime(nf, '%Y-%m-%d')

        db.session.add(opp)
        if prospect:
            prospect.status = opp.stage
        db.session.commit()
        flash('Opportunité créée avec succès !', 'success')
        return redirect(url_for('pipeline.index'))

    return render_template('pipeline/new_opportunity.html', prospects=prospects)

# ─── EDIT OPPORTUNITY ─────────────────────────────────────────────────────────
@pipeline_bp.route('/opportunity/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_opportunity(id):
    opp = Opportunity.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    if request.method == 'POST':
        opp.title           = request.form.get('title', opp.title)
        opp.product_service = request.form.get('product_service', opp.product_service)
        opp.value           = request.form.get('value') or opp.value
        opp.currency        = request.form.get('currency', opp.currency)
        opp.probability     = request.form.get('probability', opp.probability)
        opp.notes           = request.form.get('notes', opp.notes)
        nf = request.form.get('next_followup')
        if nf:
            opp.next_followup = datetime.strptime(nf, '%Y-%m-%d')
        db.session.commit()
        flash('Opportunité mise à jour.', 'success')
        return redirect(url_for('pipeline.view_opportunity', id=id))
    return render_template('pipeline/edit_opportunity.html', opp=opp)


# ─── DELETE OPPORTUNITY ───────────────────────────────────────────────────────
@pipeline_bp.route('/opportunity/<int:id>/delete', methods=['POST'])
@login_required
def delete_opportunity(id):
    opp = Opportunity.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    db.session.delete(opp)
    db.session.commit()
    flash('Opportunité supprimée.', 'success')
    return redirect(url_for('pipeline.index'))


# ─── QUICK STAGE FROM KANBAN ──────────────────────────────────────────────────
@pipeline_bp.route('/opportunity/<int:id>/quick-stage', methods=['POST'])
@login_required
def quick_stage(id):
    opp = Opportunity.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    new_stage = request.form.get('stage')
    valid = ['replied','interested','quoted','won','lost','delivered','maintenance']
    if new_stage in valid:
        opp.stage = new_stage
        if opp.prospect:
            opp.prospect.status = new_stage
        if new_stage == 'lost':
            opp.lost_reason = request.form.get('lost_reason', '')
        db.session.commit()
    return redirect(url_for('pipeline.index'))


# ─── EDIT MAINTENANCE ─────────────────────────────────────────────────────────
@pipeline_bp.route('/maintenance/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_maintenance(id):
    mc = MaintenanceContract.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    if request.method == 'POST':
        mc.contract_number = request.form.get('contract_number', mc.contract_number)
        mc.annual_value    = request.form.get('annual_value') or mc.annual_value
        mc.status          = request.form.get('status', mc.status)
        sd = request.form.get('start_date')
        ed = request.form.get('end_date')
        if sd:
            mc.start_date = datetime.strptime(sd, '%Y-%m-%d').date()
        if ed:
            mc.end_date = datetime.strptime(ed, '%Y-%m-%d').date()
        db.session.commit()
        flash('Contrat de maintenance mis à jour.', 'success')
        return redirect(url_for('pipeline.maintenance_list'))
    return render_template('pipeline/edit_maintenance.html', mc=mc)


# ─── DELETE MAINTENANCE ───────────────────────────────────────────────────────
@pipeline_bp.route('/maintenance/<int:id>/delete', methods=['POST'])
@login_required
def delete_maintenance(id):
    mc = MaintenanceContract.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    db.session.delete(mc)
    db.session.commit()
    flash('Contrat supprimé.', 'success')
    return redirect(url_for('pipeline.maintenance_list'))
