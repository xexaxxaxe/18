from services.filter_service import build_conditions

SELECT_PRODUCTS = '''SELECT p.*, c.name AS category_name,b.name AS brand_name,
    (SELECT pi.image_path FROM product_images pi WHERE pi.product_id=p.id ORDER BY pi.is_primary DESC,pi.id LIMIT 1) AS image,
    CAST(p.price*(100-p.discount)/100 AS INTEGER) AS final_price
    FROM products p JOIN categories c ON p.category_id=c.id JOIN brands b ON p.brand_id=b.id'''

def list_products(db, *, category_id=None, brand_id=None, min_price=None, max_price=None, in_stock=False, search='', sort='newest',page=1, per_page=12):
    order_map = {
        'newest':'p.created_at DESC,p.id DESC',
        'oldest':'p.created_at ASC,p.id ASC',
        'price_asc':'final_price ASC,p.id ASC',#QJ
        'price_desc':'final_price DESC,p.id DESC',
        'name_asc':'p.name COLLATE NOCASE ASC',
        'name_desc':'p.name COLLATE NOCASE DESC',
    }
    order = order_map.get(sort, order_map['newest'])
    where, params = build_conditions(category_id,brand_id,min_price,max_price,in_stock,search)
    total = db.execute('SELECT COUNT(*) FROM products p'+where,params).fetchone()[0]
    page = max(1,min(int(page),max(1,(total+per_page-1)//per_page)))
    products = db.execute(SELECT_PRODUCTS+where+' ORDER BY '+order+' LIMIT ? OFFSET ?',params+[per_page,(page-1)*per_page]).fetchall()
    return products,total,page,max(1,(total+per_page-1)//per_page)

def get_product(db,pid):
    return db.execute(SELECT_PRODUCTS+' WHERE p.id=? AND p.is_active=1',(pid,)).fetchone()
