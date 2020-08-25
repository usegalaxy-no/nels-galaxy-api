#!/usr/bin/env python3

import argparse
import pprint as pp
import sys
import os

sys.path.append(".")


import kbr.log_utils as logger
import kbr.config_utils as config_utils

import nels_galaxy_api.tornado as tornado
import nels_galaxy_api.db as nels_galaxy_db
import nels_galaxy_api.utils as utils

VERSION = '0.0.1'


DEV = True

class GalaxyHandler( tornado.BaseHandler ):

    def get_session_key(self):
        if DEV:
            session_key = 'ed42604e029aab1a5b1644a93288a9fa'
        else:
            cookie = self.get_cookie("galaxysession")
            if cookie is None or cookie == '':
                return self.send_response_403()

            session_key = utils.decrypt_cookie( cookie )

        return session_key

    def get_user(self):
        session_key = self.get_session_key()
        user = db.get_user(session_key)
        return user


db = nels_galaxy_db.DB()
id_cipher = None
grace_period = None
galaxy_config = None

def galaxy_init(galaxy_config:dict) -> None:
    if 'galaxy' not in galaxy_config:
        raise RuntimeError('galaxy entry not found in galaxy config')

    if 'database_connection' not in galaxy_config['galaxy']:
        raise RuntimeError('database_connection  entry not found in galaxy config')

    db.connect( galaxy_config['galaxy']['database_connection'])

    if 'id_secret' not in galaxy_config['galaxy']:
        id_secret = "USING THE DEFAULT IS NOT SECURE!"
    else:
        id_secret = galaxy_config['galaxy']['id_secret']

    # the crypt, will move to kbr-tools
    utils.init( id_secret )


class RootHandler ( tornado.BaseHandler ):

    def endpoint(self):
        return("/")

    def get(self):
        self.check_token()
        return self.send_response( data={'name': 'nels-galaxy-api', 'version': VERSION} )

class Info ( tornado.BaseHandler ):

    def endpoint(self):
        return("/info/")

    def get(self):
        self.check_token()
        df = os.statvfs(galaxy_config['galaxy']['file_path'])
        perc_free = df.f_bavail/df.f_blocks*100.0
        free_size = df.f_bavail*df.f_bsize/1e9
        return self.send_response( data={"perc_free":perc_free, 'free_gb': free_size} )




class Users ( GalaxyHandler ):

    def endpoint(self):
        return("/")

    def get(self):
        self.check_token()
        users = db.get_users()
        return self.send_response( data=users )


class UserHistories ( GalaxyHandler ):

    def endpoint(self):
        return("/")

    def get(self, user_id):
        self.check_token()
        user_histories = db.get_user_histories(user_id)
        return self.send_response( data=user_histories )


class UserHistory ( GalaxyHandler ):

    def endpoint(self):
        return("/")

    def delete(self, user_id, history_id):
        self.check_token()
        user_histories = db.get_user_histories(user_id)
        return self.send_response( data=user_histories )



class UserExports ( GalaxyHandler ):

    def endpoint(self):
        return("/")

    def get(self, user_id):
        self.check_token()
        filter = self.get_argument('all', 'False')
        if filter != 'False':
            user_exports = db.get_user_history_exports(user_id)
        else:
            user_exports = db.get_all_user_history_exports(user_id)
        return self.send_response( data=user_exports )


class HistoryExport ( GalaxyHandler ):

    def endpoint(self):
        return("/")

    def get(self, export_id):
        self.check_token()
        export = db.get_export(export_id)
        return self.send_response( data=export )


class HistoryExportsList ( GalaxyHandler ):

    def endpoint(self):
        return("/exports/")

    def get(self):
        self.check_token()
        filter = self.get_argument('all', 'False')
        if filter != 'False':
            exports = db.get_all_exports()
        else:
            exports = db.get_exports()
        return self.send_response( data=exports )


class Encrypt ( tornado.BaseHandler ):

    def endpoint(self):
        return("/encrypt/")

    def get(self, value):
        self.check_token()
        encrypted = utils.encrypt_value(value)
        return self.send_response( data={'value':encrypted} )


class Decrypt ( tornado.BaseHandler ):

    def endpoint(self):
        return("/decrypt/")

    def get(self, value):
        self.check_token()
        return self.send_response( data={'value':utils.decrypt_value(value)} )



class ExportDo ( GalaxyHandler ):

    def endpoint(self):
        return("/export/")

    def post(self, export_id):
        self.check_token()
        post_values =  self.post_values()

        args = ['action']
        data = self.require_arguments(post_values, args)


        export = db.get_export( export_id )

        if data['action'] == 'cancel':
            print( 'cancelling export, DOES NOT WORK!!! :-(=) ')
            try:
                job = db.get_job( export[0]['job_id'])
                job = job[0]
                print( job )
                if job['state'] in ['new', 'upload', 'waiting', 'queued','ok']:

                    db.update_job( {'id':job['id'], 'state': 'deleted_new'} )
                    self.send_response_204()
            except:
                self.send_response_400()

        elif data['action'] == 'delete':
            self.send_response_204()
            pass
        else:
            self.send_response_400()



def main():
    parser = argparse.ArgumentParser(description='blood_flow_rest: the rest service for blood_flow')

    parser.add_argument('-g', '--galaxy-config', required=True, help="galaxy config file")
    parser.add_argument('-G', '--grace-period', default=14, help="Length of grace period in days")
    parser.add_argument('-l', '--logfile', default=None, help="Logfile to write to, default is stdout")
    parser.add_argument('-p', '--port', default=8088, help="Port to bind to")
    parser.add_argument('-v', '--verbose', default=4, action="count",  help="Increase the verbosity of logging output")
    parser.add_argument('-t', '--token', default=None, help="unique token for this base_url")

    args = parser.parse_args()

    global galaxy_config
    galaxy_config = config_utils.readin_config_file( args.galaxy_config )

    if args.logfile:
        logger.init(name='nels-galaxy-helper', log_file=args.logfile )
    else:
        logger.init(name='nels-galaxy-helper')

    logger.set_log_level( args.verbose )

    logger.info( 'startup')

    if galaxy_config is not None:
        galaxy_init( galaxy_config )

    global grace_period
    grace_period = args.grace_period

    if args.token is not None:
        tornado.set_token( args.token)

    urls = [('/', RootHandler),
            (r'/info/?$', Info),
            (r'/users/?$', Users),
            (r'/user/(\w+)/histories/?$', UserHistories),
            (r'/user/(\w+)/exports/?$', UserExports),

            (r'/history/export/(\w+)/?$', HistoryExport),

#            (r'/export/(\w+)/do?$', ExportDo),
            (r'/history/exports/?$', HistoryExportsList),

            #            (r'/dataset/(\w+)/?$', Dataset), # get details inc size

            # Might drop these two
            (r'/decrypt/(\w+)/?$', Decrypt),
            (r'/encrypt/(\w+)/?$', Encrypt),

            ]

    tornado.run_app( urls, port=args.port )


if __name__ == "__main__":
    main()
