import os


"""
* note that you only need to download the tokenizer model once from spacy.
"""
# import spacy

# spacy.cli.download("en_core_web_sm")

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from datetime import timedelta, datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    make_response,
)
from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from utils import is_valid_email, is_valid_password
from constants import COOKIE_NAME, TOKEN_SECRETE
import jwt
from argon2 import PasswordHasher
from model import predict_sentiment


ph = PasswordHasher()

db_path = os.path.abspath(os.getcwd()) + r"\db\users.db"
app = Flask(__name__)
app.secret_key = "dghjkianmalu"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(days=7)

db = SQLAlchemy(app)


class TimestampMixin(object):
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)


class User(TimestampMixin, db.Model):
    id = db.Column("id", db.Integer(), primary_key=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __init__(self, email, password):
        self.password = password
        self.email = email

    def __repr__(self):
        return "<User %r>" % self.email


with app.app_context():
    db.create_all()


class AppConfig:
    PORT = 3000
    HOST = "127.0.0.1" or "localhost"
    DEBUG = True


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        me = User.query.filter_by(email=str(email).strip().lower()).first()

        if me is None:
            error = "Invalid email address"
            return make_response(
                render_template("auth/login.html", ctx={"error": error})
            )
        try:
            correct = ph.verify(me.password, str(password).strip())
            if not correct:
                error = "Invalid email address"
                return make_response(
                    render_template("auth/login.html", ctx={"error": error})
                )
            token = jwt.encode({"email": me.email, "id": me.id}, TOKEN_SECRETE)
            response = redirect(url_for("home_page"))
            response.set_cookie(
                COOKIE_NAME,
                token,
                timedelta(days=7),
                path="/",
                secure=True,
                httponly=False,
                samesite="lax",
            )
            return response, 200
        except Exception as e:
            error = "Invalid email address"
            return make_response(
                render_template("auth/login.html", ctx={"error": error})
            )
    return make_response(render_template("auth/login.html", ctx={"error": ""})), 200


@app.route("/auth/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not is_valid_email(str(email).strip()):
            error = "Email address is invalid"
            return make_response(
                render_template("auth/register.html", ctx={"error": error})
            )
        if not is_valid_password(str(password).strip()):
            error = "Password must contain at least 5 characters"
            return make_response(
                render_template("auth/register.html", ctx={"error": error})
            )

        user = User.query.filter_by(email=str(email).strip().lower()).first()
        if user:
            error = "Email address already in use"
            return make_response(
                render_template("auth/register.html", ctx={"error": error})
            )
        hashed = ph.hash(str(password).strip())
        me = User(str(email).strip().lower(), hashed)
        db.session.add(me)
        db.session.commit()
        token = jwt.encode({"email": me.email, "id": me.id}, TOKEN_SECRETE)
        response = redirect(url_for("home_page", next="/"))
        response.set_cookie(
            COOKIE_NAME,
            token,
            timedelta(days=7),
            path="/",
            secure=True,
            httponly=False,
            samesite="lax",
        )
        return response, 200
    return make_response(render_template("auth/register.html", ctx={"error": ""}))


@app.route("/", methods=["GET", "POST"], strict_slashes=False)
def home_page():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=AppConfig.DEBUG, host=AppConfig.HOST, port=AppConfig.PORT)
