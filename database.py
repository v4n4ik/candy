import pymysql
import pymysql.cursors
import json
import os
from dotenv import load_dotenv

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# Подключение к базе данных
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": "pobegami_db",
    "charset": "utf8mb4",
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def get_dict_connection():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

# Получение последнего артикула в категории
def get_last_article_number(category_prefix):
    """
    Возвращает последний порядковый номер товара в указанной категории.
    Если в категории нет товаров, возвращает 0.
    """
    connection = get_connection()
    with connection.cursor() as cursor:
        query = """
        SELECT MAX(CAST(SUBSTRING(article, 3) AS UNSIGNED))
        FROM products
        WHERE article LIKE %s
        """
        prefix_pattern = f"{category_prefix}%"
        cursor.execute(query, (prefix_pattern,))
        result = cursor.fetchone()[0]
    connection.close()
    return result if result else 0

# Сохранение продукта с артикулом и категорией
def save_product(article, name, description, price, sizes, colors, quantity, category_id):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("SET NAMES utf8mb4;")
    with connection.cursor() as cursor:
        query = """
        INSERT INTO products (article, name, description, price, sizes, colors, quantity, category_id) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        if isinstance(quantity, dict):
            quantity = json.dumps(quantity, ensure_ascii=False)
        print("Сохраняем:", quantity)  # Посмотри, что именно сохраняется
        cursor.execute(query, (article, name, description, price, sizes, colors, quantity, category_id))
        connection.commit()

# Сохранение фотографии
def save_photo(article, photo_url):
    """
    Сохраняет URL фотографии, связывая её с продуктом по артикулу.
    """
    connection = get_connection()
    with connection.cursor() as cursor:
        query = """
        INSERT INTO product_photos (product_article, photo_url)
        VALUES (%s, %s)
        """
        cursor.execute(query, (article, photo_url))
    connection.commit()
    connection.close()

def is_admin(user_id):
    connection = get_connection()
    with connection.cursor() as cursor:
        query = "SELECT COUNT(*) FROM admins WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        return cursor.fetchone()[0] > 0

def add_admin(user_id):
    connection = get_connection()
    with connection.cursor() as cursor:
        query = "INSERT IGNORE INTO admins (user_id) VALUES (%s)"
        cursor.execute(query, (user_id,))
    connection.commit()
    connection.close()

def delete_product(article):
    """
    Удаляет товар по артикулу. Также удаляет связанные фотографии.
    Возвращает True, если удаление прошло успешно, иначе False.
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # Удаляем фотографии, связанные с товаром
            query_photos = "DELETE FROM product_photos WHERE product_article = %s"
            cursor.execute(query_photos, (article,))

            # Удаляем сам товар
            query_product = "DELETE FROM products WHERE article = %s"
            cursor.execute(query_product, (article,))
            deleted_rows = cursor.rowcount
        connection.commit()
        return deleted_rows > 0
    finally:
        connection.close()

def update_product(product_id, field, new_value):
    """Обновление поля товара в базе данных."""
    connection = get_connection()
    with connection.cursor() as cursor:
        query = f"UPDATE products SET {field} = %s WHERE id = %s"
        cursor.execute(query, (new_value, product_id))
        updated_rows = cursor.rowcount
    connection.commit()
    connection.close()
    return updated_rows > 0


def get_product_by_article(article):
    connection = get_dict_connection()
    with connection.cursor() as cursor:
        query_product = "SELECT * FROM products WHERE article = %s"
        cursor.execute(query_product, (article,))
        product = cursor.fetchone()

        if not product:
            return None

        product["quantity"] = json.loads(product["quantity"])  # Преобразуем обратно в словарь

        query_photos = "SELECT photo_url FROM product_photos WHERE product_article = %s"
        cursor.execute(query_photos, (article,))
        product["photos"] = [row["photo_url"] for row in cursor.fetchall()]

        return product




def get_last_article_number(category_prefix):
    """
    Возвращает последний номер товара (последние 4 цифры) для категории.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(SUBSTRING(article, 3, 4)) AS last_number
        FROM products
        WHERE article LIKE %s
    """, (f"{category_prefix}%",))
    result = cursor.fetchone()
    return int(result[0]) if result and result[0] else None



def get_order_info(order_id):
    """Получает информацию о заказе из базы данных."""
    connection = get_dict_connection()
    with connection.cursor() as cursor:
        # Получаем основную информацию о заказе
        cursor.execute("""
            SELECT full_name, country, city, delivery_method, post_office_number, phone_number, total_price
            FROM orders
            WHERE id = %s
        """, (order_id,))
        order = cursor.fetchone()

        if not order:
            return None

        # Получаем список товаров в заказе
        cursor.execute("""
            SELECT product_article AS article, color, size, quantity, price
            FROM order_items
            WHERE order_id = %s
        """, (order_id,))
        order["items"] = cursor.fetchall()

    connection.close()
    return order

def check_stock_availability(cart_items):
    """
    Проверяет, хватает ли товаров на складе.
    Возвращает (True, {}) если всё ок,
    или (False, список_ошибок), если что-то не хватает.
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            insufficient_stock = []

            for item in cart_items:
                cursor.execute("SELECT quantity FROM products WHERE article = %s", (item["article"],))
                result = cursor.fetchone()

                if result:
                    quantity_data = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                    cleaned_quantity_data = {k.replace("  ", " "): v for k, v in quantity_data.items()}
                    product_key = f"{item['color']} - {item['size']}".replace("  ", " ")

                    if product_key in cleaned_quantity_data:
                        available_quantity = cleaned_quantity_data[product_key]
                        if available_quantity < item["quantity"]:
                            insufficient_stock.append(
                                f"{item['color']} {item['size']} (доступно: {available_quantity}, нужно: {item['quantity']})"
                            )
                    else:
                        insufficient_stock.append(f"{item['color']} {item['size']} - нет в наличии")

            if insufficient_stock:
                return False, insufficient_stock
            return True, {}

    except Exception as e:
        print("Ошибка в check_stock_availability:", e)
        return False, [f"Ошибка проверки: {e}"]
    finally:
        connection.close()


def save_order(order_data):
    """
    Проверяет доступность товаров, затем сохраняет заказ и уменьшает количество товаров.
    Возвращает order_id, если заказ успешно сохранён.
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # Заполняем пустыми строками, если чего-то нет
            cleaned_order_data = {
                key: order_data.get(key, "") for key in [
                    "lastName", "firstName", "middleName", "country", "region", "district",
                    "city", "street", "postOfficeNumber", "postalCode", "deliveryMethod",
                    "phoneNumber", "telegramUsername", "totalPrice", "order_id"
                ]
            }

            cart_items = order_data.get("cart_items", [])  # Отдельно сохраняем корзину

            full_name = f"{order_data['lastName']} {order_data['firstName']} {order_data['middleName']}".strip()

            # Проверяем, хватает ли товаров** (без изменений в БД)
            insufficient_stock = []
            updated_quantities = {}

            for item in order_data.get("cart_items", []):
                cursor.execute("SELECT quantity FROM products WHERE article = %s", (item["article"],))
                result = cursor.fetchone()

                if result:
                    quantity_data = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                    cleaned_quantity_data = {k.replace("  ", " "): v for k, v in quantity_data.items()}

                    product_key = f"{item['color']} - {item['size']}".replace("  ", " ")

                    if product_key in cleaned_quantity_data:
                        available_quantity = cleaned_quantity_data[product_key]

                        if available_quantity < item["quantity"]:
                            insufficient_stock.append(
                                f"{item['color']} {item['size']} (доступно: {available_quantity}, нужно: {item['quantity']})")
                        else:
                            updated_quantities[item["article"]] = cleaned_quantity_data.copy()
                            updated_quantities[item["article"]][product_key] -= item["quantity"]
                    else:
                        insufficient_stock.append(f"{item['color']} {item['size']} - нет в наличии")

            # Если товаров не хватает — сразу возвращаем ошибку, не дёргая `orders`
            if insufficient_stock:
                print("❌ Ошибка: Недостаточно товаров!", insufficient_stock)
                return {"success": False, "message": "Недостаточно товаров", "details": insufficient_stock}

            # Шаг 2. Теперь создаём заказ, только если всё ОК
            query = """
                INSERT INTO orders (id, full_name, country, region, city, street, postal_code, 
                                    delivery_method, post_office_number, phone_number, 
                                    telegram_username, total_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                cleaned_order_data['order_id'],
                full_name,
                cleaned_order_data["country"],
                cleaned_order_data["region"],
                cleaned_order_data["city"],
                cleaned_order_data["street"],
                cleaned_order_data["postalCode"],
                cleaned_order_data["deliveryMethod"],
                cleaned_order_data["postOfficeNumber"],
                cleaned_order_data["phoneNumber"],
                cleaned_order_data["telegramUsername"],
                cleaned_order_data["totalPrice"]
            ))
            order_id = order_data.get('order_id')
            print(f"📌 ID созданного заказа: {order_id}")

            # Шаг 3. Обновляем количество товаров
            for article, new_quantities in updated_quantities.items():
                cursor.execute("UPDATE products SET quantity = %s WHERE article = %s",
                               (json.dumps(new_quantities, ensure_ascii=False), article))

            # Шаг 4. Добавляем товары в `order_items`
            for item in cart_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_article, color, size, quantity, price)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (order_id, item["article"], item["color"], item["size"], item["quantity"], item["price"]))

            connection.commit()
            return order_id  # Возвращаем ID заказа
    except Exception as e:
        print(f"❌ Ошибка при сохранении заказа: {e}")
        connection.rollback()
        return {"success": False, "message": "Ошибка сервера"}
    finally:
        connection.close()



