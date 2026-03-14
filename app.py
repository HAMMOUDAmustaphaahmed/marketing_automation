from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from models import db, User
from config import Config
import os

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    mail.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour acceder a cette page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Upload folder
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)

    # Register blueprints
    from routes.auth         import auth_bp
    from routes.dashboard    import dashboard_bp
    from routes.competitors  import competitors_bp
    from routes.prospects    import prospects_bp
    from routes.pipeline     import pipeline_bp
    from routes.mailing      import mailing_bp
    from routes.maintenance  import maintenance_bp
    from routes.users        import users_bp
    from routes.intelligence import intelligence_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(competitors_bp)
    app.register_blueprint(prospects_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(mailing_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(intelligence_bp)

    # Create tables — non-blocking: si Aiven inaccessible au boot, on continue
    # Lancez "python update_db.py" pour appliquer les migrations manuellement
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                'db.create_all() ignore (DB inaccessible au demarrage): ' + str(e)
            )

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)