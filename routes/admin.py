import sqlite3
import uuid
from pathlib import Path
from flask import Blueprint,render_template,request,redirect,url_for,flash,abort,current_app
from werkzeug.utils import secure_filename
from database.db import get_db
from routes.common import admin_required,parse_positive_int,parse_nonneg_int
from services.order_service import order_details
bp=Blueprint('admin',__name__,url_prefix='/admin')
ALLOWED={'.png','.jpg','.jpeg','.webp','.gif'}
STATUSES={'new','processing','shipped','delivered','cancelled'}

@bp.get('')
@bp.get('/')
@admin_required
def dashboard():
    db=get_db()
    stats={
      'products':db.execute('SELECT COUNT(*) FROM products WHERE is_active=1').fetchone()[0],
      'users':db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
      'orders':db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
      'revenue':db.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='cancelled'").fetchone()[0],
    }
    recent=db.execute('SELECT o.*,u.username FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC LIMIT 6').fetchall()
    return render_template('admin/dashboard.html',stats=stats,recent=recent)

@bp.get('/products')
@admin_required
def products():
    db=get_db();q=request.args.get('q','').strip()[:100]
    cat=parse_positive_int(request.args.get('category'))
    sql='''SELECT p.*,b.name AS brand_name,c.name AS category_name FROM products p
           JOIN brands b ON b.id=p.brand_id JOIN categories c ON c.id=p.category_id WHERE p.is_active=1'''
    params=[]
    if q:sql+=' AND (p.name LIKE ? OR p.sku LIKE ?)';params.extend([f'%{q}%']*2)
    if cat:sql+=' AND p.category_id=?';params.append(cat)
    records=db.execute(sql+' ORDER BY p.id DESC',params).fetchall()
    categories=db.execute('SELECT * FROM categories ORDER BY name').fetchall()
    return render_template('admin/products.html',records=records,q=q,category=cat,categories=categories)

def save_image(upload):
    if not upload or not upload.filename:return None
    suffix=Path(secure_filename(upload.filename)).suffix.lower()
    if suffix not in ALLOWED:raise ValueError('Разрешены только файлы JPG, PNG, WEBP и GIF')
    header=upload.stream.read(16);upload.stream.seek(0)
    signatures={'.png':header.startswith(b'\x89PNG\r\n\x1a\n'),'.jpg':header.startswith(b'\xff\xd8'),'.jpeg':header.startswith(b'\xff\xd8'),'.webp':header[:4]==b'RIFF' and header[8:12]==b'WEBP', '.gif':header[:6] in (b'GIF87a',b'GIF89a')}
    if not signatures[suffix]:raise ValueError('Содержимое файла не соответствует изображению')
    filename=uuid.uuid4().hex+suffix
    upload.save(Path(current_app.root_path)/'static'/'uploads'/filename)
    return 'uploads/'+filename

def product_form_values(db,product_id=None):
    categories=db.execute('SELECT * FROM categories ORDER BY name').fetchall()
    brands=db.execute('SELECT * FROM brands ORDER BY name').fetchall()
    product=db.execute('SELECT * FROM products WHERE id=? AND is_active=1',(product_id,)).fetchone() if product_id else None
    specs=db.execute('SELECT * FROM product_specs WHERE product_id=? ORDER BY id',(product_id,)).fetchall() if product_id else []
    images=db.execute('SELECT * FROM product_images WHERE product_id=? ORDER BY is_primary DESC,id',(product_id,)).fetchall() if product_id else []
    return categories,brands,product,specs,images

@bp.route('/products/new',methods=['GET','POST'])
@bp.route('/products/<int:pid>/edit',methods=['GET','POST'])
@admin_required
def product_edit(pid=None):
    db=get_db()
    categories,brands,product,specs,images=product_form_values(db,pid)
    if pid and not product:abort(404)
    if request.method=='POST':
        name=request.form.get('name','').strip()[:150]
        sku=request.form.get('sku','').strip()[:80].upper()
        desc=request.form.get('description','').strip()[:3000]
        category_id=parse_positive_int(request.form.get('category_id'))
        brand_id=parse_positive_int(request.form.get('brand_id'))
        price=parse_nonneg_int(request.form.get('price'))
        discount=parse_nonneg_int(request.form.get('discount'))
        stock=parse_nonneg_int(request.form.get('stock'))
        spec_key=request.form.get('spec_key','').strip()[:80]
        spec_value=request.form.get('spec_value','').strip()[:300]
        try:
            if not name or not sku or price is None or stock is None or discount is None or discount>90:
                raise ValueError('Проверьте название, SKU, цену, скидку и остаток')
            if not db.execute('SELECT 1 FROM categories WHERE id=?',(category_id,)).fetchone():raise ValueError('Выберите категорию')
            if not db.execute('SELECT 1 FROM brands WHERE id=?',(brand_id,)).fetchone():raise ValueError('Выберите бренд')
            image_path=save_image(request.files.get('image'))
            if pid:
                db.execute('''UPDATE products SET name=?,sku=?,description=?,category_id=?,brand_id=?,price=?,discount=?,stock=?
                             WHERE id=?''',(name,sku,desc,category_id,brand_id,price,discount,stock,pid))
                product_id=pid
            else:
                product_id=db.execute('''INSERT INTO products(name,sku,description,category_id,brand_id,price,discount,stock)
                                         VALUES(?,?,?,?,?,?,?,?)''',(name,sku,desc,category_id,brand_id,price,discount,stock)).lastrowid
            if spec_key:
                if not spec_value:raise ValueError('Заполните значение характеристики')
                db.execute('''INSERT INTO product_specs(product_id,spec_key,spec_value) VALUES(?,?,?)
                            ON CONFLICT(product_id,spec_key) DO UPDATE SET spec_value=excluded.spec_value''',(product_id,spec_key,spec_value)) #QJ
            if image_path:
                db.execute('UPDATE product_images SET is_primary=0 WHERE product_id=?',(product_id,))
                db.execute('INSERT INTO product_images(product_id,image_path,is_primary) VALUES(?,?,1)',(product_id,image_path))
            elif not pid:
                # New items without a photo use an offline neutral illustration.
                db.execute('INSERT INTO product_images(product_id,image_path,is_primary) VALUES (?,?,1)',(product_id,'images/default-product.svg'))
            db.commit();flash('Товар успешно сохранён.','success')
            return redirect(url_for('admin.products'))
        except (ValueError,sqlite3.IntegrityError) as e:
            db.rollback();flash('Не удалось сохранить: '+str(e),'danger')
        categories,brands,product,specs,images=product_form_values(db,pid)
    return render_template('admin/product_form.html',p=product,categories=categories,brands=brands,specs=specs,images=images)

@bp.post('/products/<int:pid>/delete')
@admin_required
def product_delete(pid):
    db=get_db();db.execute('UPDATE products SET is_active=0 WHERE id=?',(pid,));db.commit()
    flash('Товар скрыт из каталога. История заказов сохранена.','success')
    return redirect(url_for('admin.products'))

@bp.route('/categories',methods=['GET','POST'])
@admin_required
def categories():
    db=get_db()
    if request.method=='POST':
        name=request.form.get('name','').strip()[:90]
        slug=request.form.get('slug','').strip().lower()[:60]
        desc=request.form.get('description','').strip()[:300]
        cid=parse_positive_int(request.form.get('id'))
        if not name or not slug or not all(ch.isascii() and (ch.islower() or ch.isdigit() or ch=='-') for ch in slug):
            flash('Название и латинский slug обязательны.','danger')
        else:
            try:
                if cid:
                    db.execute('UPDATE categories SET name=?,slug=?,description=? WHERE id=?',(name,slug,desc,cid))
                else:db.execute('INSERT INTO categories(name,slug,description) VALUES(?,?,?)',(name,slug,desc))
                db.commit();flash('Категория сохранена.','success')
                return redirect(url_for('admin.categories'))
            except sqlite3.IntegrityError:db.rollback();flash('Название или slug уже используются.','danger')
    return render_template('admin/categories.html',categories=db.execute('SELECT * FROM categories ORDER BY name').fetchall())

@bp.route('/brands',methods=['GET','POST'])
@admin_required
def brands():
    db=get_db()
    if request.method=='POST':
        name=request.form.get('name','').strip()[:80]
        if name:
            try:
                db.execute('INSERT INTO brands(name) VALUES (?)',(name,));db.commit();flash('Бренд добавлен.','success')
            except sqlite3.IntegrityError:db.rollback();flash('Такой бренд уже есть.','warning')
        return redirect(url_for('admin.brands'))
    return render_template('admin/brands.html',brands=db.execute('SELECT * FROM brands ORDER BY name').fetchall())

@bp.get('/orders')
@admin_required
def orders():
    db=get_db()
    rows=db.execute('''SELECT o.*,u.username FROM orders o JOIN users u ON u.id=o.user_id
                       ORDER BY o.created_at DESC,o.id DESC''').fetchall()
    return render_template('admin/orders.html',orders=rows,statuses=STATUSES)

@bp.post('/orders/<int:oid>/status')
@admin_required
def status(oid):
    value=request.form.get('status')
    if value not in STATUSES:abort(400)
    db=get_db();db.execute('UPDATE orders SET status=? WHERE id=?',(value,oid));db.commit()
    flash('Статус заказа изменён.','success')
    return redirect(url_for('admin.orders'))

@bp.get('/orders/<int:oid>')
@admin_required
def order(oid):
    info,items=order_details(get_db(),oid)
    if info is None:abort(404)
    return render_template('order.html',order=info,items=items,admin_view=True)

@bp.get('/users')
@admin_required
def users():
    db=get_db()
    rows=db.execute('''SELECT u.id,u.username,u.email,u.role,u.created_at,COUNT(o.id) AS orders_count
                       FROM users u LEFT JOIN orders o ON o.user_id=u.id GROUP BY u.id ORDER BY u.id DESC''').fetchall()
    return render_template('admin/users.html',users=rows)
