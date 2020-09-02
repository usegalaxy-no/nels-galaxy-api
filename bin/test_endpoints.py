#!/usr/bin/env python3

import argparse

import kbr.config_utils as config_utils
import kbr.log_utils as logger


import nels_galaxy_api.api_requests as api_requests


def main():
    parser = argparse.ArgumentParser(description='test_endpoints: validation of nels-galaxy-api endpoints')

    parser.add_argument('-c', '--config-file', required=True, help="nels-galaxy-api config file")
    parser.add_argument('-l', '--local-proxy', required=False, help="local proxy information")
    parser.add_argument('-s', '--state-id', required=False, help="state-id")

    args = parser.parse_args()

    config = config_utils.readin_config_file( args.config_file)

    logger.init(name='nels-galaxy-endpoints')

    local_api = api_requests.ApiRequests(base_url=f"http://localhost:{config['port']}", token=config['key'])
    proxy_api = api_requests.ApiRequests(base_url=config['master_url'], token=config['proxy_key'])


    print('Basic connection (no key)')
    base = local_api.get_base()
    print( f"Basic: {base['name']} version: {base['version']}" )
    print("===============================\n")

    print('System info')
    info = local_api.get_info()
    print( f"data disk: {info['perc_free']:.2f} percent free" )
    print("===============================\n")

    print('Database connection')
    users = local_api.get_users()
    print( "Database contains {} users".format(len(users)) )
    print("===============================\n")

    print('Histories & exports:')
    histories_total = 0
    exports_total = 0
    for user in users:
        histories = local_api.get_user_histories( user['email'] )
        histories_total += len(histories)
        exports = local_api.get_user_history_exports( user['email'] )
        exports_total += len(exports)
#        if len(exports):
#            print(exports)
        print( f"{user['email']:30} has {len(histories):2} histories and {len(exports):2} exports")

    print( f"\n{histories_total} histories and {exports_total} exports in the database")
    print("===============================\n")

    print('Request export')
    local_api.history_export_request()
    print("===============================\n")



    print('Proxy connection')
    proxy_info = proxy_api.get_proxy()
    print( f"Proxy endpoint: {proxy_info['instance']} running version {proxy_info['version']}" )
    print("===============================\n")

    if args.state_id is not None:
        print('Getting stored state')
        state = local_api.get_state(args.state_id)
        print( f"state fetched: {state}")
        print("===============================\n")


    if args.local_proxy is not None:
        print("-------------------------------")
        print( "Testing local proxy connection ")
        print("--------------------------------\n")

        local_proxy_api = api_requests.ApiRequests(base_url=args.local_proxy, token=config['key'])
        print('basic connection (no key) local proxy')
        base = local_proxy_api.get_base()
        print( f"Basic: {base['name']} version: {base['version']}" )
        print("===============================\n")

        print('System info local proxy')
        print( f"data disk: {info['perc_free']:.2f} percent free" )
        print("===============================\n")


    print('\nSetup looks good\n')




if __name__ == "__main__":
    main()
