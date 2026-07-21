import os
import requests  # Обязательно добавьте импорт в самый верх файла!
from flask import Flask, request, jsonify, render_template
from db.models import db, Order
from utils.db_utils import init_db

# URL соседа
LOGISTICS_SERVICE_URL = "http://logistics-service:5001"

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

# --- ОБНОВЛЕННЫЙ МЕТОД: Обновление заказа с проверкой доставки ---
@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    data = request.get_json()
    new_status = data.get('status')

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'message': 'Order not found'}), 404

    # Нам нужно также разрешить статус "Delivered" и "Delivering", которые прилетают из логистики!
    if new_status not in ["Canceled", "Received", "Delivered", "Delivering"]:
        return jsonify({'message': 'Недопустимый статус заказа'}), 400

    try:
        # Логика шага 2: если статус меняется на "Canceled"
        if new_status == "Canceled":
            # 1. Ищем доставку через новый POST-эндпоинт соседа
            search_url = f"{LOGISTICS_SERVICE_URL}/deliveries/search"
            search_response = requests.post(search_url, json={"orderId": order_id}, timeout=5)

            # 2. Если вернулся статус 200 и доставка найдена
            if search_response.status_code == 200:
                delivery_data = search_response.json()
                delivery_id = delivery_data.get('id')

                # 3. Дополнительно дергаем PUT соседа, отменяя доставку
                update_del_url = f"{LOGISTICS_SERVICE_URL}/deliveries/{delivery_id}"
                del_response = requests.put(update_del_url, json={"status": "Canceled"}, timeout=5)

                if del_response.status_code != 200:
                    return jsonify({
                        'message': 'Заказ не отменен: не удалось отменить связанную доставку в сервисе логистики'
                    }), 502

        # Если проверки пройдены (или доставка не найдена/статус другой) — обновляем статус заказа у себя
        order.status = new_status
        db.session.commit()

        return jsonify({
            'message': f'Order updated successfully to {new_status}.' +
                       (' Related delivery was also canceled.' if new_status == "Canceled" else '')
        }), 200

    except requests.exceptions.RequestException:
        return jsonify({'message': 'Ошибка связи с сервисом логистики. Статус заказа не изменен.'}), 503

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5000)
