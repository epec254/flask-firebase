# Flask-Firebase

Google Firebase integration for Flask. At this moment,
only the authentication subsystem is supported.

The extension works in two modes: development and production.
In development, there is no communication with the Firebase
system, accounts sign-in with a simple email form. The mode
depends on the `Flask.debug` variable.

## Configuration

- `FIREBASE_API_KEY`: The API key.
- `FIREBASE_PROJECT_ID`: The project identifier, eg. `foobar`.
- `FIREBASE_AUTH_SIGN_IN_OPTIONS`: Comma-separated list of enabled providers (can be any of: google,email,facebook,github,twitter)
- `FIREBASE_BASE_TEMPLATE`: What is the base Djina template the authentication widget should be enclosed in

## Providers

- `email`
- `facebook`
- `github`
- `google`
- `twitter`

## Example

1. Inside your Flask application's folder, create a file called `auth.py` with the following code:

```python
from flask import Flask, current_app
from flask_login import LoginManager, UserMixin, login_user, logout_user
from flask_firebase import FirebaseAuth
from housing import model_account

auth = FirebaseAuth()
login_manager = LoginManager()

def init_app(app):
    #init Firebase Auth & flask_login
    auth.init_app(app)
    login_manager.init_app(app)
    app.register_blueprint(auth.blueprint, url_prefix='/auth')

@auth.production_loader
def production_sign_in(token):
    account = model_account.query_by_firebase_user_id(token['sub'])
    if account is None:
        account_data = {
            'firebase_user_id': token['sub']
        }
        account = model_account.create(account_data)

    # grab the extra data
    extra_account_data = {
        'email_address': token['email'],
        'email_verified': token['email_verified'],
        'name': token.get('name'),
        'photo_url': token.get('picture')
    }

    #update the DB
    account = model_account.update(extra_account_data, account.id)

    # call the flask_user login method
    login_user(account)

@auth.development_loader
def development_sign_in(email_address):
    # try to find by email TODO: Add in error handling
    account = model_account.query_by_email_address(email_address)

    # call the flask_user login method
    login_user(account)


@auth.unloader
def sign_out():
    logout_user()

@login_manager.user_loader
def load_user(id):
    return model_account.get_by_account_id(id)


@login_manager.unauthorized_handler
def authentication_required():
    return redirect(auth.url_for('widget', mode='select', next=request.url))
```

2. Inside your Flask application's folder, create a file called `model_account.py` with the following code: 

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

builtin_list = list

db = SQLAlchemy()

def init_app(app):
    db.init_app(app)

def from_sql(row):
    """Translates a SQLAlchemy model instance into a dictionary"""
    data = row.__dict__.copy()
    data['id'] = row.id
    data.pop('_sa_instance_state')
    return data

class Account(UserMixin, db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    firebase_user_id = db.Column(db.String(50), unique=True)
    email_address = db.Column(db.String(320))
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    name = db.Column(db.Text)
    photo_url = db.Column(db.Text)

    pass

def query_by_firebase_user_id(firebase_user_id):
    return Account.query.filter_by(firebase_user_id=firebase_user_id).one_or_none()

def query_by_email_address(email_address):
    return Account.query.filter_by(email_address=email_address).one_or_none()

def get_by_account_id(id):
    return Account.query.get(id)

def create(data):
    account = Account(**data)
    db.session.add(account)
    db.session.commit()
    return account

def update(data, id):
    account = Account.query.get(id)
    for k, v in data.items():
        setattr(account, k, v)
    db.session.commit()
    return account

def delete(id):
    Account.query.filter_by(id=id).delete()
    db.session.commit()

def _create_database():
    """
    If this script is run directly, create all the tables necessary to run the
    application.
    """
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    init_app(app)
    with app.app_context():
        db.create_all()
    print("All tables created")


if __name__ == '__main__':
    _create_database()
```
3. Inside your Flask application's `__init__.py`, add the following code to your create_app function:

```python
def create_app(config, debug=False, testing=False, config_overrides=None):
	#create account model
	from . import model_account
	        model_account.init_app(app)
			
    #Include authentication code
    from . import auth
    auth.init_app(app)
```