#!/usr/bin/env python3

import argparse

import kbr.config_utils as config_utils
import kbr.log_utils as logger


import nels_galaxy_api.api_requests as api_requests


def main():
    parser = argparse.ArgumentParser(description='test_endpoints: validation of nels-galaxy-api endpoints')

    parser.add_argument('-c', '--config-file', required=True, help="nels-galaxy-api config file")
    parser.add_argument('-l', '--local-proxy', required=False, help="local proxy information")

    args = parser.parse_args()

    config = config_utils.readin_config_file( args.config_file)

    logger.init(name='nels-galaxy-endpoints')
    logger.set_log_level( args.verbose )
    local_api = api_requests.ApiRequests(base_url=f"http://localhost:{config['port']}", token=config['key'])
    proxy_api = api_requests.ApiRequests(base_url=config['proxy_url'], token=config['proxy_key'])

    print('basic connection (no key)')
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

    print('Proxy connection')
    proxy_info = proxy_api.get_proxy()
    print( f"Proxy endpoing: {proxy_info['instance']} running version {proxy_info['version']}" )
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
