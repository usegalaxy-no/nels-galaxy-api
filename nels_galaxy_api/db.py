import kbr.db_utils as db
import datetime


class DB(object):

    def connect(self, url: str) -> None:
        self._db = db.DB(url)

    def disconnect(self) -> None:

        if self._db is not None:
            self._db.close()

    def table_exist(self, name: str) -> bool:
        q = f"SELECT to_regclass('{name}')"
        table = self._db.get_as_dict(q)
        if table[0]['to_regclass'] is None:
            return False

        return True

    def get_session(self, session_key: str) -> bool:

        return self._db.get('galaxy_session', session_key=session_key)

    def _init_user_tos(self, user_id: int) -> {}:
        self._db.add('nels_tos', {'user_id': user_id,
                                  'status': 'grace',
                                  'tos_date': datetime.datetime.now() + datetime.timedelta(days=14)})

    def get_user_tos(self, session_key: str) -> {}:
        session = self.get_session(session_key)

        if session is None or session[0]['is_valid'] != True or session[0]['user_id'] is None:
            return None

        tos = self._db.get('nels_tos', user_id=session[0]['user_id'])

        if len(tos) == 0:
            self._init_user_tos(session[0]['user_id'])
            tos = self.get_user_tos(session_key)
        else:
            tos = tos[0]

        return tos

    def get_user_from_session(self, session_key: str) -> {}:
        session = self.get_session(session_key)

        if session is None or session[0]['is_valid'] != True or session[0]['user_id'] is None:
            return None

        user = self._db.get('galaxy_user', id=session[0]['user_id'])

        if len(user) == 0:
            self._init_user_tos(session[0]['user_id'])
            user = self.get_user_tos(session_key)
        else:
            user = user[0]

        user['current_history_id'] = session[0]['current_history_id']

        return user

    def get_user(self, **values) -> {}:
        return self._db.get('galaxy_user', **values)

    def update_tos(self, tos: dict) -> None:
        self._db.update('nels_tos', tos, {'id': tos['id']})

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
        self._db.do(q)

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
              tmpfile        VARCHAR(300),
              show           BOOL DEFAULT 'true'
              );
            '''
        self._db.do(q)

    def add_export_tracking(self, values):
        values['create_time'] = datetime.datetime.now()

        log = None
        if 'log' in values:
            log = values['log']
            del values['log']

        self._db.add('nels_export_tracking', values)
        tracking_id = self._db.get_id('nels_export_tracking', **values)
  #      self.add_export_tracking_log(tracking_id, state="Created", log)
        return tracking_id


    def update_export_tracking(self, tracking_id: int, values: {}):
        values['update_time'] = datetime.datetime.now()

        log = None
        if 'log' in values:
            log = values['log']
            del values['log']

        self._db.update('nels_export_tracking', values, {'id': tracking_id})
        if 'state' in values:
            self.add_export_tracking_log(tracking_id, state=values['state'], log=log)


    def create_export_tracking_logs_table(self) -> None:
        if self.table_exist('nels_export_tracking_log'):
            return

        q = '''CREATE TABLE nels_export_tracking_log (
                  id             SERIAL PRIMARY KEY,
                  create_time    TIMESTAMP,
                  tracking_id    INT,
                  log            VARCHAR(80)
               ); '''
        self._db.do(q)

    def add_export_tracking_log(self, tracking_id: int, state: str, log:str=None) -> None:
        values = {'create_time': datetime.datetime.now(),
                  'tracking_id': tracking_id,
                  'log': log}
        if log is None:
            values[ 'log' ] = f"Changed state to {state}"


        self._db.add('nels_export_tracking_log', values)

    def get_export_trackings(self, **values):
        return self._db.get('nels_export_tracking', **values)

    def get_export_tracking(self, tracking_id: int):
        return self._db.get_single('nels_export_tracking', id=tracking_id)

    def get_user_history_exports(self, user_id: int) -> []:
        exports = self.get_all_user_history_exports(user_id)

        cleaned_exports = {}

        for export in exports:
            if export['history_id'] not in cleaned_exports:
                cleaned_exports[export['history_id']] = export

            elif cleaned_exports[export['history_id']]['create_time'] < export['create_time']:
                cleaned_exports[export['history_id']] = export

        return list(cleaned_exports.values())

    def get_dataset(self, dataset_id: int) -> {}:

        r = self._db.get_by_id('dataset', dataset_id)

        if isinstance(r, list) and len(r):
            r = r[0]

        return r

    def get_all_user_history_exports(self, user_id: int) -> []:
        q = '''select ha.id as export_id, ha.dataset_id, ha.history_id, h.name, job.create_time, job.state, job.id as job_id  
               from galaxy_user as ga, history as h, job_export_history_archive as ha, job 
               where ga.id = {user_id} and 
                     ga.id = h.user_id and 
                     h.id = ha.history_id 
                     and job.id = ha.job_id;
            '''

        return (self._db.get_as_dict(q.format(user_id=user_id)))

    def get_export(self, export_id: int) -> []:
        q = '''select ha.id as export_id, ha.dataset_id, ha.history_id, h.name, job.create_time, job.state, job.id as job_id  
               from history as h, job_export_history_archive as ha, job 
               where ha.id = {export_id} and  
                     h.id = ha.history_id 
                     and job.id = ha.job_id;
            '''

        return (self._db.get_as_dict(q.format(export_id=export_id)))

    def get_latest_export_for_history(self, history_id: int) -> []:
        q = '''select ha.id as export_id, ha.dataset_id, ha.history_id, h.name, job.create_time, job.state, job.id as job_id  
               from history as h, job_export_history_archive as ha, job 
               where ha.history_id = {history_id} and  
                     h.id = ha.history_id 
                     and job.id = ha.job_id
               ORDER BY ha.id DESC LIMIT 1;
            '''

        return (self._db.get_as_dict(q.format(history_id=history_id)))

    def get_exports(self, state: str = "") -> []:
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
                export = cleaned_exports[name]
                if export['state'] == state:
                    tmp_exports[name] = export

            cleaned_exports = tmp_exports

        return list(cleaned_exports.values())

    def get_all_exports(self, state: str = "") -> []:
        if state != "":
            state = f" and job.state = '{state}'"

        q = '''select ha.id as export_id, dataset_id, ha.history_id, h.name as history_name, ga.id as user_id, ga.email, job.create_time, job.state  
               from job_export_history_archive as ha, galaxy_user as ga, history as h, job 
               where ga.id = h.user_id and 
                     h.id = ha.history_id and 
                    job.id = ha.job_id {state} 
               order by ha.id;
            '''

        return (self._db.get_as_dict(q.format(state=state)))

    def get_user_histories(self, user_id: int) -> []:
        q = "select id, update_time, name, hid_counter from history where user_id={user_id};"
        return (self._db.get_as_dict(q.format(user_id=user_id)))

    def get_all_histories(self) -> []:
        q = "select id, update_time, user_id, name from history as h order by id;"
        return (self._db.get_as_dict(q))

    def get_users(self) -> []:
        q = "select id, email, active, deleted from galaxy_user;"
        return (self._db.get_as_dict(q))

    def get_job(self, job_id: int) -> {}:
        return self._db.get_by_id('job', job_id)

    def update_job(self, values: {}) -> {}:
        # This does not work, look into bioblend it.
        return self._db.update('job', values, {'id': values['id']})

    def get_history(self, history_id: int) -> {}:
        return self._db.get('history', id=history_id)

    def add_api_key(self, user_id:int, key:str):
        values = {'user_id': user_id,
                  'key': key,
                  'create_time': datetime.datetime.now()
                  }
        self._db.add('api_keys', values)

    def get_api_key(self, user_id:int):
        values = self._db.get('api_keys', user_id=user_id, order=" create_time desc", limit=1)
        if len( values ) == 1:
            return values[ 0 ]

        return None




    def get_imports(self, state: str = "") -> []:
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
                export = cleaned_exports[name]
                if export['state'] == state:
                    tmp_exports[name] = export

            cleaned_exports = tmp_exports

        return list(cleaned_exports.values())


    def get_all_imports(self, state: str = "") -> []:
        if state != "":
            state = f" and job.state = '{state}'"

        q = '''select ha.id as import_id, ha.history_id, h.name as history_name, ga.id as user_id, ga.email, job.create_time, job.state  
               from job_import_history_archive as ha, galaxy_user as ga, history as h, job 
               where ga.id = h.user_id and 
                     h.id = ha.history_id and 
                    job.id = ha.job_id {state} 
               order by ha.id;
            '''

        return (self._db.get_as_dict(q.format(state=state)))

    def get_all_user_history_imports(self, user_id: int) -> []:
        q = '''select ha.id as import_id, ha.history_id, h.name, job.create_time, job.state, job.id as job_id  
               from galaxy_user as ga, history as h, job_import_history_archive as ha, job 
               where ga.id = {user_id} and 
                     ga.id = h.user_id and 
                     h.id = ha.history_id 
                     and job.id = ha.job_id;
            '''

        return (self._db.get_as_dict(q.format(user_id=user_id)))

    def get_import(self, import_id: int) -> []:
        q = '''select ha.id as import_id, ha.history_id, h.name, job.create_time, job.state, job.id as job_id  
               from history as h, job_import_history_archive as ha, job 
               where ha.id = {import_id} and  
                     h.id = ha.history_id 
                     and job.id = ha.job_id;
            '''

        return (self._db.get_as_dict(q.format(import_id=import_id)))

    def imports(self, user_id: int) -> []:
        imports = self.get_all_user_history_imports(user_id)

        cleaned_imports = {}

        for imp in imports:
            if imp['history_id'] not in cleaned_imports:
                cleaned_imports[imp['history_id']] = imp

            elif cleaned_imports[imp['history_id']]['create_time'] < imp['create_time']:
                cleaned_imports[imp['history_id']] =imp

        return list(cleaned_imports.values())


    def create_import_tracking_table(self) -> None:
        if self.table_exist('nels_import_tracking'):
            return

        q = '''CREATE TABLE nels_import_tracking (
              id             SERIAL PRIMARY KEY,
              user_id        INT,
              import_id      VARCHAR(80),
              state          VARCHAR(80),
              create_time    TIMESTAMP,
              update_time    TIMESTAMP,
              nels_id        INT,
              source         VARCHAR(80),
              tmpfile        VARCHAR(300),
              show           BOOL DEFAULT 'true'
              );
            '''
        self._db.do(q)

    def add_import_tracking(self, values):
        values['create_time'] = datetime.datetime.now()

        log = None
        if 'log' in values:
            log = values['log']
            del values['log']

        self._db.add('nels_import_tracking', values)
        tracking_id = self._db.get_id('nels_import_tracking', **values)
        self.add_import_tracking_log(tracking_id, state="Created", log=log)
        return tracking_id


    def update_import_tracking(self, tracking_id: int, values: {}):
        values['update_time'] = datetime.datetime.now()

        log = None
        if 'log' in values:
            log = values['log']
            del values['log']

        self._db.update('nels_import_tracking', values, {'id': tracking_id})
        if 'state' in values:
            self.add_import_tracking_log(tracking_id, state=values['state'], log=log)


    def get_import_trackings(self, **values):
        return self._db.get('nels_import_tracking', **values)

    def get_import_tracking(self, tracking_id: int):
        return self._db.get_single('nels_import_tracking', id=tracking_id)

    def create_import_tracking_logs_table(self) -> None:
        if self.table_exist('nels_import_tracking_log'):
            return

        q = '''CREATE TABLE nels_import_tracking_log (
                  id             SERIAL PRIMARY KEY,
                  create_time    TIMESTAMP,
                  tracking_id    INT,
                  log            VARCHAR(80)
               ); '''
        self._db.do(q)


    def add_import_tracking_log(self, tracking_id: int, state: str, log:str=None) -> None:
        values = {'create_time': datetime.datetime.now(),
                  'tracking_id': tracking_id,
                  'log': log}
        if log is None:
            values[ 'log' ] = f"Changed state to {state}"

        self._db.add('nels_import_tracking_log', values)

    def get_user_history_imports(self, user_id: int):
        imports = self.get_all_user_history_imports(user_id)

        cleaned_imports = {}

        for imp in imports:
            if imp['history_id'] not in cleaned_imports:
                cleaned_imports[imp['history_id']] = imp

            elif cleaned_imports[imp['history_id']]['create_time'] < imp['create_time']:
                cleaned_imports[imp['history_id']] = imp

        return list(cleaned_imports.values())



    def get_jobs(self, time_delta:int=None, user_id:str=None) -> []:
        q = 'select  j.update_time, tool_id, j.user_id, email, state, job_runner_name, destination_id from job j, galaxy_user gu where gu.id=j.user_id {filter} order by j.id'

        filter = ""

        if time_delta is not None:
            print( time_delta )
            filter += f" and j.update_time > now() - interval '{time_delta}' second "

        if user_id is not None:
            filter += f" and j.user_id = '{user_id}' "

        q = q.format(filter=filter)

        return (self._db.get_as_dict(q))


