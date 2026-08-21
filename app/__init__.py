from flask import Flask


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "College Event Resource Allocation System"

    return app