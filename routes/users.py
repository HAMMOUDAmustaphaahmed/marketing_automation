from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User
from datetime import datetime
from functools import wraps

users_bp = Blueprint('users', __name__, url_prefix='/users')


def admin_required(f):
    """Decorator: only company admin can access."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash("Accès réservé à l'administrateur de l'entreprise.", 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


# ── LIST ──────────────────────────────────────────────────────
@users_bp.route('/')
@admin_required
def index():
    members = User.query.filter_by(company_id=current_user.company_id)\
        .order_by(User.role.desc(), User.name).all()
    return render_template('users/index.html', members=members)


# ── INVITE / CREATE ───────────────────────────────────────────
@users_bp.route('/invite', methods=['GET', 'POST'])
@admin_required
def invite():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role', 'member')

        if not name or not email or not password:
            flash('Tous les champs obligatoires doivent être remplis.', 'error')
            return redirect(url_for('users.invite'))

        if len(password) < 6:
            flash('Le mot de passe doit comporter au moins 6 caractères.', 'error')
            return redirect(url_for('users.invite'))

        if User.query.filter_by(email=email).first():
            flash(f"Un compte existe déjà avec l'email {email}.", 'error')
            return redirect(url_for('users.invite'))

        user = User(
            name       = name,
            email      = email,
            password   = generate_password_hash(password),
            company_id = current_user.company_id,
            role       = role,
            can_read   = request.form.get('can_read')   == 'on',
            can_create = request.form.get('can_create') == 'on',
            can_edit   = request.form.get('can_edit')   == 'on',
            can_delete = request.form.get('can_delete') == 'on',
            is_active  = True,
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Utilisateur {name} créé avec succès.', 'success')
        return redirect(url_for('users.index'))

    return render_template('users/invite.html')


# ── EDIT PERMISSIONS ──────────────────────────────────────────
@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(id):
    user = User.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()

    if user.id == current_user.id:
        flash("Vous ne pouvez pas modifier votre propre compte ici.", 'warning')
        return redirect(url_for('users.index'))

    if request.method == 'POST':
        user.name       = request.form.get('name', user.name).strip()
        user.role       = request.form.get('role', user.role)
        user.can_read   = request.form.get('can_read')   == 'on'
        user.can_create = request.form.get('can_create') == 'on'
        user.can_edit   = request.form.get('can_edit')   == 'on'
        user.can_delete = request.form.get('can_delete') == 'on'
        user.is_active  = request.form.get('is_active')  == 'on'

        new_pw = request.form.get('new_password', '').strip()
        if new_pw:
            if len(new_pw) < 6:
                flash('Le mot de passe doit comporter au moins 6 caractères.', 'error')
                return redirect(url_for('users.edit', id=id))
            user.password = generate_password_hash(new_pw)

        db.session.commit()
        flash(f'Permissions de {user.name} mises à jour.', 'success')
        return redirect(url_for('users.index'))

    return render_template('users/edit.html', user=user)


# ── TOGGLE ACTIVE ─────────────────────────────────────────────
@users_bp.route('/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle(id):
    user = User.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    if user.id == current_user.id:
        flash("Vous ne pouvez pas désactiver votre propre compte.", 'warning')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        state = 'activé' if user.is_active else 'désactivé'
        flash(f'Compte {user.name} {state}.', 'success')
    return redirect(url_for('users.index'))


# ── DELETE ────────────────────────────────────────────────────
@users_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    user = User.query.filter_by(id=id, company_id=current_user.company_id).first_or_404()
    if user.id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte.", 'warning')
    elif user.role == 'admin':
        flash("Impossible de supprimer un autre administrateur.", 'warning')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'Utilisateur {user.name} supprimé.', 'success')
    return redirect(url_for('users.index'))
