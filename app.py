import os
from flask import Flask, jsonify, request
import json, asyncio, threading, hashlib, requests
from database import get_connection, save_order, check_stock_availability
from flask_cors import CORS
from admin_bot import send_order_to_telegram
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Можно изменить на DEBUG для более подробных логов в процессе разработки
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("../app.log"),  # Логи будут записываться в файл app.log
        logging.StreamHandler()  # Также выводим логи в консоль
    ]
)


load_dotenv()

app = Flask(__name__)

app.secret_key = '277353'
CORS(app, resources={r"/api/*": {"origins": "*"}})


FREEDOMPAY_API_URL = os.getenv('FREEDOMPAY_API_URL')
ADMIN_PROMOCODE = os.getenv('ADMIN_PROMOCODE')
FREEDOMPAY_API_KEY = os.getenv('FREEDOMPAY_API_KEY')
FREEDOMPAY_MERCHANT_ID = os.getenv('FREEDOMPAY_MERCHANT_ID')
logging.basicConfig(level=logging.DEBUG)


# API: Получение всех товаров
@app.route('/api/products/')
def get_products():
    query = """
        SELECT 
            p.article,
            p.name,
            p.price,
            (SELECT pp.photo_url FROM product_photos pp WHERE pp.product_article = p.article LIMIT 1) AS photo_url
        FROM 
            products p
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query)
    products = []
    for row in cursor.fetchall():
        products.append({
            "article": row[0],
            "name": row[1],
            "price": row[2],
            "photo_url": row[3],
        })

    return jsonify(products)

# API: Получение товаров по категории
@app.route('/api/category/<category>/')
def category_catalog(category):
    query = """
        SELECT 
            p.article,
            p.name,
            p.price,
            (SELECT pp.photo_url FROM product_photos pp WHERE pp.product_article = p.article LIMIT 1) AS photo_url
        FROM 
            products p
        WHERE
            p.category_id = %s
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query, (category,))
    products = []
    for row in cursor.fetchall():
        products.append({
            "article": row[0],
            "name": row[1],
            "price": row[2],
            "photo_url": row[3],
        })

    return jsonify(products)

# API: Получение информации о конкретном товаре
@app.route('/api/product/<article>')
def product(article):

    query = """
        SELECT 
            p.article, 
            p.name, 
            p.description, 
            p.price,  
            p.colors,
            p.sizes,
            p.quantity
        FROM 
            products p
        WHERE 
            p.article = %s
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query, (article,))
    row = cursor.fetchone()

    if row is None:
        return jsonify({"error": "Product not found"}), 404

    # Запрашиваем ВСЕ фото этого товара
    query_photos = "SELECT photo_url FROM product_photos WHERE product_article = %s"
    cursor.execute(query_photos, (article,))
    photos = [row[0] for row in cursor.fetchall()]  # Список путей к фото

    return jsonify({
        "article": row[0],
        "name": row[1],
        "description": row[2],
        "price": row[3],
        "photo_urls": photos,  # Теперь массив фото
        "available_colors": row[4].split(", "),
        "available_sizes": row[5].split(", "),
        "quantity": json.loads(row[6]) if row[6] else {}
    })

@app.route('/api/check_payment_status', methods=['POST'])
def check_payment_status():
    data = request.json
    order_id = data.get('order_id')
    order_data = data.get('orderData')

    if not order_id or not order_data:
        return jsonify({"success": False, "message": "Не указан order_id или orderData"})

    status_data = {
        "pg_merchant_id": FREEDOMPAY_MERCHANT_ID,
        "pg_order_id": order_id,
        "pg_salt": "molbulak"
    }
    status_data["pg_sig"] = generate_signature(status_data, FREEDOMPAY_API_KEY)

    try:
        response = requests.post(
            "https://api.freedompay.kg/get_status3.php",
            data=status_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()  # это заставит выбросить исключение для 4xx и 5xx ошибок

        result = response.json()
        logging.info("Результат проверки оплаты:", result)

        if result.get("pg_status") == "ok":
            process_payment(data)
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Платёж не прошёл"})
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP ошибка при запросе статуса: {http_err}")
        return jsonify({"success": False, "message": "Ошибка HTTP при запросе к FreedomPay"}), 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса: {e}")
        return jsonify({"success": False, "message": "Ошибка при запросе к FreedomPay"}), 500
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}")
        return jsonify({"success": False, "message": "Произошла неизвестная ошибка"}), 500

@app.route('/api/payment_success', methods=['POST'])
def payment_success():
    data = request.json
    logging.info("📌 Полный request.json:", request.get_json())

    order_data = data.get('orderData')

    logging.info("📌 order_data перед сохранением:", order_data)

    if not order_data:
        return jsonify({"success": False, "message": "Данные заказа не получены."}), 400

    order_id = save_order(order_data)  # Сохраняем заказ в БД
    logging.info(f"✅ Заказ сохранён с ID: {order_id}")

    order_id = data.get('order_id')
    if order_id:
        thread = threading.Thread(target=lambda: asyncio.run(send_order_to_telegram(order_id)))
        thread.start()  # Запускаем отправку в Телеграм в отдельном потоке

    return jsonify({"success": True})

def process_payment(data):
    logging.info("Полученные данные:", data)

    order_data = data.get('orderData')

    logging.info("📌 order_data перед сохранением:", order_data)

    if not order_data:
        return jsonify({"success": False, "message": "Данные заказа не получены."}), 400

    order_id = save_order(order_data)  # Сохраняем заказ в БД
    logging.info(f"✅ Заказ сохранён с ID: {order_id}")

    order_id = data.get('order_id')
    if order_id:
        thread = threading.Thread(target=lambda: asyncio.run(send_order_to_telegram(order_id)))
        thread.start()  # Запускаем отправку в Телеграм в отдельном потоке

    return jsonify({"success": True})

def flatten_params(params, parent_name=''):
    flat_params = {}
    i = 0
    for key, val in params.items():
        i += 1
        name = f"{parent_name}{key}{str(i).zfill(3)}"
        if isinstance(val, dict):
            flat_params.update(flatten_params(val, name))
        elif isinstance(val, list):
            for idx, item in enumerate(val, 1):
                flat_params.update(flatten_params(item, f"{name}{str(idx).zfill(3)}"))
        else:
            flat_params[name] = str(val)
    return flat_params

def generate_signature(params, secret_key):
    flat_params = flatten_params(params)
    sorted_items = sorted(flat_params.items())
    sorted_values = [v for _, v in sorted_items]

    sign_parts = ['init_payment.php'] + sorted_values + [secret_key]
    sign_str = ';'.join(sign_parts)

    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

@app.route('/api/create_payment', methods=['POST'])
def create_payment():
    data = request.get_json()
    order_id = data.get("order_id")

    if data.get('deliveryMethod') == 'Европочта':
        amount = int(data.get('totalPrice')) + 130
    else:
        amount = data.get('totalPrice')

    description = f'Оплата заказа №{order_id}'
    promo = data.get('promo_code')  # Исправил на promo_code

    if promo == ADMIN_PROMOCODE:
        return jsonify({"status": "admin_checkout_successful"})

    cart_items = data.get("cart_items", [])
    is_available, errors = check_stock_availability(cart_items)
    if not is_available:
        return jsonify({"success": False, "message": "Недостаточно товаров", "details": errors}), 400


    if not amount:
        return jsonify({'error': 'Отсутствуют обязательные параметры'}), 400

    payment_data = {
        'pg_order_id': str(order_id),
        'pg_merchant_id': FREEDOMPAY_MERCHANT_ID,
        'pg_amount': str(amount),
        'pg_description': description,
        'pg_currency': 'RUB',
        'pg_salt': 'molbulak',
        "pg_success_url": "https://pobegamiwebapp.ru/payment_success",
        "pg_failure_url": "https://pobegamiwebapp.ru/payment_fail",
        'pg_testing_mode': 1
    }

    pg_sig = generate_signature(payment_data, FREEDOMPAY_API_KEY)

    request_data = {
        'pg_order_id': payment_data['pg_order_id'],
        'pg_merchant_id': payment_data['pg_merchant_id'],
        'pg_amount': payment_data['pg_amount'],
        'pg_description': payment_data['pg_description'],
        'pg_salt': payment_data['pg_salt'],
        'pg_currency': payment_data['pg_currency'],
        "pg_success_url": "https://pobegamiwebapp.ru/payment_success",
        "pg_failure_url": "https://pobegamiwebapp.ru/payment_fail",
        'pg_testing_mode': 1,
        'pg_sig': pg_sig
    }

    logging.info("Запрос к FreedomPay: ", json.dumps(request_data, indent=4))

    try:
        response = requests.post(
            FREEDOMPAY_API_URL,
            data=request_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response Text: {response.text}")

        response.raise_for_status()
        root = ET.fromstring(response.text)

        pg_status = root.find('pg_status').text
        if pg_status == 'ok':
            payment_url = root.find('pg_redirect_url').text
            if promo == ADMIN_PROMOCODE:
                return jsonify({"status": "admin_checkout_successful"})
            else:
                return jsonify({'payment_url': payment_url})
        else:
            pg_description = root.find('pg_error_description').text
            return jsonify({'error': pg_description}), 500

    except requests.exceptions.RequestException as e:
        logging.error("[create_payment] Ошибка:", e)
        return jsonify({'error': f'Ошибка при запросе к FreedomPay: {str(e)}'}), 500



if __name__ == '__main__':
    app.run(debug=False)



