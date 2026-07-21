import os
from flask import Flask, request, jsonify, render_template
from db.models import db, Order
from utils.db_utils import init_db

app = Flask(__name__)
db_user = os.environ.get('DB_USER', 'user')
db_password = os.environ.get('DB_PASSWORD', 'password')
db_name = os.environ.get('DB_NAME', 'database')
app.json.ensure_ascii = False
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@db:5432/{db_name}'
db.init_app(app)

# --- ГЛАВНАЯ СТРАНИЦА: Просто рендерим HTML-файл ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# --- ПОЛУЧЕНИЕ ВСЕХ ЗАКАЗОВ ---
@app.route('/orders', methods=['GET'])
def get_orders():
    orders = db.session.scalars(db.select(Order)).all()
    if not orders:
        return jsonify({'message': 'Заказы отсутствуют'}), 200

    orders_list = []
    for order in orders:
        orders_list.append({
            'id': order.id,
            'customer_name': order.customer_name,
            'item': order.item,
            'status': order.status
        })
    return jsonify(orders_list), 200

# --- ПОЛУЧЕНИЕ ЗАКАЗА ПО ID ---
@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order_by_id(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'message': f'Заказ с ID {order_id} не найден'}), 404

    return jsonify({
        'id': order.id,
        'customer_name': order.customer_name,
        'item': order.item,
        'status': order.status
    }), 200

# --- СОЗДАНИЕ ЗАКАЗА ---
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    new_order = Order(customer_name=data['customer_name'], item=data['item'], status='Pending')
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Order created successfully'}), 201

# --- ОБНОВЛЕНИЕ ЗАКАЗА ---
@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    data = request.get_json()
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    order.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Order updated successfully'}), 200

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5000)
