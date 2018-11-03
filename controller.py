import json
import logging
import os
from urllib.parse import quote_plus

import jsonpickle
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

import common_db
from cards import Card, Card_Types, Deck
from game import Game, get_users_for_game
from models import (Base, Model_Card, Model_Game, Model_Player,
                    Model_Player_Game)
from player import Model_Player, Player, get_player_for_username

logger = logging.getLogger(__name__)


def do_login(username, password):
    """checks the username and password. If valid returns the user's ID and whether they have admin rights or not"""

    query = get_player_for_username(username)
    if not query or len(query) != 1 :
        return None, None

    query = query[0]

    if not check_password_hash(query["hash"], password):
        return None, None

    else:
        return query["player_id"], query["is_admin"]


def do_save_game(game):
    c = common_db.Common_DB()
    s = c.common_Sessionmaker()
    if game.save(s):
        s.commit()
        s.close()
        return True
    else:
        s.rollback()
        s.close()
        return False


def do_reload_game(game):
    c = common_db.Common_DB()
    s = c.common_Sessionmaker()
    game.load(s)
    s.close()


def do_load_game(game_id, this_player_id):
    """loads a game object"""
    c = common_db.Common_DB()

    logger.info(f"Starting to load game for ID '{game_id}'")
    game = Game()
    game.state.game_id = game_id
    game.state.this_player_id = this_player_id
    logger.debug("Created game")

    players = get_users_for_game(game_id, c.common_engine)
    logger.debug(f"players for game {game_id} identified: {players}")
    game.players = []
    for player in players:
        p = Player(player)
        if p.ID == this_player_id:
            logger.debug("Found this player with ID %s", this_player_id)
            game.this_player = p
        game.players.append(p)

    if not game.load(c.common_engine):
        logger.error(f"Failed to load game {game_id}")

    logger.info(f"do_load_game complete for game {game_id}")
    return game


def do_add_to_game(game):
    """attempts to add user to game"""
    if not game:
        raise ValueError("Tried to do_add_to_game without game")
    # looking to add themselves to this game
    # check whether this is allowed.
    c = common_db.Common_DB()
    this_session = c.common_Sessionmaker()
    if game.state.deal_done:
        message = "deal already done - can't add to game"
        action_result = False       

    action_result, message = game.add_players_to_game(game.state.this_player_id)
    if action_result:
        # added to the game. Check if the game is ready
        if game.ready_to_start:
            # do the deal
            game.deal()
            action_result, message = game.save(this_session)
        else:
            action_result, message = game.save(this_session)
            if action_result:
                message = "Added you to the game. Now sit tight and wait for enough other players to join."
    if action_result:
        this_session.commit()
    else:
        this_session.rollback()
    this_session.close()

    return action_result, message


def do_start_new_game(request_json, this_player_user_id):
    """starts a new game"""
    game = Game(this_player_user_id)
    logger.debug(f"do_start_new_game with {request_json}")
    parsed_values, message = game.parse_requested_config(request_json)
    if parsed_values:
        # initalise a session
        logger.debug(f"do_start_new_game parsed values, creating session to commit save.")
        c = common_db.Common_DB()
        this_session = c.common_Sessionmaker()
        result, message = game.save(this_session)
        if not result:
            logger.error("do_start_new_game save failed, rolling back")
            this_session.rollback()
            response = {"startnewgame": False,
                        "message": message}
        else:
            logger.info("do_start_new_game save ok, committing")
            this_session.commit()
            msg = quote_plus(f"Game created successfully with ID {game.state.game_id}"
                             ". Now let's wait for some other players to join.")
            response = {"startnewgame": True,
                        "new_game_id": game.state.game_id,
                        "message": message,
                        "redirect_querystring": f"?msg={msg}"}
        this_session.close()
        logger.debug("do_start_new_game completed successfully - returning: %s",
                     jsonpickle.encode(response, unpicklable=False))
        return response, game
    else:
        logger.error("do_start_new_game unable to parse values: %s", message)
        response = {"startnewgame": False,
                    "message": message}
        return response, None


def do_playcards(request_json, game):
    """validates that a user is allowed to play a specific action
    and if so, executes that action and returns the result"""
    # first, let's get the action and respond with a failure if we can't.
    if not request_json:
        logger.error("do_playcards called without reqeust_json")
        raise ValueError("do_playcards called without request_json")
    action = request_json.get("action")
    if not action:
        logger.error("do_playcards no action in json")
        response = {'action': 'unknown', 'action_result': False,
                    'action_message': "no action specified"}
        return response

    cards = request_json.get("action_cards")

    list_of_actions_which_require_cards = ["swap", "play"]
    if action in list_of_actions_which_require_cards and not cards:
        logger.error(f"do_playcards swap called wtih action '{action}' no cards specified to play")
        response = {'action': action, 'action_result': False,
                    'action_message': "no cards specified"}
        return response

    # at least we've got a candidate action - let's reload the game state from teh database
    c = common_db.Common_DB()
    s = c.common_Sessionmaker()
    game.load(s)

    if action == "swap":
        # we have a action_cards object - submit to game
        response = game.swap_cards(cards, game.this_player)

    elif action == "no_swap":
        # player has opted to play without swapping
        logger.debug("do_playcards starting game without swap")
        response = game.play_no_swap()
    elif action == "play":
        # play these cards
        logger.debug("do_playcards starting play")
        response = game.play_move(cards)

    elif action == "pick":
        # player has to pick up the cards
        response = game.play_pick_up()

    else:
        # now set this as default action in case it fails to match any action below
        response = {'action': action, 'action_result': False,
                    'action_message': "unknown action :" + action}

    logger.debug("do_playcards %s: %s", action, response)
    if not response["action_result"]:
        logger.error(response["action_message"])
        s.rollback()
        s.close
        return response
        
    if game.save(s):
        s.commit()
        logger.debug("do_playcards saved game")
    else:
        s.rollback()
        logger.error("do_playcards unable to save, transaction rolled back")
        response = {'action': action, 'action_result': False,
                    'action_message': "Unable to save game"}

    s.close()
    return response


def get_game_state(game):
    """calculates the game state that a given player is allowed
    to see (e.g. they can see their own hand cards, but not)
    the hand cards of other players) and returns it"""
    if not game:
        # set default response to indicate no active game
        return {"active-game": False}
    if not game.this_player:
        raise ValueError(
            "Tried to get game state but dont know current player")

    # always reload in case other users have caused a state change

    do_reload_game(game)
    game_state = {'active-game': True,
                  "state": game.state}
    # calculate the allowed moves at this stage of teh game for this player
    allowed_moves = game.calculate_player_allowed_actions()

    # if allowed_moves["allowed_action"] == "lost":
    # TODO move this to GAME at some point
    # this will only just have been computed. Save.
    #    game.state.players_finished.append(game.this_player.ID)
    #    game.save()

    # Construct an object which represents the parts of the game that we want to expose to users
    players_state = []
    for player in game.players:
        players_state.append(player.summarise(game.this_player.ID))

    # construct response
    total_state = {'game': game_state,
                   'allowed_moves': allowed_moves,
                   'players_state': players_state,
                   "checksum": game.checksum()}

    logger.debug("get_game_state total_state: %s", jsonpickle.dumps(total_state, unpicklable=False))
    return total_state
