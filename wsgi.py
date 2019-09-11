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


def pass_workflow_name(_k, v):
    ARGO_CMDLINE.append(v)


def pass_namespace(_k, v):
    ARGO_CMDLINE.extend(['-n', v])


def pass_parameter(k, v):
    ARGO_CMDLINE.extend(['-p', f'{k}={v}'])


SWITCHER = {
        'workflow': pass_workflow,
        'namespace': pass_namespace,
        'workflow_name': pass_workflow_name,
    }


def parse_output(output_lines) -> dict:
    lines = output_lines.strip().decode("utf-8").split('\n')
    d = dict(map(str.strip, s.split(':', 1)) for s in lines[:6])
    return d


def call_argo() -> ():
    error = 0
    try:
        result = subprocess.check_output(ARGO_CMDLINE, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        result = e.output.decode().strip("\n")
        error = 1
    ARGO_CMDLINE.clear()
    ARGO_CMDLINE.append(ARGO)
    return result, error


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


def argo_command(cmd, input_data_with_params, options=[], parse=True) -> dict:
    ARGO_CMDLINE.append(cmd)

    for k, v in input_data_with_params.items():
        func = SWITCHER.get(k, pass_parameter)
        func(k, v)

    ARGO_CMDLINE.extend(options)

    ROOT_LOGGER.info("Argo command line: %s", ARGO_CMDLINE)

    output, error = call_argo()

    if error:
        ROOT_LOGGER.exception("Argo command line error: %s", output)
        return {'Error': output}

    ROOT_LOGGER.info("Argo command line successfully executed")

    if parse:
        cmd_dict = parse_output(output)
    else:
        cmd_dict = json.loads(output.decode("utf-8"))

    return cmd_dict


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

    submit_dict = argo_command('submit', input_data)

    if submit_dict.get('Error'):
        return jsonify(submit_dict), 500

    return jsonify(submit_dict), 200


@application.route('/e2e', methods=['POST'])
def post_e2e():
    """E2E Endpoint."""

    input_data = request.get_json(force=True)

    submit_dict = argo_command('submit', input_data)

    if submit_dict.get('Error'):
        return jsonify(submit_dict), 500

    watch_on = {
        'workflow_name': submit_dict['Name'],
        'namespace': submit_dict['Namespace']
    }

    watch_output = argo_command('watch', watch_on)

    if watch_output.get('Error'):
        return jsonify(watch_output), 500

    pod_info_json = argo_command('get', watch_on, ['-o', 'json'], False)

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

    get_workflow = {
        'workflow_name': input_data.get('workflow_name'),
        'namespace': input_data.get('namespace')
    }

    get_dict = argo_command('get', get_workflow)

    return jsonify(get_dict), 200


if __name__ == '__main__':
    # pylama:ignore=C0103
    port = os.environ.get("PORT", 8003)
    application.run(port=int(port))
