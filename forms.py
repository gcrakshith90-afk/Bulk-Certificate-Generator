from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, TextAreaField, BooleanField, DateField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, Length, EqualTo


class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=100)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")])
    submit = SubmitField("Create Account")



class OrganizationForm(FlaskForm):
    name = StringField("Organization Name", validators=[DataRequired(), Length(min=2, max=150)])
    organization_type = SelectField(
        "Organization Type",
        choices=[
            ("company", "Company / Corporate"),
            ("college", "College"),
            ("university", "University"),
            ("training institute", "Training Institute"),
            ("other", "Other"),
        ],
        validators=[DataRequired()],
    )
    contact_person = StringField("Contact Person", validators=[DataRequired(), Length(min=2, max=100)])
    contact_email = StringField("Contact Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField("Phone Number", validators=[Optional(), Length(max=30)])
    address = TextAreaField("Address", validators=[Optional(), Length(max=500)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Organization")


class CSVUploadForm(FlaskForm):
    organization_id = SelectField("Select Existing Organization", coerce=int, validators=[Optional()])
    new_organization_name = StringField("Or Create New Organization", validators=[Optional(), Length(max=150)])
    course_name = StringField("Course / Event Name", validators=[DataRequired(), Length(min=2, max=200)])
    certificate_title = StringField("Certificate Title", validators=[DataRequired(), Length(min=2, max=200)], default="Certificate of Completion")
    issue_date = DateField("Issue Date", validators=[DataRequired()])
    completion_date = DateField("Completion Date", validators=[Optional()])
    signatory_name = StringField("Signatory Name", validators=[Optional(), Length(max=100)])
    signatory_designation = StringField("Signatory Designation", validators=[Optional(), Length(max=100)])
    csv_file = FileField("Upload CSV File", validators=[FileRequired(), FileAllowed(["csv"], "Only CSV files are accepted.")])
    submit = SubmitField("Upload & Preview CSV")
