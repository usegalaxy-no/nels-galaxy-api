# nels-galaxy-api 

NeLS-galaxy-api (NGA) extends the existing Galaxy API with some additional functionality:

* Basic information, eg: user, jobs, exports, etc.
* Terms of Service agreement registering.
* History export into the NeLS storage system.
* Running the export/import of histories to/from the NeLS storage.
 
TODO: To be kept? -->

To get a galaxy to display the history export progress a special version of the welcome.html is required. 
This **is** be part of the normal nels-galaxy or usegalaxy ansible playbooks and not included here. 
 
 
NGA mainly consists on:

- NGA client instances 
- NGA master instance
- Galaxy client instances
- Galaxy master instance
- NeLS master instance

NGA clients are usually accessed by users in order to export/import their histories into/from the master NGA instance and NeLS.

Users need a key to access nga client endpoints, and, if a NGA instance is acting as 
a proxy for the master NGA, this NGA instance needs the master proxy-key to allow the connection to the NGA master instance.

Finally, a webhook is installed into Galaxy in order to facilitate exporting/importing functionality to the user.


A diagram showing how NGA components from NGA clients (UiB and UiO are used just as examples) interact among them and with the master instance:

![NGA overview](images/extended_overview.png)


**Notes**:

1. By October, old usegalaxy client instances will dissapear and only usegalaxy.no will remain. NGA will still be available from there.


TODO: To be kept? -->
2.An ansible role is available for the deployment of the old version of the software as well at: https://github.com/usegalaxy-no/ansible-role-nels-galaxy-api


## NGA export and import diagrams

The most complex interaction among nga components happens when an export or import flow is requested by the user. We will describe both sequences here.

### The export flow

When the user selects the export option under history webhooks it triggers the following calls:

![NGA export flow](images/export_flow.png)



1. Redirect to local NGA where the user and history id is stored im memory
2. redirect to the nels-storage portal where the user decides where to store the export
3. callback to the master NGA      
4. user and history info is fetched from the local NGA and request is recorded in database
5. job is added to queue
6. Redirects back to the galaxy instance
7. nga-runner fetches job 
8. gets job details from NGA master
9. Trigger history export using bioblend
10. pulls until file is available 
11. download file to local temporary storage
12. get user ssh key
13. scp file across to NeLS storage


TODO: Add export flow when only the master nga instance remains.


### The import flow

In this scenario the user selects the import option under history webhooks.

Note this **only** works on the usegalaxy.no instance! 


![NGA export flow](images/import_flow.png)



1. Redirect to master NGA 
2. redirect to the nels-storage portal where the user selects the history to import
3. callback to the master NGA
4. job is added to queue
5. Redirects back to the galaxy instance
6. nga-runner fetches job
7. get user ssh key   
8. scp file from NeLS storage to local temp disk
9. get user api key, it not created will create one.   
10. Trigger history import using bioblend


## NGA Installation

Installation consists on 4 steps:

1. Install and configure the nels-galaxy-api.
2. Configure nga proxying.
3. Galaxy configuration.
4. Running the server.
5. Running the nga_runner.

Once the service is up and running you will need to:   6. share the galaxy admin api-key (from the webinterface) 


with the usegalaxy admin, this is to enable triggering the history-export through bioblend


These instructions are for the test server setup and are using the provided nels-galaxy-test.yml.sample config file. 
For production use the nels-galaxy-prod.yml.sample file instead. The files are almost identical except the name of the proxy-server to connect to.




### Install and Configure nels-galaxy-api


Install the nels-galaxy-api (by cloning its repository, creating its own virtual environment and installing its requirements):

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
```

Similarly, when nels-galaxy-api may be upgraded, it just needs to execute:

```
# pull changes
$ git pull
$ pip install -r requirements.txt
```


#### NGA client instance

There is a nels-galaxy-local.yml.sample sample configuration file into *sample_files* folder that we can reuse as a template for configuring a nga local client instance:

```
cp sample_files/nels-galaxy-local.yml.sample nels-galaxy-client.yml 

```


Edit the new nels-galaxy.yml and fill in all fields. If NGA is being installed locally, you should have all the information required, but if it is being installed in test or production environments:

1. The id of the Galaxy instance is provided by one of the usegalaxy admins
2. access-key: it is provided by one of the usegalaxy admins
3. proxy-key: it is provided by one of the usegalaxy admins

More information about every configuration value may be found by the end of this file in 'Design notes - NGA configuration values' item.


**Notes**:
1. If the localhost:8008 port is already being used change it (```netstat -a | egrep 8008```)


#### NGA master instance

There is a nels-galaxy-master-local.json.sample sample configuration file into *sample_files* folder that we can reuse as a template for configuring a nga local master instance:

```
cp sample_files/nels-galaxy-master-local.json.sample nels-galaxy-master.yml 

```

Similar considerations to the nga client instance installation must be done now.
Although, if both nga client and master are configured for testing purposes in the same machine, listening ports must be different too.

More information about every configuration value may be found by the end of this file in 'Design notes - NGA configuration values' item.


### Configure nga proxying

NGA api needs to be proxied through either nginx or apache as it binds to localhost, and this gives the options of using the https protocol instead of http.

**Note**: 

- If the default is port changed in the configuration, this needs to be done here as well.
 

#### nginx

Add the following entry in your nginx to be able to accessing it at http://\<host.no>/nga/

```
    location /nga/ {
        proxy_pass  http://127.0.0.1:8008/;
    }

```



#### apache2

Add the following entry in your appache2/httpd config file to be able to access to it at http://\<SITE>/nga/


```
        <Location /nga>

          Order allow,deny
          Allow from all
 
          proxyPass "http://localhost:8008"
          proxyPassReverse "http://localhost:8008"
        </Location>


```

**Note**: 

- Don't forget to enable proxy and http proxy modules in Apache in order to make this directive to work.
 


### Galaxy configuration

Assuming you already have a Galaxy instance running, you need to configure it in a proper way in order to nga is able to communicate with it.

#### Galaxy config file setup


The galaxy configuration file (_galaxy.yml_) needs to have some fields properly configured:


- Id (*id_secret*). As an example:

```
id_secret: fd48e1d7eb18532d83973088a64f3812
```


- The database connector (*database_connection*) defined as:

```
database_connection: 'postgresql://galaxy_nga_user:galaxy_nga_pass@localhost/galaxy_nga_database'
```

It is important to remark that postgreSQL must be used instead of default SQLite. 


- File-path specified (*file_path*), as:

```
file_path: <galaxy_installation_folder>/database/objects
```
Please note that it must be a full filepath, not just a relative one.

- Webhooks enabled (*webhooks_dir*) ponting them to the NeLS webhook root folder as

```
webhooks_dir: config/plugins/webhooks/nels
```

#### Installing the webhook

Galaxy webhooks allow to add extra options to the native Galaxy menus. In order to be directly used by the Galaxy instance users, a webhook providing access to the nga export and import functionality has been developed and it requires some configuration steps to be accessible:

- Copy the webhook available in this repo to the Galaxy instance: 

```
# from with in the nels-galaxy-api directory
mkdir -p <GALAXY-SERVER-DIR>/config/plugins/webhooks/nels/nels_export/
cp webhooks/nels_export_history_config.yml <GALAXY-SERVER-DIR>/config/plugins/webhooks/nels/nels_export/config.yml
```

- Remember to enable webhooks as described in previous section.

**Notes**


1. Ensure that the directories and the _config.yml_ file are readable by the user running galaxy: ```namei -mo /<GALAXY-SERVER-DIR>/config/plugins/webhooks/nels/nels_export_history/config.yml```


2. It looks like the webhooks needs to be with in the galaxy server dir. It will not work running them from a external config 
directory as done with the galaxy project ansible-playbook (and thus usegalaxy.no). 



### Running the server 


#### Testing stage


```
# if in a new terminal, change to the nels-galaxy-api directory
$ source venb/bin/activate

# run the server
$ ./bin/nels-galaxy-api.py -c nels-galaxy-master.yml
```

**Test the connection ...**

In a different terminal, change to the same directory and execute:

```
# change to the nels-galaxy-api directory
$ source venb/bin/activate
$ ./bin/test_endpoints.py -c nels-galaxy-master.yml  
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


Similarly, if you want to test the endpoints of a remote nga node, again in a different terminal and in the same directory you can execute:

```
$ source venv/bin/activate
$ ./bin/test_endpoints.py -c nels-galaxy-master.yml  -l https://**HOSTNAME+PATH**/nga
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


#### Production stage


```
# in the nels-galaxy-api directory
source venb/bin/activate
nohup ./bin/nels-galaxy-api.py -c nels-galaxy.yml -l nels-galaxy.log &
```

This will run the server in the background and write to a log named *nels-galaxy.log* in the current directory.


There have been some problems with the certs used by UIO (at least in test stage). In order to add the root-cert (might need to be updated later) execute:

``` 
./bin/patch_certfile.py invivo.hpc.uio.no TERENA_SSL_CA_3.pem  
```

### Running nga_runner


This program triggers the history export flow and, later, file transfers.

It mainly uses the same information available in a master nga config file (yaml or json format)

In order to execute it for running the jobs in the rabbitmq queue:


```
./bin/nga_runner.py -c <config>

```



## Design notes:

TODO: To properly understand how to access to the session keys.


Galaxy session cookies are blowfish-encrypted session keys which use the id_secret in the galaxy-config. 
The same applies to all database IDs.

The filepath is determined on a bucket method, duplicated it here so it is possible to download data files through the NGA-api.


The development has been done on postgresql and is unlikely to work with other databases.

The program will create the required tables if needed.


### Terms Of Service


This is a simple utility for registering that users have accecpted the terms of service when using usegalaxy.no. The server is meant to sit between the www-proxy and the backend database. 

The server uses the galaxysession cookie to identify the user, so no additional authentication is required.


### NGA configurations values


These are the valid values for the nels-galaxy configuration files, note the additional ones for the master NGA server. 


#### Fields for all instances can be in json or yaml:

TODO: To review and rename

* galaxy_config: location of galaxy config file,
* id: uuid of instance, used when connecting to the master NGA
* key: used for allowing access to  REST-API 
* port: port to connect to, will connect to localhost
* galaxy_url: URL of local galaxy instance
* master_url: master NGA URL
* proxy_key: allows proxy access to the master NGA 
* nels_url: NeLS URL
  
* tos_server: enable "Terms or Service" endpoint
* grace_period: grace period of the ToS


#### Fields just for the master instance, should be in json:

TODO: To review and rename


* master: is the master NGA (True/False)
* instances: NGAs to server, should be a dictionary with id as key, for each instance: 
   - name: name of the instance
   - url: galaxy url of the instance
   - api_key: galaxy administrator api key 
   - nga_url: NGA url for instance
   - nga_key: key to allow access
   - proxy_key: key to allow to behave as a proxy for the master NGA  
   - active: true


* nels_storage_client_key: Client key to connect to NeLS storage
* nels_storage_client_secret: secret for the NeLS storage
* nels_storage_url: NeLS storage url
* mq_uri: rabbitmq queue for jobs  
* sleep_time: sleep time before each pull to see of exports is finished.
* tmp_dir: Where to store tmp files




# NGA Endpoints


All endpoints return json formatted data, look into nels-galaxy-api.py for detailed descriptions.

Some common ones:

* /: api version 
* /info: disk usage info
* /users/: list users

* /user/**{email}**/histories/: list of a users histories 
* /user/**{email}**/exports/: list of a users exports
* /user/**{email}**/imports/: list of a users imports
* /user/**{email}**/api-key/: get user api-key, will create it if needed
* /user/**{id}**: detailed user info

* /user/exports/: list of user exports based on the galaxy-cookie
* /user/imports/: list of user imports based on the galaxy-cookie
* /user/export/**{id}**: export details
* /user/export/**{id}**: import details

* /history/export/request: request export 
* /history/import/request: request import
* /tos/: terms of service

For tracking and the nga-cli


* /export/**{id}**/requeue/: requeue export
* /import/**{id}**/requeue/: requeue import  


* /exports/**{email}**: exports for email
* /exports/**{email}**/**{instance}**: exports for email
* /exports/all/**{instance}**/: all exports for instance
* /exports: all exports


* /imports/**{email}**: imports for email
* /imports/**{email}**/**{instance}**: imports for email
* /imports/all/**{instance}**/: all imports for instance
* /imports: all imports

  
* /jobs: list jobs, can be filtered based on user_id






