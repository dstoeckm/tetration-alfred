from flask import request, Flask, jsonify, abort, make_response
import json
import os
from alfred_utils import email

# Define the path of python3 and tetration_alfred.py
python_executable = '/usr/bin/python3.6'
alfred_working_dir = '/tetration-alfred/'
process_executable = 'tetration_alfred.py'
log_file = 'tetration_alfred.log'


# Define a function to alter alfred service
def alfred_alter_service(directive):

    if directive == 'start':
        os.chdir(alfred_working_dir)
        os.system('nohup ' + python_executable + ' ' + process_executable + '>' + log_file + '&')
    elif directive == 'stop':
        os.chdir(alfred_working_dir)
        os.system("ps aux | grep tetration_alfred.py | grep -v grep | awk '{print $1}' | xargs kill -9")
    elif directive == 'restart':
        os.chdir(alfred_working_dir)
        alfred_alter_service('stop')
        alfred_alter_service('start')
    else:
        print('Unsupported')
        exit(1)

# Define a function that check remote endpoints reachability
def check_restapi_reachability(target):

    # Importing current config
    alfred_config = json.load(open('alfred_configuration.json'))
    apic_config = json.load(open('apic_data.json'))

    # Parse alfred config to fetch tetration host to probe
    tetration_host = str(alfred_config['API_ENDPOINT']).split('/')[2]
    # Parse apic_data.json to fetch APIC to probe
    apic_host = str(apic_config['apic_ip']).split('/')[2]

    if target == 'tetration':
        host_is_up = True if os.system("ping -c 1 " + tetration_host) is 0 else False
        return host_is_up

    elif target == 'aci':
        host_is_up = True if os.system("ping -c 1 " + apic_host) is 0 else False
        return host_is_up


# Define Flask app name
alfred_api = Flask(__name__)


# Return a message in case apic_data.json is not found
@alfred_api.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'config_files': 'Not found'}), 404)

###### REST API GET Section ######

# REST API - GET current APIC configuration
@alfred_api.route('/api/v1/apic', methods=['GET'])
def get_apic_cfg():
    try:
        alfred_config = json.load(open('alfred_configuration.json'))
        apic_config = json.load(open('apic_data.json'))

        apic_config_full = {
            "aci_annotations_enabled": alfred_config['aci_annotations_enabled'],
            "apic_ip": apic_config["apic_ip"],
            "apic_port": apic_config["apic_port"],
            "apic_user": apic_config["apic_user"],
            "apic_password": apic_config["apic_password"]
        }
    except Exception:
        print("Couldn't load the configuration files")
        abort(404)
    return jsonify(apic_config_full)

# REST API - GET current Kafka broker configuration
@alfred_api.route('/api/v1/broker', methods=['GET'])
def get_broker_cfg():
    try:
        with open('brokers_list.txt', 'r') as f1:
            brokers_string = f1.read()
            brokers_split = brokers_string.split(":")
            brokers_list_dict = {
                "broker_ip": brokers_split[0],
                "broker_port": brokers_split[1]
            }

        with open('alfred_configuration.json','r') as f2:
            alfred_config = json.load(open('alfred_configuration.json'))
            brokers_list_dict['topic'] = alfred_config['topic']

    except Exception:
        print("Couldn't load brokers list file")
        abort(404)

    return jsonify(brokers_list_dict)

# REST API - GET current Tetration configuration
# This WILL NOT include the API/SECRET keys
@alfred_api.route('/api/v1/tetration', methods=['GET'])
def get_tetration_cfg():
    try:
        alfred_config = json.load(open('alfred_configuration.json'))
        tetration_config = {
            "API_ENDPOINT": alfred_config["API_ENDPOINT"],
            "VRF": alfred_config["VRF"],
            "app_scope": alfred_config["app_scope"]
        }
    except Exception:
        print("Couldn't load configuration file")
        abort(404)
    return jsonify(tetration_config)

# REST API - GET current Mailer configuration
@alfred_api.route('/api/v1/mailer', methods=['GET'])
def get_mailer_cfg():
    try:
        alfred_config = json.load(open('alfred_configuration.json'))
        mailer_config = {
            "mail_server_enabled": alfred_config['mail_server_enabled'],
            "mail_server_address": alfred_config["mail_server_address"],
            "mail_server_proto": alfred_config["mail_server_proto"],
            "mail_server_auth": alfred_config["mail_server_auth"],
            "mail_server_user": alfred_config["mail_server_user"],
            "mail_server_password": alfred_config["mail_server_password"],
            "mail_server_sender": alfred_config["mail_server_sender"],
            "mail_server_recipient": alfred_config["mail_server_recipient"]
        }
    except Exception:
        print("Couldn't load configuration file")
        abort(404)
    return jsonify(mailer_config)

# REST API - GET service status
@alfred_api.route('/api/v1/service', methods=['GET'])
def get_service():
    process_status = {
        "alfred_status": "unknown"
    }
    try:
        process_name = 'tetration_alfred.py'
        process_list = os.popen("ps aux").read()
        if process_name not in process_list[:]:
            process_status['alfred_status'] = 'dead'
        else:
            process_status['alfred_status'] = 'alive'
    except Exception:
        abort(404)
    return jsonify(process_status)

# REST API - GET remote system status
@alfred_api.route('/api/v1/endpoints', methods=['GET'])
def get_endpoints():
    endpoints = {
        "tetration_status": "unknown",
        "apic_status": "unknown"
    }
    if check_restapi_reachability('tetration'):
        endpoints['tetration_status'] = 'reachable'
    else:
        endpoints['tetration_status'] = 'down'

    if check_restapi_reachability('aci'):
        endpoints['apic_status'] = 'reachable'
    else:
        endpoints['apic_status'] = 'down'

    return jsonify(endpoints)

# REST API - GET Alfred logs
@alfred_api.route('/api/v1/alfred-logs', methods=['GET'])
def get_alfred_logs():
    def generate():
        with open('logs/alfred.log') as f:
            yield f.read()
    return alfred_api.response_class(generate(), mimetype='text/plain')

# REST API - GET Kafka logs
@alfred_api.route('/api/v1/kafka-logs', methods=['GET'])
def get_kafka_logs():
    def generate():
        with open('logs/kafka.log') as f:
            yield f.read()
    return alfred_api.response_class(generate(), mimetype='text/plain')

# REST API - GET ACI Annotations logs
@alfred_api.route('/api/v1/aci-annotations-logs', methods=['GET'])
def get_aci_annotations_logs():
    def generate():
        with open('logs/aci-annotations.log') as f:
            yield f.read()
    return alfred_api.response_class(generate(), mimetype='text/plain')



###### REST API POST Section ######

# REST API - POST APIC configuration
@alfred_api.route('/api/v1/apic', methods=['POST'])
def create_apic_cfg():
    if not request.json or not 'apic_ip' in request.json:
        abort(400)

    alfred_config = json.load(open('alfred_configuration.json'))

    # Fill the dict with POST payload
    apic_config = {
        "apic_ip": request.json["apic_ip"],
        "apic_port": request.json["apic_port"],
        "apic_user": request.json["apic_user"],
        "apic_password": request.json["apic_password"]
    }

    with open('apic_data.json', 'w') as f1:
        json.dump(apic_config, f1, indent=4, sort_keys=True)

    with open('alfred_configuration.json', 'w') as f2:
        alfred_config['aci_annotations_enabled'] = request.json['aci_annotations_enabled']
        json.dump(alfred_config, f2, indent=4, sort_keys=True)

    return_json = {**apic_config, **alfred_config}
    return jsonify(return_json), 201

# REST API - POST Kafka broker configuration
@alfred_api.route('/api/v1/broker', methods=['POST'])
def create_broker_cfg():
    if not request.json or not 'broker_ip' in request.json:
        abort(400)

    # Load current Alfred config
    alfred_config = json.load(open('alfred_configuration.json'))

    # Fill the dict with POST payload
    broker_config = {
        "broker_ip": request.json["broker_ip"],
        "broker_port": request.json["broker_port"]
    }

    with open('brokers_list.txt', 'w') as f1:
        f1.write(broker_config["broker_ip"] + ":" + broker_config["broker_port"])

    with open('alfred_configuration.json', 'w') as f2:
        # Replace values in Alfred config
        alfred_config['topic'] = request.json['topic']
        json.dump(alfred_config, f2, indent=4, sort_keys=True)
        # Merge config into a single JSON to be sent as response
        broker_config_final = broker_config
        broker_config_final['topic'] = alfred_config['topic']

    return jsonify(broker_config_final), 201

# REST API - POST Tetration configuration
@alfred_api.route('/api/v1/tetration', methods=['POST'])
def create_tetration_cfg():
    if not request.json or not 'API_ENDPOINT' in request.json:
        abort(400)

    # Load current Alfred config and credentials file
    alfred_config = json.load(open('alfred_configuration.json'))
    tetration_credentials = json.load(open('tetration_credentials.json'))

    # Fill the dict with POST payload
    tetration_config = {
        "API_ENDPOINT": request.json["API_ENDPOINT"],
        "VRF": request.json["VRF"],
        "app_scope": request.json["app_scope"],
        "api_key": request.json["api_key"],
        "api_secret": request.json["api_secret"]
    }

    with open('alfred_configuration.json', 'w') as f1:
        # Write POST payload in global alfred config
        alfred_config['API_ENDPOINT'] = tetration_config['API_ENDPOINT']
        alfred_config['VRF'] = tetration_config['VRF']
        alfred_config['app_scope'] = tetration_config['app_scope']
        json.dump(alfred_config, f1, indent=4, sort_keys=True)

    with open('tetration_credentials.json', 'w') as f2:
        # Write POST credentials payload in credential file for TA
        tetration_credentials['api_key'] = tetration_config['api_key']
        tetration_credentials['api_secret'] = tetration_config['api_secret']
        json.dump(tetration_credentials, f2, indent=4, sort_keys=True)

    return jsonify(tetration_config), 201

# REST API - POST service start/stop/restart
@alfred_api.route('/api/v1/service', methods=['POST'])
def alter_service():

    if not request.json or not 'alter_service' in request.json:
        abort(400)

    service_altered = {
        "alfred_service": "unknown"
    }

    if request.json['alter_service'] == 'start':
        try:
            alfred_alter_service('start')
            service_altered['alfred_service'] = 'started'
        except Exception:
            abort(400)

    elif request.json['alter_service'] == 'stop':
        try:
            alfred_alter_service('stop')
            service_altered['alfred_service'] = 'stopped'
        except Exception:
            abort(400)

    elif request.json['alter_service'] == 'restart':
        try:
            alfred_alter_service('restart')
            service_altered['alfred_service'] = 'restarted'
        except Exception:
            abort(400)


    return jsonify(service_altered)

# REST API - POST Mailer configuration
@alfred_api.route('/api/v1/mailer', methods=['POST'])
def create_mailer_cfg():
    if not request.json or not 'mail_server_address' in request.json:
        abort(400)

    # Load current Alfred config
    alfred_config = json.load(open('alfred_configuration.json'))

    # Fill the dict with POST payload
    mailer_config = {
        "mail_server_address": request.json["mail_server_address"],
        "mail_server_proto": request.json["mail_server_proto"],
        "mail_server_auth": request.json["mail_server_auth"],
        "mail_server_user": request.json["mail_server_user"],
        "mail_server_password": request.json["mail_server_password"],
        "mail_server_sender": request.json["mail_server_sender"],
        "mail_server_recipient": request.json["mail_server_recipient"],
        "mail_server_enabled": request.json["mail_server_enabled"],
    }

    with open('alfred_configuration.json', 'w') as f1:
        # Replace values in Alfred config
        alfred_config['mail_server_address'] = mailer_config['mail_server_address']
        alfred_config['mail_server_proto'] = mailer_config['mail_server_proto']
        alfred_config['mail_server_auth'] = mailer_config['mail_server_auth']
        alfred_config['mail_server_user'] = mailer_config['mail_server_user']
        alfred_config['mail_server_password'] = mailer_config['mail_server_password']
        alfred_config['mail_server_sender'] = mailer_config['mail_server_sender']
        alfred_config['mail_server_recipient'] = mailer_config['mail_server_recipient']
        alfred_config['mail_server_enabled'] = mailer_config['mail_server_enabled']
        json.dump(alfred_config, f1, indent=4, sort_keys=True)

    return jsonify(mailer_config), 201

# REST API - POST Send Test Email
@alfred_api.route('/api/v1/mailtest', methods=['POST'])
def create_mail_test():
    if not request.json or not 'mail_body' in request.json:
        abort(400)

    email_subject = request.json['email_sub']
    email_body = request.json['email_body']
    email(email_subject,email_body)
    return jsonify(request.json), 201


if __name__ == '__main__':
    alfred_api.run(host='0.0.0.0', debug=True)