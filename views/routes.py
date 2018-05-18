from flask import render_template, redirect, flash
from . import library
from forms.forms import LoginForm, SearchForm, ContactForm, RegistrationForm
from send_email.emails import send_email
from config import DevConfig
import os


@library.route('/')
def index():
    return render_template('index.html', title='Welcome!')


@library.route('/login')
def login():
    return render_template('login.html', title='Sign In', form=LoginForm())


@library.route('/search')
def search():
    return render_template('search.html', title='Search', form=SearchForm())


@library.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        flash('Message send', 'ok')
        try:
            email_template = open('./templates/emails/contact_confirmation.html', 'r').read()
        except:
            email_template = open(os.path.abspath(os.curdir) + './templates/emails/contact_confirmation.html',
                                  'r').read()
        send_email(
            'Contact confirmation, title: '+form.title.data,
            DevConfig.MAIL_USERNAME,
            [form.email.data],
            None,
            email_template)
        send_email(
            'Contact form: ' + form.title.data,
            DevConfig.MAIL_USERNAME,
            [DevConfig.MAIL_USERNAME],
            'Send by: '+form.email.data+'\n\n'+form.message.data,
            None)
        return redirect('/contact')
    return render_template('contact.html', title='Contact', form=form)


@library.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('registration.html', title='Register', form=RegistrationForm())
