import os
from flask import Flask, request, jsonify
from db.models import db, Delivery
from utils.db_utils import init_db

app = Flask(__name__)
app.json.ensure_ascii = False 
db_user=os.environ.get('DB_USER','user')
db_password=os.environ.get('DB_PASSWORD','password')
db_name=os.environ.get('DB_NAME','database')
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@db:5432/{db_name}'
db.init_app(app)

# --- ГЛАВНАЯ СТРАНИЦА: Меню со ссылками на эндпоинты ---
@app.route('/', methods=['GET'])
def index():
    links = []
    # Перебираем все зарегистрированные во Flask роуты
    for rule in app.url_map.iter_rules():
        # Исключаем служебный роут для статики и саму главную страницу
        if rule.endpoint != 'static' and rule.rule != '/':

            # Получаем чистый путь (например, /deliveries/<int:delivery_id>)
            raw_path = rule.rule

            # Делаем путь кликабельным: заменяем плейсхолдеры <int:...> на тестовую "1"
            clean_path = raw_path
            if '<' in clean_path:
                import re
                clean_path = re.sub(r'<[^>]+>', '1', clean_path)

            # Получаем доступные HTTP-методы (GET, POST и т.д.)
            methods = ', '.join([m for m in rule.methods if m not in ['OPTIONS', 'HEAD']])

            # Формируем элемент списка: если есть GET, делаем ссылку кликабельной активной
            if 'GET' in rule.methods:
                links.append(f'<li>[{methods}] <a href="{clean_path}">{rule.endpoint} -> {raw_path}</a></li>')
            else:
                links.append(f'<li>[{methods}] <b>{rule.endpoint} -> {raw_path}</b> <i>(для отправки через Postman/cURL)</i></li>')

    return f"""
    <html>
        <head>
            <title>Logistics Service API</title>
            <style>
                body {{ font-family: sans-serif; margin: 40px; background: #f4f6f9; color: #333; }}
                h1 {{ color: #e67e22; }}
                ul {{ background: white; padding: 20px 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                li {{ margin: 10px 0; font-size: 16px; line-height: 1.5; }}
                a {{ color: #e67e22; text-decoration: none; font-weight: bold; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>🚚 Logistics Service API Menu</h1>
            <p>Список доступных эндпоинтов приложения:</p>
            <ul>
                {"".join(links) if links else "<li>Эндпоинты не найдены или еще не зарегистрированы</li>"}
            </ul>
        </body>
    </html>
    """

# --- НОВЫЙ МЕТОД: Получение всех доставок ---
@app.route('/deliveries', methods=['GET'])
def get_deliveries():
    # Безопасно вытягиваем все записи из таблицы deliveries
    deliveries = db.session.scalars(db.select(Delivery)).all()

    if not deliveries:
        return jsonify({'message': 'Нет доставок'}), 200

    # Сериализуем объекты SQLAlchemy в массив словарей для JSON
    deliveries_list = []
    for d in deliveries:
        deliveries_list.append({
            'id': d.id,
            'order_id': d.order_id,
            'status': d.status
        })

    return jsonify(deliveries_list), 200

# --- НОВЫЙ МЕТОД: Получение доставки по ID ---
@app.route('/deliveries/<int:delivery_id>', methods=['GET'])
def get_delivery_by_id(delivery_id):
    # Находим конкретную запись по первичному ключу
    delivery = db.session.get(Delivery, delivery_id)

    if not delivery:
        return jsonify({'message': f'Не найдена доставка {delivery_id}'}), 404

    return jsonify({
        'id': delivery.id,
        'order_id': delivery.order_id,
        'status': delivery.status
    }), 200

@app.route('/deliveries', methods=['POST'])
def create_delivery():
    data = request.get_json()
    new_delivery = Delivery(order_id=data['order_id'], status='In Transit')
    db.session.add(new_delivery)
    db.session.commit()
    return jsonify({'message': 'Delivery created successfully'}), 201

@app.route('/deliveries/<int:delivery_id>', methods=['PUT'])
def update_delivery(delivery_id):
    data = request.get_json()
    delivery = db.session.get(Delivery, delivery_id)
    if not delivery:
        return jsonify({'message': 'Delivery not found'}), 404
    delivery.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Delivery updated successfully'})

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5001)
