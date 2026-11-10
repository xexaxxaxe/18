from services.cart_service import get_cart

def create_order(db,user_id,name,address,phone):
    # BEGIN IMMEDIATE keeps inventory and order-writing in one atomic transaction.
    db.execute('BEGIN IMMEDIATE')
    try:
        items,total=get_cart(db,user_id)
        if not items: raise ValueError('Корзина пуста')
        for item in items:
            if item['stock']<item['quantity']:
                raise ValueError('Товара на складе недостаточно: '+item['name'])
        order_id=db.execute('''INSERT INTO orders(user_id,total,status,delivery_name,delivery_address,phone)
                                VALUES (?,?,'new',?,?,?)''',(user_id,total,name,address,phone)).lastrowid
        for item in items:
            db.execute('''INSERT INTO order_items(order_id,product_id,product_name,price,quantity,subtotal)
                          VALUES(?,?,?,?,?,?)''',(order_id,item['id'],item['name'],item['final_price'],item['quantity'],item['final_price']*item['quantity']))
            result=db.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',
                              (item['quantity'],item['id'],item['quantity']))
            if result.rowcount != 1: raise ValueError('Изменились остатки на складе')
        db.execute('DELETE FROM cart_items WHERE cart_id=(SELECT id FROM carts WHERE user_id=?)',(user_id,))
        db.commit()
        return order_id
    except Exception:
        db.rollback()
        raise

def get_user_orders(db,user_id): #QJ
    return db.execute('''SELECT o.* FROM orders o WHERE o.user_id=?
                        ORDER BY o.created_at DESC,o.id DESC''',(user_id,)).fetchall()

def order_details(db,order_id,user_id=None):
    if user_id is not None:
        order=db.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(order_id,user_id)).fetchone()
    else:
        order=db.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
    if order is None:return None,None
    lines=db.execute('SELECT * FROM order_items WHERE order_id=? ORDER BY id',(order_id,)).fetchall()
    return order,lines
