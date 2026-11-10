from flask import Blueprint,render_template,request,redirect,url_for,flash,g,jsonify
from database.db import get_db
from routes.common import login_required,parse_positive_int,parse_nonneg_int
from services.cart_service import get_cart,adjust_cart
from services.order_service import create_order
bp=Blueprint('cart',__name__,url_prefix='/cart')

def wants_json(): return 'application/json' in request.headers.get('Accept','')

@bp.get('/')
@login_required
def view():
    items,total=get_cart(get_db(),g.user['id'])
    return render_template('cart.html',items=items,total=total)

@bp.post('/add')
@login_required
def add():
    pid=parse_positive_int(request.form.get('product_id'))
    qty=parse_positive_int(request.form.get('quantity'),1)
    if not pid or not qty: message='Недействительный товар или количество';ok=False
    else:
        try:
            adjust_cart(get_db(),g.user['id'],pid,qty,mode='add')
            message='Товар добавлен в корзину';ok=True
        except ValueError as e:message=str(e);ok=False
    if wants_json():return jsonify(ok=ok,message=message),200 if ok else 400
    flash(message,'success' if ok else 'danger')
    return redirect(request.referrer if request.referrer and request.referrer.startswith(request.host_url) else url_for('cart.view'))

@bp.post('/update')
@login_required
def update():
    pid=parse_positive_int(request.form.get('product_id'))
    raw=request.form.get('quantity')
    qty=parse_nonneg_int(raw)
    if not pid or qty is None:message='Укажите правильное количество';ok=False
    else:
        try:
            adjust_cart(get_db(),g.user['id'],pid,qty)
            message='Корзина обновлена';ok=True
        except ValueError as e:message=str(e);ok=False
    if wants_json():
        _,total=get_cart(get_db(),g.user['id'])
        return jsonify(ok=ok,message=message,total=total),200 if ok else 400
    flash(message,'success' if ok else 'danger')
    return redirect(url_for('cart.view'))

@bp.post('/remove')
@login_required
def remove():
    pid=parse_positive_int(request.form.get('product_id'))
    if pid:
        try:adjust_cart(get_db(),g.user['id'],pid,0)
        except ValueError:pass
    flash('Товар удалён из корзины.','success')
    return redirect(url_for('cart.view'))

@bp.route('/checkout',methods=['GET','POST'])
@login_required
def checkout():
    db=get_db();items,total=get_cart(db,g.user['id'])
    if not items:flash('Добавьте товары в корзину.','warning');return redirect(url_for('store.catalog'))
    if request.method=='POST':
        name=request.form.get('name','').strip()[:100]
        address=request.form.get('address','').strip()[:220]
        phone=request.form.get('phone','').strip()[:30]
        if not (2<=len(name) and 8<=len(address) and 7<=len(phone)):
            flash('Заполните имя, адрес доставки и телефон.','danger')
        else:
            try:
                order_id=create_order(db,g.user['id'],name,address,phone)
                flash(f'Заказ №{order_id} успешно создан.','success')
                return redirect(url_for('account.order',oid=order_id))
            except ValueError as e:flash(str(e),'danger')
    return render_template('checkout.html',items=items,total=total)
