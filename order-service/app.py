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
