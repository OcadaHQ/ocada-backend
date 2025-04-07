from typing import Optional
import requests
from app.api.exceptions import SnipsInvalidExternalTokenError


class GoogleUser(object):
    def __init__(self, user_id: str, email: str, name: Optional[str] = None, raw: any = None):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.raw = raw

    def __repr__(self):
        return "<GoogleUser {}>".format(self.id)


class GoogleAuth():
    def __init__(self):
        self.userinfo_url = 'https://www.googleapis.com/userinfo/v2/me'
    
    def validate_access_token(self, access_token: str):
        response = requests.get(self.userinfo_url, headers={'Authorization': f'Bearer {access_token}'})
        if response.status_code == 200:
            return GoogleUser(
                user_id=response.json()['id'],
                email=response.json()['email'],
                name=response.json()['name'],
                raw=response.json()
            )
        else:
            raise SnipsInvalidExternalTokenError('Invalid Google access token')
