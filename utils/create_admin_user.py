from werkzeug.security import generate_password_hash
import re

from forms.custom_validators import email_regex
from ldap_utils.ldap_utils import ldap_client, refine_data
from models.users import User, Role, RoleEnum
from init_db import db


email_list = [
    'katarzyna.kaminska@tieto.com',
    'hubert.nafalski@tieto.com',
    'pawel.biel@tieto.com'
]


def create_super_user():
    global email_list
    for email_data in email_list:
        user_ldap = ldap_client.get_object_details(user=email_data)
        if user_ldap:
            if refine_data(user_ldap, 'l') != 'Wroclaw':
                print(
                    'Error - employee {} do not work in Wroclaw'.format(email_data)
                    )

            user_ldap_data = {
                'mail': refine_data(user_ldap, 'mail'),
                'givenName': refine_data(user_ldap, 'givenName'),
                'sn': refine_data(user_ldap, 'sn'),
                'employeeID' : refine_data(user_ldap, 'employeeID')
            }
            user_db = User.query.filter_by(
                employee_id=user_ldap_data['employeeID']
                ).first()
            if user_db:
                user_db_data = {
                    'mail': user_db.email,
                    'givenName': user_db.first_name,
                    'sn': user_db.surname,
                    'employeeID' : user_db.employee_id
                }
                if user_db_data != user_ldap_data:
                    user_db.email = user_ldap_data['mail']
                    user_db.first_name = user_ldap_data['givenName']
                    user_db.surname = user_db_data['sn']
            else:
                new_user = User(
                    email=user_ldap_data['mail'],
                    first_name=user_ldap_data['givenName'],
                    surname=user_ldap_data['sn'],
                    employee_id=user_ldap_data['employeeID'],
                    active=True
                )
                db.session.add(new_user)
                db.session.commit()
            user = User.query.filter_by(email=email_data).first()
            role = Role.query.filter_by(name=RoleEnum.USER).first()
            user.roles.remove(role)
            role = Role.query.filter_by(name=RoleEnum.ADMIN).first()
            user.roles.append(role)
            db.session.commit()
            print(
                "Employee {} granted with admin privileges".format(email_data)
                )
        else:
            print(
                'Error - employee {} not present in Tieto ldap.'.format(email_data)
                )
