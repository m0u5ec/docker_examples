import os
from flask import Flask, request, jsonify
from db.models import db, Delivery
from utils.db_utils import init_db

app = Flask(__name__)
app.json.ensure_ascii = False 
db_password = os.environ.get('DB_PASSWORD', 'password')
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:{db_password}@db:5432/logistics'
db.init_app(app)

# --- ГЛАВНАЯ СТРАНИЦА: Меню со ссылками на эндпоинты ---
@app.route('/', methods=['GET'])
def index():
    links = []
    # Перебираем все зарегистрированные во Flask роуты
    for rule in app.url_map.iter_rules():
        # Исключаем служебный роут для статики и сам корень
        if rule.endpoint != 'static' and rule.endpoint != 'index':
            try:
                # Если эндпоинт требует ID доставки, подставляем тестовую "1" для ссылки
                if 'delivery_id' in rule.arguments:
                    url = url_for(rule.endpoint, delivery_id=1)
                else:
                    url = url_for(rule.endpoint)

                # Получаем доступные HTTP-методы (POST, PUT и т.д.)
                methods = ', '.join([m for m in rule.methods if m not in ['OPTIONS', 'HEAD']])

                # Добавляем строку в список (так как GET-эндпоинтов тут пока нет, все будут помечены как для Postman)
                if 'GET' in rule.methods:
                    links.append(f'<li>[{methods}] <a href="{url}">{rule.endpoint} -> {url}</a></li>')
                else:
                    links.append(f'<li>[{methods}] <b>{rule.endpoint} -> {url}</b> <i>(для отправки через Postman/cURL)</i></li>')
            except Exception:
                continue

    return f"""
    <html>
        <head>
            <title>Logistics Service API</title>
            <style>
                body {{ font-family: sans-serif; margin: 40px; background: #f4f6f9; color: #333; }}
                h1 {{ color: #2c3e50; }}
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
                {"".join(links)}
            </ul>
        </body>
    </html>
    """

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
    delivery = Delivery.query.get(delivery_id)
    if not delivery:
        return jsonify({'message': 'Delivery not found'}), 404
    delivery.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Delivery updated successfully'})

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5001)
