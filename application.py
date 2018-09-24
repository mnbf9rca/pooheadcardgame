import json
import os
from tempfile import mkdtemp
import jsonpickle
from flask import (Flask, flash, jsonify, make_response, redirect,
                   render_template, request, session, url_for)
from flask_session import Session
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from cards import Card, Deck
from game import Game, get_users_for_game, get_list_of_games_for_this_user, get_list_of_games_looking_for_players
# from https://github.com/cs50/python-cs50
from helpers import apology, login_required, lookup
from application_helpers import admin_user_required
from player import Player
# from https://github.com/cs50/python-cs50
from sql import SQL
from urllib.parse import quote_plus

# from game_helpers import get_users_for_game

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
    message = ""
    try:
         message = request.args["msg"]
    except (KeyError, IndexError):
        pass
    except:
        raise

    games = get_list_of_games_for_this_user(session["user_id"], db)
    new_games = get_list_of_games_looking_for_players(session["user_id"], db)
    return render_template("logged_in.html", games=games, new_games=new_games, message = message)

@app.route("/load_game")
@login_required
def load_game():
    if not request.args["game_id"]:
        return apology("must provide game id", 500)

    game_id = int(request.args["game_id"])

    # check the users playing this game

    game = Game(session["user_id"])
    session["game"] = game

    game.state.game_id = game_id
    session["game_id"] = game.state.game_id


    message = "Loaded the game, but it's not ready to start yet. Wait for other players."
    players = get_users_for_game(game_id, db)
    print("players loaded: " + str(players))
    game.players = []
    for player in players:
        game.players.append(Player(player))
    game.load(db)
    add = None
    try:
        add = request.args["add"]
    except (KeyError, IndexError):
        pass
    except:
        raise

    if add:
        # looking to add themselves to this game
        # check whether this is allowed.
        if not game.add_players_to_game(session["user_id"], db):
            message = quote_plus("could not add you to the game")
            return redirect(url_for("logged_in") + f"?msg={message}")
        else:
            message = "Added you to the game. Now sit tight and wait for enough other players to join."

    if game.ready_to_start:
        if not game.state.deal_done:
            game.deal()
            game.save(db)
        return redirect("/play")
    else:
        msg = quote_plus(message)
        return redirect(url_for("logged_in") + f"?msg={msg}")

@app.route("/playcards", methods=["POST"])
@login_required
def play_cards():
    # TODO --> need to build the front end to start sending these
    # find out the action
    if session["game"]:
        if not request.is_json:
            response = {'action':'unknown', 'action_result':False, 'action_message': "submit your request via POST using JSON"}
        else:
            request_json = request.get_json(cache=False)
            # first, let's get the action and respond with a failure if we can't.
            try:
                action = request_json["action"]
            except (KeyError, IndexError):
                response = {'action':'unknown', 'action_result':False, 'action_message':"no action specified"}
                return json.dumps(response)
            except:
                raise
            # now set this as default action in case it fails to match any action below
            response = {'action':action, 'action_result':False, 'action_message':"unknown action :" + action}

            # at least we've got a candidate action - let's reload the game state from teh database
            game = session["game"]
            player = session["player"]
            game.load(db)

            if action == "swap":
                try:
                    cards = request_json["action_cards"]
                except (KeyError, IndexError):
                    response = {'action':action, 'action_result':False, 'action_message':"no cards specified"}
                    return json.dumps(response)
                except:
                    raise

                # we have a action_cards object - submit to game
                response = game.swap_cards(cards, player)

            elif action == "no_swap":
                # player has opted to play without swapping
                print("starting game without swap")
                response = game.play_no_swap()
            elif action == "play":
                # play these cards
                print("starting play")
                try:
                    cards = request_json["action_cards"]
                except (KeyError, IndexError):
                    response = {'action':action, 'action_result':False, 'action_message':"no cards specified"}
                    return json.dumps(response)

                response = game.play_move(cards, player)

            elif action == "pick":
                # player has to pick up the cards
                response = game.play_pick_up()

            if response["action_result"]:
                # if any of the items above report success, save state
                game.save(db)
                print("saved game")
    else:
        response = {'action':"any", 'action_result':False, 'action_message':"no active game"}
    return json.dumps(response)

@app.route("/checkstate", methods=["GET", "POST"])
@login_required
def checkstate():
    """ returns the latest checksum recorded for this game in the database,
        and the latest held in game state in session """
    game = session["game"]
    response = {"action":"haschanged",
                "database_checksum": game.get_database_checksum(db)}
    return json.dumps(response)


@app.route("/getgamestate")
@login_required
def getgamestate():
    """returns a JSON object to caller with a summary of the current
       state of the game, excluding sensitive information such as
       hidden cards, cards in other players' hands, or the deck"""
    game = session["game"]
    # set default response to indicate no active game
    game_state= {"active-game":False}
    players_state = []
    allowed_moves = []
    # if we have an active game, use that
    if game:
        # always reload in case other users have caused a state change
        game.load(db)
        game_state = {'active-game':True,
                        "state": game.state}
        # calculate the allowed moves at this stage of teh game for this player
        allowed_moves  = game.calculate_player_allowed_actions()
        if allowed_moves["allowed_action"] == "lost":
            # this will only just have been computed. Save.
            game.state.players_finished.append(session["user_id"])
            game.save(db)
        # Construct an object which represents the parts of the game that we want to expose to users
        for player in game.players:
            players_state.append( player.summarise(session["user_id"]) )
    print(jsonpickle.encode(players_state, unpicklable=False))
    # construct response
    total_state = { 'game': game_state,
                    'allowed_moves' : allowed_moves,
                    'players_state': players_state,
                    "checksum":game.checksum()}
    print("total_state_", total_state)

    resp = make_response(jsonpickle.encode(total_state, unpicklable=False), 200)
    resp.headers['Content-Type']= 'application/json'
    return resp


@app.route("/game_internals")
@admin_user_required
def game_internals():
    game = session["game"]
    if game:
        game_state= {"active-game":True,
                    'state':game}
    else:
        game_state= {"active-game":False}
    resp = make_response(jsonpickle.encode(game_state, unpicklable=False), 200)
    resp.headers['Content-Type']= 'application/json'
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
            # start to parse it
            game=Game(session["user_id"])
            print("initiated a game")
            parsed_values, message = game.parse_requested_config(request_json)
            if parsed_values:
                game_id = game.save(db)
                session["game_id"] = game.state.game_id
                session["game"] = game
                msg = quote_plus(f"Game created successfully with ID {game.state.game_id}. Now let's wait for some other players to join.")
                print("msg",msg)
                response = {"startnewgame":True,
                            "new_game_id": game_id,
                            "message": message,
                            "redirect": url_for("logged_in") + f"?msg={msg}"}
                return jsonpickle.dumps(response, unpicklable=False)
            else:
                response = {"startnewgame": False,
                            "message": message}
                resp = make_response(jsonpickle.encode(response, unpicklable=False), 200)
                resp.headers['Content-Type']= 'application/json'
                return resp
        else:
            response = {"startnewgame": False,
                        "message": "you must submit your message as a JSON encoded object"}
            resp = make_response(jsonpickle.encode(response, unpicklable=False), 400)
            resp.headers['Content-Type']= 'application/json'
            return resp

    else:
        # they want to start a new game
        # and have requested via http get
        return render_template("configure_new_game.html", game_options = Game.game_properties)

@app.route("/play")
@login_required
def play():
    # if no game, start a new one
    if session["game_id"] == None:
        return redirect(url_for('startnewgame'))
    else:
        # take game from session
        game = session["game"]
        game.load(db)

    for player in game.players:
        userid = session["user_id"]
        print(f'player {player.ID} session {userid}')
        if player.ID == session["user_id"]:
            session["player"] = player
            break

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
        rows = db.execute("SELECT player_id, hash, is_admin FROM users WHERE username = :username",
                          username=request.form.get("username").lower())

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["player_id"]
        session["is_admin"] = rows[0]["is_admin"]
        session["game_id"] = None
        session["game"] = None

        # Redirect user to home page
        return redirect(url_for("logged_in"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    if "game" in session:
        if session["game"]:
            game = session["game"]
            game.save(db)
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
        rows = db.execute("SELECT player_id, hash FROM users WHERE username = :username",
                          username=request.form.get("username"))

        if len(rows) != 0:
            return apology("username already taken, sorry")

        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :password_hash)",
                          username=request.form.get("username").lower(), password_hash=generate_password_hash(request.form.get("password")))
        if not result:
            return apology("could not register")


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
