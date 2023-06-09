from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class DeployAgent_form(FlaskForm):
    name = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    description = StringField('Description', validators=[DataRequired(), Length(min=20, max=400)]) # sets max description length
    deploy = SubmitField('Deploy Agent')


class MakeTweet_form(FlaskForm):
    name = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    content = StringField('Content', validators=[DataRequired(), Length(min=2, max=200)])
    submit = SubmitField('Send Tweet')

