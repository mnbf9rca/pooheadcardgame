import json
import logging
import os
from tempfile import mkdtemp
from urllib.parse import quote_plus

import jsonpickle
import requests
from flask import (Flask, flash, jsonify, make_response, redirect,
                   render_template, request, session, url_for)
from flask_sessionstore import Session
from flask_sslify import SSLify

from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

import common_db
import controller
from application_helpers import admin_user_required
from cards import Card, Deck
from game import (Game, get_list_of_games_for_this_user,
                  get_list_of_games_looking_for_players, get_users_for_game)
# from https://github.com/cs50/python-cs50
from helpers import apology, login_required, lookup
from player import Player
app_logger = logging.getLogger(__name__)
app_logger.info("startup")

# Configure application
app = Flask(__name__)
sslify = SSLify(app, permanent=True)

# idea from https://cloud.google.com/appengine/docs/flexible/python/using-cloud-sql
# Environment variables are defined in app.yaml.

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


c = common_db.Common_DB()
app_logger.info("got db engine %s", c.common_engine)
c.initialise_models()
app_logger.debug("models initialised")

sqalchemy_database_uri = c.sqalchemy_database_uri
secret_key = c.secret_key
if sqalchemy_database_uri and secret_key:
    app.config['SQLALCHEMY_DATABASE_URI'] = sqalchemy_database_uri
    app.config['SECRET_KEY'] = secret_key
else:
    raise ValueError(
        "Cannot load database connection details - sqalchemy_database_uri, secret_key missing")

app.config["SESSION_PERMANENT"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config['SESSION_TYPE'] = 'filesystem'

# initiate session
Session(app)


# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    app_logger.debug("call to /")
    if session:
        app_logger.debug("has session - redirecting to /logged_in")
        return redirect("/logged_in")
    else:
        app_logger.debug("no session - rendering template index.html")
        return render_template("index.html")


@app.route("/logged_in")
@login_required
def logged_in():
    app_logger.debug("call to /logged_in")
    # user is logged in, check for an active game
    message = request.args.get("msg", default="")

    games = get_list_of_games_for_this_user(session["user_id"],include_finished = False)
    new_games = get_list_of_games_looking_for_players(session["user_id"])
    finished_games = get_list_of_games_for_this_user(session["user_id"], include_finished = True)
    return render_template("logged_in.html", 
                            games=games, 
                            new_games=new_games, 
                            finished_games=finished_games,
                            message=message)


@app.route("/load_game")
@login_required
def load_game():
    app_logger.debug("call to /load_game")
    game_id = request.args.get("game_id")
    if not game_id:
        app_logger.error("called /load_game but didnt include a game ID")
        return apology("must provide game id", 500)

    game_id = int(game_id)
    app_logger.debug("/load_game with game ID %s", game_id)
    game = controller.do_load_game(game_id, session["user_id"])
    if not game:
        # TODO make this better...
        app_logger.error("Unable to load game %s", game_id)
        return "error loading game"
    else:
        session["game"] = game  # even if None
        session["game_id"] = game.state.game_id
        app_logger.info("Loaded game %s", session["game_id"])

    add = request.args.get("add")
    if add:
        # would like to be added to this game
        app_logger.debug(
            f"requesting /logged_in to add user to game {game.state.game_id} for user '{add}'")
        action_result, message = controller.do_add_to_game(game)
        app_logger.debug(
            f"do_add_to_game returned {action_result} and message '{message}'")
    else:
        # loading an existing game without adding the user to it
        action_result = True

    if action_result and game.ready_to_start:
        app_logger.debug(
            "/load_game completed - game ready to play, redirecting to /play")
        return redirect(url_for("play"))
    else:
        app_logger.debug(
            "/load_game completed - game NOT ready to play, returning message '%s'", message)
        return redirect(url_for("logged_in") + f"?msg={quote_plus(message)}")


@app.route("/playcards", methods=["POST"])
@login_required
def play_cards():
    # TODO --> need to build the front end to start sending these
    # find out the action
    app_logger.debug("call to /playcards")
    if session["game"]:
        if not request.is_json:
            app_logger.error("/playcards without JSON payload")
            response = {'action': 'unknown', 'action_result': False,
                        'action_message': "submit your request via POST using JSON"}
        else:
            request_json = request.get_json(cache=False)
            app_logger.debug("/playcards request: %s", request_json)
            response = controller.do_playcards(request_json, session["game"])
            app_logger.debug("/playcards response: %s",
                             jsonpickle.encode(response, unpicklable=False))
            return jsonpickle.encode(response, unpicklable=False)
    else:
        app_logger.error("caleld /playcards without active game")
        response = {'action': "any", 'action_result': False,
                    'action_message': "no active game"}
    return json.dumps(response)


@app.route("/checkstate", methods=["GET", "POST"])
@login_required
def checkstate():
    """ returns the latest checksum recorded for this game in the database,
        and the latest held in game state in session """
    game = session["game"]
    response = {"action": "haschanged",
                "database_checksum": game.get_database_checksum()}
    return json.dumps(response)


@app.route("/getgamestate")
@login_required
def getgamestate():
    """returns a JSON object to caller with a summary of the current
       state of the game, excluding sensitive information such as
       hidden cards, cards in other players' hands, or the deck"""
    state = jsonpickle.encode(controller.get_game_state(
        session["game"]), unpicklable=False)
    resp = make_response(state, 200)
    resp.headers['Content-Type'] = 'application/json'
    app_logger.debug("/getgamestate returns: %s", state)
    return resp


@app.route("/game_internals")
@admin_user_required
def game_internals():
    game = session["game"]
    if game:
        game_state = {"active-game": True,
                      'state': game}
    else:
        game_state = {"active-game": False}
    game_state = jsonpickle.encode(game_state, unpicklable=False)
    resp = make_response(game_state, 200)
    app_logger.debug("/game_internals returns: %s", game_state)
    resp.headers['Content-Type'] = 'application/json'
    return resp


@app.route("/startnewgame", methods=["GET", "POST"])
@login_required
def startnewgame():
    if request.method == "POST":
        # tehy have sent the new game definition
        # no game - start one
        # find out how many people the ywant
        # and validate the other new game properties
        if request.is_json:
            request_json = request.get_json(cache=False)
            app_logger.debug("/startnewgame with JSON: %s", request_json)
            response, game = controller.do_start_new_game(request_json, session["user_id"])
            if game:
                session["game_id"] = game.state.game_id
                session["game"] = game
                response["redirect"] = url_for("logged_in") + response["redirect_querystring"]
            resp = make_response(jsonpickle.encode(
                response, unpicklable=False), 200)
            resp.headers['Content-Type'] = 'application/json'
            return resp
        else:
            app_logger.error("/startnewgame POST without JSON")
            response = {"startnewgame": False,
                        "message": "you must submit your message as a JSON encoded object"}
            resp = make_response(jsonpickle.encode(response, unpicklable=False), 400)
            resp.headers['Content-Type'] = 'application/json'
            return resp

    else:
        app_logger.debug("/startnewgame called via GET")
        # they want to start a new game
        # and have requested via http get
        return render_template("configure_new_game.html", game_options=Game.game_properties)


@app.route("/play")
@login_required
def play():
    # if no game, start a new one
    if session["game_id"] == None:
        return redirect(url_for('startnewgame'))
    else:
        # take game from session
        game = session["game"]
        controller.do_reload_game(game)
        return render_template("play.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        username = request.form.get("username").lower()
        password = request.form.get("password")

        user_id, is_admin = controller.do_login(username, password)
        if user_id:
            session["user_id"] = user_id
            session["is_admin"] = is_admin
            session["password"] = password
            session["game"] = None
            session["game_id"] = None
            return redirect(url_for("logged_in"))
        else:
            return apology("Incorrect username or password", 403)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    game = session.get("game")
    if game:
        controller.do_save_game(game)
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure passwords match
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords must match", 400)

        # Query database for username
        c = common_db.Common_DB()
        rows = c.execute(c.common_engine, "SELECT player_id, hash FROM users WHERE username = :username",
                         username=request.form.get("username"))

        if len(rows) != 0:
            return apology("username already taken, sorry")
        this_session = c.common_Sessionmaker()
        result = c.execute(this_session, "INSERT INTO users (username, hash) VALUES (:username, :password_hash)",
                           username=request.form.get("username").lower(), password_hash=generate_password_hash(request.form.get("password")))
        if not result:
            this_session.rollback()
            this_session.close()
            return apology("could not register")
        this_session.commit()
        this_session.close()

        # Redirect user to home page
        return redirect(url_for('login'))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
