import os
from cards import Card, Deck
from game import Game

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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
    #if session["user_id"]:
     #  return redirect("/logged_in")
    #else:
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
    if not request.form.get("game_id"):
        return apology("must provide game id", 500)
    game_id = int(request.form.get("game_id"))

    game = Game()
    game.game_id = game_id

    # load the deck
    cards = db.execute("SELECT card_suit, card_rank FROM game_cards WHERE game_id = :game_id AND card_location = :pile ORDER BY card_sequence DESC",
                        game_id = game_id, pile = game.pile_types["deck"])
    for card in cards:
        card_to_add = Card()
        card_to_add.rank = card.card_rank
        card_to_add.suit = card.card_suit
        game.deck.append(card_to_add)

    # load the burn pile
    # load the played cards
    # load the deck




@app.route("/play")
@login_required
def play():
    # if no game, start a new one
    if session["game_id"] == None:
        #no game - start one
        g = Game([1,2])

        g.deal()
        #save the game
        result = db.execute('INSERT INTO "games" ("last_player_id","less_than_card","transparent_card","burn_card","reset_card","number_of_decks","number_face_down_cards","number_hand_cards","current_turn_number","last_player","gameid") VALUES (NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)')
        print("game id:" + str(result))
        g.game_id = result

        #now save the cards
        if len(g.deck) > 0:
            # save the deck
            i = 0
            print("begin")
            for card in g.deck:
                print(card + " at position " + str(i))
                insert = "INSERT INTO game_cards (game_id, card_location, card_suit, card_rank, card_sequence) VALUES (" + str(g.game_id) + ", " + str(Game.pile_types_inverse["deck"]) + ", " + str(card.suit) + ", " +  str(card.rank) + ", " + str(i) + ")"
                result = db.execute(insert)
                i += 1



        # save the burn pile
        # save the played cards
        # save the deck


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

        # Query database for username
        rows = db.execute("SELECT player_id, hash FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["player_id"]
        session["game_id"] = None

        # Redirect user to home page
        return redirect("/logged_in")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

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

        rows = db.execute("SELECT player_id, hash FROM users WHERE username = :username",
                          username=request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["player_id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")




def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
