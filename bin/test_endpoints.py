#!/usr/bin/env python3

import argparse
import pprint as pp

import kbr.config_utils as config_utils
import kbr.log_utils as logger


import nels_galaxy_api.api_requests as api_requests


def main():
    parser = argparse.ArgumentParser(description='test_endpoints: validation of nels-galaxy-api endpoints')

    parser.add_argument('-c', '--config-file', required=True, help="nels-galaxy-api config file")
    parser.add_argument('-l', '--local-proxy', required=False, help="local proxy information")
    parser.add_argument('-s', '--state-id', required=False, help="state-id")
    parser.add_argument('-u', '--user', required=False, help="user to get info for")
    parser.add_argument('-m', '--master-api', required=False, default=False, action='store_true', help="test the master api")

    args = parser.parse_args()

    config = config_utils.readin_config_file( args.config_file)

    logger.init(name='nels-galaxy-endpoints')

    local_api = api_requests.ApiRequests(base_url=f"http://localhost:{config['port']}", token=config['key'])
    proxy_api = api_requests.ApiRequests(base_url=config['master_url'], token=config['proxy_key'])

    instance_id = config['id']


    print('Basic connection (no key)')
    base = local_api.get_base()
    print( f"Basic: {base['name']} version: {base['version']}" )
    print("===============================\n")

    print('System info')
    info = local_api.get_info()
    print( f"data disk: {info['perc_free']:.2f} percent free for instance {info['id']}" )
    print("===============================\n")

    print('Database connection')
    users = local_api.get_users()
    print( "Database contains {} users".format(len(users)) )
    print("===============================\n")


    print('Proxy connection')
    proxy_info = proxy_api.get_proxy()
    print( f"Proxy endpoint: {proxy_info['instance']} running version {proxy_info['version']}" )
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


    print('history exports (last entry/history)')
    exports = local_api.get_history_exports( )
    print( f"{len(exports)} history exports in the database")
    if len(exports):
        state = exports[0]['state']
        exports = local_api.get_history_exports( {'state':state})
        print( f"{len(exports)} history exports with state = '{state}' in the database")
    print("===============================\n")


    print('history exports (all)')
    exports = local_api.get_all_history_exports( )
    print( f"{len(exports)} history exports in the database (all versions )")
    print("===============================\n")


    print('Request export')
    local_api.history_export_request()
    print("===============================\n")

    print('User session export trackings (locally)')
    session_exports = local_api.get_session_exports()
    print( f"There are {len(session_exports)} exports linked to the session " )
    print("===============================\n")

    print('User session export trackings (proxy)')
    exports = proxy_api.get_session_exports()
    print( f" User has {len(exports)} exports registered" )
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



    if args.master_api and args.user:

        print('Master specific endpoints')
        print("===============================\n")

        user = args.user

        print('User exports all (master)')
        exports = local_api.get_user_exports(user)
        print(f"User {user} has {len(exports)} in total" )
        print("===============================\n")

        print('User exports master in instance (master)')
        exports = local_api.get_user_instance_exports(user, instance_id)
        print(f"User {user} has {len(exports)} for instance {instance_id} in total")
        print("===============================\n")

        print('All user exports master in instance (master)')
        exports = local_api.get_instance_exports(instance_id)
        print(f"{len(exports)} for instance {instance_id} in total")
        print("===============================\n")

        print('All user exports master in all instances (master)')
        exports = local_api.get_exports()
        print(f"{len(exports)} exports for for all instances ")
        print("===============================\n")

    print('\nSetup looks good\n')




if __name__ == "__main__":
    main()
