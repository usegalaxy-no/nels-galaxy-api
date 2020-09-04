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
import functools
import threading
import re
import time

from bioblend.galaxy import GalaxyInstance


sys.path.append(".")

import kbr.mq_utils as mq_utils
import kbr.run_utils as run_utils
import kbr.config_utils as config_utils
import kbr.version_utils as version_utils
import kbr.log_utils as logger

import nels_galaxy_api.api_requests as api_requests
import nels_galaxy_api.db as db
import nels_galaxy_api.db as nels_galaxy_db


master_url = None
nels_url = None
instances  = None
version = '0.0.0'
mq = None
db = nels_galaxy_db.DB()
nels_galaxy_api = None


def init( config_file) -> {}:
    config = config_utils.readin_config_file(config_file)
    logger.info("init from config ")

    # set incoming and proxy keys
    api_requests.set_token(config.get('proxy_key', None))

    global master_url, nels_url, instances, version, db, nels_galaxy_api
    master_url = config['master_url'].rstrip("/")
    nels_url = config['nels_url'].rstrip("/")
    version = version_utils.as_string()
    instances = {}
    nels_galaxy_api = api_requests.ApiRequests(master_url, config['key'])

    galaxy_config = config_utils.readin_config_file(config['galaxy_config'])
    db.connect(galaxy_config['galaxy']['database_connection'])




#    mq = mq_utils.Mq()
#    mq.connect(uri=config['mq_uri'])


    tmp_instances = config['instances']

    for iid in tmp_instances:

        if 'active' not in tmp_instances[iid] or not tmp_instances[iid]['active']:
            continue

        instances[iid] = tmp_instances[iid]
        instance = tmp_instances[iid]

        instances[instance['name']] = instance
        instances[instance['name']]['api'] = api_requests.ApiRequests(instance['nga_url'].rstrip("/"), instance['nga_key'])



    return config


def submit_mq_job(tracker_id:int, state:str = None ) -> None:

    payload = {'tracker_id': tracker_id,
               'state': state}

    if mq is None:
        logger.error('MQ not configured, cannot send message')
        return

    mq.publish(body=json.dumps(payload))


def run_cmd(cmd:str, name:str=None, verbose:bool=False):


    logger.debug(f"{name}:")

    logger.debug(f"cmd: {cmd}")

    exec_info = run_utils.launch_cmd(cmd)

    logger.debug("exit code: %s" % exec_info.p_status)
    logger.debug("std out: %s" % exec_info.stdout)
    logger.debug("std error: %s" % exec_info.stderr)

    return exec_info.p_status


def run_history_export( tracking ):

    logger.debug('run_history_export')
    logger.debug(f'..... {tracking}')

    instance = tracking['instance']
    print( instance )
    info = instances[instance]['api'].get_info()
    print( info )
    if info['free_gb'] < 30:
        # Not enough free disk space to do this, alert sysadmin
        logger.error("Not enough free space for export, email admin.")
        nels_galaxy_api.update_export(tracking['id'], {'state': 'disk-space-error'})
        return


    try:
        galaxy_instance = GalaxyInstance(instances[instance]['url'], key=instances[instance]['api_key'])
    except Exception as e :
        logger.error(f"Trigger export through bioblend: {e}")

    logger.debug( galaxy_instance )

    while True:
        try:
            export_id = galaxy_instance.histories.export_history(tracking['history_id'], maxwait=1, gzip=True)
        except Exception as e:
            logger.error(f"bioblend trigger export {e}")
            return


        if export_id is None or export_id == '':
            history = nels_galaxy_api.get_history_export(history_id=tracking['history_id'])

            if history is not None and history != '':
                nels_galaxy_api.update_export(tracking['id'], {"export_id": history['export_id'], 'state': 'new'})
            else:
                logger.error(f"No history id associated with {export_id}")
        else:
            export = nels_galaxy_api.get_history_export(export_id=export_id)
            nels_galaxy_api.update_export(tracking['id'], {"export_id": export_id, 'state': export['state']})

            if export['state'] in ['ok', 'error']:
                submit_mq_job(tracking['id'], state=export['state'] )
                return

            break

        time.sleep( sleep_time )

def run_fetch_export(tracking):

    logger.debug('run_fetch_export')

    export_id = tracking['export_id']
    tracking_id = tracking['id']

    outfile = "{}/{}.tgz".format(tempfile.mkdtemp(dir=tmp_dir), export_id)
    nels_galaxy_api.update_export(tracking_id, {'tmpfile': outfile, 'state':'fetch-running'})

    #    token   = 'usegalaxy_secret'

    try:
        cmd = f"curl -H 'Authorization: bearer {token}' -Lo {outfile} {helper_url}/history/download/{export_id}/"
        logger.debug(f'fetch-cmd: {cmds}')
        run_cmd(cmd)
        nels_galaxy_api.update_export(tracking_id, {'tmpfile': outfile, 'state':'fetch-ok'})
        submit_mq_job(tracking_id, state=export['fetch-ok'] )

    except Exception as e:
        nels_galaxy_api.update_export(tracking_id, {'tmpfile': outfile, 'state':'fetch-error'})
        logger.debug(f" tracking['id'] fetch error: {e}")

    return


def run_push_export( tracking ):

    logger.debug('run_push_export')
    tracking_id = tracking['id']

    try:
        nels_galaxy_api.update_export(tracking_id, {'state': 'nels-transfer-running'})
        history = helper_api.get_history_export(export_id=tracking['export_id'])
        create_time = tracking['create_time'].replace("-", "").replace(":", "")
        create_time = re.sub(r'\.\d+', '', create_time)
        history['name'] = history['name'].replace(" ", "_")
        dest_file = f"{tracking['destination']}/{history['name']}-{create_time}.tgz"


        ssh_info = get_ssh_credential(tracking['nels_id'])


        cmd = f"scp -o StrictHostKeyChecking=no -o BatchMode=yes -i {ssh_info['key_file']} {tracking['tmpfile']} {ssh_info['username']}@{ssh_info['hostname']}:{dest_file}"
        logger.debug("CMD:", cmd)
        run_cmd(cmd)
        nels_galaxy_api.update_export(tracking_id, {'state': 'nels-transfer-ok'})
    except Exception as e:
        nels_galaxy_api.update_export(tracking_id, {'state':'nels-transfer-error'})
        logger.debug(f" tracking['id'] transfer to NeLS error: {e}")



def get_ssh_credential(nels_id: int):
    # make sure the id is a string
    nels_id = str(nels_id)
    #    api_url = 'https://nels.bioinfo.no/'
    #    api_url = 'https://test-fe.cbu.uib.no/nels-'

    api_url = nels_url + "storage2/users/" + nels_id
    logger.debug(f"API URL: {api_url}")
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




def ack_message(ch, delivery_tag):
    """Note that `ch` must be the same pika channel instance via which
    the message being ACKed was retrieved (AMQP protocol constraint).
    """
    if ch.is_open:
        ch.basic_ack(delivery_tag)
    else:
        # Channel is already closed, so we can't ACK this message;
        # log and/or do something that makes sense for your app in this case.
        pass


def on_message(ch, method_frame, _header_frame, body, args):
    (conn, thrds) = args
    delivery_tag = method_frame.delivery_tag
    t = threading.Thread(target=do_work, args=(conn, ch, delivery_tag, body))
    t.start()
    thrds.append(t)


def do_work(conn, ch, delivery_tag, body):
    thread_id = threading.get_ident()
    print("Thread id: %s Delivery tag: %s Message body: %s\n" % ( thread_id,
                delivery_tag, body))


    try:
        payload = json.loads(body)
    except Exception as e:
        print( e )
        return

    if "tracker_id" not in payload or 'state' not in payload:
        raise Exception(f"Invalid message {payload}")

    tracking_id = payload['tracker_id']
    tracking = db.get_export_tracking( tracking_id )

    if payload['state'] != tracking['state']:
        logger.warn(f"state in db {tracking['state']} differs from payload {payload['state']}")


    try:

        state = tracking['state']

        logger.info(f"State: {state}")

        if state == 'pre-queueing':
            run_history_export( tracking )

        elif state == 'ok':
            run_fetch_export( tracking )

        elif state == 'fetch-ok':
            run_push_export( tracking )
        else:
            raise Exception(f"Unknown state {state} for tracking_id: {tracking_id}")

    except Exception as e:
        logger.error(f"Error in state selector: {e}")

        if 'error' in payload and payload['error'] is not None:
            print(f"error: {payload['error']}")
            evaluate(payload["error"], ['requests', 'update_export'])


    cb = functools.partial(ack_message, ch, delivery_tag)
    conn.add_callback_threadsafe(cb)


def main():

    parser = argparse.ArgumentParser(description='consumes a mq ')

    parser.add_argument('-c', '--config', required=True, help="conductor config file ", default="conductor.yml")
    parser.add_argument('-T', '--threads', default=5, help="number of theads to run with")
    parser.add_argument('-l', '--logfile', default=None, help="Logfile to write to, default is stdout")
    parser.add_argument('-v', '--verbose', default=4, action="count", help="Increase the verbosity of logging output")

    args = parser.parse_args()


    if args.logfile:
        logger.init(name='nga_runner', log_file=args.logfile)
    else:
        logger.init(name='nga_runner')

    logger.set_log_level(args.verbose)
    logger.info('startup')


    config = config_utils.readin_config_file( args.config )


    api_requests.set_token( config['key'])


    config = init( args.config )

    global mq
    # prefetch  translates to thread count!
    mq = mq_utils.Mq()
    mq.connect(uri=config['mq_uri'], prefetch_count=int(args.threads))
#    mq.channel_qos(prefetch_count=int(args.threads))
    #mq.channel.basic_qos(prefetch_count=int(args.threads))

    threads = []
    on_message_callback = functools.partial(on_message, args=(mq.connection, threads))


    try:
        mq.consume(route='default', callback=on_message_callback)
#        rmq.consume(route='default, callback=callback')

    except KeyboardInterrupt:
        mq.channel.stop_consuming()

    # Wait for all to complete
    logger.debug('waiting for threads')
    for thread in threads:
        thread.join()

    mq.channel.close()


if __name__ == "__main__":
    main()
    
