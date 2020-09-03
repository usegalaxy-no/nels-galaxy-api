#!/usr/bin/env python3

import argparse
import sys
import os
import time
import pprint as pp

from tornado import iostream

sys.path.append(".")

import datetime

import kbr.log_utils as logger
import kbr.config_utils as config_utils
import kbr.string_utils as string_utils
import kbr.version_utils as version_utils

import nels_galaxy_api.tornado as tornado
import nels_galaxy_api.db as nels_galaxy_db
import nels_galaxy_api.utils as utils
import nels_galaxy_api.states as states
import nels_galaxy_api.api_requests as api_requests

version = '0.0.0'
DEV = True

db = nels_galaxy_db.DB()
galaxy_file_path = None

master_url = None
instance_id = None

nels_url = None

# when running as the master version
proxy_keys = None
instances = None

tos_grace_period = None
# galaxy_config = None
no_proxy = False  # The NGA-master does not need to use the proxy connections.


class GalaxyHandler(tornado.BaseHandler):
    def get_tos(self):
        session_key = self.get_session_key()

        user_tos = db.get_user_tos(session_key)
        if user_tos is None:
            logger.error(f"cannot find user from session-key {session_key}")
            return self.send_response_403()

        return user_tos

    def get_session_key(self):
        if DEV:
            session_key = 'ed42604e029aab1a5b1644a93288a9fa'
        else:
            cookie = self.get_cookie("galaxysession")
            if cookie is None or cookie == '':
                return None

            session_key = utils.decrypt_value(cookie)

        return session_key

    def get_user(self):
        session_key = self.get_session_key()
        user = db.get_user_from_session(session_key)
        return user

def galaxy_init(galaxy_config: dict) -> None:
    logger.info("init from galaxy-config ")

    # Galaxy specific things:
    if 'galaxy' not in galaxy_config:
        raise RuntimeError('galaxy entry not found in galaxy config')

    if 'database_connection' not in galaxy_config['galaxy']:
        raise RuntimeError('database_connection  entry not found in galaxy config')
    global db
    db.connect(galaxy_config['galaxy']['database_connection'])

    if 'file_path' not in galaxy_config['galaxy']:
        raise RuntimeError('file_path  entry not found in galaxy config')
    global galaxy_file_path
    galaxy_file_path = galaxy_config['galaxy']['file_path']

    if 'id_secret' not in galaxy_config['galaxy']:
        id_secret = "USING THE DEFAULT IS NOT SECURE!"
    else:
        id_secret = galaxy_config['galaxy']['id_secret']

    utils.init(id_secret)

    return



def init(config_file: dict) -> None:
    config = config_utils.readin_config_file(config_file)
    galaxy_config = config_utils.readin_config_file(config['galaxy_config'])

    galaxy_init(galaxy_config)

    logger.info("init from config ")

    # set incoming and proxy keys
    tornado.set_token(config.get('key', None))
    api_requests.set_token(config.get('proxy_key', None))

    global master_url, nels_url, instance_id
    master_url = config.get('master_url', None)
    instance_id = config['id']
    nels_url = config['nels_url']

    if 'tos_server' in config and config['tos_server']:
        logger.info("Running with the tos-server")

        db.create_tos_table()
        global tos_grace_period
        tos_grace_period = config.get('grace_period', 14)

    if 'master' in config and config['master']:
        logger.info("Running with the master API")
        db.create_export_tracking_table()
        db.create_export_tracking_logs_table()

        global proxy_keys, instances, no_proxy
        proxy_keys = {}
        instances = {}

        no_proxy = True

        tmp_instances = config['instances']

        for iid in tmp_instances:
            instances[iid] = tmp_instances[iid]
            instance = tmp_instances[iid]

            instances[instance['name']] = instance
            instances[instance['name']]['api'] = api_requests.ApiRequests(f"{instance['url']}", instance['nga_key'])
            if instance['proxy_key'] in proxy_keys.keys():
                logger.warn(f"Proxy key for {instance['name']} is also used for {proxy_keys[instance['proxy_key']]}")
            proxy_keys[instance['proxy_key']] = instance['name']

    global version
    version = version_utils.as_string()

    return config


class RootHandler(tornado.BaseHandler):

    def endpoint(self):
        return ("/")

    def get(self):
        logger.debug("get root")
        return self.send_response(data={'name': 'nels-galaxy-api', 'version': version})


class Info(tornado.BaseHandler):

    def endpoint(self):
        return ("/info/")

    def get(self):
        logger.debug("get info")
        self.check_token()
        df = os.statvfs(galaxy_file_path)
        perc_free = df.f_bavail / df.f_blocks * 100.0
        free_size = df.f_bavail * df.f_bsize / 1e9
        return self.send_response(data={"id": instance_id, "perc_free": perc_free, 'free_gb': free_size})


class State(tornado.BaseHandler):

    def endpoint(self):
        return ("/state/")

    def get(self, state_id):
        logger.debug("get state")
        self.check_token()
        data = states.get(state_id, True)
        if data is None:
            return self.send_response_404()

        return self.send_response(data=data)


class Users(GalaxyHandler):

    def endpoint(self):
        return ("/users")

    def get(self):
        logger.debug("get users")
        self.check_token()

        users = utils.encrypt_ids( db.get_users() )
        return self.send_response(data=users)


class UserHistories(GalaxyHandler):

    def endpoint(self):
        return ("/")

    def get(self, user_email):
        logger.debug("get user histories")
        self.check_token()
        user = db.get_user(email=user_email)
        if user is None or user == []:
            return self.send_response_404()

        # Should only be one user with a given email!
        user = user[0]

        user_histories = utils.encrypt_ids(db.get_user_histories(user['id']))
        return self.send_response(data=user_histories)


class UserExports(GalaxyHandler):

    def endpoint(self):
        return ("/")

    def get(self, user_email):
        logger.debug("get user exports")
        self.check_token()
        user = db.get_user(email=user_email)
        if user is None or user == []:
            return self.send_response_404()

        # Should only be one user with a given email!
        user = user[0]

        user_exports = utils.encrypt_ids(db.get_user_history_exports(user['id']))
        return self.send_response(data=user_exports)


class HistoryExportRequest(GalaxyHandler):

    def endpoint(self):
        return ("/history/export/request")

    def get(self):
        logger.debug("request history export")

        user = self.get_user()
        data = {'user': user['email'], 'history_id': utils.encrypt_value(user['current_history_id'])}
        uuid = states.set( data )

        redirect_url = f"{nels_url}/welcome.xhtml"
        redirect_url += f"?appCallbackUrl={master_url}/export/" + instance_id + "/" + uuid + "/"

        if DEV:
            print( redirect_url )
            return

        self.redirect(redirect_url)


class HistoryExport(GalaxyHandler):

    def endpoint(self):
        return ("/history/export")

    def get(self, export_id=None):
        logger.debug("get history exports")
        self.check_token()

        if export_id is None:
            logger.debug('getting by history_id')
            filter = self.arguments()

            self.require_arguments(filter, ['history_id', ])
            history_id = utils.decrypt_value(filter['history_id'])
            export = db.get_latest_export_for_history(history_id)
        else:
            logger.debug('getting by export_id')
            export_id = utils.decrypt_value(export_id)
            export = db.get_export(export_id)

        if len(export):
            export = export[0]
            export = utils.encrypt_ids(export)
            return self.send_response(data=export)
        else:
            return self.send_response_404()


class HistoryExportsList(GalaxyHandler):

    def endpoint(self):
        return ("/history/exports/")

    def get(self, all=False):
        logger.debug("get history exports list")
        self.check_token()
        filter = self.arguments()

        self.valid_arguments(filter, ['state', ])

        if 'state' not in filter:
            filter['state'] = ''

        if 'state' in filter and filter['state'] not in ['new', 'upload', 'waiting', '',
                                                         'queued', 'running', 'ok', 'error',
                                                         'paused', 'deleted', 'deleted_new', 'pre-queueing', 'all']:
            return self.send_response_400(data="Invalid value for state {}".format(filter['state']))

        if all == 'all':
            exports = db.get_all_exports(state=filter['state'])
        else:
            exports = db.get_exports(state=filter['state'])

        exports = utils.list_encrypt_ids(exports)
        return self.send_response(data=exports)


class HistoryDownload(GalaxyHandler):

    def endpoint(self):
        return ("/history/download")

    async def get(self, export_id=None):
        logger.debug("get history download")
        self.check_token()

        # chunk size to read
        chunk_size = 1024 * 1024 * 1  # 1 MiB

        export_id = utils.decrypt_value(export_id)
        export = db.get_export(export_id)[0]

        try:

            dataset = db.get_dataset(export['dataset_id'])
            filename = utils.construct_file_path(obj_id=dataset['id'], file_dir=galaxy_file_path)
            logger.debug("start the download")

            with open(filename, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    try:
                        self.write(chunk)  # write the cunk to response
                        await self.flush()  # flush the current chunk to socket
                    except iostream.StreamClosedError:
                        # this means the client has closed the connection
                        # so break the loop
                        break
                    finally:
                        # deleting the chunk is very important because
                        # if many clients are downloading files at the
                        # same time, the chunks in memory will keep
                        # increasing and will eat up the RAM
                        del chunk
                    time.sleep(0)

        except Exception as e:
            logger.error(e)
            self.send_response_400(data={'error': str(e)})

        logger.debug("download completed")


class Encrypt(tornado.BaseHandler):

    def endpoint(self):
        return ("/encrypt/")

    def get(self, value):
        logger.debug("encrypt value")
        self.check_token()
        encrypted = utils.encrypt_value(value)
        return self.send_response(data={'value': encrypted})


class Decrypt(tornado.BaseHandler):

    def endpoint(self):
        return ("/decrypt/")

    def get(self, value):
        logger.debug("decrypt value")
        self.check_token()
        return self.send_response(data={'value': utils.decrypt_value(value)})


class ExportsListProxy(GalaxyHandler):

    def endpoint(self):
        return ("/user/exports/")

    def get(self):
        logger.debug("proxy export list")
        # Will not check token here as relying on the session id instead
        #        self.check_token()
        user = self.get_user()

        # cannot proxy to it-self, read directly from the database
        if no_proxy:
            logger.debug('accessing the data directly')
#            print( user )
            trackings = db.get_export_trackings(user_email=user['email'], instance=instances[instance_id]['name'])
        else:
            logger.debug('accessing the data using the proxy')
            trackings, _ = api_requests.get_user_instance_exports(master_url, user['email'], instance_id)

        results = []
        for tracking in trackings:
            history_id = utils.decrypt_value(tracking['history_id'])
            history = db.get_history(history_id)[0]

            results.append({'name': history['name'],
                            'id': tracking['id'],
                            'state': tracking['state'],
                            'create_time': tracking['create_time'],
                            'destination': tracking['destination'],
                            'update_time': tracking['update_time'], })

        return self.send_response(data=results)


class ProxyTest(GalaxyHandler):

    def endpoint(self):
        return ("/proxy/")

    def get(self):
        logger.debug("proxy endpoint test")
        #        logger.debug( f"Having proxy_keys {proxy_keys}" )
        self.check_token(proxy_keys)
        data = {'instance': instances[instance_id]['name'], 'version': version, 'proxy-connection': True}
        return self.send_response(data=data)


class Tos(GalaxyHandler):

    def endpoint(self):
        return ("/tos")

    def get(self):
        logger.debug("get TOS")
        user_tos = self.get_tos()

        logger.debug("getting tos for {}".format(user_tos['user_id']))
        res = {}

        if user_tos['status'] == 'grace':
            time_diff = (user_tos['tos_date'] - datetime.datetime.now())
            if time_diff.days >= 0:
                res['grace_period'] = "{} days".format(time_diff.days + 1)
            else:
                user_tos['status'] = 'expired'
                db.update_tos(user_tos)

        res['status'] = user_tos['status']
        return self.send_response(data=res)

    def patch(self):
        logger.debug("patch TOS")
        user_tos = self.get_tos()
        data = tornado.json_decode(self.request.body)

        if 'status' in data and data['status'] == 'accepted':
            logger.info("Updating TOS for {}".format(user_tos['user_id']))
            user_tos['status'] = 'accepted'
            user_tos['tos_date'] = datetime.datetime.now()
            db.update_tos(user_tos)
            return self.send_response_204()

        return self.send_response_404()


class Export (GalaxyHandler):

    def endpoint(self):
        return ("/export/")

    def get(self, tracking_id):

        logger.debug("get tracking details")
        self.check_token()
        tracking_id = utils.decrypt_value(tracking_id)
        tracking = utils.encrypt_ids(db.get_export_tracking(tracking_id))
        self.send_response(data=tracking)

    def patch(self, tracking_id):
        logger.debug("patch tracking details")
        self.check_token()
        data = self.post_values()
        self.valid_arguments(data, ['state', 'export_id', 'tmpfile'])
        # need to decrypt the id otherwise things blow up!
        tracking_id = utils.decrypt_value(tracking_id)

        db.update_export_tracking(tracking_id, data)
        return self.send_response_204()


    def _register_export(self, instance: str, user: str, history_id: str, nels_id: int, destination: str):
        logger.debug("registering export")
        tracking = {'instance': instance,
                    'user_email': user,
                    'history_id': history_id,
                    'state': 'pre-queueing',
                    'nels_id': nels_id,
                    'destination': destination}

        # Need this function next
        #        if not db.history_export_exists(tracking):
        db.add_export_tracking(tracking)

    def post(self, instance, state_id):

        #        post_values = self.post_values()
        nels_id = int(self.get_body_argument("nelsId", default=None))
        location = self.get_body_argument("selectedFiles", default=None)

        print( f"{instance} != {instance_id}:")

        if instance == instance_id:
            logger.debug( "No proxy access to state")
            state = states.get( state_id)
        else:
            logger.debug( "Proxy access to state")
            state = instances[ instance]['api'].get_state(state_id)

        if state is None:
            self.send_response_404()

        logger.debug( f"State info for export: {state}")

        try:
            instance_name = instances[instance]['name']
            user = state[ 'user' ]
            history_id = state[ 'history_id' ]
            self._register_export(instance_name, user, history_id, nels_id, location)
            self.redirect(instances[instance]['url'])
        except Exception as e:
            logger.error(f"Error during export registation: {e}")
            logger.debug( f"State info for export: {state}")
            logger.debug( f"nels_id: {nels_id}")
            logger.debug( f"location: {location}")

            self.send_response_400()


class Export_not_used(GalaxyHandler):

    def endpoint(self):
        return ("/export/")


    def _usegalaxy_export(self):
        user = self.get_user()

        current_history_id = user['current_history_id']
        if not isinstance(current_history_id, int):
            current_history_id = utils.encrypt_value(str(current_history_id))

        return user['email'], current_history_id





class ExportsList(Export):

    def endpoint(self):
        return ("/export/")

    def get(self, user: str = None, instance_id: str = None):
        logger.debug("get Export list")
        logger.debug(proxy_keys)
        self.check_token(proxy_keys)
        filter = self.arguments()

        # potential states: 'new', 'upload', 'waiting', 'queued', 'running', 'ok', 'error', 'paused', 'deleted', 'deleted_new' + 'pre-queueing'

        # Ones we care about when polling: 'new', 'waiting', 'queued', 'running'  + 'pre-queueing'

        self.valid_arguments(filter, ['state', ])

        if 'state' in filter and filter['state'] not in ['new', 'upload', 'waiting',
                                                         'queued', 'running', 'ok', 'error',
                                                         'paused', 'deleted', 'deleted_new',
                                                         'pre-queueing', 'fetch-running', 'fetch-ok', 'fetch-error',
                                                         'nels-transfer-queue', 'nels-transfer-running',
                                                         'nels-transfer-ok', 'nels-transfer-error']:
            return self.send_response_400(data="Invalid value for state {}".format(filter['state']))

        if instance_id is not None:
            filter['instance'] = instances[instance_id]['name']

        if user is not None and user != 'all':
            filter['user_email'] = user

        pp.pprint( filter )

        exports = utils.encrypt_ids(db.get_export_trackings(**filter))
        self.send_response(data=exports)


class ImportHandler(GalaxyHandler):

    def endpoint(self):
        return ("/import/")


def main():
    parser = argparse.ArgumentParser(description='nels-galaxy-api: extending the functionality of galaxy')

    parser.add_argument('-c', '--config-file', required=True, help="nels-galaxy-api config file")
    parser.add_argument('-l', '--logfile', default=None, help="Logfile to write to, default is stdout")
    parser.add_argument('-v', '--verbose', default=4, action="count", help="Increase the verbosity of logging output")

    args = parser.parse_args()

    if args.logfile:
        logger.init(name='nels-galaxy-api', log_file=args.logfile)
    else:
        logger.init(name='nels-galaxy-api')

    logger.set_log_level(args.verbose)
    logger.info('startup')

    config = init(args.config_file)

    # Base functionality
    urls = [('/', RootHandler), #Done
            (r'/info/?$', Info), #Done
            (r'/state/(\w+)/?$', State), #Done

            # for the cli...
            (r'/users/?$', Users), #Done
            (r"/user/({email_match})/histories/?$".format(email_match=string_utils.email_match), UserHistories), #Done
            (r"/user/({email_match})/exports/?$".format(email_match=string_utils.email_match), UserExports), # all, brief is default #Done

            # for proxying into the usegalaxy tracking api, will get user email and instance from the galaxy client.
            (r"/user/exports/?$", ExportsListProxy), # done
            (r'/history/export/request/?$', HistoryExportRequest),  # Register export request #Done

            (r'/history/export/(\w+)?$', HistoryExport),  # export_id, last one pr history is default # skip
            (r'/history/export/?$', HistoryExport),  # possible to search by history_id               # ship

            (r'/history/exports/(all)/?$', HistoryExportsList),  # for the local instance, all, brief is default # done
            (r'/history/exports/?$', HistoryExportsList),  # for the local instance, all, brief is default       # done
            (r'/history/download/(\w+)/?$', HistoryDownload),  # fetching exported histories                     # skip

            # Might drop these two
#            (r'/decrypt/(\w+)/?$', Decrypt),
#            (r'/encrypt/(\w+)/?$', Encrypt)
            ]

    # Terms of service server:
    if 'tos_server' in config and config['tos_server']:
        urls += [(r'/tos/?$', Tos)]

    # for the orchestrator functionality:
    if 'master' in config and config['master']:
        logger.debug( "setting the master endpoints")
        urls += [(r"/export/(\w+)/(\w+)/?$", Export), #instance-id, state-id (post) #done
                 (r'/export/(\w+)/?$', Export),  # get or patch an export request # skip

                 (r"/exports/({email_match})/?$".format(email_match=string_utils.email_match), ExportsList), # user_email # done
                 (r"/exports/({email_match})/(\w+)/?$".format(email_match=string_utils.email_match), ExportsList),  # user_email, instance. If user_email == all, export all entries for instance # done
                 (r"/exports/(all)/(\w+)/?$", ExportsList), # done
                 # user_email, instance. If user_email == all, export all entries for instance

                 (r'/exports/?$', ExportsList),  # All entries in the table, for the cli (differnt key?) # done
                 # For testing the setup

                 (r'/proxy/?$', ProxyTest),  # an  endpoint for testing the proxy connection #done
                 ]

    if DEV:
        sid = states.set({'id':1234, 'name': 'tyt'})
        logger.info( f"TEST STATE ID: {sid}")

    logger.info(f"Running on port: {config.get('port', 8008)}")
    tornado.run_app(urls, port=config.get('port', 8008))


if __name__ == "__main__":
    main()
