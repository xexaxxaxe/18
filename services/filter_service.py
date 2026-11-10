"""Composable SQL filters; every value is a bound parameter."""

def build_conditions(category_id=None, brand_id=None, min_price=None, max_price=None, in_stock=False, search='', active=True):
    where, params = [], []
    if active: where.append('p.is_active=1')
    if category_id:
        where.append('p.category_id=?');params.append(category_id)
    if brand_id:
        where.append('p.brand_id=?');params.append(brand_id)
    effective = '(p.price * (100-p.discount) / 100)'
    if min_price is not None:
        where.append(f'{effective}>=?');params.append(min_price)
    if max_price is not None: #1J
        where.append(f'{effective}<=?');params.append(max_price)
    if in_stock: where.append('p.stock>0')
    if search:
        where.append('(p.name LIKE ? OR p.description LIKE ? OR p.sku LIKE ?)')
        params.extend([f'%{search}%']*3)
    return (' WHERE '+' AND '.join(where)) if where else '',params
