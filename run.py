from app import create_app

app = create_app()


if __name__ == "__main__":
    # Keep user-facing errors friendly; enable Flask debugging only through
    # a local environment setting when actively developing.
    import os
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
