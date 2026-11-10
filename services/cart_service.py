from services.catalog import SELECT_PRODUCTS

def get_or_create_cart(db,user_id):
    db.execute('INSERT OR IGNORE INTO carts(user_id) VALUES(?)',(user_id,))
    return db.execute('SELECT id FROM carts WHERE user_id=?',(user_id,)).fetchone()[0]

def get_cart(db,user_id):
    rows=db.execute('''SELECT ci.id AS item_id,ci.quantity, p.id, p.name,p.stock,p.discount,p.price,
          CAST(p.price*(100-p.discount)/100 AS INTEGER) AS final_price,
          (SELECT image_path FROM product_images WHERE product_id=p.id ORDER BY is_primary DESC,id LIMIT 1) AS image
          FROM cart_items ci JOIN carts c ON c.id=ci.cart_id JOIN products p ON ci.product_id=p.id
          WHERE c.user_id=? ORDER BY ci.id''',(user_id,)).fetchall()
    return rows,sum(row['final_price']*row['quantity'] for row in rows)

def adjust_cart(db,user_id,product_id,quantity,mode='set'):
    p=db.execute('SELECT id,stock,is_active FROM products WHERE id=?',(product_id,)).fetchone()
    if p is None or not p['is_active']: raise ValueError('Товар недоступен')
    cart_id=get_or_create_cart(db,user_id)
    old=db.execute('SELECT quantity FROM cart_items WHERE cart_id=? AND product_id=?',(cart_id,product_id)).fetchone()
    current=old['quantity'] if old else 0
    new_quantity=current+quantity if mode=='add' else quantity
    if new_quantity<0: raise ValueError('Некорректное количество')
    if new_quantity>p['stock']: raise ValueError('Недостаточно товара на складе')
    if new_quantity==0: db.execute('DELETE FROM cart_items WHERE cart_id=? AND product_id=?',(cart_id,product_id))
    else:
        db.execute('''INSERT INTO cart_items(cart_id,product_id,quantity) VALUES(?,?,?)
                    ON CONFLICT(cart_id,product_id) DO UPDATE SET quantity=excluded.quantity''',(cart_id,product_id,new_quantity))
    db.commit()
    return new_quantity
