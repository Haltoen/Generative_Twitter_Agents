from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class DeployAgent_form(FlaskForm):
    name = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    description = StringField('Description', validators=[DataRequired(), Length(min=10, max=200)]) # sets max description length
    deploy = SubmitField('Deploy Model')


class MakeTweet_form(FlaskForm):
    name = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    content = StringField('Content', validators=[DataRequired(), Length(min=10, max=200)])
    submit = SubmitField('Send Tweet')

class SearchForm(FlaskForm):
  search = StringField('search field', validators=[DataRequired()])
  submit = SubmitField('Search')