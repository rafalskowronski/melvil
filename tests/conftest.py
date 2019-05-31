from datetime import datetime
import random
from random import choice, randint
import string

import pytest
from mimesis import Generic
from sqlalchemy import event
from werkzeug.security import generate_password_hash

from app import create_app, ldap_client
from app import db as _db
from app import mail as _mail
from forms.book import BookForm, MagazineForm,\
    AddNewItemBookForm, AddNewItemMagazineForm
from models import (
    User,
    Book,
    Magazine,
    Copy,
    WishListItem,
    Author,
    Tag,
    LibraryItem
)
from models.users import Role, RoleEnum
from forms.copy import CopyAddForm, CopyEditForm
from forms.edit_profile import EditProfileForm
from forms.forms import (
    SearchForm,
    WishlistForm,
    LoginForm,
    RegistrationForm,
    ForgotPass,
    EditPasswordForm
)
from tests.populate import (
    populate_users,
    populate_copies,
    populate_authors,
    populate_books,
    populate_rental_logs,
    populate_magazines,
    populate_wish_list_items
)
from models.library import BookStatus


g = Generic('en')


@pytest.fixture(scope="module")
def app():
    """
    Returns flask app with context for testing.
    """
    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
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
def mock_ldap():
    global ldap_client

    # this class mimics ldap object
    class MockLdap:
        # those properties correspond to use cases
        # for example user not present in ldap try to log in
        def __init__(self, user, non_user, user_not_wroc):
            self.user = user
            self.non_user = non_user
            self.user_not_wroc = user_not_wroc

        # check id credentials are valid
        def bind_user(self, user_name, passwd):
            if ((user_name == self.user['user_name'] and
                    passwd == self.user['passwd']) or
                    (user_name == self.user_not_wroc['user_name'] and
                        passwd == self.user_not_wroc['passwd'])):
                return True
            else:
                return None

        # return employee data
        def get_object_details(self, user):
            if (user == self.user['user_name'] or
                    user == self.user['mail']):
                return self.user
            elif (user == self.user_not_wroc['user_name'] or
                    user == self.user_not_wroc['mail']):
                return self.user_not_wroc
            else:
                return None

    # create fake user data
    def create_user(wroclaw_usr=True, non_user=False):
        login = Generic().person.identifier(mask='@@@@@@@@').lower()
        email = Generic().person.email(['@tieto.com'])
        passwd = Generic().person.password(length=12)
        name = Generic().person.name()
        surname = Generic().person.last_name()
        identifier = Generic().person.identifier(mask='#####')

        if wroclaw_usr:
            location = 'Wroclaw'
        else:
            while True:
                location = Generic().address.city()
                if location != 'Wroclaw':
                    break

        if non_user:
            return dict(user_name=login, passwd=passwd)
        else:
            return dict(
                user_name=login,
                passwd=passwd,
                mail=email,
                givenName=name,
                sn=surname,
                employeeID=identifier
            )

    # substitute ldap object
    ldap_client = MockLdap(
        create_user(),
        create_user(non_user=True),
        create_user(wroclaw_usr=False)
    )


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
        'email': g.person.email(),
        'first_name': g.person.name(),
        'surname': g.person.surname(),
        'password': password_generator(),
        'title': text_generator(),
        'message': text_generator()}
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
def view_book(session, client):
    languages = ['polish', 'english', 'other']
    categories = ['developers', 'managers',
                  'magazines', 'other']
    type_book = ['book', 'magazine']

    form = AddNewItemBookForm(
        radio=choice(type_book),
        first_name=g.person.name(),
        surname=g.person.surname(),
        title=' '.join(g.text.title().split(' ')[:5]),
        table_of_contents=g.text.sentence(),
        language=choice(languages),
        category=choice(categories),
        tag=g.text.words(1),
        description=g.text.sentence(),
        isbn=str(1861972717),
        original_title=' '.join(g.text.title().split(' ')[:5]),
        publisher=g.business.company(),
        pub_date=str(randint(1970, 2018)),
    )

    return form


@pytest.fixture(scope="function")
def view_magazine(session, client):
    languages = ['polish', 'english', 'other']
    categories = ['developers', 'managers',
                  'magazines', 'other']
    type_book = ['book', 'magazine']

    form = AddNewItemMagazineForm(
        radio=choice(type_book),
        title_of_magazine=' '.join(g.text.title().split(' ')[:5]),
        table_of_contents=g.text.sentence(),
        language=choice(languages),
        category=choice(categories),
        tag=g.text.words(1),
        description=g.text.sentence(),
        pub_date=str(randint(1970, 2018)),
        issue=g.text.words(1)
    )

    return form


@pytest.fixture(scope="function")
def view_edit_book(session):
    languages = ['polish', 'english', 'other']
    categories = ['developers', 'managers',
                  'magazines', 'other']

    author = Author(first_name=g.person.name(),
                    last_name=g.person.surname())
    session.add(author)

    tag = Tag(name=g.text.words(1))
    session.add(tag)
    session.commit()
    form = BookForm(
        radio='book',
        first_name=author.first_name,
        surname=author.last_name,
        title=' '.join(g.text.title().split(' ')[:3]),
        table_of_contents=g.text.sentence(),
        language=choice(languages),
        category=choice(categories),
        tag=tag.name,
        description=g.text.sentence(),
        isbn=str(9789295055025),
        original_title=' '.join(g.text.title().split(' ')[:3]),
        publisher=g.business.company(),
        pub_date=str(randint(1970, 2018))
    )

    book = Book(
        title=form.title.data,
        authors=[author],
        table_of_contents=form.table_of_contents.data,
        language=form.language.data,
        category=form.category.data,
        tags=[tag],
        description=form.description.data,
        isbn=form.isbn.data,
        original_title=form.original_title.data,
        publisher=form.publisher.data,
        pub_date=datetime(year=int(form.pub_date.data),
                          month=1,
                          day=1))

    session.add(book)
    session.commit()

    return form


@pytest.fixture(scope="function")
def view_edit_magazine(session):
    languages = ['polish', 'english', 'other']
    categories = ['developers', 'managers',
                  'magazines', 'other']

    tag = Tag(name=g.text.words(1))
    session.add(tag)
    session.commit()
    form = MagazineForm(
        radio='magazine',
        title_of_magazine=' '.join(g.text.title().split(' ')[:3]),
        table_of_contents=g.text.sentence(),
        language=choice(languages),
        category=choice(categories),
        tag=tag.name,
        description=g.text.sentence(),
        pub_date=str(randint(1970, 2018))
    )

    magazine = Magazine(
        title=form.title_of_magazine.data,
        table_of_contents=form.table_of_contents.data,
        language=form.language.data,
        category=form.category.data,
        tags=[tag],
        description=form.description.data,
        year=datetime(year=int(form.pub_date.data),
                      month=1,
                      day=1))

    session.add(magazine)
    session.commit()

    return form


@pytest.fixture(scope="function")
def copy_form(session, client):
    form_add = CopyAddForm(
        asset_code='wr109100',
        has_cd_disk=True,
        shelf='shelf_one'
    )

    form_edit = CopyEditForm(
        asset_code='ab109100',
        has_cd_disk=True,
        available_status=BookStatus.RETURNED,
        shelf='shelf_two'
    )

    yield (form_add, form_edit)


@pytest.fixture(scope="function")
def view_login(session, client, db_user):
    form = LoginForm(
        email=db_user.email,
        password=db_user.password_hash
    )

    yield form


@pytest.fixture(scope="function")
def view_registration(session):
    """
    Creates and return function-scoped User database entry
    """
    a = "65$asdMNB"
    u = RegistrationForm(email="asd.qwe@tieto.com",
                         first_name=g.person.name(),
                         surname=g.person.surname(),
                         password=a,
                         confirm_pass=a)

    yield u


@pytest.fixture(scope="function")
def db_magazine(session):
    m = Magazine(
        title=' '.join(g.text.title().split(' ')[:5]),
        language=g.person.language(),
        description=g.text.sentence(),
        year=g.datetime.datetime(),
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
        available_status=BookStatus.RETURNED
    )
    copy_reserved = Copy(
        asset_code='{}{}'.format(
            g.code.locale_code()[:2],
            g.code.pin(mask='######')),
        library_item=db_book,
        available_status=BookStatus.RESERVED
    )
    copy_borrowed = Copy(
        asset_code='{}{}'.format(
            g.code.locale_code()[:2],
            g.code.pin(mask='######')),
        library_item=db_book,
        available_status=BookStatus.BORROWED
    )
    session.add_all([copy_available, copy_reserved, copy_borrowed])
    session.commit()

    yield (copy_available, copy_reserved, copy_borrowed)


@pytest.fixture
def app_session(client, db_user):
    with client.session_transaction() as app_session:
        app_session['logged_in'] = True
        app_session['id'] = db_user.id
        return app_session


@pytest.fixture
def empty_app_session(client):
    with client.session_transaction() as app_session:
        app_session['logged_in'] = False
        return app_session


@pytest.fixture(scope="function")
def search_form(session, client):
    """
    Form for searching for an item in library.search view
    """
    form = SearchForm(query=g.text.word())
    return form


@pytest.fixture
def view_wish_list(app):
    form = WishlistForm()
    form.authors.data = g.person.surname() + " " + g.person.name()
    form.title.data = ' '.join(g.text.title().split(' ')[:5])
    form.pub_date.data = str(randint(1970, 2018))
    form.type.data = 'book'
    return form


@pytest.fixture(scope="function")
def db_wishlist_item(session):
    """
    Creates and return function-scoped User database entry
    """
    w = WishListItem(authors=g.person.surname() + " " + g.person.name(),
                     title=' '.join(g.text.title().split(' ')[:5]),
                     pub_year=g.datetime.datetime(),
                     item_type='book'
                     )
    session.add(w)
    session.commit()

    yield w

    if WishListItem.query.get(w.id):
        session.delete(w)
        session.commit()


@pytest.fixture(scope="function")
def edit_profile_form(session, client):
    f_name = g.person.name()
    surname = g.person.surname()
    mail = f_name + surname + "@tieto.com"
    form_edit = EditProfileForm(
        first_name=f_name,
        surname=surname,
        email=mail
    )

    yield (form_edit)


@pytest.fixture(scope="function")
def db_tieto_user(session):
    """
    Creates and return function-scoped Tieto user database entry
    """
    password = g.person.password(length=8)
    u = User(email=g.person.name() + g.person.surname() + '.' + '@tieto.com',
             first_name=g.person.name(),
             surname=g.person.surname(),
             password_hash=generate_password_hash(password),
             active=True,
             roles=[])
    session.add(u)
    session.commit()

    yield u, password

    if User.query.get(u.id):
        session.delete(u)
        session.commit()


@pytest.fixture(scope="function")
def db_admin_user(session):
    """
    Creates and return function-scoped Admin user database entry
    """
    password = g.person.password(length=8)
    u = User(email=g.person.name() + g.person.surname() + '.' + '@tieto.com',
             first_name=g.person.name(),
             surname=g.person.surname(),
             password_hash=generate_password_hash(password),
             active=True,
             roles=[])
    role_admin = Role.query.filter_by(name=RoleEnum.ADMIN).first()
    u.roles.append(role_admin)
    session.add(u)
    session.commit()

    yield u, password

    if User.query.get(u.id):
        session.delete(u)
        session.commit()


@pytest.fixture(scope="function")
def login_form(db_tieto_user):
    """
    Returns login form containing valid data of registered user.
    """
    form = LoginForm(
        email=User.query.filter_by(id=db_tieto_user[0].id).first().email,
        password=db_tieto_user[1],
    )
    yield form


@pytest.fixture(scope="function")
def login_form_admin_credentials(db_admin_user):
    """
    Returns login form containing valid data of registered admin user.
    """
    form = LoginForm(
        email=User.query.filter_by(id=db_admin_user[0].id).first().email,
        password=db_admin_user[1],
    )
    yield form


@pytest.fixture(scope="function")
def search_query(session, client):
    """
    Create db entries for books and magazines
    """
    authors = populate_authors(n=5)
    books = populate_books(authors=authors)
    magazines = populate_magazines()

    for i in [authors, books, magazines]:
        session.add_all(i)

    session.commit()

    yield (books, magazines)


@pytest.fixture(scope="function")
def wishlist_query(session, client):
    """
    Create db entries for wishlist items
    """
    wishlist = populate_wish_list_items()

    for i in wishlist:
        session.add(i)

    session.commit()

    yield wishlist


@pytest.fixture(scope="function")
def get_title(session, client):
    """
    Get title of item in Library
    """
    item = LibraryItem.query.first()
    yield item


@pytest.fixture(scope="function")
def get_wish(session, client):
    """
    Get title of wish in wishlist db
    """
    item = WishListItem.query.first()
    yield item


@pytest.fixture(scope="function")
def login_form_invalid(db_tieto_user):
    """
    Returns login form containing invalid data.
    """
    invalid_password = g.person.password(length=8)
    while(invalid_password == db_tieto_user[1]):
        invalid_password = g.person.password(length=8)

    form = LoginForm(
        email=User.query.filter_by(id=db_tieto_user[0].id).first().email,
        password=invalid_password,
    )
    yield form


@pytest.fixture(scope="function")
def registration_form():
    """
    Returns registration form containing valid data.
    """
    new_password = g.cryptographic.hash() + "!A"
    form = RegistrationForm(
        email=g.person.name() + '.' + g.person.surname() + '@tieto.com',
        first_name=g.person.name(),
        surname=g.person.surname(),
        password=new_password,
        confirm_pass=new_password,
        submit=True
    )
    yield form


@pytest.fixture(scope="function")
def registration_form_registered_user(db_tieto_user):
    """
    Returns registration form containing data of already registered user.
    """
    form = RegistrationForm(
        email=User.query.filter_by(id=db_tieto_user[0].id).first().email,
        first_name=User.query.filter_by
        (id=db_tieto_user[0].id).first().first_name,
        surname=User.query.filter_by(id=db_tieto_user[0].id).first().surname,
        password=db_tieto_user[1],
        confirm_pass=db_tieto_user[1],
    )
    yield form


@pytest.fixture(scope="function")
def registration_form_invalid():
    """
    Returns registration form containing invalid data
    """
    form = RegistrationForm(
        email=g.person.name() + '.' + g.person.surname() + '@gmail.com',
        first_name=g.person.name(),
        surname=g.person.surname(),
        password=g.cryptographic.hash(),
        confirm_pass=g.cryptographic.hash(),
    )
    yield form


@pytest.fixture(scope="function")
def forgot_pass(db_tieto_user):
    """
    Returns password reset form
    """
    form = ForgotPass(
        email=User.query.filter_by(id=db_tieto_user[0].id).first().email,
        submit=True
    )
    yield form


@pytest.fixture
def user_reservations(session):
    """
    Creates reservations for one user
    """
    user = populate_users(n=1)
    session.add_all(user)
    session.commit()
    authors = populate_authors(n=2)
    session.add_all(authors)
    session.commit()
    books = populate_books(n=2, authors=authors)
    session.add_all(books)
    session.commit()
    magazines = populate_magazines(n=2)
    session.add_all(magazines)
    session.commit()
    copies = []
    copies.append(populate_copies(books[0], n=1)[0])
    copies.append(populate_copies(books[1], n=1)[0])
    copies.append(populate_copies(magazines[0], n=1)[0])
    copies.append(populate_copies(magazines[1], n=1)[0])
    session.add_all(copies)
    session.commit()
    reservations = []
    reservations.append(populate_rental_logs(copies[0].id, user[0].id, n=1)[0])
    reservations.append(populate_rental_logs(copies[1].id, user[0].id, n=1)[0])
    reservations.append(populate_rental_logs(copies[2].id, user[0].id, n=1)[0])
    reservations.append(populate_rental_logs(copies[3].id, user[0].id, n=1)[0])
    session.add_all(reservations)
    session.commit()
    reservations[0].book_status = BookStatus.RESERVED
    reservations[1].book_status = BookStatus.BORROWED
    reservations[2].book_status = BookStatus.RESERVED
    reservations[3].book_status = BookStatus.BORROWED

    yield user[0], (books[0], reservations[0]), (books[1], reservations[1]), \
        (magazines[0], reservations[2]), (magazines[1], reservations[3])
    for r in reservations:
        session.delete(r)
    for c in copies:
        session.delete(c)
    for b in books:
        session.delete(b)
    for m in magazines:
        session.delete(m)
    session.delete(user[0])
    session.commit()


@pytest.fixture(scope="function")
def password_edition_form(db_user):
    password = g.person.password(length=8)
    new_password = g.person.password(length=8)
    form = EditPasswordForm(
        password=password,
        new_password=new_password,
        confirm_password=new_password,
    )
    yield form
