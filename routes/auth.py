from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Company
import json

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash("Votre compte est désactivé. Contactez l'administrateur.", 'error')
                return redirect(url_for('auth.login'))
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=True)
            return redirect(url_for('dashboard.index'))
        flash('Email ou mot de passe incorrect.', 'error')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        name         = request.form.get('name')
        email        = request.form.get('email')
        password     = request.form.get('password')
        company_name = request.form.get('company_name')
        country      = request.form.get('country', 'Tunisie')
        description  = request.form.get('description')
        sector       = request.form.get('sector')

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'error')
            return render_template('auth/register.html')

        company = Company(
            name=company_name,
            country=country,
            sector=(sector or '')[:200],
            description=description
        )
        db.session.add(company)
        db.session.flush()

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            company_id=company.id,
            role='admin'
        )
        db.session.add(user)
        db.session.commit()

        # Analyze with Grok in background (simple sync for now)
        try:
            from utils.groq_ai import analyze_company_profile
            analysis, err = analyze_company_profile(description, country)
            if analysis:
                company.keywords = json.dumps(analysis.get('keywords', []))
                company.icp_profile = json.dumps(analysis.get('icp', {}))
                if not sector:
                    company.sector = (analysis.get('sector', '') or '')[:200]
                db.session.commit()
        except Exception:
            pass

        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user, remember=True)
        flash('Compte créé avec succès ! Bienvenue.', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    company = current_user.company
    if request.method == 'POST':
        company.name        = request.form.get('company_name', company.name)
        company.country     = request.form.get('country', company.country)
        company.sector      = request.form.get('sector', company.sector)
        company.description = request.form.get('description', company.description)
        current_user.name   = request.form.get('name', current_user.name)
        db.session.commit()
        flash('Profil mis à jour.', 'success')
    from models import Competitor, Prospect, Opportunity
    stats = {
        'competitors':   Competitor.query.filter_by(company_id=company.id).count(),
        'prospects':     Prospect.query.filter_by(company_id=company.id).count(),
        'opportunities': Opportunity.query.filter_by(company_id=company.id).count(),
    }
    return render_template('auth/profile.html', company=company, stats=stats)


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    from werkzeug.security import generate_password_hash
    new_pw = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    if len(new_pw) < 6:
        flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
    elif new_pw != confirm:
        flash('Les mots de passe ne correspondent pas.', 'error')
    else:
        current_user.password = generate_password_hash(new_pw)
        db.session.commit()
        flash('Mot de passe modifié avec succès.', 'success')
    return redirect(url_for('auth.profile'))