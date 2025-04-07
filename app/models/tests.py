import unittest
import datetime
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Base, Character, Portfolio, User, Account


# class TestQuery(unittest.TestCase):
#     def setUp(self):
#         self.engine = create_engine('sqlite:///:memory:')
#         self.session = Session(self.engine)
#         Base.metadata.create_all(self.engine)
#         self.session.commit()

#     def tearDown(self):
#         Base.metadata.drop_all(self.engine)

#     def test_add_user(self):
#         expected = []
#         result = self.session.query(User).all()

#         self.assertEqual(result, expected)




engine = create_engine('sqlite:///:memory:')
session = Session(engine)
Base.metadata.create_all(engine)
session.commit()

# add user
user1 = User(
    display_name='Player1',
    email='player1@example.com',
)

user2 = User(
    display_name='Player2',
    email='player2@example.com',
)

session.add(user1)
session.add(user2)
session.commit()


account1 = Account(
    provider='google',
    user_id=user1.id,
    ext_user_id='secretsididididididi',
)

session.add(account1)

session.commit()
try:

    account2 = Account(
        provider='google',
        user_id=user2.id,
        ext_user_id='secretsididididididi',
    )

    session.add(account2)
    session.commit()

except IntegrityError as e:
    print('Account already exists')
    session.rollback()

character1 = Character(
    image_url='https://example.com/image1.png',
    category='people',
)

print('add new character icon')
session.add(character1)
session.commit()

print('add new portfolio')
portfolio1 = Portfolio(
    user_id=user1.id,
    character_id=character1.id,
    name='Portfolio1',
    cash_balance=1000,
    is_public=True,
    is_risk_taker=True,
    status='active',
    date_last_updated=datetime.datetime.now(),
    date_created=datetime.datetime.now(),

)
session.add(portfolio1)
session.commit()

print(user1.portfolios[0].name)

print("XP test start")
print("Add XP (+1)")
user1.xp_total = User.xp_total + 1
user1.xp_current_week = User.xp_total + 1
session.merge(user1)
session.commit()

users = session.query(User).all()
for user in users:
    print(f"ID: {user.id}, XP total: {user.xp_total}, XP weekly: {user.xp_current_week}")

print("Add XP again (+1)")
user1.xp_total = User.xp_total + 1
user1.xp_current_week = User.xp_total + 1
session.merge(user1)
session.commit()

users = session.query(User).all()
for user in users:
    print(f"ID: {user.id}, XP total: {user.xp_total}, XP weekly: {user.xp_current_week}")

users = session.query(User).all()
for user in users:
    session.delete(user)


session.commit()


accounts = session.query(Account).count()
print(accounts)