# Makes the Website folder a package. It means we can import the website folder in. It means that anything inside of the __init__ file will run automatically when we import folder
from flask import Flask


def create_app():
    app = Flask(__name__)

    from .views import views
    app.register_blueprint(views, url_prefix='/')

    return app
