import os
import logging

from flask import Flask, jsonify, request
from flask.logging import default_handler
import subprocess


# Set up logging
ROOT_LOGGER = logging.getLogger()
ROOT_LOGGER.addHandler(default_handler)


application = Flask(__name__)  # noqa

# Set up logging level
ROOT_LOGGER.setLevel(application.logger.level)

ARGO = '/usr/local/bin/argo'
ARGO_CMDLINE = [ARGO]


def pass_workflow(_k, v):
    ARGO_CMDLINE.append(v)


def pass_workflow_name(v):
    ARGO_CMDLINE.append(v)


def pass_namespace(_k, v):
    ARGO_CMDLINE.append('-n')
    ARGO_CMDLINE.append(v)


def pass_parameter(k, v):
    ARGO_CMDLINE.append('-p')
    ARGO_CMDLINE.append(f'{k}={v}')


SWITCHER = {
        'workflow': pass_workflow,
        'namespace': pass_namespace,
    }


def parse_output(output_lines) -> dict:
    lines = output_lines.decode("utf-8").split('\n')
    d = dict(map(str.strip, s.split(':')) for s in lines[:4])
    return d


def call_argo() -> str:
    result = subprocess.check_output(ARGO_CMDLINE)
    ARGO_CMDLINE.clear()
    ARGO_CMDLINE.append(ARGO)
    return result


@application.route('/', methods=['GET'])
def get_root():
    """Root Endpoint."""

    return jsonify(
        status="Success",
        message="Up and Running"
    ), 200


@application.route('/submit', methods=['POST'])
def post_submit():
    """Submit Endpoint."""

    input_data = request.get_json(force=True)

    ARGO_CMDLINE.append('submit')

    for k, v in input_data.items():
        func = SWITCHER.get(k, pass_parameter)
        func(k, v)

    output = call_argo()
    submit_dict = parse_output(output)

    return jsonify(submit_dict), 200


@application.route('/get', methods=['POST'])
def post_get():
    """Submit Endpoint."""

    input_data = request.get_json(force=True)

    ARGO_CMDLINE.append('get')

    pass_workflow_name(input_data.get('workflow_name'))

    output = call_argo()
    get_dict = parse_output(output)

    return jsonify(get_dict), 200


if __name__ == '__main__':
    # pylama:ignore=C0103
    port = os.environ.get("PORT", 8003)
    application.run(port=int(port))
