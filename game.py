import json
import logging
import sys
from collections import namedtuple
from enum import Enum
from random import shuffle
from typing import List
from zlib import crc32
import jsonpickle

import jsonpickle
from sqlalchemy.ext.declarative import declarative_base

import common_db
from cards import Card, Card_Types, Deck
from models import Model_Card, Model_Game, Model_Player, Model_Player_Game
from player import Player

logger = logging.getLogger(__name__)

Base = declarative_base()


class Game(object):

    class Card_Pile_ID(Enum):
        PILE_BURN = Card_Types.CARD_BURN
        PILE_PICK = Card_Types.CARD_PICK
        PILE_PLAYED = Card_Types.CARD_PLAYED
        PILE_DECK = Card_Types.CARD_DECK

    Pile_Objects = {
        Card_Pile_ID.PILE_DECK: "pile_deck",
        Card_Pile_ID.PILE_PICK: "pile_pick",
        Card_Pile_ID.PILE_PLAYED: "pile_played",
        Card_Pile_ID.PILE_BURN: "pile_burn"}
    Pile_Counts = {
        Card_Pile_ID.PILE_DECK: "pile_deck_size",
        Card_Pile_ID.PILE_PICK: "pile_pick_size",
        Card_Pile_ID.PILE_PLAYED: "pile_played_size",
        Card_Pile_ID.PILE_BURN: "pile_burn_size"
    }

    game_properties = {
        "special_cards": [
            {
                "code": "less_than_card",
                "display": "Less than card",
                "value": '7',
                "play_on_anything": False
            },
            {
                "code": "transparent_card",
                "display": "Transparent card",
                "value": 'None',
                "play_on_anything": True
            },
            {
                "code": "burn_card",
                "display": "Burn card",
                "value": '10',
                "play_on_anything": True
            },
            {
                "code": "reset_card",
                "display": "'Can play on anything' card",
                "value": '2',
                "play_on_anything": True
            }
        ],
        "all_cards": ['None', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],
        "number_of_decks": 1,
        "number_face_down_cards": 3,
        "number_hand_cards": 7,
        "number_of_players": 2
    }

    def __init__(self, this_player_id=None, number_of_players=0):
        logger.info("Creating new Game for player %s with %s players",
                    this_player_id,
                    number_of_players)
        self.state = self.State(number_of_players)
        self.cards = self.Cards()
        self.state.this_player_id = this_player_id
        self.players = []
        self.this_player = None
        if this_player_id:
            this_player = Player(this_player_id)
            self.this_player = this_player
            self.add_player(this_player)

    def add_player(self, player):
        self.players.append(player)
        self.state.number_of_players_joined = len(self.players)

    def add_players_to_game(self, player_id, session):
        """Checks if there's enough space left in this game, and
           that this player is not already in the list,
           adds the selected player ID"""

        # check if a) number players < number requested
        # and this player is not already in the list of players
        if (not self.ready_to_start and
                len(list(set(player.ID for player in self.players) - set([player_id]))) == len(self.players)):
            logger.debug("adding this player to the game")

            player_to_add = Player(player_id)

            self.add_player(player_to_add)
            self.state.play_order = [player.ID for player in self.players]
            if self.save(session):
                logger.debug("successfully added player to game")
                return True
            else:
                logger.error("could not add player to game")
                return False
        else:
            logger.error(
                f"could not add player to game - either too many players (evaluates to: {self.ready_to_start})"
                ", or this player is already in the game")
            return False

    def __parse_int_from_json(self, value_to_clean, min=0, max=13):
        """takes a value sent from the jquery serialised form and returns an integer equivalent to a card rank"""
        if value_to_clean.lower() == "none":
            val = 0
        else:
            try:
                val = int(value_to_clean)
            except ValueError:
                raise
        if (val > max) or (val < min):
            raise ValueError(
                f"Invalid value provided in requested configuration JSON: {min} < {val} < {max}")
        return val

    def __parse_bool_from_json(self, value):
        if value.lower() == "on":
            return True
        else:
            return False
    

    def parse_requested_config(self, requested_config):
        """parses a serialised configuraiton sent by the new game
           request and assigns the values to the game state object.
           Returns true or false depending on whether the process was successful"""
        list_of_special_cards = []

        for config_item in requested_config:
            name = config_item.get("name")
            value = config_item.get("value")

            if not name or not value:
                message = "Unable to read 'name' or 'value' key in config_item"
                return False, message

            values_to_parse_as_int = {"less_than_card":(0,13), 
                                      "transparent_card":(0,13),
                                      "burn_card":(0,13), 
                                      "reset_card":(0,13), 
                                      "number_face_down_cards":(1,9),
                                      "number_hand_cards":(1,9),
                                      "number_of_decks":(1,2),
                                      "number_of_players_requested":(2,6)}
            
            values_to_parse_as_bool = {"less_than_card_on_anything":("less_than_card", False),
                                        "transparent_card_on_anything":("transparent_card", False),
                                        "burn_card_on_anything":("burn_card", False),
                                        "reset_card_on_anything":("reset_card", False)}

            if name in values_to_parse_as_int:
                min, max = values_to_parse_as_int[name]
                setattr(self.state, name, self.__parse_int_from_json(value, min, max))

            if name in values_to_parse_as_bool:
                state_attribute, currentval = values_to_parse_as_bool[name] 
                # bool is a subclasss of int with value 0 or 1
                values_to_parse_as_bool[name] = (state_attribute, self.__parse_bool_from_json(value))

        # store a list of the "on everything" cards
        for key in values_to_parse_as_bool:
            state_attribute, value = values_to_parse_as_bool[key] 
            parsed_value = getattr(self.state, state_attribute)
            if parsed_value > 0:
                list_of_special_cards.append(parsed_value)
                if value:
                    self.state.play_on_anything_cards.append(parsed_value)

        message = "parsed successfully"
        no_duplicates = len(list_of_special_cards) == len(set(list_of_special_cards))
        if not no_duplicates:
            message = "duplicate special play cards"
        return no_duplicates, message

    def __are_there_enough_players_to_start(self):
        """have enough players joined this game yet?"""
        self.state.number_of_players_joined = len(self.players)
        return self.state.number_of_players_requested == self.state.number_of_players_joined

    ready_to_start = property(fget=__are_there_enough_players_to_start)

    class State(object):
        """holds the current state of this game, excluding players and card decks """

        def __init__(self, number_of_players):

            self.number_of_players_requested = number_of_players
            self.number_of_players_joined = 0
            self.game_finished = False
            self.play_order = None
            self.this_player_id = None
            # game config
            self.game_id = None
            self.less_than_card = 7
            self.transparent_card = 0
            self.burn_card = 10
            self.reset_card = 2
            self.number_of_decks = 1
            self.number_face_down_cards = 3
            self.number_hand_cards = 3
            self.players_ready_to_start = []
            self.players_finished = []
            self.play_on_anything_cards = [2, 10]
            self.deal_done = False

            # game state
            self.current_turn_number = 0
            self.last_player = None
            self.play_list = []
            self.pile_burn_size = 0
            self.pile_pick_size = 0
            self.pile_played_size = 0
            self.pile_deck_size = 0

        @property
        def all_special_cards(self):
            """returns all special cards"""
            cards = []
            cards.append(self.transparent_card)
            cards.append(self.less_than_card)
            cards.append(self.burn_card)
            cards.append(self.reset_card)

            while 0 in cards:
                cards.remove(0)

            cards = set(cards)
            return cards

    class Cards(object):
        """stores cards separately from state to keep secret from client"""

        def __init__(self):
            # piles
            self.pile_burn = []
            self.pile_pick = []
            self.pile_played = []
            self.pile_deck = []

    def get_database_checksum(self):
        """loads the 'checksum' field from teh database for the current game and returns it"""
        c = common_db.Common_DB()
        config = c.execute(c.common_engine, 'SELECT game_checksum FROM games WHERE gameid = :game_id',
                           game_id=self.state.game_id)
        database_checksum = config[0]["game_checksum"]
        return database_checksum

    def checksum(self):
        """calculates a CRC32 checksum for the current state based on an arbitrary but static representative set of game objects"""
        state_summary = jsonpickle.dumps({"play_order": self.state.play_order,
                                          "cards": self.cards,
                                          "players_ready_to_start": self.state.players_ready_to_start,
                                          "players_finished": self.state.players_finished,
                                          "play_list": self.state.play_list})
        return str(crc32(state_summary.encode()))

    def deal(self):
        """creates a new deck of cards, deals to each player, then puts the remaining cards in the pick stack"""
        logger.debug("starting deal")
        new_deck = Deck()

        # cards are shuffled so we just issue them sequentially
        for _ in range(self.state.number_face_down_cards):
            for player in self.players:
                player.face_down.append(new_deck.deal())
                player.face_up.append(new_deck.deal())

        for _ in range(self.state.number_hand_cards):
            for player in self.players:
                player.hand.append(new_deck.deal())

        self.cards.pile_deck = new_deck.cards
        self.__update_pile_sizes()
        self.state.deal_done = True
        logger.debug("Deal done")

    def write_state_to_database(self, session):
        c = common_db.Common_DB()
        if not self.state.game_id:
            logger.debug("save - no current game_id")
            querystring = "INSERT INTO games (game_finished, players_requested, game_ready_to_start, game_checksum, players_finished, play_on_anything_cards, play_order, less_than_card, transparent_card, burn_card, reset_card, number_of_decks, number_face_down_cards, number_hand_cards, current_turn_number, players_ready_to_start, deal_done) VALUES (:game_finished, :number_of_players_requested, :game_ready_to_start, :game_checksum, :players_finished, :play_on_anything_cards,:play_order,:less_than_card,:transparent_card,:burn_card,:reset_card,:number_of_decks,:number_face_down_cards,:number_hand_cards,:current_turn_number,:players_ready_to_start, :deal_done)"
            result = c.execute(session, querystring,
                               game_finished=self.state.game_finished,
                               number_of_players_requested=self.state.number_of_players_requested,
                               game_ready_to_start=self.ready_to_start,
                               game_checksum=self.checksum(),
                               players_finished=json.dumps(self.state.players_finished),
                               play_on_anything_cards=json.dumps(self.state.play_on_anything_cards),
                               play_order=json.dumps(self.state.play_order),
                               less_than_card=self.state.less_than_card,
                               transparent_card=self.state.transparent_card,
                               burn_card=self.state.burn_card,
                               reset_card=self.state.reset_card,
                               number_of_decks=self.state.number_of_decks,
                               number_face_down_cards=self.state.number_face_down_cards,
                               number_hand_cards=self.state.number_hand_cards,
                               current_turn_number=self.state.current_turn_number,
                               players_ready_to_start=json.dumps(self.state.players_ready_to_start),
                               deal_done=self.state.deal_done)
        else:
            logger.debug("save - with game_id")
            querystring = "UPDATE games SET game_finished = :game_finished, players_requested = :number_of_players_requested, game_ready_to_start = :game_ready_to_start, game_checksum = :game_checksum, players_finished = :players_finished, play_on_anything_cards = :play_on_anything_cards, play_order = :play_order, less_than_card = :less_than_card, transparent_card = :transparent_card, burn_card = :burn_card, reset_card = :reset_card, number_of_decks = :number_of_decks, number_face_down_cards = :number_face_down_cards ,number_hand_cards = :number_hand_cards,current_turn_number = :current_turn_number, players_ready_to_start = :players_ready_to_start, deal_done = :deal_done WHERE gameid = :game_id"
            result = c.execute(session, querystring,
                               game_finished=self.state.game_finished,
                               number_of_players_requested=self.state.number_of_players_requested,
                               game_ready_to_start=self.ready_to_start,
                               game_checksum=self.checksum(),
                               players_finished=json.dumps(self.state.players_finished),
                               play_on_anything_cards=json.dumps(self.state.play_on_anything_cards),
                               play_order=json.dumps(self.state.play_order),
                               less_than_card=self.state.less_than_card,
                               transparent_card=self.state.transparent_card,
                               burn_card=self.state.burn_card,
                               reset_card=self.state.reset_card,
                               number_of_decks=self.state.number_of_decks,
                               number_face_down_cards=self.state.number_face_down_cards,
                               number_hand_cards=self.state.number_hand_cards,
                               current_turn_number=self.state.current_turn_number,
                               players_ready_to_start=json.dumps(self.state.players_ready_to_start),
                               deal_done=self.state.deal_done,
                               game_id=self.state.game_id)

        if result:
            message = f"Game saved with ID {int(result)}"
            if not(self.state.game_id):
                self.state.game_id = int(result)
        else:
            message = "Unable to save game state"

        return result, message

    def get_list_of_game_cards_to_store(self):
        cards_to_store = []
        for pile_id in self.Card_Pile_ID:
            # iterate through each pile ID
            # append the list of cards
            logger.debug("saving pile_id %s", pile_id)
            relevant_pile = getattr(self.cards, self.Pile_Objects[pile_id])

            cards_to_store.extend([ f"({self.state.game_id}, NULL, {pile_id.value}, {card.suit}, {card.rank})" for card in relevant_pile])
            logger.debug("cards_to_store now includes: %s", cards_to_store)
        return cards_to_store

    def store_game_cards(self, session):
        c = common_db.Common_DB()
        cards_to_store = self.get_list_of_game_cards_to_store()
        if not cards_to_store:
            return True,  "no cards to store"

        logger.debug("starting to save game cards")
        cards_to_store = ", ".join(cards_to_store)
        result = c.execute(
            session, f"INSERT INTO game_cards (game_id, player_id, card_location, card_suit, card_rank) VALUES {cards_to_store};")
        if result:
            message = "failed to store game gards, rolling back"
            retval = False
        else:
            message = "saved game cards"
            retval = True
        return retval, message

    def save_players(self, session):
        for player in self.players:
            logger.debug("saving player: %s", jsonpickle.dumps(player, unpicklable=True))
            save_result, message = player.save(session, self.state.game_id)
            if not save_result:
                return False, message
            # store a reference to this player's object on the game itself
            if player.ID == self.state.this_player_id:
                self.this_player = player
        return True, "Players all saved successfully"

    def delete_existing_game_cards(self, session):
        c = common_db.Common_DB()
        result = c.execute(session, f"DELETE FROM game_cards WHERE game_id = {self.state.game_id} and player_id is null;")
        if result == None:
            # some kind of exception
            message = "unable to delete existing game cards"
            return False, message
        return True, f"Old game cards removed from DB, {result} records affected"

    def save(self, session):
        """saves the current state of the game, using a transaction to ensure
           that we can roll back if not successful. If this is a new game
           without an ID, it creates one, otherwise it updates the existing one"""
        logger.info("beginning game save")

        write_state_result, message = self.write_state_to_database(session)

        if not write_state_result:
            logger.error(message)
            return False, message
        
        # stored ok - log for debug
        logger.debug(message)

        delete_cards, message = self.delete_existing_game_cards(session)

        if not delete_cards:
            logger.error(message)
            return False, message
        
        # stored ok - log for debug
        logger.debug(message)

        store_cards, message = self.store_game_cards(session)
        if not store_cards:
            logger.error(message)
            return False, message
        
        # stored ok - log for debug
        logger.debug(message)

        player_save, message = self.save_players(session)
        if not player_save:
            logger.error(message)
            return False, message

        # stored ok - log for debug
        logger.debug(message)

        # return the game_id for future use
        logger.debug("game saved successfully")
        return True, "game saved successfully"

    def rotate_player(self):
        """rotates the play list once a player has played"""
        last_player = self.state.play_order.pop(0)
        self.state.last_player = last_player
        self.state.play_order.append(last_player)

    def load(self, session):
        """loads the configuration of the game defined by state.game_id"""
        logger.debug("starting game load")
        if not self.state.game_id:
            logger.error("tried to load game without setting game_id")
            raise ValueError('tried to load game without setting game_id.')
        if not self.state.this_player_id:
            logger.error(
                "tried to load game without setting ID of current player or it doesnt exist in current instantiation")
            raise ValueError(
                'tried to load game without setting ID of current player or it doesnt exist in current instantiation.')

        # load game config
        # fields not retrieved: `last_move_at`, `gameid`,`checksum`,`game_ready_to_start`
        c = common_db.Common_DB()

        config = c.execute(session, 'SELECT "game_finished", "players_requested", "players_finished", "play_on_anything_cards", "play_order", "less_than_card","transparent_card","burn_card","reset_card","number_of_decks","number_face_down_cards","number_hand_cards","current_turn_number","last_player", "players_ready_to_start", "deal_done" FROM games WHERE gameid = :game_id',
                           game_id=self.state.game_id)
        config = config[0]
        logger.debug("config loaded from db: %s", jsonpickle.dumps(config, unpicklable=False))
        self.state.game_finished = config["game_finished"]
        self.state.number_of_players_requested = config["players_requested"]
        self.state.players_finished = json.loads(config["players_finished"])
        self.state.play_on_anything_cards = json.loads(config["play_on_anything_cards"])
        self.state.play_order = json.loads(config["play_order"])
        self.state.less_than_card = config["less_than_card"]
        self.state.transparent_card = config["transparent_card"]
        self.state.burn_card = config["burn_card"]
        self.state.reset_card = config["reset_card"]
        self.state.number_of_decks = config["number_of_decks"]
        self.state.number_face_down_cards = config["number_face_down_cards"]
        self.state.number_hand_cards = config["number_hand_cards"]
        self.state.current_turn_number = config["current_turn_number"]
        self.state.players_ready_to_start = json.loads(config["players_ready_to_start"])
        self.state.deal_done = config["deal_done"]

        # load decks
        logger.debug("reconstructing decks")
        for pile_id in self.Card_Pile_ID:
            setattr(self.cards, self.Pile_Objects[pile_id], self.__load_cards_from_database(
                pile_id.value, self.state.game_id, session))

        self.__update_pile_sizes()

        logger.debug("loading players, if any")
        for player in self.players:
            if not player.load(session, self.state.game_id):
                logger.error("Unable to load player: %s", player.ID)
                return False
            # store a reference to this player's object on the game itself
            if player.ID == self.state.this_player_id:
                self.this_player = player
        logger.debug("completed game load")
        return True

    def __update_pile_sizes(self):
        """updates the summary count of each pile size, and copies the played pile to the active state"""
        for pile_id in self.Card_Pile_ID:
            setattr(self.state, self.Pile_Counts[pile_id], len(
                getattr(self.cards, self.Pile_Objects[pile_id])))

        self.state.play_list = self.cards.pile_played

    def calculate_player_allowed_actions(self):
        """calculates what action, if any, the current player is allowed to perform

            returns:
            always:
                "allowed_action": finished | lost | wait | swap | play,
                "action_message": to display to the end user

            depending on state:
                "allowed_cards": Card_Types.Short_Name,
                "allowed_players": a list of players allowed to play,
                "is_next_player": boolean,
        """
        logger.debug("starting calculate_player_allowed_actions")
        response = {"allowed_action": "unknown", "allowed_players": "unknown"}

        all_player_id = set([player.ID for player in self.players])
        logger.debug(f"all_player_id: {all_player_id}")

        players_still_to_swap = (list(all_player_id - set(self.state.players_ready_to_start)))
        logger.debug(f"players_still_to_swap: {players_still_to_swap}")

        players_still_not_finished = (list(all_player_id - set(self.state.players_finished)))
        logger.debug(f"players_still_not_finished: {players_still_not_finished}")
        logger.debug(
            f"set(self.state.players_ready_to_start): {set(self.state.players_ready_to_start)}")

        logger.debug(f"set(self.state.players_finished): {set(self.state.players_finished)}")

        if len(players_still_to_swap) > 0:
            # still some players not yet ready to start --> must be swapping
            if self.state.this_player_id in players_still_to_swap:
                action = "swap"
                message = "You can choose to swap cards,"
            else:
                action = "wait"
                message = "You've swapped - but others are still swapping. Wait for them..."
            response = {"allowed_action": action,
                        "action_message": message,
                        "allowed_players": players_still_to_swap}
        elif (self.state.this_player_id in self.state.play_order and
              len(self.state.play_order) < 2):
            # you;re the last player
            logger.debug("Only 1 player left, and it's this player")
            response = {"allowed_action": "lost",
                        "action_message": "You lost!"}
            self.state.game_finished = True
        elif len(self.state.play_order) < 2:
            # all done
            logger.debug("only 1 player left, but it's not this playe")
            response = {"allowed_action": "finished",
                        "action_message": f"Game over - player {self.state.play_order} lost"}
            self.state.game_finished = True
        elif self.state.this_player_id in self.state.players_finished:
            # this player finished, others havent
            logger.debug("This player finished, but others haven't")
            response = {"allowed_action": "wait",
                        "action_message": "You've finished - but others are still playing. Please wait.",
                        "allowed_players": players_still_not_finished}
        elif self.state.this_player_id in players_still_not_finished:
            # ok - so we've not finished the game overall
            # this player is still in play too
            # and everyone has swapped
            # so must be in game play
            # check if we're next or have to wait
            logger.debug("this player still not finished")

            is_next_player = self.state.this_player_id == self.state.play_order[0]
            if is_next_player:
                # can we actually play or do we have to pick up?
                logger.debug("this player is the next player")
                card_type, card_stack = self.this_player.which_player_cards_can_player_use()
                can_player_play_a_card = self.__can_play_cards(card_stack)
                if can_player_play_a_card or card_type == Card_Types.CARD_FACE_DOWN:
                    # if we can play from visible cards on top of the played stack,
                    # or if we have only face down cards left
                    # let us play
                    logger.debug("Player can play a move and move type is %s", card_type)
                    action = "play"
                    action_message = "Please play your move"
                else:
                    logger.debug("Player cannot move so must pick up")
                    action = "pick"
                    action_message = "You can't play - you must pick up cards."
                response = {"allowed_action": action,
                            "allowed_cards": Card_Types.Short_Name[card_type],
                            "action_message": action_message,
                            "allowed_players": players_still_not_finished,
                            "is_next_player": is_next_player}
            else:
                # someone else is the next player
                logger.debug("this player is not the next player - deferring calculations")
                response = {"allowed_action": "wait",
                            "allowed_players": players_still_not_finished,
                            "is_next_player": is_next_player,
                            "action_message": "wait for others to finish their moves"}
        else:
            logger.error("Unable to calculate game allowed moves")
            raise ValueError("Unable to calculate game allowed moves")
        return response

    def work_out_who_plays_first(self):
        """ looks at all the players 'hand' cards and finds the one with the lowest rank.
            that player starts the game, the others proceed in numerical order from them.
        """
        lowest_player = None
        lowest_rank = 999
        logger.debug("calculating player with lowest card")
        for player in self.players:
            this_player_lowest_rank = min([card.rank for card in player.hand])
            logger.debug(f"Player {player.ID} has lowest card {this_player_lowest_rank}")
            # if (this_player_lowest_rank < lowest_rank and this_player_lowest_rank not in self.state.all_special_cards):
            if this_player_lowest_rank < lowest_rank:
                logger.debug("this is the lowest card seen so far...")
                lowest_player = player.ID
                lowest_rank = this_player_lowest_rank

        while not self.state.play_order[0] == lowest_player:
            self.rotate_player()

        logger.debug(f"Set player {lowest_player} to start")

    def play_no_swap(self):
        """plays the move 'dont swap, ready to start' at the beginning of the game"""
        logger.debug("play_no_swap -> adding user to players_ready_to_start")
        self.state.players_ready_to_start.append(self.state.this_player_id)
        if self.ready_to_start:
            logger.debug("play_no_swap -> ready_to_start")
            self.work_out_who_plays_first()
        return {'action': 'no_swap', 'action_result': True}

    def play_pick_up(self):
        """picks up the cards from the played stack and puts them in the player's hand"""
        response = {'action': 'pick', 'action_result': False,
                    'action_message': "You are not allowed to pick up cards right now"}
        allowed_actions = self.calculate_player_allowed_actions()
        if (allowed_actions["allowed_action"] == "pick" and
                allowed_actions["is_next_player"]):
            # we're allowed to pick up cards right now
            logger.debug("allowed_actions ok - execute __pick_up_cards")
            response = self.__pick_up_cards()
        else:
            logger.debug("Not allowed to pick up right now")
            response = {'action': 'pick', 'action_result': False,
                        'action_message': "Could not pick up - either not an allowed move, or it's not your turn"}
        return response

    def __pick_up_cards(self):
            # --> not relevant?? card_type, cards  = self.this_player.which_player_cards_can_player_use()
            # when we pick up cards, they always go in our hand from the played pile
        logger.debug("Picking up cards %s", jsonpickle.encode(
            self.cards.pile_played, unpicklable=False))
        self.this_player.add_cards_to_player_cards(self.cards.pile_played, Card_Types.CARD_HAND)
        self.cards.pile_played = []
        self.__update_pile_sizes()
        self.rotate_player()
        return {'action': 'pick', 'action_result': True}

    def play_move(self, cards_to_play):
        """ plays a given move"""
        # check game state
        # 1. is "play" a valid move?
        # 2. is it this player's turn?
        logger.debug("Starting play_move")
        response = {'action': 'play', 'action_result': False,
                    'action_message': "You are not allowed to play right now (waiting for other?)"}
        # play
        allowed_actions = self.calculate_player_allowed_actions()
        logger.debug("allowed_actions: %s", allowed_actions)
        if (allowed_actions["allowed_action"] == "play" and allowed_actions["is_next_player"] == True):
            if cards_to_play:
                logger.debug("play_move -> allowed 'play' -> has cards_to_play")
                allowed_card_type = Card_Types.Card_Type_From_Code.get(
                    allowed_actions["allowed_cards"])

                # validate that these cards are in this user's hand and are all the same type (face down, up, hand)
                response, message, validated_cards, card_type = self.__validate_cards_exist_in_type(cards_to_play, allowed_card_type)
                if not response:
                    logger.debug("Cannot play: %s", message)
                    return {'action': 'play',
                            'action_result': False,
                            'action_message': message}
                elif not self.__are_all_cards_same_rank(validated_cards):
                    # check if all cards are the same rank:
                    logger.debug("Player tried to play multiple cards of different ranks")
                    result = {'action': 'play', 'action_result': False,
                              'action_message': f'If playing more than one card, they must all be the same rank (value).'}
                    return result

                can_play_cards = self.__can_play_cards(validated_cards)

                if can_play_cards:
                    response = self.play_validated_cards(validated_cards, card_type)
                else:
                    if card_type == Card_Types.CARD_FACE_DOWN:
                        # tried to play a face down card but lost
                        # move this card to the player's hand
                        self.this_player.add_cards_to_player_cards(
                            validated_cards, Card_Types.CARD_HAND)
                        # pick up the rest of the played cards
                        self.__pick_up_cards()
                        self.this_player.remove_cards_from_player_cards(validated_cards, card_type)
                        response = {'action': 'play',
                                    'action_result': True,
                                    'action_message': 'You played a face down card but lost'}
                    else:
                        response = {'action': 'play',
                                    'action_result': False,
                                    'action_message': f'Cannot play that move on the current stack'}

            else:
                response = {'action': 'play', 'action_result': False,
                            'action_message': "Select one or more cards to play"}
        self.__update_pile_sizes()
        return response

    def play_validated_cards(self, validated_cards, card_type):
        """plays a set of validated_cards of type card_type for the current player"""
        # great - play teh cards!
        response = {'action': 'play',
                    'action_result': True}
        just_run_out_of_cards = False
        self.cards.pile_played.extend(validated_cards)
        # remove these cards from teh player's hand/hidden/up cards and refill their hand if there are cards left in teh deck
        self.this_player.remove_cards_from_player_cards(validated_cards, card_type)
        logger.debug("Moved cards %s from player's pile %s",
                     jsonpickle.encode(validated_cards, unpicklable=False),
                     card_type)
        if card_type == Card_Types.CARD_HAND:
            # replenish the player's hand from the deck
            # while there are still cards in the pile, and
            # while they have fewer than number_hand_cards
            # cards in their hand
            while (len(self.this_player.hand) < self.state.number_hand_cards and
                    len(self.cards.pile_deck) > 0):
                self.this_player.hand.append(self.cards.pile_deck.pop())

        if (not self.this_player.face_down) and (not self.this_player.face_up) and (not self.this_player.hand):
            # has run out of cards. Game over (for them at least)!
            logger.debug(f"Player {self.state.this_player_id} has run out of cards")
            self.state.players_finished.append(self.state.this_player_id)
            # skip checking or rotatiung player later
            just_run_out_of_cards = True
            # remove this player from play rder
            self.state.play_order.pop(0)
            if len(self.state.play_order) < 2:
                # all players in players_finished
                logger.debug(
                    "This player has finished, and now there are fewer than 2 players left in game - game over!")
                self.state.game_finished = True
                message = "game over!"
            else:
                logger.debug(
                    "Although this player has finished, there are at least 2 other players still active")
                message = "You've finished. Wait for others."
            response = {'action': 'play',
                        'action_result': True,
                        "action_message": message}

        if not just_run_out_of_cards:
            # skip this if we just poped ourselves from play order...
            # # check if last move clears the deck
            if self.__clears_deck(self.cards.pile_played):
                self.cards.pile_burn.extend(self.cards.pile_played)
                self.cards.pile_played = []
            else:
                self.rotate_player()

        return response

    def __validate_cards_exist_in_type(self, cards_to_play, allowed_card_type):
        """validate that a set of card indexes exists within a set of cards
           of a given type belonging to this player. Check also that the cards
           are all of the same rank. If they are, return the validated list of
           cards, otherwise return narative error"""

        response = True
        message = None

        card_types = [card_description[0] for card_description in cards_to_play]
        card_type = Card_Types.Card_Type_From_Code.get(card_types[0])
 
        card_indexes = [int(card_description[2:]) for card_description in cards_to_play]

        if not card_type:
            response = False
            message = f"Unknown card type '{card_type}'."

        elif card_types.count(card_types[0]) != len(card_types):
            # TODO change this to use sets to compare
            logger.debug("card_types.count(card_types[0]) != len(card_types): %s",
                         card_types.count(card_types[0]) != len(card_types))
            response = False
            message = 'You can only play cards of the same type (hand, face up, face down) in a single move.'

        elif card_type != allowed_card_type:
            response = False
            message = 'You cannot play that card type at this time.'

        elif (card_type == Card_Types.CARD_FACE_DOWN and len(card_types) != 1):
                # can only play one face down card at a time
            response = False,
            message = f'You can only play one face down card at a time'

        elif self.__check_card_index_over_deck_length(max(card_indexes), card_type):
            response = False,
            message = f'Attempted to play card which is above face card count in __validate_cards_exist_in_type.'

        if response:
            cards_being_played_from = self.this_player.get_cards(card_type)
            # validated_cards contains a list of Card objects which have been demonstated
            # to be the same rank and that actually exist in a given set of cards that a player has
            # (e.g. face down, face up, or hand).
            validated_cards = list(
                cards_being_played_from[card_location] for card_location in card_indexes)
        else:
            validated_cards = None
        return response, message, validated_cards, card_type

    def __clears_deck(self, played_pile):
        all_match = False
        if len(played_pile) > 3:
            pile_played = played_pile[-4:]
            logger.debug("card1 %s, card2 %s, card3 %s, card4 %s", 
                        pile_played[0], 
                        pile_played[1],
                        pile_played[2],
                        pile_played[3])
            all_match = (pile_played[0].rank == pile_played[1].rank) and (
                pile_played[1].rank == pile_played[2].rank) and (pile_played[2].rank == pile_played[3].rank)
        logger.debug("self.cards.pile_played[0].rank: %s, self.state.burn_card, %s",
                     self.cards.pile_played[0].rank,
                     self.state.burn_card)
        return ((self.cards.pile_played[-1].rank == self.state.burn_card) or
                all_match)

    def __are_all_cards_same_rank(self, cards):
        """checks whether all the cards in a given set are all of the same value"""
        # now check they're all the same
        last_card = None
        for card in cards:
            if last_card and not card.rank == last_card.rank:
                return False
            last_card = card
        return True

    def __can_play_cards(self, cards_to_check):
        """checks whether the card/cards can be played e.g. does
           the user have ANY cards in the set cards_to_check which can be played
           on the current played stack, or can the cards in the user's play
           list be played on teh current played stack"""
        logger.debug("__can_play_cards -> cards to check: %s",
                     jsonpickle.encode(cards_to_check, unpicklable=False))

        if not self.cards.pile_played:
            return True
        else:
            last_played_card = self.cards.pile_played[-1]
            if last_played_card.rank == self.state.transparent_card:
                return self.__can_play_cards(self.cards.pile_played[:-1])
            else:
                for card in cards_to_check:
                    if (card.rank in self.state.play_on_anything_cards) or \
                         (last_played_card.rank == self.state.less_than_card and card.rank <= last_played_card.rank) or \
                         (card.rank >= last_played_card.rank):
                        return True
            return False

    def __check_card_index_over_deck_length(self, card_index, card_type):
        """checks that the card at a given index actually exists in the given hand"""

        if card_type == Card_Types.CARD_FACE_UP:
            deck = self.this_player.face_up
        elif card_type == Card_Types.CARD_FACE_DOWN:
            deck = self.this_player.face_down
        elif card_type == Card_Types.CARD_HAND:
            deck = self.this_player.hand
        else:
            raise ValueError(
                f'unknown card type {card_type} in __check_card_index_over_deck_length.')

        return card_index > (len(deck) - 1)

    def swap_cards(self, cards_to_swap, player):
        """swaps cards in hand with cards in face up"""
        # check game state - has this user already committed cards?
        # if not, then just swap the cards
        response = None

        allowed_actions = self.calculate_player_allowed_actions()
        if (allowed_actions["allowed_action"] == "swap" and
                player.ID in allowed_actions["allowed_players"]):

            logger.debug("ready to swap")
            hand_cards = []
            face_cards = []

            for card in cards_to_swap:
                card_index = int(card[2:])
                logger.debug("swapping for index %s", card_index)
                card_type = Card_Types.Card_Type_From_Code.get(card[0])
                if not card_type:
                    response = {'action': 'swap',
                                'action_result': False,
                                'action_message': f"Unrecognised card type '{card[0]}'"}
                    return response

                if self.__check_card_index_over_deck_length(card_index, card_type):
                    response = {
                        'action': 'swap',
                        'action_result': False,
                        'action_message': f"Attempted to play card number {card_index} in set {Card_Types.Long_Name[card_type]} which is over set length"}
                    return response

                if card_type == Card_Types.CARD_FACE_UP:
                    face_cards.append(card_index)

                elif card_type == Card_Types.CARD_HAND:
                    hand_cards.append(card_index)
                else:
                    response = {'action': 'swap',
                                'action_result': False,
                                'action_message': 'You can only swap hand and face up cards.'}
                    return response

            if len(hand_cards) != len(face_cards):
                response = {'action': 'swap', 'action_result': False,
                            'action_message': 'You must select the same number of cards from your hand and face up sets.'}
            elif len(hand_cards) <= 0:
                response = {'action': 'swap', 'action_result': False,
                            'action_message': 'Select the face up and hand cards you want to swap.'}
            else:
                for i in range(len(hand_cards)):
                    player.hand[hand_cards[i]], player.face_up[face_cards[i]
                                                               ] = player.face_up[face_cards[i]], player.hand[hand_cards[i]]
                response = {'action': 'swap', 'action_result': True}

        else:
            response = {'action': 'swap', 'action_result': False,
                        'action_message': 'You can\'t swap cards right now'}
        logger.debug("swap response: %s", jsonpickle.dumps(response, unpicklable=False))
        return response

    def __load_cards_from_database(self, deck_type, game_id, session):
        """load a set of cards and return them in a sorted list"""
        c = common_db.Common_DB()
        logger.debug(f"deck_type {deck_type}, game_id {game_id}")
        cards = c.execute(session,
                          "SELECT card_suit, card_rank FROM game_cards WHERE game_id = :game_id AND card_location = :deck_type",
                          game_id=game_id, deck_type=deck_type)
        cards_to_return = []
        if len(cards) > 0:
            logger.debug(f"found {len(cards)} cards")
            cards_to_return.extend([Card(card["card_suit"], card["card_rank"]) for card in cards])
        return cards_to_return


def get_users_for_game(game_id, session):
    """load the list of users playing a game"""
    c = common_db.Common_DB()
    players = c.execute(session, "SELECT player_id FROM player_game WHERE game_id = :game_id",
                        game_id=game_id)
    list_of_players = []
    if len(players) > 0:
        list_of_players.extend([player["player_id"] for player in players])
    return list_of_players


def get_list_of_games_looking_for_players(player_id):
    """find all the games that this player is waiting to start"""
    sql = "SELECT games.gameid, player_counts.number_of_players, games.game_ready_to_start, games.game_finished, games.players_requested FROM games LEFT JOIN (SELECT player_game.game_id as game_id, count(player_game.player_id) as number_of_players FROM player_game group by player_game.game_id) as player_counts ON games.gameid = player_counts.game_id LEFT JOIN (select game_id from player_game where player_id = :player_id) AS games_to_exclude on games_to_exclude.game_id = games.gameid where games_to_exclude.game_id IS NULL"
    c = common_db.Common_DB()
    games = c.execute(c.common_engine,
                      sql, player_id=player_id)
    return games


def get_list_of_games_for_this_user(player_id, include_game_ready=False, include_finished=False):
    """find all the games that this player is waiting to start"""

    sql = "SELECT games.gameid, player_counts.number_of_players, games.game_ready_to_start, (games.players_requested = player_counts.number_of_players)  as has_enough_players, games.game_finished, games.players_requested, games.play_order FROM games join (select player_game.game_id from player_game where player_game.player_id = :player_id) as games_for_this_player on games.gameid = games_for_this_player.game_id LEFT JOIN (SELECT player_game.game_id as game_id, count(player_game.player_id) as number_of_players FROM player_game group by player_game.game_id) as player_counts ON games.gameid = player_counts.game_id WHERE games.game_finished = :include_finished ORDER BY games.gameid ASC"

    '''
    conditionals = []
    if include_only_unready:
        conditionals.append("games.players_requested > player_counts.number_of_players")
    conditionals.append(f"games.game_finished = {include_finished}")

    if conditionals:
        sql = " WHERE ".join([sql, " AND ".join(conditionals)])
    '''
    c = common_db.Common_DB()
    games = c.execute(c.common_engine,
                      sql,
                      player_id=player_id,
                      include_finished=include_finished)
    return games
