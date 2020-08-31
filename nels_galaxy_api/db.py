import kbr.db_utils as db
import datetime




class DB(object):

    def connect(self, url:str) -> None:
        self._db = db.DB( url )

    def disconnect(self) -> None:

        if self._db is not None:
            self._db.close()

    def table_exist(self, name:str) -> bool:
        q = f"SELECT to_regclass('{name}')"
        table = self._db.get_as_dict( q )
        if table[0]['to_regclass'] is None:
            return False

        return True

    def get_session(self, session_key:str) -> bool:

        return self._db.get('galaxy_session', session_key=session_key)

    def _init_user_tos(self, user_id:int) -> {}:
        self._db.add('nels_tos', {'user_id': user_id,
                                  'status': 'grace',
                                  'tos_date': datetime.datetime.now()+datetime.timedelta(days=14)})

    def get_user_tos(self, session_key:str) -> {}:
        session = self.get_session( session_key)

        if session is None or session[0]['is_valid'] != True or session[0]['user_id'] is None:
            return None

        tos  = self._db.get('nels_tos', user_id=session[0]['user_id'])

        if len(tos) == 0:
            self._init_user_tos(session[0]['user_id'])
            tos = self.get_user_tos(session_key)
        else:
            tos = tos[0]

        return tos


    def get_user_from_session(self, session_key:str) -> {}:
        session = self.get_session( session_key)

        if session is None or session[0]['is_valid'] != True or session[0]['user_id'] is None:
            return None

        user  = self._db.get('galaxy_user', id=session[0]['user_id'])


        if len(user) == 0:
            self._init_user_tos(session[0]['user_id'])
            user = self.get_user_tos(session_key)
        else:
            user = user[0]

        user['current_history_id'] = session[0]['current_history_id']

        return user

    def get_user(self, **values) -> {}:
        return self._db.get('galaxy_user', **values)

    def update_tos(self, tos:dict) -> None:
        self._db.update('nels_tos', tos, {'id': tos['id']} )

    def create_tos_table(self) -> None:
        if self.table_exist('nels_tos'):
            return

        q = '''CREATE TABLE nels_tos (
              id             SERIAL PRIMARY KEY,
              user_id        INT REFERENCES galaxy_user(id),
              status         VARCHAR(80),
              tos_date       TIMESTAMP
              );
            '''
        self._db.do( q )


    def create_export_tracking_table(self) -> None:
        if self.table_exist('nels_export_tracking'):
            return

        q = '''CREATE TABLE nels_export_tracking (
              id             SERIAL PRIMARY KEY,
              instance       VARCHAR(80),
              user_email     VARCHAR(80),
              history_id     VARCHAR(80),
              export_id      VARCHAR(80),
              state          VARCHAR(80),
              create_time    TIMESTAMP,
              update_time    TIMESTAMP,
              nels_id        INT,
              destination    VARCHAR(80),
              tmpfile        VARCHAR(300)
              );
            '''
        self._db.do( q )


    def add_export_tracking(self, values:{}):
        values['create_time'] = datetime.datetime.now()
        self._db.add('nels_export_tracking', values)

    def update_export_tracking(self, tracking_id:int, values:{}):
        values['update_time'] = datetime.datetime.now()
        self._db.update('nels_export_tracking', values, {'id': tracking_id})


    def get_export_trackings(self, **values):
        return self._db.get('nels_export_tracking', **values)

    def get_export_tracking(self, tracking_id:int):
        return self._db.get_single('nels_export_tracking', id=tracking_id)




    def get_user_history_exports(self, user_id:int) -> []:
        exports = self.get_all_user_history_exports(user_id)

        cleaned_exports = {}

        for export in exports:
            if export['history_id'] not in cleaned_exports:
                cleaned_exports[export['history_id']] = export

            elif cleaned_exports[export['history_id']]['create_time'] < export['create_time']:
                cleaned_exports[export['history_id']] = export

        return list(cleaned_exports.values())


    def get_dataset(self, dataset_id:int) -> {}:

        r = self._db.get_by_id('dataset', dataset_id)

        if isinstance(r, list) and len(r):
            r = r[0]

        return r




    def get_all_user_history_exports(self, user_id:int) -> []:
        q = '''select ha.id as export_id, ha.dataset_id, ha.history_id, h.name, job.create_time, job.state, job.id as job_id  
               from galaxy_user as ga, history as h, job_export_history_archive as ha, job 
               where ga.id = {user_id} and 
                     ga.id = h.user_id and 
                     h.id = ha.history_id 
                     and job.id = ha.job_id;
            '''

        return( self._db.get_as_dict(q.format( user_id=user_id )))


    def get_export(self, export_id:int) -> []:
        q = '''select ha.id as export_id, ha.dataset_id, ha.history_id, h.name, job.create_time, job.state, job.id as job_id  
               from history as h, job_export_history_archive as ha, job 
               where ha.id = {export_id} and  
                     h.id = ha.history_id 
                     and job.id = ha.job_id;
            '''

        return( self._db.get_as_dict(q.format( export_id=export_id )))

    def get_latest_export_for_history(self, history_id:int) -> []:
        q = '''select ha.id as export_id, ha.dataset_id, ha.history_id, h.name, job.create_time, job.state, job.id as job_id  
               from history as h, job_export_history_archive as ha, job 
               where ha.history_id = {history_id} and  
                     h.id = ha.history_id 
                     and job.id = ha.job_id
               ORDER BY ha.id DESC LIMIT 1;
            '''

        return( self._db.get_as_dict(q.format( history_id=history_id )))


    def get_exports(self, state:str="") -> []:
        exports = self.get_all_exports()

        cleaned_exports = {}

        for export in exports:
            if export['history_id'] not in cleaned_exports:
                cleaned_exports[export['history_id']] = export

            elif cleaned_exports[export['history_id']]['create_time'] < export['create_time']:
                cleaned_exports[export['history_id']] = export

        if state != '':
            tmp_exports = {}
            for name in cleaned_exports:
                export = cleaned_exports[ name ]
                if export['state'] == state:
                    tmp_exports[ name ] = export

            cleaned_exports = tmp_exports

        return list(cleaned_exports.values())


    def get_all_exports(self,state:str="") -> []:
        if state != "":
            state = f" and job.state = '{state}'"

        q = '''select ha.id as export_id, dataset_id, ha.history_id, h.name as history_name, ga.id as user_id, ga.email, job.create_time, job.state  
               from job_export_history_archive as ha, galaxy_user as ga, history as h, job 
               where ga.id = h.user_id and 
                     h.id = ha.history_id and 
                    job.id = ha.job_id {state} 
               order by ha.id;
            '''

        return( self._db.get_as_dict(q.format(state=state)))


    def get_user_histories(self, user_id:int) -> []:
        q = "select id, update_time, name, hid_counter from history where user_id={user_id};"
        return( self._db.get_as_dict(q.format( user_id=user_id )))

    def get_all_histories(self) -> []:
        q = "select id, update_time, user_id, name from history as h order by id;"
        return( self._db.get_as_dict(q))


    def get_users(self) -> []:
        q = "select id, email, active, deleted from galaxy_user;"
        return( self._db.get_as_dict(q))


    def get_job(self, job_id:int) -> {}:
        return self._db.get_by_id('job', job_id)

    def update_job(self, values:{}) -> {}:
        # This does not work, look into bioblend it.
        return self._db.update('job', values, {'id': values['id']})


    def get_history(self, history_id:int) -> {}:
        return self._db.get('history', id=history_id)
