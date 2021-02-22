import unittest


import nels_galaxy_api.api_requests as requests

# Tests basic (and not so basic) galaxy api functionality

base_url = 'http://localhost:8008'
instance = 'usegalaxy'
user     = 3
token    = 'my_secret'

def test_set_token():
    requests.set_token( token )


def test_request_get():

    requests.set_token( token )
    response, return_token = requests.request_get(base_url)
    assert return_token == token

def test_request_post():

    requests.set_token( token )
    response, return_token = requests.request_post(base_url, {'user': 'me'})
    assert return_token == token

def test_request_patch():

    requests.set_token( token )
    response, return_token = requests.request_patch(base_url, {'user': 'me'})
    assert return_token == token

def test_request_delete():

    requests.set_token( token )
    response, return_token = requests.request_delete(base_url, {'user': 'me'})
    assert return_token == token

def test_get_info():

    requests.set_token( token )
    r = requests.get_info(base_url)
    assert True

def test_get_users():

    requests.set_token( token )
    r = requests.get_users(base_url)
    assert True

def test_get_user_histories():

    requests.set_token( token )
    r = requests.get_user_histories(base_url, 3)
    assert True

def test_get_user_history_exports():

    requests.set_token( token )
    r = requests.get_user_history_exports(base_url, 3)
    assert True

def test_get_history_exports():

    requests.set_token( token )
    r = requests.get_history_exports(base_url)
    assert True

def test_get_history_export():

    requests.set_token( token )
    r = requests.get_history_export(base_url, 13)
    assert True

def test_encrypt():

    requests.set_token( token )
    r = requests.encrypt(base_url, 13)
    assert True

#def test_decrypt():

#    requests.set_token( token )
#    r = requests.decrypt(base_url, "bc729496af0697be")
#    assert True

def test_add_history_export():

    requests.set_token( token )
    data = {"nels_id": 3, "selectedFiles": ["goes_here"]}
    r = requests.add_export(base_url, instance, user, 3, data)
    assert True

def test_add_bulk_history_export():

    requests.set_token( token )
    data = {"nels_id": 3, "selectedFiles": ["goes_here"]}
    r = requests.add_bulk_export(base_url, instance, user, data)
    assert True

def test_get_export():
    requests.set_token( token )
    r = requests.get_history_export(base_url, 3)
    assert True

def test_update_export():
    requests.set_token( token )

    r = requests.update_export(base_url, 3, data={"state": "new"})
    assert True

def test_get_user_instance_exports():
    requests.set_token( token )
    r = requests.get_user_instance_exports(base_url, user, instance)
    assert True


def test_get_user_exports():
    requests.set_token( token )
    r = requests.get_user_exports(base_url, user)
    assert True

def test_get_all_exports():
    requests.set_token( token )
    r = requests.get_instance_exports(base_url, user)
    assert True

def test_get_exports():
    requests.set_token( token )
    r = requests.get_history_exports(base_url)
    assert True
