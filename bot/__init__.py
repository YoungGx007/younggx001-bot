from flask import Flask
from .reply import setup_routes


def create_app():
    app = Flask(__name__)
    setup_routes(app)
    return app
