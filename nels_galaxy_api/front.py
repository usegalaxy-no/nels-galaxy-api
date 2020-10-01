import pprint as pp

import kbr.timedate_utils as timedate_utils

import nels_galaxy_api.utils as nga_utils


def get_users( config:{}, instance_name:str=None, summary=False ):

    users = []
    brief = []

    for instance_id in config['instances']:
        if instance_name and instance_id != instance_name:
            continue

        if config['instances'][ instance_id]['name'] != instance_id:
            continue

        instance = config['instances'][ instance_id]

        instance_users = []
        tmp_users = instance['api'].get_users()
        brief.append({'name': instance['name'], 'users': len(tmp_users)})

        for tmp_user in tmp_users:

            tmp_user['instance'] = instance['name']
            tmp_user['active'] = bool(tmp_user['active'])
            tmp_user['deleted'] = bool(tmp_user['deleted'])

            instance_users.append( tmp_user )

        users += sorted(instance_users, key=lambda x: x['email'].lower())

    if summary:
        return brief

    return users


def get_histories( config:{}, instance_name:str=None, user_email:str=None, summary=False):

    histories = []
    brief     = []


    for instance_id in config['instances']:
        if instance_name and instance_id != instance_name:
            continue

        if config['instances'][ instance_id]['name'] != instance_id:
            continue

        instance = config['instances'][ instance_id]

        users = instance['api'].get_users()
        users = sorted(users, key=lambda x: x['email'].lower())

        for user in users:
            if user_email is not None and user['email'] != user_email:
                continue

            tmp_histories = instance['api'].get_user_histories(user['email'])
            brief.append({'name':instance['name'], 'user': user['email'], 'histories': len( tmp_histories )})
            for tmp_history in tmp_histories:
                tmp_history['instance'] = instance['name']
                tmp_history['changed'] = nga_utils.readable_date(tmp_history['update_time'])
                del tmp_history['update_time']

                tmp_history['user'] = user['email']
                del tmp_history['hid_counter']

                histories.append( tmp_history )


    if summary:
        return brief

    return histories


def get_exports( config:{}, instance_name:str=None, user_email:str=None, summary=False, full=False):

    exports = []
    brief     = []

    for instance_id in config['instances']:
        if instance_name and instance_id != instance_name:
            continue

        if config['instances'][ instance_id]['name'] != instance_id:
            continue

        instance = config['instances'][ instance_id]

        users = instance['api'].get_users()
        users = sorted(users, key=lambda x: x['email'].lower())

        for user in users:
            if user_email is not None and user['email'] != user_email:
                continue

            tmp_exports = instance['api'].get_user_history_exports(user['email'])
            nr_exports = len( tmp_exports )
            if not nr_exports:
                continue

            brief.append({'name':instance['name'], 'user': user['email'], 'instance exports':  nr_exports })
            for tmp_export in tmp_exports:
                if not full:
                    del tmp_export['export_id']
                    del tmp_export['job_id']
                    del tmp_export['history_id']

                tmp_export['instance'] = instance['name']
                tmp_export['user'] = user['email']
                tmp_export['created'] = nga_utils.readable_date(tmp_export['create_time'])
                del tmp_export['create_time']

                exports.append( tmp_export )

    if summary:
        return brief

    return exports


def get_imports( config:{}, user_email:str=None, summary=False, full=False):

    imports = []
    brief     = []


    users = config['master_api'].get_users()
    users = sorted(users, key=lambda x: x['email'].lower())

    for user in users:
        if user_email is not None and user['email'] != user_email:
            continue

        tmp_imports = config['master_api'].get_user_history_imports(user['email'])
        nr_imports = len( tmp_imports )
        if not nr_imports:
            continue

        brief.append({'user': user['email'], 'imports':  nr_imports })
        for tmp_import in tmp_imports:
            if not full:
                del tmp_import['import_id']
                del tmp_import['job_id']
                del tmp_import['history_id']
            #                del tmp_import['tmpfile']

            tmp_import['user'] = user['email']
            tmp_import['created'] = nga_utils.readable_date(tmp_import['create_time'])
            del tmp_import['create_time']

            imports.append( tmp_import )


    if summary:
        return brief

    return imports


def get_export_requests(config, time_delta) -> []:

    exports = []

    for request in config['master_api'].get_exports():
        create_time = timedate_utils.datestr_to_ts(request['create_time'])
        create_time = timedate_utils.to_sec_since_epoch(create_time)

        if time_delta:
            if time_delta <= create_time:
                exports.append(request)
        else:
            exports.append(request)

    return exports

def get_import_requests(config, time_delta) -> []:

    imports = []

    for request in config['master_api'].get_imports():
        create_time = timedate_utils.datestr_to_ts(request['create_time'])
        create_time = timedate_utils.to_sec_since_epoch(create_time)

        if time_delta:
            if time_delta <= create_time:
                imports.append(request)
        else:
            imports.append(request)

    return imports