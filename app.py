import os
import secrets
from datetime import datetime
from pathlib import Path
from flask import Flask, g, session, request, abort, redirect, url_for, flash
from config import DB_PATH, SECRET_KEY, MAX_UPLOAD_BYTES
from database.db import close_db, get_db

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=SECRET_KEY, DB_PATH=DB_PATH, MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES)
    if test_config: app.config.update(test_config)
    Path(app.config['DB_PATH']).parent.mkdir(parents=True, exist_ok=True)
    (Path(__file__).parent/'static'/'uploads').mkdir(exist_ok=True)

    @app.before_request
    def load_user_and_csrf():
        g.user = None
        if 'user_id' in session:
            g.user = get_db().execute('SELECT id,username,email,role,created_at FROM users WHERE id=?',(session['user_id'],)).fetchone()
        if 'csrf_token' not in session: session['csrf_token'] = secrets.token_hex(24)
        if request.method in ('POST','PUT','PATCH','DELETE'):
            sent = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not secrets.compare_digest(str(sent or ''), session['csrf_token']): abort(400, 'Недействительный CSRF-токен')
    @app.context_processor
    def shared():
        db = get_db()
        categories = db.execute('SELECT * FROM categories ORDER BY name').fetchall()
        count = 0
        if g.user:
            count = db.execute('SELECT COALESCE(SUM(ci.quantity),0) FROM cart_items ci JOIN carts c ON ci.cart_id=c.id WHERE c.user_id=?',(g.user['id'],)).fetchone()[0]
        return {'site_categories':categories,'cart_count':count,'csrf_token':session.get('csrf_token',''),
                'money':lambda n: f'{int(n):,}'.replace(',',' ')+' ₸',
                'price_of':lambda p: int(p['price']*(100-p['discount'])/100)}
    from routes.store import bp as store
    from routes.auth import bp as auth
    from routes.cart import bp as cart
    from routes.account import bp as account
    from routes.admin import bp as admin
    for bp in (store,auth,cart,account,admin): app.register_blueprint(bp)
    app.teardown_appcontext(close_db)
    @app.errorhandler(404)
    def not_found(err):
        return __import__('flask').render_template('error.html',title='Страница не найдена',message='Проверьте адрес или перейдите в каталог.'),404
    @app.errorhandler(403)
    def forbidden(err):
        return __import__('flask').render_template('error.html',title='Нет доступа',message='У вас недостаточно прав для этого действия.'),403
    @app.errorhandler(400)
    def bad_request(err):
        return __import__('flask').render_template('error.html',title='Ошибка запроса',message=str(err.description)),400
    return app

app = create_app()
if __name__=='__main__':
    app.run(host='127.0.0.1',port=int(os.environ.get('PORT','5000')),debug=os.environ.get('FLASK_DEBUG')=='1')
