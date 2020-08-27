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
import time

sys.path.append(".")

import kbr.mq_utils as mq_util
import kbr.run_utils as run_utils
import kbr.log_utils as logger
import kbr.config_utils as config_utils

import nels_galaxy_api.api_requests as requests

ALLOWED_NAMES = {
    k: v for k, v in requests.__dict__.items() if not k.startswith("__")
}

# Trying to lock down eval a bit, adapted from: https://realpython.com/python-eval-function
def evaluate(expression, allowed_names=[]):
    # Compile the expression
    code = compile(expression, "<string>", "eval")

    # Validate allowed names
    for name in code.co_names:
        if name not in allowed_names:
            raise NameError(f"The use of '{name}' is not allowed")

    return eval(code, {"__builtins__": {}, 'requests': requests}, ALLOWED_NAMES)


def run_cmd(cmd:str, name:str=None, verbose:bool=False):

    if name is not None:
        print(f"{name}:")

    if verbose:
        print(f"cmd: {cmd}")

    exec_info = run_utils.launch_cmd(cmd)

    if verbose:
        print("exit code: %s" % exec_info.p_status)
        print("std out: %s" % exec_info.stdout)
        print("std error: %s" % exec_info.stderr)

    return exec_info.p_status


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
                delivery_tag, "body"))


    try:
        payload = json.loads(body)
    except(e):
        print( e )
        return

    try:

        if "cmds" not in payload:
            raise Exception("Invalid message")

        print( payload )
        # prologue - handle preparation for running job
        if 'pre' in payload and payload['pre'] is not None:
            print(f"pre-stage: {payload['pre']}")
            evaluate(payload["pre"], ['requests', 'update_export'])


        if not isinstance(payload['cmds'], list):
            payload['cmds'] = [payload['cmds']]

        for cmd in payload['cmds']:
            exit_code = run_cmd(cmd, 'main', False)
            if exit_code:
                raise RuntimeError(f'could not run command {cmd}')

        if 'success' in payload and payload['success'] is not None:
            print(f"success: {payload['success']}")
            evaluate(payload["success"], ['requests', 'update_export'])


        if 'post' in payload and payload['post'] is not None:
            run_cmd(payload['post'], 'post', True)

    except Exception as ex:
        if 'error' in payload and payload['error'] is not None:
            print(f"error: {payload['error']}")
            evaluate(payload["error"], ['requests', 'update_export'])


    cb = functools.partial(ack_message, ch, delivery_tag)
    conn.add_callback_threadsafe(cb)


def main():

    parser = argparse.ArgumentParser(description='consumes a mq ')

    parser.add_argument('-c', '--config', required=True, help="conductor config file ", default="conductor.yml")
#    parser.add_argument('-m', '--mq_uri',  default='amqp://localhost/', help="rabbit amqp uri")
#    parser.add_argument('-t', '--token',   default=None, help="token for communicating with the nels-galaxy-api")
    parser.add_argument('-T', '--threads', default=5, help="number of theads to run with")




    args = parser.parse_args()

    config = config_utils.readin_config_file( args.config )
    mq = mq_util.Mq()
    mq.connect(uri=config['mq_uri'])
    requests.set_token( config['nels_galaxy_key'])

    logger.init(name='mq_runner')


#    mq.connect(uri=args.mq_uri)
    # this translates to thread count!
    mq.channel.basic_qos(prefetch_count=int(args.threads))

    threads = []
    on_message_callback = functools.partial(on_message, args=(mq.connection, threads))
#    channel.basic_consume('standard', on_message_callback)

    try:
        mq.consume(route='default', callback=on_message_callback)
    except KeyboardInterrupt:
        mq.channel.stop_consuming()

    # Wait for all to complete
    for thread in threads:
        thread.join()

    mq.disconnect()


if __name__ == "__main__":
    main()
    
