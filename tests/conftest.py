import random
import string

import pytest
from mimesis import Generic
from flask import url_for
from sqlalchemy import event

from app import create_app
from app import db as _db
from app import mail as _mail
from models import User, Book, Magazine, Copy
from sqlalchemy import event
from models import User, Book, Author


g = Generic('en')


@pytest.fixture(scope='module')
def app():
    """
    Returns flask app with context for testing.
    """
    app = create_app()
    _mail.init_app(app)
    ctx = app.app_context()
    ctx.push()

    yield app

    ctx.pop()


@pytest.fixture
def client(app):
    with app.test_client() as client:
        return client


@pytest.fixture(scope="module", autouse=True)
def db(app):
    """
    Returns module-wide initialised database.
    """
    _db.create_all()

    yield _db


@pytest.fixture(scope="module")
def session(db):
    """
    Returns module-scoped session.
    """
    conn = db.engine.connect()
    txn = conn.begin()

    options = dict(bind=conn, binds={})
    sess = db.create_scoped_session(options=options)

    sess.begin_nested()

    @event.listens_for(sess(), 'after_transaction_end')
    def restart_savepoint(sess2, trans):
        if trans.nested and not trans._parent.nested:
            sess2.expire_all()
            sess.begin_nested()

    db.session = sess
    yield sess

    sess.remove()
    txn.rollback()
    conn.close()


@pytest.fixture
def mailbox(app):
    return _mail.record_messages()


@pytest.fixture(scope='module')
def email_generator(chars=string.ascii_letters + string.digits + '.' + '-'):
    size = random.randint(10, 25)
    return ''.join(random.choice(chars) for _ in range(size)) + '@tieto.com'


@pytest.fixture(scope='module')
def text_generator(chars=string.ascii_letters + 'ąćęłóżź \n\t'):
    size = random.randint(25, 40)
    return ''.join(random.choice(chars) for _ in range(size))


@pytest.fixture(scope='module')
def text_generator_no_whitespaces(chars=string.ascii_letters + 'ąćęłóżź'):
    size = random.randint(25, 40)
    return ''.join(random.choice(chars) for _ in range(size))


@pytest.fixture(scope='module')
def password_generator(chars=string.ascii_letters):
    size = random.randint(10, 25)
    return ''.join(random.choice(chars) for _ in range(size))


@pytest.fixture(scope='module')
def user(app):

    data = {
        'email': email_generator(),
        'first_name': text_generator(),
        'surname': text_generator(),
        'password': password_generator()}
    yield data


@pytest.fixture(scope="function")
def db_user(session):
    """
    Creates and return function-scoped User database entry
    """
    u = User(email=g.person.email(),
             first_name=g.person.name(),
             surname=g.person.surname(),
             password_hash=g.cryptographic.hash(),
             active=g.development.boolean(),
             roles=[])
    session.add(u)
    session.commit()

    yield u

    if User.query.get(u.id):
        session.delete(u)
        session.commit()


@pytest.fixture(scope="function")
def db_book(session):
    """
    Creates and return function-scoped Book database entry
    """
    b = Book(isbn=g.code.isbn(),
             authors=[],
             title=' '.join(g.text.title().split(' ')[:5]),
             original_title=' '.join(g.text.title().split(' ')[:5]),
             publisher=g.business.company(),
             pub_date=g.datetime.datetime().date(),
             language=g.person.language(),
             tags=[],
             description=g.text.sentence())
    session.add(b)
    session.commit()

    yield b

    if Book.query.get(b.id):
        session.delete(b)
        session.commit()


@pytest.fixture(scope="function")
def db_author(session, client):
    a = {'first_name': g.person.name(),
         'surname': g.person.surname(),
         'submit': 'Create'
         }
    aa = Author(
        first_name=g.person.name(),
        last_name=g.person.surname()
    )

    client.post(url_for('library_books.add_book'), data=a)
    # client.post(client.post(url_for('library.login'), data=data))
    session.add(aa)
    session.commit()

    yield a

    # if Author.query.filter_by(first_name=a['first_name']
    # , last_name=a['last_name']).first():
    #     session.delete(aa)
    #     session.commit()


@pytest.fixture(scope="function")
def db_magazine(session):
    m = Magazine(
        title=' '.join(g.text.title().split(' ')[:5]),
        language=g.person.language(),
        description=g.text.sentence(),
        year=g.datetime.year(maximum=2018),
        issue=random.randint(1, 12),
        tags=[],
    )
    session.add(m)
    session.commit()

    yield m

    if Magazine.query.get(m.id):
        session.delete(m)
        session.commit()


@pytest.fixture(scope="function")
def db_copies(session, db_book):
    copy_available = Copy(
        asset_code='{}{}'.format(
            g.code.locale_code()[:2],
            g.code.pin(mask='######')),
        library_item=db_book,
        available_status=True
    )
    copy_not_available = Copy(
        asset_code='{}{}'.format(
            g.code.locale_code()[:2],
            g.code.pin(mask='######')),
        library_item=db_book,
        available_status=False
    )
    session.add_all([copy_available, copy_not_available])
    session.commit()

    yield (copy_available, copy_not_available)


@pytest.fixture
def app_session(client, db_user):
    with client.session_transaction() as app_session:
        app_session['id'] = db_user.id
        return app_session
