import os
import logging

from flask import Flask, jsonify, request
from flask.logging import default_handler
import subprocess
import json


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
    ARGO_CMDLINE.extend(['-n', v])


def pass_parameter(k, v):
    ARGO_CMDLINE.extend(['-p', f'{k}={v}'])


def workflow_info_json(workflow_name):
    ARGO_CMDLINE.extend(['get', workflow_name, '-o', 'json'])


SWITCHER = {
        'workflow': pass_workflow,
        'namespace': pass_namespace,
    }


def parse_output(output_lines) -> dict:
    lines = output_lines.decode("utf-8").split('\n')
    d = dict(map(str.strip, s.split(':', 1)) for s in lines[:5])
    return d


def call_argo() -> str:
    result = subprocess.check_output(ARGO_CMDLINE)
    ARGO_CMDLINE.clear()
    ARGO_CMDLINE.append(ARGO)
    return result


def outputs_and_artifacts(pod_info_json, node) -> dict:
    outputs = pod_info_json['status']['nodes'][node].get('outputs', {})
    phase = pod_info_json['status']['nodes'][node].get('phase', 'No info available')
    message = pod_info_json['status']['nodes'][node].get('message', 'No info available')

    per_pod_output_info = {
        'phase': phase,
        'message': message
    }

    artifacts = outputs.get('artifacts')

    if artifacts:
        for i, artifact in enumerate(artifacts):
            s3info = artifact.get('s3', {}) # For now we assume that artifacts are of the type s3
            per_pod_output_info['outputs'] = {
                'artifact_type': 'S3',
                'bucket': s3info.get('bucket', ''),
                'endpoint-url': s3info.get('endpoint', ''),
                'key': s3info.get('key', '')
            }
    else:
        outputs['artifact_type'] = 'No artifacts info available'
        per_pod_output_info['outputs'] = outputs

    return per_pod_output_info


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


@application.route('/e2e', methods=['POST'])
def post_e2e():
    """E2E Endpoint."""

    input_data = request.get_json(force=True)

    ARGO_CMDLINE.append('submit')

    for k, v in input_data.items():
        func = SWITCHER.get(k, pass_parameter)
        func(k, v)

    submit_output = call_argo()
    submit_dict = parse_output(submit_output)

    workflow_name = submit_dict['Name']

    ARGO_CMDLINE.extend(['watch', workflow_name])
    _watch_output = call_argo()

    workflow_info_json(workflow_name)
    pod_info = call_argo().decode("utf-8")
    pod_info_json = json.loads(pod_info)

    response_json = {
        "Completed": pod_info_json['metadata']['labels']['workflows.argoproj.io/completed'],
        "Phase": pod_info_json['status'].get('phase'),
        "Message": pod_info_json['status'].get('message', 'No Errors'),
        "Per_Step_Output": {},
    }

    nodes = pod_info_json['status']['nodes']

    for node in nodes:
        pod_name = pod_info_json['status']['nodes'][node].get('name', '')
        response_json['Per_Step_Output'][pod_name] = outputs_and_artifacts(pod_info_json, node)

    return jsonify({"workflow_response": response_json}), 200


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
