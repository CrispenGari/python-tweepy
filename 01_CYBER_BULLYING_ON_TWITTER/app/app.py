import os

"""
* note that you only need to download the tokenizer model once from spacy.
"""
# import spacy

# spacy.cli.download("en_core_web_sm")

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from datetime import timedelta, datetime
from flask import Flask, render_template, request, redirect, make_response, jsonify
from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from utils import is_valid_email, is_valid_password
from constants import COOKIE_NAME, TOKEN_SECRETE
import jwt
from argon2 import PasswordHasher
from model import predict_sentiment, cbtsa_model, device


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


@app.errorhandler(404)
def page_not_found(e):
    return make_response(render_template("common/404.html")), 404


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    res = make_response(render_template("auth/login.html", ctx={"error": ""}))
    if request.method == "GET":
        try:
            token = request.cookies.get(COOKIE_NAME)
            user = jwt.decode(str(token), TOKEN_SECRETE, algorithms=["HS256"])
            if user:
                me = User.query.filter_by(id=user.get("id")).first()
                if me is not None:
                    response = redirect(url_for("home_page"))
                    token = jwt.encode({"email": me.email, "id": me.id}, TOKEN_SECRETE)
                    response.set_cookie(
                        COOKIE_NAME,
                        token,
                        timedelta(days=7),
                        path="/",
                        secure=True,
                        httponly=False,
                        samesite="lax",
                    )
                    return response, 302
        except:
            res.delete_cookie(
                COOKIE_NAME,
                path="/",
                secure=True,
                httponly=False,
                samesite="lax",
            )
            return res, 200
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        me = User.query.filter_by(email=str(email).strip().lower()).first()
        print(me)
        if me is None:
            error = "Invalid email address"
            return make_response(
                render_template("auth/login.html", ctx={"error": error})
            )
        try:
            correct = ph.verify(me.password, str(password).strip())
            if not correct:
                error = "Invalid account password."
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
            return response, 302
        except Exception as e:
            error = "Invalid account password."
            return make_response(
                render_template("auth/login.html", ctx={"error": error})
            )
    return res, 200


@app.route("/auth/register", methods=["GET", "POST"])
def register():
    res = make_response(render_template("auth/register.html", ctx={"error": ""}))
    if request.method == "GET":
        try:
            token = request.cookies.get(COOKIE_NAME)
            user = jwt.decode(str(token), TOKEN_SECRETE, algorithms=["HS256"])
            if user:
                me = User.query.filter_by(id=user.get("id")).first()
                if me:
                    response = redirect(url_for("home_page"))
                    token = jwt.encode({"email": me.email, "id": me.id}, TOKEN_SECRETE)
                    response.set_cookie(
                        COOKIE_NAME,
                        token,
                        timedelta(days=7),
                        path="/",
                        secure=True,
                        httponly=False,
                        samesite="lax",
                    )
                    return response, 302
        except:
            res.delete_cookie(
                COOKIE_NAME,
                path="/",
                secure=True,
                httponly=False,
                samesite="lax",
            )
            return res, 200
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
        return response, 302
    return res, 200


@app.route("/auth/logout", methods=["GET", "POST"], strict_slashes=False)
def logout():
    if request.method == "POST":
        response = redirect("/auth/login")
        response.delete_cookie(
            COOKIE_NAME,
            path="/",
            secure=True,
            httponly=False,
            samesite="lax",
        )
        return response, 302
    return "logout", 302


@app.route("/about", methods=["GET", "POST"], strict_slashes=False)
def about():
    response = make_response(render_template("about.html"))
    if request.method == "GET":
        try:
            token = request.cookies.get(COOKIE_NAME)
            user = jwt.decode(str(token), TOKEN_SECRETE, algorithms=["HS256"])
            if user is None:
                res = redirect(url_for("login"))
                res.delete_cookie(
                    COOKIE_NAME,
                    path="/",
                    secure=True,
                    httponly=False,
                    samesite="lax",
                )
                return res, 302
            else:
                me = User.query.filter_by(id=user.get("id")).first()
                if me is None:
                    res = redirect(url_for("login"))
                    res.delete_cookie(
                        COOKIE_NAME,
                        path="/",
                        secure=True,
                        httponly=False,
                        samesite="lax",
                    )
                    return res, 302
                else:
                    token = jwt.encode({"email": me.email, "id": me.id}, TOKEN_SECRETE)
                    response.set_cookie(
                        COOKIE_NAME,
                        token,
                        timedelta(days=7),
                        path="/",
                        secure=True,
                        httponly=False,
                        samesite="lax",
                    )
        except:
            res = redirect(url_for("login"))
            res.delete_cookie(
                COOKIE_NAME,
                path="/",
                secure=True,
                httponly=False,
                samesite="lax",
            )
            return res, 302
    return response, 200


@app.route("/", methods=["GET", "POST"], strict_slashes=False)
def home_page():
    response = make_response(render_template("index.html", ctx={"me": None}))
    if request.method == "GET":
        try:
            token = request.cookies.get(COOKIE_NAME)
            user = jwt.decode(str(token), TOKEN_SECRETE, algorithms=["HS256"])
            if user is None:
                res = redirect(url_for("login"))
                res.delete_cookie(
                    COOKIE_NAME,
                    path="/",
                    secure=True,
                    httponly=False,
                    samesite="lax",
                )
                return res, 302
            else:
                me = User.query.filter_by(id=user.get("id")).first()
                if me is None:
                    res = redirect(url_for("login"))
                    res.delete_cookie(
                        COOKIE_NAME,
                        path="/",
                        secure=True,
                        httponly=False,
                        samesite="lax",
                    )
                    return res, 302
                else:
                    token = jwt.encode({"email": me.email, "id": me.id}, TOKEN_SECRETE)
                    response = make_response(
                        render_template("index.html", ctx={"me": me})
                    )
                    response.set_cookie(
                        COOKIE_NAME,
                        token,
                        timedelta(days=7),
                        path="/",
                        secure=True,
                        httponly=False,
                        samesite="lax",
                    )
        except:
            res = redirect(url_for("login"))
            res.delete_cookie(
                COOKIE_NAME,
                path="/",
                secure=True,
                httponly=False,
                samesite="lax",
            )
            return res, 302

    data = {"success": False, "prediction": None, "error": None}
    if request.method == "POST":
        tweet = request.form.get("tweet")
        if len(str(tweet).split(" ")) < 3:
            data["success"] = False
            data["success"] = None
            data["error"] = "The tweet text must have at least 3 words."
            return make_response(jsonify(data)), 200
        prediction = predict_sentiment(cbtsa_model, tweet, device)
        data["prediction"] = prediction.to_json()
        data["success"] = True
        data["error"] = False
        return make_response(jsonify(data)), 200
    return response, 200


if __name__ == "__main__":
    app.run(debug=AppConfig.DEBUG, host=AppConfig.HOST, port=AppConfig.PORT)
