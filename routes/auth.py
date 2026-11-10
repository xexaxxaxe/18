import re
from flask import Blueprint,render_template,request,redirect,url_for,flash,session,g
from werkzeug.security import generate_password_hash,check_password_hash
from database.db import get_db
bp=Blueprint('auth',__name__)

@bp.route('/register',methods=['GET','POST'])
def register():
    if g.user:return redirect(url_for('account.profile'))
    if request.method=='POST':
        username=request.form.get('username','').strip()
        email=request.form.get('email','').strip().lower()
        password=request.form.get('password','')
        if not 3<=len(username)<=36 or not re.fullmatch(r'[A-Za-z0-9_а-яА-ЯёЁ]+',username):
            flash('Логин: от 3 до 36 букв, цифр или _.','danger')
        elif not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):flash('Укажите корректный email.','danger')
        elif len(password)<8:flash('Пароль должен содержать не менее 8 символов.','danger')
        else:
            db=get_db()
            try:
                cur=db.execute('INSERT INTO users(username,email,password_hash,role) VALUES (?,?,?,?)',(username,email,generate_password_hash(password),'USER'))
                db.execute('INSERT INTO carts(user_id) VALUES (?)',(cur.lastrowid,))
                db.commit()
                session.clear();session['user_id']=cur.lastrowid
                flash('Аккаунт создан. Добро пожаловать!','success')
                return redirect(url_for('account.profile'))
            except __import__('sqlite3').IntegrityError:
                db.rollback();flash('Логин или email уже зарегистрирован.','danger')
    return render_template('auth.html',mode='register')

@bp.route('/login',methods=['GET','POST'])
def login():
    if g.user:return redirect(url_for('account.profile'))
    if request.method=='POST':
        identity=request.form.get('identity','').strip()
        password=request.form.get('password','')
        user=get_db().execute('SELECT * FROM users WHERE username=? COLLATE NOCASE OR email=? COLLATE NOCASE',(identity,identity)).fetchone()
        if not user or not check_password_hash(user['password_hash'],password):
            flash('Неверный логин/email или пароль.','danger')
        else:
            session.clear();session['user_id']=user['id']
            flash('Вы успешно вошли.','success')
            next_page=request.args.get('next','')
            if not next_page.startswith('/') or next_page.startswith('//'):next_page=url_for('account.profile')
            return redirect(next_page)
    return render_template('auth.html',mode='login')

@bp.post('/logout')
def logout():
    session.clear();flash('Вы вышли из аккаунта.','success')
    return redirect(url_for('store.index'))
