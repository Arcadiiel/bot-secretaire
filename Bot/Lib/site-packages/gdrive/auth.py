import json
import logging
import os
import pickle
import secretstorage
import urllib.request
import base64
from typing import Type, TypeVar, List, Dict
from urllib.parse import urlparse, parse_qs
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from gdrive.exception import SettingsException
from pathlib import Path

GA = TypeVar('GA', bound='GoogleAuth')
log = logging.getLogger(__name__)


class GoogleAuth:
    def __init__(self, credentials: Credentials, **kwargs):
        self.credentials = credentials

    @classmethod
    def from_settings(cls: Type[GA], token_file: str, secrets_file_qs: str, scopes: List[str], ssl_context=None) -> GA:
        '''
        Load credentials from local file or rest api
        Provide proper query string

        :param token_file:
        :param secrets_file_qs:
        :param scopes:
        :return:
        '''

        def fetch():
            try:
                res = urllib.request.urlopen(secrets_file_qs, context=ssl_context)
            except ConnectionRefusedError as e:
                msg = f"Cannot connect to secret API: {secrets_file_qs}"
                log.exception(msg)
                raise SettingsException(msg)
            data = json.loads(res.read().decode(res.info().get_param('charset') or 'utf-8'))
            config = data[0]
            return config

        parsed_qs = urlparse(secrets_file_qs)
        credentials = None
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                credentials = pickle.load(token)
        elif parsed_qs.scheme.startswith('http'):
            config = fetch()
            token_file_basename = os.path.basename(token_file)
            remote_token = next((e[1] for e in config['attachments'] if e[0] == token_file_basename), None)
            if remote_token:
                credentials = pickle.loads(base64.b64decode(remote_token))

        # If there are no (valid) credentials available, let the user log in.
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow

                if parsed_qs.scheme.startswith('http'):
                    if config is None:
                        config = fetch()
                    secret_json = json.loads(config['secret'])
                    flow = InstalledAppFlow.from_client_config(secret_json, scopes)
                elif parsed_qs.scheme == 'file' or parsed_qs.scheme == '':
                    secrets_file = parsed_qs.path
                    flow = InstalledAppFlow.from_client_secrets_file(secrets_file, scopes)
                else:
                    raise SettingsException(f"{secrets_file_qs} cannot be handled")

                credentials = flow.run_local_server(port=0)
            # Save the credentials for the next run
            Path(token_file).parent.mkdir(exist_ok=True, parents=True)
            with open(token_file, 'wb') as token:
                pickle.dump(credentials, token)
                # todo all creadentials present, upload to underlying password service?
                # the token might got refreshed - it would be good to upload it
        return GoogleAuth(credentials)
