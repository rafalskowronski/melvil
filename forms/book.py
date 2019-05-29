from flask_wtf import FlaskForm
from datetime import datetime
from wtforms import (
    StringField,
    SubmitField,
    TextAreaField,
    SelectField,
    RadioField

)
from wtforms.validators import DataRequired, Length
from forms.custom_validators import \
    check_author, check_language, \
    check_category, check_isbn, \
    check_pub_date, title_book_exists


class LibraryItemForm(FlaskForm):
    languages = [('polish', 'Polish'),
                 ('english', 'English'),
                 ('other', 'Other')]
    categories = [('developers', 'Developers'),
                  ('managers', 'Managers'),
                  ('magazines', 'Magazines'),
                  ('other', 'Other')]

    # LibraryItem
    radio = RadioField("radio",
                       choices=[('book', 'Book'),
                                ('magazine', 'Magazine')],
                       render_kw=({'class': 'radio_but'}))

    table_of_contents = TextAreaField('Table of contents',
                                      render_kw=({'class': 'inputs',
                                                  'id': 'table_of_contest',
                                                  'placeholder':
                                                      'Table of contents'}))

    language = SelectField('Language',
                           choices=languages,
                           validators=[check_language],
                           render_kw=({
                               'class': 'inputs custom-select '
                                        'mb-2 mr-sm-2 mb-sm-0',
                               'id': 'mySelect',
                               'placeholder': 'Language'}))

    category = SelectField('Category',
                           choices=categories,
                           validators=[check_category],
                           render_kw=({
                               'class': 'inputs custom-select'
                                        ' mb-2 mr-sm-2 mb-sm-0',
                               'id': 'mySelect',
                               'placeholder': 'Category'}))

    tag = StringField('Tag',
                      render_kw=({'class': 'inputs',
                                  'id': 'tag',
                                  'placeholder': 'Tag'}))
    description = TextAreaField('Description',
                                render_kw=({'class': 'inputs',
                                            'id': 'description',
                                            'placeholder': 'Description'}))

    pub_date = SelectField('Year of publication',
                           choices=[(str(year), str(year))
                                    for year in
                                    range(1970,
                                          datetime.now().year + 1)],
                           validators=[check_pub_date],
                           render_kw=({
                               'class': 'inputs custom-select '
                                        'mb-2 mr-sm-2 mb-sm-0',
                               'id': 'mySelect',
                               'placeholder': 'Year of publication'}))

    submit = SubmitField('Update',
                         render_kw=({'class': 'btn btn-primary submits',
                                     'id': 'button'}))


class BookForm(LibraryItemForm):
    title = StringField('Title',
                        validators=[DataRequired(),
                                    Length(3),
                                    title_book_exists],
                        render_kw=({'class': 'inputs',
                                    'id': 'title',
                                    'placeholder': 'Title'}))

    isbn = StringField('ISBN number',
                       validators=[DataRequired(), check_isbn],
                       render_kw=({'class': 'inputs',
                                   'id': 'isbn',
                                   'placeholder': 'ISBN number'}))

    original_title = StringField('Original title',
                                 render_kw=({'class': 'inputs',
                                             'id': 'original_title',
                                             'placeholder': 'Original title'}))
    publisher = StringField('Publisher',
                            validators=[DataRequired()],
                            render_kw=({'class': 'inputs',
                                        'id': 'publisher',
                                        'placeholder': 'Publisher'}))

    # Authors
    first_name = StringField('First name',
                             validators=[DataRequired(), check_author],
                             render_kw=({'class': 'inputs',
                                         'placeholder': 'First Name'}))
    surname = StringField('Surname',
                          validators=[DataRequired(), check_author],
                          render_kw=({'class': 'inputs',
                                      'placeholder': 'Surname'}))

    first_name_1 = StringField('First_name_1',
                               validators=[check_author],
                               render_kw=({'class': 'inputs',
                                           'placeholder': 'First Name 1'}))
    surname_1 = StringField('Surname_1',
                            validators=[check_author],
                            render_kw=({'class': 'inputs',
                                        'placeholder': 'Surname 1'}))

    first_name_2 = StringField('First name 2',
                               validators=[check_author],
                               render_kw=({'class': 'inputs',
                                           'placeholder': 'First Name 2'}))
    surname_2 = StringField('Surname 2',
                            validators=[check_author],
                            render_kw=({'class': 'inputs',
                                        'placeholder': 'Surname 2'}))


class MagazineForm(LibraryItemForm):
    title_of_magazine = StringField('Title',
                                    validators=[DataRequired(),
                                                Length(3)],
                                    render_kw=({'class': 'inputs',
                                                'id': 'title_of_magazine',
                                                'placeholder':
                                                    'Title of magazine'}))

    issue = StringField('Issue',
                        render_kw=({'class': 'inputs',
                                    'id': 'issue',
                                    'placeholder': 'Issue'}))


class AddNewItemBookForm(BookForm):
    submit1 = SubmitField('Create Book',
                          render_kw=({'class': 'btn btn-primary submits',
                                     'id': 'button1'}))


class AddNewItemMagazineForm(MagazineForm):
    submit2 = SubmitField('Create Magazine',
                          render_kw=({'class': 'btn btn-primary submits',
                                     'id': 'button2'}))
