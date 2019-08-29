import os
import logging

from flask import Flask, jsonify
from flask.logging import default_handler


# Set up logging
ROOT_LOGGER = logging.getLogger()
ROOT_LOGGER.addHandler(default_handler)


application = Flask(__name__)  # noqa

# Set up logging level
ROOT_LOGGER.setLevel(application.logger.level)


@application.route('/', methods=['GET'])
def get_root():
    """Root Endpoint."""

    return jsonify(
        status="Success",
        message="Up and Running"
    ), 200


if __name__ == '__main__':
    # pylama:ignore=C0103
    port = os.environ.get("PORT", 8003)
    application.run(port=int(port))
