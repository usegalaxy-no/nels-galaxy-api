#!/usr/bin/env python3
# Based on:
# https://github.com/pika/pika/blob/master/examples/basic_consumer_threaded.py
# 
# 
# Kim Brugger (03 Apr 2019), contact: kim@brugger.dk

import sys
import pprint
pp = pprint.PrettyPrinter(indent=4)
import json
import argparse
import re
import tempfile
import time
import requests
import traceback
import certifi


from bioblend.galaxy import GalaxyInstance


sys.path.append(".")

import kbr.mq_utils as mq_utils
import kbr.run_utils as run_utils
import kbr.config_utils as config_utils
import kbr.version_utils as version_utils
import kbr.log_utils as logger

import nels_galaxy_api.api_requests as api_requests


version = version_utils.as_string()

master_url = None
nels_url   = None
instances  = None
mq = mq_utils.Mq()

master_api = None
tmp_dir = "/tmp/"
nels_storage_client_key = None
nels_storage_client_secret = None
nels_storage_url = None
sleep_time = 5



def init( config_file) -> {}:
    config = config_utils.readin_config_file(config_file)
    logger.info("init from config ")

    # set incoming and proxy keys
    api_requests.set_token(config.get('proxy_key', None))

    global master_url, nels_url, instances, master_api, tmp_dir, sleep_time
    master_url = config['master_url'].rstrip("/")
    nels_url = config['nels_url'].rstrip("/")
    instances = {}
    master_api = api_requests.ApiRequests(master_url, config['key'])


    global nels_storage_client_key, nels_storage_client_secret, nels_storage_url, sleep_time
    nels_storage_client_key = config['nels_storage_client_key']
    nels_storage_client_secret = config['nels_storage_client_secret']
    nels_storage_url = config['nels_storage_url'].rstrip("/")

    tmp_dir = config.get('tmp_dir', tmp_dir)
    sleep_time = config.get('sleep_time', sleep_time)


    tmp_instances = config['instances']

    for iid in tmp_instances:

        if 'active' not in tmp_instances[iid] or not tmp_instances[iid]['active']:
            continue

        instances[iid] = tmp_instances[iid]
        instance = tmp_instances[iid]
        instance['api'] = api_requests.ApiRequests(instance['nga_url'].rstrip("/"), instance['nga_key'])

        instances[instance['name']] = instance



    return config


def submit_mq_job(tracker_id:int, type:str ) -> None:

    payload = {'tracker_id': tracker_id, 'type': type}

    if mq is None:
        logger.error('MQ not configured, cannot send message')
        return

    mq.publish(body=json.dumps(payload))


def run_cmd(cmd:str, name:str=None, verbose:bool=False):

    logger.debug(f"run-cmd: {cmd}")

    exec_info = run_utils.launch_cmd(cmd)

    logger.debug("exit code: %s" % exec_info.p_status)
    logger.debug("std out: %s" % exec_info.stdout)
    logger.debug("std error: %s" % exec_info.stderr)

    return exec_info.p_status


def run_history_export( tracker ):

    logger.info(f'{tracker["id"]}: history export start')

    instance = tracker['instance']
    print( instance )
    try:
        info = instances[instance]['api'].get_info()
        if info['free_gb'] < 30:
            # Not enough free disk space to do this, alert sysadmin
            logger.error("Not enough free space for export, email admin.")
            master_api.update_export(tracker['id'], {'state': 'disk-space-error'})
            return
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        logger.error( f"{tracker['id']}: Fetch info error {e}")

    try:
        galaxy_instance = GalaxyInstance(instances[instance]['url'], key=instances[instance]['api_key'], verify=certifi.where())
    except Exception as e :
        logger.error(f"{tracker['id']}: Trigger export through bioblend: {e}")
        master_api.update_export(tracker['id'], {'state': 'bioblend-error'})
        return

    while True:
        try:
            export_id = galaxy_instance.histories.export_history(tracker['history_id'], maxwait=1, gzip=True)
        except Exception as e:
            logger.error(f"{tracker['id']}/{tracker['instance']}: bioblend trigger export {e}")
            master_api.update_export(tracker['id'], {'state': 'bioblend-error', 'log': e['err_msg']})
            return


        if export_id is None or export_id == '':
            history = instances[instance]['api'].get_history_export(history_id=tracker['history_id'])

            if history is not None and history != '':
                master_api.update_export(tracker['id'], {"export_id": history['export_id'], 'state': 'new'})
            else:
                logger.error(f"{tracker['id']}: No history id associated with {export_id}")
        else:
#            print( f" API :: {instance['api']}" )
            export = instances[instance]['api'].get_history_export(export_id=export_id)
            master_api.update_export(tracker['id'], {"export_id": export_id, 'state': export['state']})

            if export['state'] in ['ok', 'error']:
                submit_mq_job(tracker['id'], 'export')
                logger.info(f'{tracker["id"]}: history export done')

                return

            break

        time.sleep( sleep_time )

def run_fetch_export(tracker):

    logger.info(f'{tracker["id"]}: fetch export start')

    export_id = tracker['export_id']
    tracker_id = tracker['id']
    instance = tracker['instance']

    outfile = "{}/{}.tgz".format(tempfile.mkdtemp(dir=tmp_dir), export_id)
    master_api.update_export(tracker_id, {'tmpfile': outfile, 'state': 'fetch-running'})

    try:

        cmd = f"curl -H 'Authorization: bearer {instances[instance]['nga_key']}' -Lo {outfile} {instances[instance]['nga_url']}/history/download/{export_id}/"
        logger.debug(f'{tracker["id"]}: fetch-cmd: {cmd}')
        run_cmd(cmd)
        logger.debug('{tracker["id"]}: fetch cmd done')
        submit_mq_job(tracker_id, "export")
        master_api.update_export(tracker_id, {'tmpfile': outfile, 'state': 'fetch-ok'})

    except Exception as e:
        master_api.update_export(tracker_id, {'tmpfile': outfile, 'state': 'fetch-error', 'log': str(e)})
        logger.error(f"{tracker['id']} fetch error: {e}")

    logger.info(f'{tracker["id"]}: fetch export done')

    return


def run_push_export( tracker ):

    tracker_id = tracker['id']
    logger.info(f'{tracker_id}: push export start')

    try:

        instance = tracker['instance']

        master_api.update_export(tracker_id, {'state': 'nels-transfer-running'})

        history = instances[instance]['api'].get_history_export(export_id=tracker['export_id'])
        logger.debug( f"{tracker_id} history: {history}")
        create_time = str(tracker['create_time']).replace("-", "").replace(":", "").replace(" ", "_")
#        logger.debug( f'{tracker_id} Create time {create_time}')
        create_time = re.sub(r'\.\d+', '', create_time)
#        logger.debug( f'{tracker_id} Create time {create_time}')
        history['name'] = history['name'].replace(" ", "_")
        dest_file = f"{tracker['destination']}/{history['name']}-{create_time}.tgz"
        logger.debug(f"{tracker_id} dest file: {dest_file}")

        ssh_info = get_ssh_credential(tracker['nels_id'])
        logger.debug(f"{tracker_id} ssh info {ssh_info}")

        cmd = f'scp -o StrictHostKeyChecking=no -o BatchMode=yes -i {ssh_info["key_file"]} {tracker["tmpfile"]} "{ssh_info["username"]}@{ssh_info["hostname"]}:{dest_file}"'
#        logger.debug(f"CMD: {cmd}")
        run_cmd(cmd, 'push data')
        master_api.update_export(tracker_id, {'state': 'nels-transfer-ok'})
        cmd = f"rm {tracker['tmpfile']}"
        master_api.update_export(tracker_id, {'state': 'finished'})
        logger.debug(f"CMD: {cmd}")
        run_cmd(cmd, 'cleanup')
        logger.info(f'{tracker_id}: push export done')
    except Exception as e:
        import traceback
        traceback.print_tb(e.__traceback__)

        master_api.update_export(tracker_id, {'state': 'nels-transfer-error'})
        logger.debug(f" tracker-id:{tracker['id']} transfer to NeLS error: {e}")



def get_ssh_credential(nels_id: int):
    # make sure the id is a string
    nels_id = str(nels_id)
    #    api_url = 'https://nels.bioinfo.no/'
    #    api_url = 'https://test-fe.cbu.uib.no/nels-'

    api_url = nels_storage_url + "/users/" + nels_id
#    logger.debug(f"API URL: {api_url}")
    response = requests.get(api_url, auth=(nels_storage_client_key, nels_storage_client_secret))
    if (response.status_code == requests.codes.ok):
        json_response = response.json()
        # write key to a tmp file
        tmp = tempfile.NamedTemporaryFile(mode='w+t', suffix=".txt", dir=tmp_dir, delete=False)
        tmp.write(json_response['key-rsa'])
        tmp.close()
        json_response['key_file'] = tmp.name
        return json_response
    else:
        raise Exception("HTTP response code=%s" % str(response.status_code))


def get_history_from_nels( tracker ):

    tracker_id = tracker['id']
    logger.info(f'{tracker_id}: push export start')

    try:

        master_api.update_import(tracker_id, {'state': 'nels-transfer-running'})

        outfile = "{}/{}.tgz".format(tempfile.mkdtemp(dir=tmp_dir), tracker['source'])

        ssh_info = get_ssh_credential(tracker['nels_id'])
        logger.debug(f"{tracker_id} ssh info {ssh_info}")

        cmd = f'scp -o StrictHostKeyChecking=no -o BatchMode=yes -i {ssh_info["key_file"]} "{ssh_info["username"]}@{ssh_info["hostname"]}:{tracker["source"]}" outfile'
        #        logger.debug(f"CMD: {cmd}")
        run_cmd(cmd, 'pull data')
        master_api.update_import(tracker_id, {'state': 'nels-transfer-ok'})
        submit_mq_job(tracker_id, "import")
    except Exception as e:
        import traceback
        traceback.print_tb(e.__traceback__)

        master_api.update_import(tracker_id, {'state': 'nels-transfer-error'})
        logger.debug(f" tracker-id:{tracker['id']} transfer to NeLS error: {e}")

def import_history( tracker ):

    tracker_id = tracker['id']
    logger.info(f'{tracker_id}: import started')

    try:


        user_id = tracker['user_id']
        user_api_key = db.get_api_key(user_id)
        galaxy_instance = GalaxyInstance(master_url, key=user_api_key['key'], verify=certifi.where())

        galaxy_instance.histories.import_history( tmp_file)
        master_api.update_export(tracker_id, {'state': 'history-import-triggered'})
        # track job!

        while True:

            try:
                import_id = galaxy_instance.histories.import_history( tmp_file)
            except Exception as e:
                logger.error(f"{tracker['id']}/{tracker['instance']}: bioblend trigger export {e}")
                master_api.update_export(tracker['id'], {'state': 'bioblend-error', 'log': e['err_msg']})
                return

            print( import_id )

            #
            # if import_id is None or export_id == '':
            #     history = instances[instance]['api'].get_history_export(history_id=tracker['history_id'])
            #
            #     if history is not None and history != '':
            #         master_api.update_export(tracker['id'], {"export_id": history['export_id'], 'state': 'new'})
            #     else:
            #         logger.error(f"{tracker['id']}: No history id associated with {export_id}")
            # else:
            #     #            print( f" API :: {instance['api']}" )
            #     import = instances[instance]['api'].get_history_export(export_id=export_id)
            #     master_api.update_export(tracker['id'], {"export_id": export_id, 'state': export['state']})
            #
            #     if export['state'] in ['ok', 'error']:
            #     submit_mq_job(tracker['id'])
            #     logger.info(f'{tracker["id"]}: history export done')
            #
            #     return

            break

        time.sleep( sleep_time )



        # clean up!
        cmd = f"rm {tracker['tmpfile']}"
        master_api.update_export(tracker_id, {'state': 'finished'})
        logger.debug(f"CMD: {cmd}")
        run_cmd(cmd, 'cleanup')
        logger.info(f'{tracker_id}: history import done')
    except Exception as e:
        import traceback
        traceback.print_tb(e.__traceback__)

        master_api.update_export(tracker_id, {'state': 'nels-transfer-error'})
        logger.debug(f" tracker-id:{tracker['id']} transfer to NeLS error: {e}")



def do_work(ch, method, properties, body):

    logger.debug("Callback call::: Method %s Delivery tag: %s Message body: %s\n" % ( method, properties, body))
    ch.basic_ack(delivery_tag=method.delivery_tag)


    try:
        payload = json.loads(body)
    except Exception as e:
        print( e )
        return

    if "tracker_id" not in payload and "type" not in payload:
        logger.error(f"Invalid message {payload}")
        raise Exception(f"Invalid message {payload}")
        return

    tracker_id = payload['tracker_id']
    type = payload['type']
    if type == 'export':
        tracker = master_api.get_export( tracker_id )
    elif type == 'import':
        tracker = master_api.get_import( tracker_id )
    else:
        logger.error(f"Invalid type '{type}'")
        raise Exception(f"Invalid type '{type}'")
        return


    logger.debug(f"tracker {tracker}")
    state = tracker['state']

    logger.debug(f"do_work tracker_id: {tracker_id} state: '{state}'")

    if type == 'export' and state == 'pre-queueing':
        run_history_export( tracker )
    elif type == 'export' and state == 'ok':
        run_fetch_export( tracker )
    elif type == 'export' and state == 'fetch-ok':
        run_push_export( tracker )
    elif state == 'finished':
        pass
    elif type == 'import' and state == 'pre-fetch':
        get_history_from_nels(tracker)
    elif type == 'import' and state == 'nels-transfer-ok':
        import_history( tracker )
    else:
        logger.error(f"Unknown state {state} for tracker_id: {tracker_id}")


def main():

    parser = argparse.ArgumentParser(description='consumes a mq ')

    parser.add_argument('-c', '--config', required=True, help="conductor config file ", default="conductor.yml")
    parser.add_argument('-l', '--logfile', default=None, help="Logfile to write to, default is stdout")
    parser.add_argument('-v', '--verbose', default=4, action="count", help="Increase the verbosity of logging output")

    args = parser.parse_args()

    config = init( args.config )


    if args.logfile:
        logger.init(name='nga_runner', log_file=args.logfile)
    else:
        logger.init(name='nga_runner')

    logger.set_log_level(args.verbose)
    logger.info(f'startup (v:{version})')


    api_requests.set_token( config['key'])



    global mq
    mq.connect(uri=config['mq_uri'], prefetch_count=1)

    try:
        mq.consume(route='default', callback=do_work)

    except KeyboardInterrupt:
        mq.channel.stop_consuming()

    # Wait for all to complete
 #   logger.debug('waiting for threads')
    mq.channel.close()


if __name__ == "__main__":
    main()
    
