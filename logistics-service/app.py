import os
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

# --- ГЛАВНАЯ СТРАНИЦА: Рендерим HTML-интерфейс ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# --- ПОЛУЧЕНИЕ ВСЕХ ДОСТАВОК ---
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

# --- ПОЛУЧЕНИЕ ДОСТАВКИ ПО ID ---
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

# --- СОЗДАНИЕ ДОСТАВКИ ---
@app.route('/deliveries', methods=['POST'])
def create_delivery():
    data = request.get_json()
    new_delivery = Delivery(order_id=data['order_id'], status='In Transit')
    db.session.add(new_delivery)
    db.session.commit()
    return jsonify({'message': 'Delivery created successfully'}), 201

# --- ОБНОВЛЕНИЕ СТАТУСА ДОСТАВКИ ---
@app.route('/deliveries/<int:delivery_id>', methods=['PUT'])
def update_delivery(delivery_id):
    data = request.get_json()
    delivery = db.session.get(Delivery, delivery_id)
    if not delivery:
        return jsonify({'message': 'Delivery not found'}), 404
    delivery.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Delivery updated successfully'}), 200

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5001)
