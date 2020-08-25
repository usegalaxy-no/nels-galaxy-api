# nels-galaxy-api 

The NeLS-galaxy-api extend the existing galaxy api with some additional functionality 

* Terms of Service agreement registering
* History export into the NeLS storage system 
* conducting the export and transfers of histries from galaxy and into NeLS storage
 
To get a galaxy to display the history export progress a special version of the welcome.html is required. 
This **will** be part of the normal nels-galaxy or usegalaxy code bases 
 
A simple diagram:
```
       user
        |
        |
    www-proxy
    |       |
    |       |
  galaxy  nels-galaxy-api ---> usegalaxy.no
    |       |                       |
     \_____/                        |
        |                           |
      database                NeLS storage
```

An ansible role is available for the deployment of the old version of the software as well at: https://github.com/usegalaxy-no/ansible-role-nels-galaxy-api

## Installation


Installation consists of 4 steps

1. install and configure the nels-galaxy-api
3. configure the https proxying
4. add and configure the webhook plugin to galaxy  
4. run the service.
5. share the admin api-key with the usegalaxy admin (to trigger the history-export)



### Install and Configure nels-galaxy-api


Install the nels-galaxy-api.
```
#Clone the repository
git clone https://github.com/usegalaxy-no/nels-galaxy-api/
cd nels-galaxy-api
#install virtual env and required libraries
python3 -m venv venv
source venv/bin/activate
pip install wheel
pip install -r requirements.txt
```


There arw two config files repository: nels-galaxy-test.yml for the test, and nels-galaxy-prod.yml for the production server.

The following needs to filled in:
1. path to the galaxy config file
2. base url of the instance, eg galaxy-uib.bioinfo.no  
3. access-key: provided by one of the usegalaxy admins
4. proxy-key: provided by one of the usegalaxy admins

optionally if the localhost:8008 port is already being used change it

### Proxying


The api needs to be proxied through either nginx or apache as it binds to localhost, and this gives the options of 
using the https protocol instead of http 

**Note**: if changed the default port in the configuration, this needs to be done here as well

#### nginx

Add the following entry in your nginx to be able to accessing it at http://\<SITE>/nels-galaxy/

```
    location /nels-galaxy/ {
        proxy_pass  http://127.0.0.1:8008/;
    }

```

#### apache2

Add the following entry in your appache2/httpd be able to accessing it at http://\<SITE>/nels-galaxy/

```
        <Location /nels-galaxy>

          Order allow,deny
          Allow from all
 
          proxyPass "http://localhost:8081/"
          proxyPassReverse "http://localhost:8801/"
        </Location>


```


### Installing the webhook

```
mkdir -p <GALAXY-SERVER-DIR>/config/plugins/webhooks/nels/nels_export/
cp <NELS-GALAXY-API/webhooks/nels_export_history_config.yml <GALAXY-SERVER-DIR>/config/plugins/webhooks/nels/nels_export/config.yml
```

By default the plugin uses the test server, remove the entry to switch to the production server instead.

**Note** the webhooks needs to be with in the galaxy server dir. It will not work running them from a external config 
directory as done with the galaxy project ansible-playbook (and thus usegalaxy.no). 
 

### Running the server

This is just one of many options of how to run the server, note it will write to a logfile cakked nels-galaxy.log

```
# in the nels-galaxy-api directory
source venb/bin/activate
# when using the test server
nohup ./bin/nels-galaxy-api.py -c nels-galaxy-test.yml -l nels-galaxy.log &
# and for production
nohup ./bin/nels-galaxy-api.py -c nels-galaxy-prod.yml -l nels-galaxy.log &

```




## nels-galaxy-conductor

This is the program conducting the flow of triggering of history exports and the later transfers.

```
nels_storage_client_key: "ASK KIDARNE"
nels_storage_client_secret: "ASK KIDARNE"
nels_url: 'https://test-fe.cbu.uib.no/nels-'

nels_galaxy_api: "https://test.usegalaxy.no/nels-galaxy"
nels_galaxy_key: "ASK KIM"

mq_uri: amqps://RMQ-connection/nels_galaxy

nodes: [{"galaxy_url": "https://test.usegalaxy.no/",
         "api_key": "ADMIN API KEY FROM THE GALAXY WEBSITE",
         "helper_api": "https://test.usegalaxy.no/nels-galaxy",
         "helper_key": "GET FROM KIM",
         "contact_email": "admin@galaxy.uib.no",
         "max_exports": 5,
         "name": "test.usegalaxy.no"
        },
        ]


```


## Design notes:



Galaxy session cookies are session keys with encrypted with blowfish using the id_secret in the galaxy-config.


This have only been tested on postgresql and is unlikely to work with
other databases

The program will create the required table if it does not exist.

### Terms Of Service


This is a simple utility for registering that users have accecpted the terms of service when using usegalaxy.no. The server is meant to sit between the www-proxy and the backend database. 

The server uses the galaxysession cookie to identify the user, so no additional authentication is required.





### Configurations values


These are the valid values for the nels-galaxy helper configuration files

* galaxy_config: \<FULL PATH TO>/galaxy.yml
* name: \<INSTANCE NAME>
* key: \<SECRET KEY> limits access to API point
* port: \<PORT NUMBER> port to run under
* proxy_url: \<PROXY URL>, URL to needed for 
* proxy_token: \<PROXY KEY>, KEY for connecting to the proxy URL

For the main server these values are 
* tos_server: <true/false> #run the term of service, default=false 
* grace_period: 14 # tos grace period to accept ToS in days
* full_api: <true/false> # run the full api? default=false
* proxy_keys: {'PROXY_KEY_A>': 'INSTANCE-A',
               'PROXY_KEY_B': 'INSTANCE-B', 
             ...}
 




### Endpoints


All endpoints return json formated data.
















