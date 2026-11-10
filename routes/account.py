from flask import Blueprint,render_template,g,abort
from database.db import get_db
from routes.common import login_required
from services.order_service import get_user_orders,order_details
bp=Blueprint('account',__name__,url_prefix='/account')

@bp.get('/')
@login_required
def profile():
    return render_template('account.html',orders=get_user_orders(get_db(),g.user['id']))

@bp.get('/orders/<int:oid>')
@login_required
def order(oid):
    info,items=order_details(get_db(),oid,g.user['id'])
    if info is None:abort(404)
    return render_template('order.html',order=info,items=items,admin_view=False)
