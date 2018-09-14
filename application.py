import os
import json
from cards import Card, Deck
from game import Game
from player import Player

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
from game_helpers import persist_cards_to_database, get_users_for_game, load_cards_from_database

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure Library to use SQLite database
db = SQL("sqlite:///app.db")


@app.route("/")
def index():
    if session:
       return redirect("/logged_in")
    else:
        return render_template("index.html")

@app.route("/logged_in")
@login_required
def logged_in():
     # user is logged in, check for an active game
    games = db.execute("SELECT game_id FROM player_game WHERE player_id = :player_id",
                        player_id=session["user_id"])


    return render_template("logged_in.html", games=games)

@app.route("/load_game")
@login_required
def load_game():
    if not request.args["game_id"]:
        return apology("must provide game id", 500)
    game_id = int(request.args["game_id"])

    # check the users playing this game

    players = get_users_for_game(game_id, db)
    print("players loaded: " + str(players))
    g = Game(players)
    session["game"] = g

    g.game_id = game_id
    session["game_id"] = g.game_id
    g.load(db)

    # load the deck

    print("deck loaded - " + str(len(g.deck)) + "cards")

    # load the burn pile
    # load the played cards
    # load the deck

    return redirect("/play")

@app.route("/playcards")
@login_required
def play_cards():
    # find out the action
    if session["game"]:
        game = session["game"]
        player = session["player"]
        action = request.args["action"]
        if action == "Swap":
            # do something
            print("starting swap")
        elif action == "No swap":
            # player has opted to play without swapping
            print("starting game without swap")
            game.players_ready_to_start.append(player.ID)
            print("ready to start: " + str(game.players_ready_to_start))
        elif action == "Play":
            # play these cards
            print("starting play")
            # find out which cards were selected
            selected_cards = request.args.getlist("card")

        game.rotate_player()
        print("final play order: " + json.dumps(game.play_order))
        game.save(db)

    return redirect("/play")


@app.route("/play")
@login_required
def play():
    # if no game, start a new one
    if session["game_id"] == None or request.args.getlist("new"):
        #no game - start one
        game = Game([int(session["user_id"]),2,3])

        game.deal()
        #save the game
        game_id = game.save(db)

        print("game id:" + str(game_id))
        session["game_id"] = game.game_id
        session["game"] = game
    else:
        # take game from session
        game = session["game"]
        game.load(db)

    for players in game.players:
        if players.ID == session["user_id"]:
            player = players
            session["player"] = player
            break


    return render_template("play.html", game = game, player = player)

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

        # Query database for username
        rows = db.execute("SELECT player_id, hash FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["player_id"]
        session["game_id"] = None
        session["game"] = None

        # Redirect user to home page
        return redirect("/logged_in")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    if "game" in session:
        if session["game"]:
            g = session["game"]
            g.save(db)
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


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
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :password_hash)",
                          username=request.form.get("username"), password_hash=generate_password_hash(request.form.get("password")))
        if not result:
            return apology("could not register")
#
#        rows = db.execute("SELECT player_id, hash FROM users WHERE username = :username",
#                          username=request.form.get("username"))
#
#        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
#            return apology("invalid username and/or password", 403)
#
#        # Remember which user has logged in
#        session["user_id"] = rows[0]["player_id"]

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
