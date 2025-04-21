from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import *
import os
import uuid
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO, filename="bot_debug.log", filemode="a", format="%(asctime)s - %(message)s")

load_dotenv()

editing_data = {}
product_data = {}
ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
app = Application.builder().token(ADMIN_BOT_TOKEN).build()

# Список категорий
CATEGORIES = {
    1: "платья",
    2: "костюмы",
    3: "верхняя одежда",
    4: "футболки",
}

# Список атрибутов продукта
ATRIBUTES = {
    1: "name",
    2: "photos",
    3: "colors",
    4: "sizes",
    5: "price",
    6: "description",
    7: "quantity"
}



async def send_order_to_telegram(order_id):
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
    except Exception as e:
        print(f"❌ Ошибка при запросе данных о заказе: {e}")
        return

    if not order:
        print(f"❌ Ошибка: Заказ с ID {order_id} не найден!")
        return

    # Получаем товары из заказа
    cursor.execute("""
        SELECT oi.*, p.photo_url 
        FROM order_items oi
        JOIN product_photos p ON oi.product_article = p.product_article
        WHERE oi.order_id = %s
    """, (order_id,))
    order_items = cursor.fetchall()

    bot = Bot(token=ADMIN_BOT_TOKEN)

    match order[7]:
        case 'Европочта':
            order_text = (
                f"📦 *Новый заказ #{order_id}*\n"
                f"🏤 Способ доставки: {order[7]}\n"  # Метод доставки
                f"👤 {order[1]}\n"  # Фамилия Имя Отчество
                f"🌍 Страна: {order[2]}\n"  # Страна
                f"🌳 Область: {order[4]}\n"  # Область
                f"🏙 Город: {order[3]}\n"  # Город
                f"🏠 Адрес: {order[5]}\n"  # Улица
                f"📦 Номер ПВЗ: {order[8]}\n"  # Номер пункта выдачи
                f"📞 Номер телефона: {order[9]}\n"  # Номер телефона
                f"💬 Телеграм: {order[10]}\n"  # Ник в Телеграме
                f"💰 Общая сумма: {order[11]} RUB\n"  # Общая сумма
                f"⏰ Время заказа: {order[12]}\n\n"  # Время заказа
                f"Товары:\n"
            )
        case 'Белпочта':
            order_text = (
                f"📦 *Новый заказ #{order_id}*\n"
                f"🏤 Способ доставки: {order[7]}\n"  # Метод доставки
                f"👤 {order[1]}\n"  # Фамилия Имя Отчество
                f"🌍 Страна: {order[2]}\n"  # Страна
                f"🌳 Область: {order[4]}\n"  # Область
                f"🏙 Город: {order[3]}\n"  # Город
                f"🏠 Адрес: {order[5]}\n"  # Улица
                f"📍 Индекс: {order[6]}\n"  # Индекс
                f"📞 Номер телефона: {order[9]}\n"  # Номер телефона
                f"💬 Телеграм: {order[10]}\n"  # Ник в Телеграме
                f"💰 Общая сумма: {order[11]} RUB\n"  # Общая сумма
                f"⏰ Время заказа: {order[12]}\n\n"  # Время заказа
                f"Товары:\n"
            )
        case 'СДЭК':
            order_text = (
                f"📦 *Новый заказ #{order_id}*\n"
                f"🏤 Способ доставки: {order[7]}\n"  # Метод доставки
                f"👤 {order[1]}\n"  # Фамилия Имя Отчество
                f"🌍 Страна: {order[2]}\n"  # Страна
                f"🌳 Область: {order[4]}\n"  # Область
                f"🏙 Город: {order[3]}\n"  # Город
                f"🏠 Адрес: {order[5]}\n"  # Улица
                f"📦 Номер ПВЗ: {order[8]}\n"  # Номер пункта выдачи
                f"📞 Номер телефона: {order[9]}\n"  # Номер телефона
                f"💬 Телеграм: {order[10]}\n"  # Ник в Телеграме
                f"💰 Общая сумма: {order[11]} RUB\n"  # Общая сумма
                f"⏰ Время заказа: {order[12]}\n\n"  # Время заказа
                f"Товары:\n"
            )
        case 'Боксберри':
            order_text = (
                f"📦 *Новый заказ #{order_id}*\n"
                f"🏤 Способ доставки: {order[7]}\n"  # Метод доставки
                f"👤 {order[1]}\n"  # Фамилия Имя Отчество
                f"🌍 Страна: {order[2]}\n"  # Страна
                f"🌳 Область: {order[4]}\n"  # Область
                f"🏙 Город: {order[3]}\n"  # Город
                f"🏠 Адрес: {order[5]}\n"  # Улица
                f"📦 Номер ПВЗ: {order[8]}\n"  # Номер пункта выдачи
                f"📞 Номер телефона: {order[9]}\n"  # Номер телефона
                f"💬 Телеграм: {order[10]}\n"  # Ник в Телеграме
                f"💰 Общая сумма: {order[11]} RUB\n"  # Общая сумма
                f"⏰ Время заказа: {order[12]}\n\n"  # Время заказа
                f"Товары:\n"
            )

    # Отправляем текст с инфой о заказе
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=order_text, parse_mode="Markdown")

    # Отправляем отдельные сообщения с фото
    for item in order_items:
        product_name = item[2]
        color = item[3]
        size = item[4]
        quantity = item[5]
        price = item[6]
        photo_filename = item[7]

        if photo_filename:
            photo_url = f"https://pobegamiwebapp.ru/maryanashop_webapp/public_html/assets/uploads/{photo_filename}"
            caption = (
                f"🛒 *{product_name}*\n"
                f"🎨 Цвет: {color}\n"
                f"📏 Размер: {size}\n"
                f"🔢 Кол-во: {quantity}\n"
                f"💵 Цена: {price} RUB"
            )
            await bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=photo_url,
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            # fallback без фото
            text = (
                f"🛒 *{product_name}*\n"
                f"🎨 Цвет: {color}\n"
                f"📏 Размер: {size}\n"
                f"🔢 Кол-во: {quantity}\n"
                f"💵 Цена: {price} RUB"
            )
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown")

    print(f"✅ Заказ #{order_id} отправлен в Telegram.")

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления нового товара."""
    user_id = update.message.from_user.id
    product_data[user_id] = {
        "article" : [],
        "name": None,
        "photos": [],
        "colors": [],
        "sizes": [],
        "price": [],
        "description": [],
        "quantity": [],
        "category": None,
        "step": "category",
    }
    category_options = "\n".join([f"{num}: {name}" for num, name in CATEGORIES.items()])
    await update.message.reply_text(
        f"Выберите категорию товара, отправив номер:\n{category_options}"
    )

async def product_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in product_data:
        await update.message.reply_text("Нет активного процесса добавления товара.")
        return

    status = product_data[user_id]
    await update.message.reply_text(f"Текущие данные товара:\n{json.dumps(status, indent=2, ensure_ascii=False)}")

def generate_article(category_prefix):
    """
    Генерирует уникальный артикул для товара на основе категории.
    Артикул формируется как {prefix}{номер}, где prefix - префикс категории,
    а номер - следующий доступный номер в категории.
    """
    last_number = get_last_article_number(category_prefix)  # Получаем последний номер для категории
    if last_number is None:  # Если товаров в категории ещё нет
        last_number = 0
    new_number = last_number + 1
    return f"{category_prefix}{new_number:04d}"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений."""
    user_id = update.message.from_user.id
    logging.info("Пользователь написал текст")
    if user_id not in product_data:
        await update.message.reply_text("Сначала используйте команду /add_product.")
        return

    current_step = product_data[user_id]["step"]

    if current_step == "category":
        try:
            category_prefix = int(update.message.text.strip())
            if category_prefix not in CATEGORIES:
                raise ValueError
            product_data[user_id]["category"] = category_prefix
            product_data[user_id]["article"] = generate_article(category_prefix)
            product_data[user_id]["step"] = "name"
            await update.message.reply_text("Категория выбрана. Введите название товара:")
        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, отправьте корректный номер категории. Доступные категории:\n"
                + "\n".join([f"{num}: {name}" for num, name in CATEGORIES.items()])
            )
    elif current_step == "name":
        product_data[user_id]["name"] = update.message.text.strip()
        product_data[user_id]["step"] = "photos"
        await update.message.reply_text("Теперь отправьте фото товара. Отправьте одно или несколько фото, затем напишите 'Готово'.")
    elif current_step == "colors":
        product_data[user_id]["colors"].extend(update.message.text.split(","))
        await update.message.reply_text("Цвета добавлены. Теперь введите размеры (например: S, M, L или 42, 44, 46):")
        product_data[user_id]["step"] = "sizes"
    elif current_step == "sizes":
        product_data[user_id]["sizes"].extend(update.message.text.split(","))
        await update.message.reply_text("Размеры добавлены. Теперь введите цены в RUB.")
        product_data[user_id]["step"] = "prices"
    elif current_step == "prices":
        try:
            product_data[user_id]["price"] = update.message.text.strip()
            await update.message.reply_text("Цены добавлены. Теперь введите описание:")
            product_data[user_id]["step"] = "description"
        except (IndexError, ValueError):
            await update.message.reply_text(
                "Пожалуйста, укажите цены корректно в RUB. Например: '1500'"
            )
    elif current_step == "description":
        product_data[user_id]["description"] = update.message.text.strip()
        await update.message.reply_text("Описание добавлено.")
        product_data[user_id]["step"] = "quantity"

        colors = product_data[user_id]["colors"]
        sizes = product_data[user_id]["sizes"]

        # Генерируем список комбинаций цветов и размеров
        combinations = [f"{color} - {size}" for color in colors for size in sizes]

        product_data[user_id]["quantity_combinations"] = combinations  # Сохраняем комбинации
        product_data[user_id]["step"] = "quantity_values"  # Переход на следующий шаг

        # Отправляем пользователю комбинации
        message = "Введите количество для каждой комбинации через запятую:\n\n" + "\n".join(combinations)

        # Используем `context.bot.send_message`, передав chat_id
        await context.bot.send_message(chat_id=update.message.chat_id, text=message)
    elif current_step == "quantity_values":
        try:
            values = list(map(int, update.message.text.split(",")))  # Преобразуем в список чисел
            combinations = product_data[user_id]["quantity_combinations"]

            if len(values) != len(combinations):
                await update.message.reply_text(
                    f"Ошибка! Количество чисел не совпадает с количеством комбинаций ({len(combinations)}). Попробуйте ещё раз.")
                return

            # Создаём словарь вида {"Красный-M": 5, "Синий-L": 2}
            quantity_dict = {comb: val for comb, val in zip(combinations, values)}
            product_data[user_id]["quantity"] = quantity_dict  # Храним как словарь, а не строку

            await update.message.reply_text("Количество добавлено. Теперь завершаем процесс сохранения товара.")
            product_data[user_id]["step"] = "save"

        except ValueError:
            await update.message.reply_text("Ошибка! Введите числа через запятую, например: 5, 10, 3, 7")

        # Сохранение товара в БД
        product_info = product_data[user_id]
        article = product_data[user_id]["article"]
        sizes = ",".join(product_info["sizes"])
        colors = ",".join(product_info["colors"])
        name = product_info["name"]
        price = product_info["price"]
        description = product_info["description"]
        category_prefix = product_info["category"]
        quantity = product_info["quantity"]

        # Декодируем строку в словарь, если это строка
        if isinstance(product_data[user_id]["quantity"], str):
            try:
                quantity_dict = json.loads(product_data[user_id]["quantity"])
            except json.JSONDecodeError:
                await update.message.reply_text("Ошибка: количество товаров имеет неверный формат.")
                return
        else:
            quantity_dict = product_data[user_id]["quantity"]  # Если уже словарь, оставляем без изменений

        # Теперь quantity_dict точно словарь, можно использовать .values()
        total_quantity = sum(quantity_dict.values())

        # Подсчёт количества по каждому цвету
        color_totals = {}
        for key, value in quantity_dict.items():
            color = key.split(" - ")[0]  # Достаём цвет
            color_totals[color] = color_totals.get(color, 0) + value

        # Формируем строку с количеством по цветам
        color_quantity_text = ", ".join([f"{color}: {qty}" for color, qty in color_totals.items()])

        # Сохраняем продукт в БД
        save_product(article, name, description, price, sizes, colors, quantity, category_prefix)

        # Сохранение фото
        for photo in product_data[user_id]["photos"]:
            # Извлекаем имя файла из полного пути
            file_name = os.path.basename(photo)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO product_photos (product_article, photo_url) 
                VALUES (%s, %s)
            """, (product_data[user_id]["article"], file_name))
            conn.commit()

        # Подтверждение добавления
        result_message = (
            f"🎉 Товар успешно добавлен!\n\n"
            f"📌 Название: {name}\n"
            f"📋 Артикул: {article}\n"
            f"📸 Фото: {len(product_info['photos'])} шт.\n"
            f"🎨 Цвета: {colors}\n"
            f"📏 Размеры: {sizes}\n"
            f"💵 Цены: {price}\n"
            f"📝 Описание: {description}\n"
            f"🔢 Количество: {color_quantity_text}\n"
        )
        await update.message.reply_text(result_message)

        # Удаляем данные о процессе добавления
        del product_data[user_id]
    else:
        await update.message.reply_text("Неизвестное состояние. Попробуйте снова команду /add_product.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий."""
    user_id = update.message.from_user.id
    upload_path = os.path.join(os.path.dirname(__file__), "../assets/uploads")

    # Проверяем, находится ли пользователь на этапе добавления фото
    if user_id not in product_data or product_data[user_id].get("step") != "photos":
        await update.message.reply_text("Сначала используйте команду /add_product.")
        return

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    unique_name = f"{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(upload_path, unique_name)

    await file.download_to_drive(file_path)

    try:
        # Проверяем, существует ли файл
        if os.path.exists(file_path):
            product_data.setdefault(user_id, {}).setdefault("photos", []).append(file_path)
            normalized_path = file_path.replace("\\", "/")  # Приводим путь к универсальному виду
            
        else:
            await update.message.reply_text("Ошибка: файл не был сохранён.")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка при сохранении фото: {e}")
    # Сообщение о следующем действии
    await update.message.reply_text("Отправьте ещё фото или напишите 'Готово', чтобы продолжить.")

async def handle_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды 'Готово'."""
    user_id = update.message.from_user.id

    if user_id in product_data:
        # Процесс добавления нового товара
        current_step = product_data[user_id]["step"]
        if current_step == "photos":
            product_data[user_id]["step"] = "colors"
            await update.message.reply_text(
                "Фотографии сохранены. Теперь введите доступные цвета (например: Красный, Синий, Чёрный):")
        else:
            await update.message.reply_text("Команда 'Готово' недоступна на этом этапе.")

    elif user_id in editing_data:
        # Процесс редактирования товара
        current_step = editing_data[user_id]["step"]

        if current_step == "photos":
            editing_data[user_id]["step"] = "colors"
            await update.message.reply_text(
                "Фотографии обновлены. Теперь введите доступные цвета (например: Красный, Синий, Чёрный):")
        elif current_step == "colors":
            editing_data[user_id]["step"] = "sizes"
            await update.message.reply_text("Цвета обновлены. Теперь введите размеры (например: S, M, L):")
        elif current_step == "sizes":
            editing_data[user_id]["step"] = "prices"
            await update.message.reply_text(
                "Размеры обновлены. Теперь введите цены в RUB, BYN, KZT, KGS (например: 1600, 49, 4680, 1300):")
        elif current_step == "prices":
            editing_data[user_id]["step"] = "description"
            await update.message.reply_text("Цены обновлены. Теперь введите описание:")
        elif current_step == "description":
            editing_data[user_id]["step"] = "quantity"
            await update.message.reply_text("Описание обновлено. Теперь введите количество:")
        elif current_step == "quantity":
            # Сохранение изменений в БД
            product_info = editing_data[user_id]
            article = product_info["article"]
            sizes = ",".join(product_info["sizes"])
            colors = ",".join(product_info["colors"])
            name = product_info["name"]
            price = json.dumps(product_info["price"])
            description = product_info["description"]
            quantity = product_info["quantity"]

            update_product(article, name, description, price, sizes, colors, quantity)

            # Подтверждение редактирования
            await update.message.reply_text(
                f"✅ Товар успешно отредактирован!\n\n"
                f"📌 Название: {name}\n"
                f"📋 Артикул: {article}\n"
                f"📸 Фото: {len(product_info['photos'])} шт.\n"
                f"🎨 Цвета: {colors}\n"
                f"📏 Размеры: {sizes}\n"
                f"💵 Цены: {price}\n"
                f"📝 Описание: {description}\n"
                f"🔢 Количество: {quantity}\n"
            )

            # Удаляем данные о редактировании
            del editing_data[user_id]
        else:
            await update.message.reply_text("Команда 'Готово' недоступна на этом этапе.")

    else:
        await update.message.reply_text("Сначала начните добавление или редактирование товара.")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Введите артикул товара, который хотите удалить. Например:\n`/delete 10001`", parse_mode="Markdown")
        return

    article = args[0]
    product = get_product_by_article(article)
    if not product:
        await update.message.reply_text("Товар с таким артикулом не найден.")
        return

    delete_product(article)
    await update.message.reply_text(f"Товар с артикулом {article} удалён.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in product_data:
        del product_data[user_id]
        await update.message.reply_text("Процесс добавления товара отменён.")
    else:
        await update.message.reply_text("Нет активного процесса для отмены.")



def main():

    app.add_handler(CommandHandler("add_product", add_product))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Готово"), handle_done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()
