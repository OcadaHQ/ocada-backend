from typing import Optional
import jwt
from jwt.algorithms import RSAAlgorithm
import requests
from time import time
import json
import os
from app.api.exceptions import SnipsInvalidExternalTokenError
from app.api.constants import APPLE_BUNDLE_ID


class AppleUser(object):
    def __init__(self, user_id: str, email: str, name: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None, raw: any = None):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.first_name = first_name
        self.last_name = last_name
        self.raw = raw


    def __repr__(self):
        return "<AppleUser {}>".format(self.id)


class AppleAuth():
    def __init__(self):

        self.APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"
        self.APPLE_PUBLIC_KEYS = {}
        self.APPLE_KEY_CACHE_EXP = 60 * 60 * 24
        self.APPLE_LAST_KEY_FETCH = 0

    def _refresh_apple_public_keys(self):

        if (self.APPLE_LAST_KEY_FETCH + self.APPLE_KEY_CACHE_EXP) < int(time()) or not self.APPLE_PUBLIC_KEYS:
            key_payload = requests.get(self.APPLE_PUBLIC_KEY_URL).json()
            
            for key_dict in key_payload["keys"]:
                kid = key_dict['kid']
                self.APPLE_PUBLIC_KEYS[kid] = RSAAlgorithm.from_jwk(json.dumps(key_dict))
            self.APPLE_LAST_KEY_FETCH = int(time())

    def validate_jwt(self, apple_user_token):
        
        self._refresh_apple_public_keys()

        try:

            unverified_token = jwt.get_unverified_header(apple_user_token)
            kid = unverified_token['kid']
            if kid not in self.APPLE_PUBLIC_KEYS:
                raise KeyError("Invalid public key id")

            token = jwt.decode(
                jwt=apple_user_token,
                key=self.APPLE_PUBLIC_KEYS.get(kid, None),
                algorithms=["RS256"],
                audience=APPLE_BUNDLE_ID # os.getenv("APPLE_APP_ID")
                )
            
        except jwt.exceptions.InvalidSignatureError as e:
            print('invalid signature')
            raise SnipsInvalidExternalTokenError('invalid signature')
        except jwt.exceptions.ExpiredSignatureError as e:
            print("token expired")
            raise SnipsInvalidExternalTokenError("That token has expired")
        except jwt.exceptions.InvalidAudienceError as e:
            print("token audience did not match")
            raise SnipsInvalidExternalTokenError("That token's audience did not match")
        except Exception as e:
            print(e)
            raise SnipsInvalidExternalTokenError("An unexpected error occurred")

        return AppleUser(
            user_id=token["sub"],
            email=token["email"],
            raw=token
        )
