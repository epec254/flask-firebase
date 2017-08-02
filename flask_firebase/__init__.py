from flask import Blueprint, abort, current_app, redirect, request, \
    render_template, url_for
import urlparse
import google.oauth2.id_token
import google.auth.transport.requests
import requests
HTTP_REQUEST = google.auth.transport.requests.Request()

blueprint = Blueprint('firebase_auth', __name__, template_folder='templates')

@blueprint.route('/widget', methods={'GET', 'POST'})
def widget():
    return current_app.extensions['firebase_auth'].widget()


@blueprint.route('/sign-in', methods={'POST'})
def sign_in():
    return current_app.extensions['firebase_auth'].sign_in()


@blueprint.route('/sign-out')
def sign_out():
    return current_app.extensions['firebase_auth'].sign_out()


class FirebaseAuth:

    KEYCHAIN_URL = 'https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com'  # noqa

    PROVIDER_CLASSES = {
        'email': 'EmailAuthProvider',
        'facebook': 'FacebookAuthProvider',
        'github': 'GithubAuthProvider',
        'google': 'GoogleAuthProvider',
        'twitter': 'TwitterAuthProvider',
    }

    def __init__(self, app=None):
        self.debug = None
        self.api_key = None
        self.project_id = None
        self.provider_ids = None
        self.server_name = None
        self.production_load_callback = None
        self.development_load_callback = None
        self.unload_callback = None
        self.blueprint = blueprint
        self.keys = {}
        self.max_age = 0
        self.cached_at = 0
        # self.lock = Lock()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.extensions['firebase_auth'] = self
        self.debug = app.debug
        if self.debug:
            return
        self.api_key = app.config['FIREBASE_API_KEY']
        self.project_id = app.config['FIREBASE_PROJECT_ID']
        self.server_name = app.config['SERVER_NAME']
        provider_ids = []
        for name in app.config['FIREBASE_AUTH_SIGN_IN_OPTIONS'].split(','):
            class_name = self.PROVIDER_CLASSES[name.strip()]
            provider_id = 'firebase.auth.{}.PROVIDER_ID'.format(class_name)
            provider_ids.append(provider_id)
        self.provider_ids = ','.join(provider_ids)

    def production_loader(self, callback):
        self.production_load_callback = callback
        return callback

    def development_loader(self, callback):
        self.development_load_callback = callback
        return callback

    def unloader(self, callback):
        self.unload_callback = callback
        return callback

    def url_for(self, endpoint, **values):
        full_endpoint = 'firebase_auth.{}'.format(endpoint)
        if self.debug:
            return url_for(full_endpoint, **values)
        else:
            return url_for(
                full_endpoint,
                # _external=True,
                # _scheme='https',
                **values)

    def widget(self):
        next_ = self.verify_redirection()
        if self.debug:
            if request.method == 'POST':
                self.development_load_callback(request.form['email'])
                return redirect(next_)
            else:
                return render_template('firebase_auth/development_widget.html')
        else:
            return render_template(
                'firebase_auth/production_widget.html',
                firebase_auth=self)

    def sign_in(self):
        assert not self.debug

        # Verify Firebase auth.
        id_token = request.headers['Authorization'].split(' ').pop()
        claims = google.oauth2.id_token.verify_firebase_token(
            id_token, HTTP_REQUEST)
        if not claims:
            raise Exception('Authentication failed')

        # have the token, return it
        self.production_load_callback(claims)
        return 'OK'

    def sign_out(self):
        self.unload_callback()
        return redirect(self.verify_redirection())

    def verify_redirection(self):
        next_ = request.args.get('next')
        if not next_:
            return request.url_root
        if self.server_name:
            url = urlparse(next_)
            if not url.netloc.endswith(self.server_name):
                abort(400)
        return next_
