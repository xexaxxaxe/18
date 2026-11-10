from functools import wraps
from flask import g,flash,redirect,url_for,abort,request

def login_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if not g.user:
            flash('Войдите в аккаунт, чтобы продолжить.','warning')
            return redirect(url_for('auth.login',next=request.path))
        return fn(*a,**kw)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*a,**kw):
        if g.user['role']!='ADMIN': abort(403)
        return fn(*a,**kw)
    return wrapped

def parse_positive_int(s, default=None):
    try:
        result=int(s)
        if result>0:return result
    except (ValueError,TypeError):pass
    return default

def parse_nonneg_int(s,default=None):
    try:
        result=int(s)
        if result>=0:return result
    except (ValueError,TypeError):pass
    return default
