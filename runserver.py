import os

from image_service import app


def is_debug_enabled():
    return os.environ.get("FLASK_DEBUG", "False").lower() in ("1", "true", "yes")


if __name__ == "__main__":
    app.run(debug=is_debug_enabled(), host="127.0.0.1", port=5000)