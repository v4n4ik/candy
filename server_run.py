from app import app as flask_app
from gunicorn.app.base import BaseApplication
import logging
from flask_cors import CORS

CORS(flask_app)

# Устанавливаем логирование для Gunicorn
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GunicornApplication(BaseApplication):
    def __init__(self, flask_app):
        self.flask_app = flask_app
        super().__init__()

    def load(self):
        return self.flask_app

if __name__ == "__main__":
    try:
        logger.info("Starting the server...")
        # Запуск Flask на всех интерфейсах (0.0.0.0)
        flask_app.run(host='0.0.0.0', port=3000, debug=False)  # Укажи порт по необходимости
    except Exception as e:
        logger.error(f"Error starting the server: {e}")
