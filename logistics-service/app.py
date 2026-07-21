import os
import requests  # Добавили импорт для HTTP-запросов к соседнему сервису
from flask import Flask, request, jsonify, render_template
from db.models import db, Delivery
from utils.db_utils import init_db

app = Flask(__name__)
app.json.ensure_ascii = False
db_user = os.environ.get('DB_USER', 'user')
db_password = os.environ.get('DB_PASSWORD', 'password')
db_name = os.environ.get('DB_NAME', 'database')
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@db:5432/{db_name}'
db.init_app(app)

# URL соседнего микросервиса внутри сети Docker
ORDER_SERVICE_URL = "http://order-service:5000"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/deliveries', methods=['GET'])
def get_deliveries():
    deliveries = db.session.scalars(db.select(Delivery)).all()
    if not deliveries:
        return jsonify({'message': 'Нет доставок'}), 200

    deliveries_list = []
    for d in deliveries:
        deliveries_list.append({
            'id': d.id,
            'order_id': d.order_id,
            'status': d.status
        })
    return jsonify(deliveries_list), 200

@app.route('/deliveries/<int:delivery_id>', methods=['GET'])
def get_delivery_by_id(delivery_id):
    delivery = db.session.get(Delivery, delivery_id)
    if not delivery:
        return jsonify({'message': f'Не найдена доставка {delivery_id}'}), 404

    return jsonify({
        'id': delivery.id,
        'order_id': delivery.order_id,
        'status': delivery.status
    }), 200

# --- ОБНОВЛЕННЫЙ МЕТОД: Создание доставки с проверкой заказа ---
@app.route('/deliveries', methods=['POST'])
def create_delivery():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'message': 'Не указан order_id'}), 400

    try:
        # 1. Проверяем существование заказа в order-service
        check_url = f"{ORDER_SERVICE_URL}/orders/{order_id}"
        order_response = requests.get(check_url, timeout=5)

        # 2. Если ответ 404 — возвращаем ошибку и не создаем доставку
        if order_response.status_code == 404:
            return jsonify({'message': f'Заказ с ID {order_id} не существует в системе заказов'}), 404

        # Обработка других возможных ошибок со стороны соседа (например, 500)
        if order_response.status_code != 200:
            return jsonify({'message': 'Не удалось проверить заказ из-за внутренней ошибки внешнего сервиса'}), 502

        # 3. Если ответ 200 (заказ есть), меняем его статус на "Delivering"
        update_url = f"{ORDER_SERVICE_URL}/orders/{order_id}"
        update_response = requests.put(update_url, json={"status": "Delivering"}, timeout=5)

        if update_response.status_code != 200:
            return jsonify({'message': 'Заказ найден, но не удалось обновить его статус в order-service'}), 502

        # 4. Если всё прошло успешно — создаем запись о доставке в своей БД
        new_delivery = Delivery(order_id=order_id, status='In Transit')
        db.session.add(new_delivery)
        db.session.commit()

        return jsonify({
            'message': f'Delivery created successfully for order {order_id}. Order status updated to Delivering.'
        }), 201

    except requests.exceptions.RequestException:
        # На случай, если order-service лежит или недоступен по сети
        return jsonify({'message': 'Сервис заказов (order-service) недоступен'}), 503

@app.route('/deliveries/<int:delivery_id>', methods=['PUT'])
def update_delivery(delivery_id):
    data = request.get_json()
    new_status = data.get('status')

    delivery = db.session.get(Delivery, delivery_id)
    if not delivery:
        return jsonify({'message': 'Delivery not found'}), 404

    # Валидация пришедшего статуса на бэкенде (для безопасности)
    if new_status not in ["Created", "In Transit", "Done", "Canceled"]:
        return jsonify({'message': 'Недопустимый статус доставки'}), 400

    try:
        # Логика шага 2: если статус меняется на "Done", синхронизируем с сервисом заказов
        if new_status == "Done":
            order_id = delivery.order_id
            update_url = f"{ORDER_SERVICE_URL}/orders/{order_id}"

            # Дергаем соседний сервис и проставляем статус "Delivered"
            update_response = requests.put(update_url, json={"status": "Delivered"}, timeout=5)

            if update_response.status_code != 200:
                return jsonify({
                    'message': f'Доставка не обновлена: не удалось изменить статус заказа {order_id} на Delivered'
                }), 502

        # Если проверка пройдена или статус не "Done" — сохраняем изменения у себя
        delivery.status = new_status
        db.session.commit()

        return jsonify({
            'message': f'Delivery updated successfully to {new_status}.' +
                       (' Order status updated to Delivered.' if new_status == "Done" else '')
        }), 200

    except requests.exceptions.RequestException:
        return jsonify({'message': 'Ошибка связи с сервисом заказов. Статус доставки не изменен.'}), 503

# --- НОВЫЙ МЕТОД: Поиск доставки по order_id (без вывода в шаблон) ---
@app.route('/deliveries/search', methods=['POST'])
def search_delivery_by_order_id():
    data = request.get_json() or {}
    order_id = data.get('orderId')

    if not order_id:
        return jsonify({'message': 'Не указан параметр orderId в теле запроса'}), 400

    # Ищем доставку, привязанную к данному заказу
    delivery = db.session.scalars(db.select(Delivery).where(Delivery.order_id == order_id)).first()

    if not delivery:
        return jsonify({'message': f'Доставка для заказа {order_id} не найдена'}), 404

    return jsonify({
        'id': delivery.id,
        'order_id': delivery.order_id,
        'status': delivery.status
    }), 200


if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5001)
