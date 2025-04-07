from app.api.firebase_custom_client import client_instance as fcc
from app.api.database import SessionLocal
from app.api import crud

from app.api.tools.utils import run_function_in_parallel
from app.models import models

def populate_last_message_to_all_users(db, collection_name):
    users = crud.get_all_users(db=db)
    user_ids = [user.id for user in users]
    # user_ids = [3620, 2]
    message_doc = fcc.get_last_records(collection_name, 1)[0]
    
    # Create a tuple of arguments to pass to fcc.populate_system_message
    args_to_pass = [(message_doc, user_id, 'news') for user_id in user_ids]
    run_function_in_parallel(fcc.populate_system_message, args_to_pass)
    
# def send_personalized_message_to_all_users(db, collection_name):
#     portfolios = db.query(models.Portfolio).all()
#     names_and_ids = []
#     for token in tokens:
#         if len(token.user.portfolios) > 0:
#             pair = (token.user_id, token.user.portfolios[0].name)
#             names_and_ids.append(pair)
#     print(names_and_ids)

if __name__ == "__main__":
    db = SessionLocal()
    populate_last_message_to_all_users(db, 'news')