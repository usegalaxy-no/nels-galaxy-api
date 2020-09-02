from requests import Request, Session

import json
import kbr.requests_utils as requests_utils


class ApiRequests( object ):
    def __init__(self, base_url:str, token:str=None):
        self._token = token
        self._base_url = base_url

    def set_token(new_token:str):
        self._token = new_token

    def _request_get(self, url:str, as_json:bool=True, data:{}=None):
        return self._generic_request(url, as_json, call='GET', data=data, send_as_json=False)

    def _request_post(self, url:str, data:{}):
        return self._generic_request(url, call='POST', data=data)

    def _request_patch(self, url:str, data:{}):
        return self._generic_request(url, call='PATCH', data=data)

    def _request_delete(self, url:str, data:{}):
        return self._generic_request(url, call='DELETE', data=data)




    def _generic_request(self, url:str, as_json:bool=True, call='GET', data:{}=None, send_as_json:bool=True):

        s = Session()
        if send_as_json:
            req = Request(call,  url, json=data)
        else:
            req = Request(call,  url, data=data)

        prepped = s.prepare_request(req)


        if self._token is not None:
            prepped.headers['Authorization'] = f"bearer {self._token}"

        r = s.send(prepped)
        r.raise_for_status()

        if as_json and r.text:
            return json.loads( r.text )
        elif r.text:
            return None


# Basic stuff shared between the two api's

    def get_base(self) -> {}:
        return self._request_get(f"{self._base_url}/")

    def get_info(self) -> {}:
        return self._request_get(f"{self._base_url}/info/")

    def get_state(self, state_id) -> {}:
        return self._request_get(f"{self._base_url}/state/{state_id}/")

    def get_users(self) -> []:
        return self._request_get(f"{self._base_url}/users")

    def get_user_histories(self, user_id:str) -> []:
        return self._request_get(f"{self._base_url}/user/{user_id}/histories")

    def get_user_history_exports(self, user_id:str) -> []:
        return self._request_get(f"{self._base_url}/user/{user_id}/exports")

    def get_history_exports(self, filter:{}={}) -> []:
        return self._request_get(f"{self._base_url}/history/exports", data=filter)

    def get_history_export(self, export_id:str=None, history_id:str=None):

        if export_id is not None:
            return self._request_get(f"{self._base_url}/history/export/{export_id}")
        elif history_id is not None:
            return self._request_get(f"{self._base_url}/history/export/?history_id={history_id}")
        else:
            raise RuntimeError('provide either export_id or history_id.')

    def history_export_request(self) -> {}:
        return self._request_get(f"{self._base_url}/history/export/request/")


    def decrypt(self, export_id:str):
        return self._request_get(f"{self._base_url}/decrypt/{export_id}")

    def encrypt(self, export_id:str):
        return self._request_get(f"{self._base_url}/encrypt/{export_id}")

    # full api specific functionality:
    ###############################################
    def add_export(self, instance:str, user:str, history_id:str, data:{}):
        return self._request_post(f"{self._base_url}/export/{instance}/{user}/{history_id}/", data=data)

    def add_bulk_export(self, instance:str, user:str, data:{}):
        return self._request_post(f"{self._base_url}/export/{instance}/{user}/bulk/", data)

    def get_export(self, tracking_id:str):
        return self._request_get(f"{self._base_url}/export/{tracking_id}/")

    def update_export(self, tracking_id:str, data:{}):
        return self._request_patch(f"{self._base_url}/export/{tracking_id}/", data=data)

    def get_user_instance_exports(self, user:str, instance:str):
        return self._request_get(f"{self._base_url}/exports/{user}/{instance}/")

    def get_user_exports(self, user:str):
        return self._request_get(f"{self._base_url}/exports/{user}/")

    def get_instance_exports(self, instance:str, filter):
        return self._request_get(f"{self._base_url}/exports/all/{instance}/", data=filter)

    def get_exports(self):
        return self._request_get(f"{self._base_url}/exports/")

    def get_proxy(self):
        return self._request_get(f"{self._base_url}/proxy/")

# Need these as the request thingy has changed slightly
def set_token(new_token:str):
    requests_utils.set_token( new_token)

def update_export(base_url:str, tracking_id:str, data:dict):
    return requests_utils.patch(f"{base_url}/export/{tracking_id}/", data=data)

def get_user_instance_exports(base_url, user:str, instance:str):
    return requests_utils.get(f"{base_url}/exports/{user}/{instance}/")
