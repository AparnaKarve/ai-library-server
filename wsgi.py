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

from kubernetes_configuration import kubernetes_api_instance, NAMESPACE


# Set up logging
ROOT_LOGGER = logging.getLogger()
ROOT_LOGGER.addHandler(default_handler)


application = Flask(__name__)  # noqa

# Set up logging level
ROOT_LOGGER.setLevel(logging.INFO)

ARGO = 'argo'

GROUP = "argoproj.io"
VERSION = "v1alpha1"
PLURAL = "workflows"
KIND = "Workflow"

TRAINING = 'training'


def pass_entity(_k, v, cmd_line):
    cmd_line.append(v)


def pass_namespace(_k, v, cmd_line):
    cmd_line.extend(['-n', v])


def pass_parameter(k, v, cmd_line):
    cmd_line.extend(['-p', f'{k}={v}'])


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


def call_argo(argo_cmd_line) -> ():
    error = 0

    try:
        result = subprocess.check_output(argo_cmd_line, stderr=subprocess.STDOUT)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        if hasattr(e, 'output'):
            result = e.output.decode().strip()
        else:
            result = e.strerror
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
    argo_cmd_line = []
    argo_cmd_line.extend([ARGO, cmd])

    for k, v in input_data_with_params.items():
        func = PARAM_METHODS.get(k, pass_parameter)
        func(k, v, argo_cmd_line)

    argo_cmd_line.extend(options)

    ROOT_LOGGER.info("Argo command line: %s", argo_cmd_line)

    output, error = call_argo(argo_cmd_line)

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
        'workflow_name': input_data.get('workflow_name')
    }

    if 'namespace' in input_data:
        get_workflow['namespace'] = input_data['namespace']

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


def validate_workflow(workflow_yaml, type) -> bool:
    with open(workflow_yaml) as yaml_file:
        workflow = yaml.full_load(yaml_file)
        if workflow['metadata'].get('labels', {}).get('jobType', '') == type:
            return True
    return False


def e2e(input_data) -> dict:
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


@application.route('/status', methods=['GET'])
def get_root():
    """Status Endpoint."""

    version_dict = argo_version()
    if version_dict.get('Error'):
        return jsonify(version_dict), 500

    return jsonify(
        status="Success",
        message="Up and Running"
    ), 200


@application.route('/training-jobs', methods=['POST'])
def post_training_jobs():
    """POST Training Jobs Endpoint."""

    input_data = analyze_request()

    if not validate_workflow(input_data['workflow_yaml'], TRAINING):
        return jsonify({'Error': 'Workflow type is not TRAINING'}), 500

    submit_dict = argo_command('submit', input_data)
    if submit_dict.get('Error'):
        return jsonify(submit_dict), 500

    if str(input_data.get('quick-submit', False)).lower() in ['true', 'y']:
        return jsonify(submit_dict['metadata']), 200
    else:
        input_data['workflow_name'] = submit_dict['metadata']['name']
        input_data['namespace'] = submit_dict['metadata']['namespace']
        return e2e(input_data)


@application.route('/training-jobs/<workflow_name>', methods=['GET'])
def get_training_jobs_id_info(workflow_name):
    """GET Individual Training Jobs Endpoint."""

    input_data = {}

    if request.json:
        input_data = request.get_json(force=True)

    input_data['workflow_name'] = workflow_name

    pods_output = argo_get(input_data)
    if pods_output.get('Error'):
        return jsonify(pods_output), 500

    response_json = format_pod_info_response(pods_output)
    return jsonify({"workflow_response": response_json}), 200


@application.route('/training-jobs', methods=['GET'])
def get_training_jobs():
    """GET Training Jobs Endpoint."""

    namespace = NAMESPACE

    if request.json:
        input_data = request.get_json(force=True)
        namespace = input_data.get('namespace', NAMESPACE)

    api_instance = kubernetes_api_instance()

    api_response = api_instance.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=namespace,
        plural=PLURAL,
        pretty=True,
        label_selector=f"jobType={TRAINING}")

    response_json = {}

    for i in api_response['items']:
        response_json[i['metadata']['name']] = format_pod_info_response(i)

    return jsonify({"training_jobs_response": response_json}), 200


if __name__ == '__main__':
    # pylama:ignore=C0103
    port = os.environ.get("PORT", 8080)
    application.run(port=int(port))
