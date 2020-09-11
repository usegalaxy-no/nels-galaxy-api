#!/usr/bin/env python3

import certifi
import requests
import argparse
import warnings
warnings.simplefilter("ignore")


parser = argparse.ArgumentParser(description=f'add missing certs to certfi?')
parser.add_argument('hostname', nargs=1,    help="hostname to check cert for")
parser.add_argument('certificate', nargs=1, help="certificate to add if not working")

args = parser.parse_args()
hostname = args.hostname[0]
certfile = args.certificate[0]


try:
    print('Checking connection to Github...')
    test = requests.get(f'https://{hostname}')
    print(f'Connection to {hostname} OK.')
except requests.exceptions.SSLError as err:
    print('SSL Error. Adding custom certs to local certifi list...')
    cafile = certifi.where()
#    print( cafile )
    with open(certfile, 'rb') as infile:
        customca = infile.read()
    with open(cafile, 'ab') as outfile:
        outfile.write(customca)
    print('Certfile patched, rerun to check if is have worked.')
