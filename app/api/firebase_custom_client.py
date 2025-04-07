import json
import requests
import firebase_admin
from datetime import datetime
from firebase_admin import firestore, credentials
from google.cloud.firestore_v1.base_query import FieldFilter
from fastapi import HTTPException
from app.api.tools.utils import encoded_var_to_creds

class FirebaseAdminClient:
    def __init__(self, service_account_path):
        self.creds = credentials.Certificate(service_account_path)
        self.app = firebase_admin.initialize_app(self.creds)
        self.db = firestore.client()
    
    def get_firestore_client(self):
        return self.db
    
    def conversation_seen(self, conversation_id, user_id):
        conversations_doc_ref = self.db.collection(f'conversations/user_{user_id}/user_conversations').document(conversation_id)
        if not conversations_doc_ref.get().exists:
            conversations_doc_ref.set({})
        conversations_doc_ref.set({'unseen': False}, merge=True)
        print(f'[user_{user_id}] marked {conversation_id} conversation as seen')

    def lock_user(self, user_id):
        current_ts = datetime.now().timestamp()
        user_ref = self.db.collection("conversations").document(f'user_{user_id}')
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            started_generating = user_data.get("started_generating", None)

            if not started_generating:
                user_ref.update({"started_generating": current_ts})
                print(f"[user_{user_id}] locked the user with {current_ts}")
                return True

            diff = datetime.now() - datetime.fromtimestamp(float(started_generating))
            if diff.total_seconds() > 60:
                user_ref.update({"started_generating": current_ts})
                print(f"[user_{user_id}] WARNING: There was a timestamp set:{started_generating}, replaced it with {current_ts}")
                return True
            else:
                print(f"[user_{user_id}] WARNING: There is a job in progress, started recently:{started_generating}")
                return False
        else:
            user_ref.set({"started_generating": current_ts})
            print(f"[user_{user_id}] locked the user with {current_ts}")
            return True

    def release_user(self, user_id):
        user_ref = self.db.collection("conversations").document(f'user_{user_id}')
        try:
            user_ref.update({
                'started_generating': firestore.DELETE_FIELD
            })
            print(f"[user_{user_id}] user released")
        except Exception as e:
            print(f"[user_{user_id}] ERROR: failed to release a user, reason: {e}")
            
    def init_user_conversations(self, user_id):
        user_doc_ref = self.db.document(f'conversations/user_{user_id}')
        if not user_doc_ref.get().exists:
            user_doc_ref.set({})
            print(f'[user_{user_id}] created new user collection')
        # # Setup news
        # news_ref = self.db.collection(f'conversations/user_{user_id}/user_conversations').document('news')
        # if not news_ref.get().exists:
        #     news_ref.set({
        #         'display_name': 'Market News 🗞️',
        #         # 2226 year
        #         'last_update': 9999999998,
        #         'unseen': True
        #     })
        #     print(f'[user_{user_id}] created news document')
        # last_news = self.get_last_records('news', 5)
        # for rec in last_news:
        #     self._create_message_doc(
        #         'news',
        #         rec['content'],
        #         rec['sender'],
        #         user_id,
        #         rec['ts'],
        #     )
        # # Setup announcements
        # announcements_ref = self.db.collection(f'conversations/user_{user_id}/user_conversations').document('announcements')
        # if not announcements_ref.get().exists:
        #     announcements_ref.set({
        #         'display_name': 'Announcements 📢',
        #         # 2226 year
        #         'last_update': 9999999999,
        #         'unseen': True
        #     })
        #     print(f'[user_{user_id}] created announcements document')
        # last_ann = self.get_last_records('announcements', 5)
        # for rec in last_ann:
        #     self._create_message_doc(
        #         'announcements',
        #         rec['content'],
        #         rec['sender'],
        #         user_id,
        #         rec['ts'],
        #     )
        # # Setup feedback
        # feedback_ref = self.db.collection(f'conversations/user_{user_id}/user_conversations').document('feedback')
        # if not feedback_ref.get().exists:
        #     feedback_ref.set({
        #         'display_name': 'Feedback 🤗',
        #         # 2226 year
        #         'last_update': 9999999997,
        #         'unseen': True
        #     })
        #     print(f'[user_{user_id}] created feedback document')
        # self._create_message_doc(
        #     'feedback',
        #     "We're thrilled to hear your thoughts on Snips! 😍 \nPlease share your feedback with us so we can continue to enhance your experience 😌\nThe feedback will be rewarded with virtual dollars 💰🤑",
        #     "system",
        #     user_id
        # )

    def save_message(self, message, conversation_id, user_id, sender):
        current_ts = datetime.now().timestamp()
        # We have to init full hierarchy of parent documents explicitly
        conversations_doc_ref = self.db.collection(f'conversations/user_{user_id}/user_conversations').document(conversation_id)
        if not conversations_doc_ref.get().exists:
            conversations_doc_ref.set({})

        # Add conversation metadata
        # Check if "display_name" is already set in the conversation document
        conversation_data = conversations_doc_ref.get().to_dict()
        if 'display_name' not in conversation_data:
            conversation_data['display_name'] = message
        if conversation_id not in ['feedback', 'announcements', 'news']:
            conversation_data['last_update'] = current_ts
        # mark conversation as unseen
        if sender == 'system': conversation_data['unseen'] = True
        conversations_doc_ref.set(conversation_data, merge=True)

        message_data = self._create_message_doc(
            conversation_id,
            message,
            sender,
            user_id,
            current_ts
        )
        print(f'[user_{user_id}] finshed saving message.')
        return message_data

    def save_to_feed(self, collection_name, message_doc):
        conversations_doc_ref = self.db.collection(f'{collection_name}').document(str(message_doc['ts']))
        conversations_doc_ref.set(message_doc)
        print(f'[user_{message_doc["sender"]}] saved to feed under "{message_doc["ts"]}" doc in "{collection_name}" collection')
        return str(message_doc['ts'])

    def get_last_records(self, collection_name, number):
        collection = self.db.collection(collection_name)
        query = collection.order_by("ts", direction=firestore.Query.DESCENDING).limit(number)
        latest_records = query.stream()
        result = [rec.to_dict() for rec in latest_records]
        return result
    
    def _create_message_doc(self, collection, content, sender, user_id='system', ts=datetime.now().timestamp()):
        # if there is a doc exists it will be replaced with a new one
        message_data = {
            'ts': ts,
            'server_ts': firestore.SERVER_TIMESTAMP,
            'content': content,
            'sender': sender,
            'user': user_id,
            'conversation_id': collection
        }
        self.db.document(f'conversations/user_{user_id}/user_conversations/{collection}/messages/{ts}').set(message_data)
        print(f'[user_{user_id}] created document "{ts}" under: {collection}')
        return message_data

    def get_unseen_conversation_count_by_user_id(self, user_id: int):
        try:
            unseen_count = self.db \
                .collection('conversations') \
                .document('user_' + str(user_id)) \
                .collection('user_conversations') \
                .where(filter=FieldFilter("unseen", "==", True)) \
                .count() \
                .get()
            
            return unseen_count[0][0].value
        except Exception as e:
            return 0
    
    def get_conversations_by_user_id(self, user_id: int):
        print(f'[user_{user_id}] pulling conversations list...')
        conversations = self.db \
            .collection('conversations') \
            .document('user_' + str(user_id)) \
            .collection('user_conversations') \
            .order_by('last_update', direction=firestore.Query.DESCENDING) \
            .get()
        conversations_list = []
        for conversation_doc in conversations:
            conversation_data = conversation_doc.to_dict()
            if 'display_name' not in conversation_data:
                conversation_data['display_name'] = 'No name'
            if 'last_update' not in conversation_data:
                conversation_data['last_update'] = 0
            if 'unseen' not in conversation_data:
                conversation_data['unseen'] = False
            if conversation_doc.id in ['news', 'feedback', 'announcements']:
                conversation_data['show_prompts'] = False
            else:
                conversation_data['show_prompts'] = True
            if conversation_doc.id in ['news', 'feedback', 'announcements']:
                conversation_data['allow_input'] = True
            else:
                conversation_data['allow_input'] = True
            conversations_list.append({'id': conversation_doc.id,
                                       'display_name': conversation_data['display_name'],
                                       'last_update': conversation_data['last_update'],
                                       'unseen': conversation_data['unseen'],
                                       'show_prompts': conversation_data['show_prompts'],
                                       'allow_input': conversation_data['allow_input']})
        print(f'[user_{user_id}] found {len(conversations_list)} conversations')
        return conversations_list

    def get_messages_by_conversation_id(self, user_id: int, conversation_id: str, skip: int, limit: int, reverse=True):
        print(f'[user_{user_id}] pulling messages from {conversation_id}...')
        conversation_ref = self.db.document(f'conversations/user_{user_id}/user_conversations/{conversation_id}')
        resp = {
            'messages': [],
            'display_name': '',
            'last_update': 0,
            'unseen': False,
            'show_prompts': True,
            'allow_input': True
        }
        conversation_data = conversation_ref.get().to_dict()
        if conversation_ref.get().exists:
            resp['display_name'] = conversation_data['display_name'] if 'display_name' in conversation_data else 'No name'
            resp['last_update'] = conversation_data['last_update'] if 'last_update' in conversation_data else 0
            resp['unseen'] = conversation_data['unseen'] if 'unseen' in conversation_data else False
            resp['show_prompts'] = False if conversation_id in ['news', 'feedback', 'announcements'] else True
            messages_ref = conversation_ref.collection('messages')
            q = messages_ref \
                .order_by('ts', direction=firestore.Query.DESCENDING if reverse else firestore.Query.ASCENDING) \
                .offset(num_to_skip=skip) \
                .limit(count=limit)
            for message in q.stream():
                resp['messages'].append(message.to_dict())
        print(f'[user_{user_id}] pulled {len(resp["messages"])} messages from {conversation_id}')
        return resp

    def get_bard_info(self, user_id):
        print(f'[user_{user_id}] getting bard info...')
        # Could have done it like this:
        # query = fs.collection('scrapers').where("status", "==", "up")
        # but there is a bug that produces warnings: https://github.com/googleapis/python-firestore/issues/705
        # TODO: update the code once the bug resolved
        query = self.db.collection('scrapers').where(filter=FieldFilter("status", "==", "up"))
        scrapers = query.get()
        if not len(scrapers):
            print(f'[user_{user_id}] ERROR: NO BARD SERVERS AVAILABLE')
            raise HTTPException(status_code=500, detail="No available servers")
        # selector is used to spread the load between bard servers equally
        selector = (user_id % len(scrapers))
        server_data = scrapers[selector].to_dict()
        info = {}
        info['bard_cookies'] = json.loads(server_data['bard_cookies'])
        info['url'] = server_data['bard_cookies_url']
        info['server_name'] = server_data['name']
        info['proxy'] = server_data['proxy']
        print(f'[user_{user_id}] pulled bard server info')
        print(f'[user_{user_id}] going to use bard from: {server_data["name"]}')
        return info

    def update_bard_cookies(self, info):
        print(f'[BARD_SERVER] going to update cookies on {info["url"]}')
        # TODO: verify=False is a bad practice and has been implemented as a workaround
        resp = requests.get(info['url'], verify=False)
        print(f'[BARD_SERVER] response code: {resp.status_code}')
        if (not resp.ok):
            raise HTTPException(status_code=500, detail="Failed to refresh keys")
        bard_cookies = resp.json()
        print(f'[BARD_SERVER] received new cookies')
        self.db.collection('scrapers').document(info['server_name']).update({'bard_cookies': json.dumps(bard_cookies)})
        print('[BARD_SERVER] saved new cookies')
        return bard_cookies

    def create_doc_and_save_to_feed(self, collection, content):
        doc = {
            'ts': datetime.now().timestamp(),
            'server_ts': firestore.SERVER_TIMESTAMP,
            'content': content,
            'sender': 'system',
        }
        self.save_to_feed(collection, doc)
        return doc

    def populate_system_message(self, doc, id, collection):
        doc['user'] = id
        doc['conversation_id'] = collection
        doc_ref = self.db.document(f'conversations/user_{id}/user_conversations/{collection}/messages/{doc["ts"]}').set(doc)
        collection_doc_ref = self.db.document(f'conversations/user_{id}/user_conversations/{collection}')
        collection_doc_ref.set({'unseen': True}, merge=True)
        print(f'[user_{id}]: populated {doc["ts"]} doc to {collection} and marked as unseen')


client_instance = FirebaseAdminClient(service_account_path=encoded_var_to_creds('FIREBASE_ADMIN_CREDS'))
