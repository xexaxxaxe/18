import sqlite3
from flask import Blueprint,render_template,request,redirect,url_for,flash,g,abort
from database.db import get_db,load_named_sql
from services.catalog import list_products,get_product,SELECT_PRODUCTS
from routes.common import login_required,parse_positive_int,parse_nonneg_int
bp=Blueprint('store',__name__)

@bp.get('/')
def index():
    db=get_db()
    popular=db.execute(SELECT_PRODUCTS+' WHERE p.is_active=1 AND p.stock>0 ORDER BY p.discount DESC,p.id LIMIT 8').fetchall()
    latest=db.execute(SELECT_PRODUCTS+' WHERE p.is_active=1 ORDER BY p.created_at DESC,p.id DESC LIMIT 8').fetchall()
    categories=db.execute('SELECT c.*,COUNT(p.id) AS count FROM categories c LEFT JOIN products p ON p.category_id=c.id AND p.is_active=1 GROUP BY c.id ORDER BY c.id').fetchall()
    return render_template('home.html',popular=popular,latest=latest,categories=categories)

@bp.get('/catalog')
def catalog():
    db=get_db()
    category=parse_positive_int(request.args.get('category'))
    brand=parse_positive_int(request.args.get('brand'))
    min_price=parse_nonneg_int(request.args.get('min_price'))
    max_price=parse_nonneg_int(request.args.get('max_price'))
    stock=request.args.get('in_stock')=='1'
    search=request.args.get('q','').strip()[:100]
    sort=request.args.get('sort','newest')
    page=parse_positive_int(request.args.get('page'),1)
    products,total,page,pages=list_products(db,category_id=category,brand_id=brand,min_price=min_price,max_price=max_price,in_stock=stock,search=search,sort=sort,page=page)
    brands=db.execute('SELECT * FROM brands ORDER BY name').fetchall()
    return render_template('catalog.html',products=products,total=total,page=page,pages=pages,brands=brands,
        category=category,brand=brand,min_price=min_price,max_price=max_price,in_stock=stock,search=search,sort=sort)

@bp.get('/product/<int:pid>')
def product(pid):
    db=get_db();p=get_product(db,pid)
    if not p:abort(404)
    specs=db.execute('SELECT * FROM product_specs WHERE product_id=? ORDER BY id',(pid,)).fetchall()
    reviews=db.execute('''SELECT r.*,u.username FROM reviews r JOIN users u ON u.id=r.user_id
                           WHERE r.product_id=? ORDER BY r.created_at DESC,r.id DESC''',(pid,)).fetchall()
    images=db.execute('SELECT * FROM product_images WHERE product_id=? ORDER BY is_primary DESC,id',(pid,)).fetchall()
    recommended=db.execute(SELECT_PRODUCTS+' WHERE p.is_active=1 AND p.category_id=? AND p.id<>? ORDER BY p.id DESC LIMIT 4',(p['category_id'],pid)).fetchall()
    return render_template('product.html',p=p,specs=specs,reviews=reviews,images=images,recommended=recommended)

@bp.post('/product/<int:pid>/review')
@login_required
def review(pid):
    db=get_db()
    if not get_product(db,pid):abort(404)
    rating=parse_positive_int(request.form.get('rating'))
    comment=request.form.get('comment','').strip()
    if rating not in (1,2,3,4,5) or not 5<=len(comment)<=1000:
        flash('Выберите оценку и напишите отзыв от 5 до 1000 символов.','warning')
    else:
        try:
            db.execute(load_named_sql('INSERT_REVIEW'),{'user_id':g.user['id'],'product_id':pid,'rating':rating,'comment':comment})
            db.commit();flash('Отзыв сохранён.','success')
        except sqlite3.DatabaseError:
            db.rollback();flash('Не удалось сохранить отзыв. Повторите попытку.','danger')
    return redirect(url_for('store.product',pid=pid)+'#reviews')
