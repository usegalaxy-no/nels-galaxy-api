#!/usr/bin/env python3
# 
# 
# 
# 
# Kim Brugger (03 Apr 2019), contact: kim@brugger.dk

import sys
import pprint
pp = pprint.PrettyPrinter(indent=4)
import json
import argparse

sys.path.append(".")


import kbr.mq_utils as mq_util
import kbr.run_utils as run_utils


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


def callback(ch, method, properties, body):

    try:
        payload = json.loads(body)
    except:
        return

#    ch.basic_ack(delivery_tag=method.delivery_tag)
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
            exit_code = run_cmd(cmd, 'main', True)
            if exit_code:
                raise RuntimeError

        if 'success' in payload and payload['success'] is not None:
            print(f"success: {payload['success']}")
            evaluate(payload["success"], ['requests', 'update_export'])


        if 'post' in payload and payload['post'] is not None:
            run_cmd(payload['post'], 'post', True)
        
    except Exception as ex:
        if 'error' in payload and payload['error'] is not None:
            print(f"error: {payload['error']}")
            evaluate(payload["error"], ['requests', 'update_export'])


    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():

    parser = argparse.ArgumentParser(description='consumes a mq ')

    parser.add_argument('-m', '--mq_uri',  default='amqp://localhost/', help="rabbit amqp uri")
    parser.add_argument('-t', '--token', default=None, help="token for communicating with the nels-galaxy-api")
    args = parser.parse_args()

    if args.token is not None:
        requests.set_token( args.token)


    mq = mq_util.Mq()
    mq.connect(uri=args.mq_uri)
    mq.consume(route='default', callback=callback)

if __name__ == "__main__":
    main()
    
