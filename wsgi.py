import os
import logging

from flask import Flask, jsonify, request
from flask.logging import default_handler
import subprocess
import json

from io import BytesIO
import multipart as mp
import yaml
import tempfile


# Set up logging
ROOT_LOGGER = logging.getLogger()
ROOT_LOGGER.addHandler(default_handler)


application = Flask(__name__)  # noqa

# Set up logging level
ROOT_LOGGER.setLevel(application.logger.level)

ARGO = '/usr/local/bin/argo'
ARGO_CMDLINE = [ARGO]


def pass_entity(_k, v):
    ARGO_CMDLINE.append(v)


def pass_namespace(_k, v):
    ARGO_CMDLINE.extend(['-n', v])


def pass_parameter(k, v):
    ARGO_CMDLINE.extend(['-p', f'{k}={v}'])


PARAM_METHODS = {
        'workflow_yaml': pass_entity,
        'workflow': pass_entity,
        'workflow_name': pass_entity,
        'namespace': pass_namespace,
    }


def parse_output(output_lines) -> dict:
    lines = output_lines.strip().decode("utf-8").split('\n')
    d = dict(map(str.strip, s.split(':', 1)) for s in lines[:6])
    return d


def call_argo() -> ():
    error = 0
    local_argo_cmdline = ARGO_CMDLINE.copy()
    ARGO_CMDLINE.clear()
    ARGO_CMDLINE.append(ARGO)
    try:
        result = subprocess.check_output(local_argo_cmdline, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        result = e.output.decode().strip("\n")
        error = 1
    return result, error


def outputs_and_artifacts(pods_output, node) -> dict:
    outputs = pods_output['status']['nodes'][node].get('outputs', {})
    phase = pods_output['status']['nodes'][node].get('phase', 'No info available')
    message = pods_output['status']['nodes'][node].get('message', 'No info available')

    per_pod_output_info = {
        'phase': phase,
        'message': message
    }

    artifacts = outputs.get('artifacts')

    if artifacts:
        for i, artifact in enumerate(artifacts):
            # For now we assume that artifacts are of the type s3
            s3info = artifact.get('s3', {})
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


def argo_command(cmd, input_data_with_params, options=['-o', 'json']) -> dict:
    ARGO_CMDLINE.append(cmd)

    for k, v in input_data_with_params.items():
        func = PARAM_METHODS.get(k, pass_parameter)
        func(k, v)

    ARGO_CMDLINE.extend(options)

    ROOT_LOGGER.info("Argo command line: %s", ARGO_CMDLINE)

    output, error = call_argo()

    try:
        if 'workflow_yaml' in input_data_with_params:
            os.remove(input_data_with_params['workflow_yaml'])
    except (TypeError, IOError) as e:
        # simply log the exception in this case
        # do not return an error since this is not a critical error
        error_msg = "Error while deleting the temporary file: " + str(e)
        ROOT_LOGGER.exception("Exception: %s", error_msg)

    if error:
        ROOT_LOGGER.exception("Argo command line error: %s", output)
        return {'Error': output}

    ROOT_LOGGER.info("Argo command line executed successfully")

    if options:
        cmd_dict = json.loads(output.decode("utf-8"))
    else:
        cmd_dict = parse_output(output)

    return cmd_dict


def argo_get(input_data) -> dict:
    get_workflow = {
        'workflow_name': input_data.get('workflow_name'),
        'namespace': input_data.get('namespace')
    }
    get_dict = argo_command('get', get_workflow)

    return get_dict


def argo_watch(input_data) -> dict:
    watch_workflow = {
        'workflow_name': input_data.get('workflow_name'),
        'namespace': input_data.get('namespace')
    }
    watch_dict = argo_command('watch', watch_workflow, [])

    return watch_dict


def argo_version() -> dict:
    version_dict = argo_command('version', {}, [])

    return version_dict


def format_pod_info_response(pods_output) -> dict:
    response_json = {
        "Info": pods_output['metadata'],
        "Per_Step_Output": {},
    }

    nodes = pods_output['status']['nodes']

    for node in nodes:
        pod_name = pods_output['status']['nodes'][node].get('name', '')
        response_json['Per_Step_Output'][pod_name] = outputs_and_artifacts(pods_output, node)

    return response_json


def resolve_multipart(data) -> dict:
    boundary = data.decode().split("\r")[0][2:]
    multipart_parser = mp.MultipartParser(BytesIO(data), boundary)

    blob = multipart_parser.parts()[0].value
    temp_file_name = tempfile.NamedTemporaryFile(delete=False).name
    f = open(temp_file_name, "wb")
    f.write(blob.encode("latin-1"))
    f.close()

    parameters = multipart_parser.parts()[1].value
    parameters_json = yaml.load(parameters, Loader=yaml.SafeLoader)
    parameters_json['workflow_yaml'] = temp_file_name

    return parameters_json


def analyze_request() -> dict:
    if request.headers['Content-Type'].startswith('multipart/mixed'):
        input_data = resolve_multipart(request.data)
    else:
        input_data = request.get_json(force=True)

    return input_data


@application.route('/', methods=['GET'])
def get_root():
    """Root Endpoint."""

    version_dict = argo_version()
    if version_dict.get('Error'):
        return jsonify(version_dict), 500

    return jsonify(
        status="Success",
        message="Up and Running"
    ), 200


@application.route('/submit', methods=['POST'])
def post_submit():
    """Submit Endpoint."""

    input_data = analyze_request()

    submit_dict = argo_command('submit', input_data)
    if submit_dict.get('Error'):
        return jsonify(submit_dict), 500

    return jsonify(submit_dict['metadata']), 200


@application.route('/e2e', methods=['POST'])
def post_e2e():
    """E2E Endpoint."""

    input_data = analyze_request()

    submit_dict = argo_command('submit', input_data)
    if submit_dict.get('Error'):
        return jsonify(submit_dict), 500

    input_data['workflow_name'] = submit_dict['metadata']['name']
    input_data['namespace'] = submit_dict['metadata']['namespace']
    watch_output = argo_watch(input_data)
    if watch_output.get('Error'):
        error_message = f"Workflow {input_data['workflow_name']} submitted OK, output/artifacts info cannot be produced"
        watch_output['message'] = error_message
        return jsonify(watch_output), 500

    pods_output = argo_get(input_data)
    if pods_output.get('Error'):
        error_message = f"Workflow {input_data['workflow_name']} submitted OK, output/artifacts info cannot be produced"
        pods_output['message'] = error_message
        return jsonify(pods_output), 500

    response_json = format_pod_info_response(pods_output)
    return jsonify({"workflow_response": response_json}), 200


@application.route('/get', methods=['POST'])
def post_get():
    """Get Endpoint."""

    input_data = request.get_json(force=True)

    pods_output = argo_get(input_data)
    if pods_output.get('Error'):
        return jsonify(pods_output), 500

    response_json = format_pod_info_response(pods_output)
    return jsonify({"workflow_response": response_json}), 200


if __name__ == '__main__':
    # pylama:ignore=C0103
    port = os.environ.get("PORT", 8003)
    application.run(port=int(port))
