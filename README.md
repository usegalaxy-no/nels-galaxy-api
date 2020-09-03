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
5. running the server in production mode.

Once the service is up and running you will need to 5. share the galaxy admin api-key (from the webinterface) 
with the usegalaxy admin, this is to enable triggering the history-export through bioblend


These instructions are for the test server setup and are using the provided nels-galaxy-test.yml.sample config file. 
For production use the nels-galaxy-prod.yml.sample file instead. The files are almost identical except the name of the proxy-server to connect to.


### Install and Configure nels-galaxy-api


Install the nels-galaxy-api.
```
#Clone the repository
$ git clone https://github.com/usegalaxy-no/nels-galaxy-api/
$ cd nels-galaxy-api
#install virtual env and required libraries
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install wheel
$ pip install --upgrade pip
$ pip install -r requirements.txt
# make a copy of the config sample to use

cp nels-galaxy-test.yml.sample nels-galaxy.yml 

```


Edit the config-file nels-galaxy.yml.

The following needs to filled in:
1. path to the galaxy config file
2. id of the instance, provided by one of the usegalaxy admins
3. access-key: provided by one of the usegalaxy admins
4. proxy-key: provided by one of the usegalaxy admins

**Notes**:
1. The galaxy files needs to have the database connector and file-path defined, and should include the full filepath, 
not only relative ones. 
2. If the localhost:8008 port is already being used change it (```netstat -a | egrep 8008```)

### Running the server (testing stage)


```
# if in a new terminal, change to the nels-galaxy-api directory
$ source venb/bin/activate

# run the server
$ ./bin/nels-galaxy-api.py -c nels-galaxy.yml
```

**Test the connection ...**

In a different terminal, and change into the same directory

```
# change to the nels-galaxy-api directory
$ source venb/bin/activate
$ ./bin/test_endpoints.py -c nels-galaxy.yml  
Basic connection (no key)
Basic: nels-galaxy-api version: 1.3.0
===============================

System info
data disk: 84.54 percent free
===============================

Database connection
Database contains 11 users
===============================

Proxy connection
Proxy endpoing: test.usegalaxy.no running version 1.3.0
===============================

(etc)

Setup looks good
```

### Proxying


The api needs to be proxied through either nginx or apache as it binds to localhost, and this gives the options of 
using the https protocol instead of http 

**Note**: if changed the default port in the configuration, this needs to be done here as well

#### nginx

Add the following entry in your nginx to be able to accessing it at http://\<host.no>/nga/

```
    location /nga/ {
        proxy_pass  http://127.0.0.1:8008/;
    }

```



#### apache2

Add the following entry in your appache2/httpd be able to accessing it at http://\<SITE>/nels-galaxy/


```
        <Location /nga>

          Order allow,deny
          Allow from all
 
          proxyPass "http://localhost:8008"
          proxyPassReverse "http://localhost:8008"
        </Location>


```


**Test the connection ...**

Again in a different terminal, and in the same directory

```
$ source venv/bin/activate
$ ./bin/test_endpoints.py -c nels-galaxy.yml  -l https://**HOSTNAME+PATH**/nels-galaxy
-------------------------------
Testing local proxy connection 
--------------------------------

basic connection (no key) local proxy
Basic: nels-galaxy-api version: 1.3.0
===============================

System info local proxy
data disk: 84.54 percent free
===============================

Setup looks good
```


### Installing the webhook

```
# from with in the nels-galaxy-api directory
mkdir -p <GALAXY-SERVER-DIR>/config/plugins/webhooks/nels/nels_export/
cp webhooks/nels_export_history_config.yml <GALAXY-SERVER-DIR>/config/plugins/webhooks/nels/nels_export/config.yml
```





**Notes**



1. Ensure that the directories and the config.yml file is readable by the user running galaxy ```namei -mo /<GALAXY-SERVER-DIR>/config/plugins/webhooks/nels/nels_export_history/config.yml```



2. It looks like the webhooks needs to be with in the galaxy server dir. It will not work running them from a external config 
directory as done with the galaxy project ansible-playbook (and thus usegalaxy.no). 

In the galaxy.yml enable webhooks (if not already done)  

 webhooks_dir: config/plugins/webhooks/nels/


### Running the server (production)


```
# in the nels-galaxy-api directory
source venb/bin/activate
nohup ./bin/nels-galaxy-api.py -c nels-galaxy.yml -l nels-galaxy.log &
```

This will run the server in the background and write to a log named nels-galaxy.log in the current directory



## Upgrade the nels-galaxy-api



```
# pull changes
$ git pull
$ pip install -r requirements.txt
```



## nels-galaxy-conductor

This is the program conducting the flow of triggering of history exports and later the file transfers.

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

## mq_runner.py

Runs the jobs in the rabbitmq queue

```
./bin/mq_runner.py -c conducter-config -T <threads

```



## Design notes:



Galaxy session cookies are session keys with encrypted with blowfish using the id_secret in the galaxy-config.


The development has been done on postgresql and is unlikely to work with
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
















