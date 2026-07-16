import os
from flask import Flask, request, jsonify
from db.models import db, Order
from utils.db_utils import init_db

app = Flask(__name__)
# Разрешаем корректное отображение кириллицы в JSON
db_password=os.environ.get('DB_PASSWORD','password')
app.json.ensure_ascii = False 
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:{db_password}@db:5432/orders'
db.init_app(app)

# --- ГЛАВНАЯ СТРАНИЦА: Меню со ссылками на эндпоинты ---
@app.route('/', methods=['GET'])
def index():
    links = []
    # Перебираем все зарегистрированные во Flask роуты
    for rule in app.url_map.iter_rules():
        # Исключаем служебный роут для статики и саму главную страницу
        if rule.endpoint != 'static' and rule.rule != '/':

            # Получаем чистый путь (например, /orders/<int:order_id>)
            raw_path = rule.rule

            # Делаем путь кликабельным: заменяем типы данных <int:...> на тестовую "1"
            clean_path = raw_path
            if '<' in clean_path:
                # Универсальная замена для Flask-плейсхолдеров (например, <int:order_id> -> 1)
                import re
                clean_path = re.sub(r'<[^>]+>', '1', clean_path)

            # Получаем доступные HTTP-методы (GET, POST и т.д.)
            methods = ', '.join([m for m in rule.methods if m not in ['OPTIONS', 'HEAD']])

            # Формируем элемент списка: если есть GET, делаем ссылку активной
            if 'GET' in rule.methods:
                links.append(f'<li>[{methods}] <a href="{clean_path}">{rule.endpoint} -> {raw_path}</a></li>')
            else:
                links.append(f'<li>[{methods}] <b>{rule.endpoint} -> {raw_path}</b> <i>(для отправки через Postman/cURL)</i></li>')

    return f"""
    <html>
        <head>
            <title>Order Service API</title>
            <style>
                body {{ font-family: sans-serif; margin: 40px; background: #f4f6f9; color: #333; }}
                h1 {{ color: #2c3e50; }}
                ul {{ background: white; padding: 20px 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                li {{ margin: 10px 0; font-size: 16px; line-height: 1.5; }}
                a {{ color: #3498db; text-decoration: none; font-weight: bold; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>📦 Order Service API Menu</h1>
            <p>Список доступных эндпоинтов приложения:</p>
            <ul>
                {"".join(links) if links else "<li>Эндпоинты не найдены или еще не зарегистрированы</li>"}
            </ul>
        </body>
    </html>
    """
# --- НОВЫЙ МЕТОД: Получение всех заказов ---
@app.route('/orders', methods=['GET'])
def get_orders():
    # Получаем все записи из таблицы orders
    orders = db.session.scalars(db.select(Order)).all()
    
    if not orders:
        return jsonify({'message': 'Заказы отсутствуют'}), 200
        
    # Преобразуем список объектов SQLAlchemy в список словарей для JSON
    orders_list = []
    for order in orders:
        orders_list.append({
            'id': order.id,
            'customer_name': order.customer_name,
            'item': order.item,
            'status': order.status
        })
        
    return jsonify(orders_list), 200

# --- НОВЫЙ МЕТОД: Получение заказа по ID ---
@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order_by_id(order_id):
    # Безопасно получаем заказ из БД по первичному ключу
    order = db.session.get(Order, order_id)
    
    if not order:
        return jsonify({'message': f'Заказ с ID {order_id} не найден'}), 404
        
    # Возвращаем данные найденного заказа
    return jsonify({
        'id': order.id,
        'customer_name': order.customer_name,
        'item': order.item,
        'status': order.status
    }), 200

@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    new_order = Order(customer_name=data['customer_name'], item=data['item'], status='Pending')
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Order created successfully'}), 201

@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    data = request.get_json()
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    order.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Order updated successfully'})

if __name__ == '__main__':
    print("Поехали")
    with app.app_context():
        init_db()
    print("Едем дальше")
    app.run(host='0.0.0.0', port=5000)
    print("Привет, мир!")
