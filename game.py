import json
from random import shuffle
from zlib import crc32
from typing import List

import jsonpickle
from sqlalchemy.orm import sessionmaker

from cards import Card, Card_Types, Deck
from player import Player


class Game(object):
    PILE_BURN = 1
    PILE_PICK = 2
    PILE_PLAYED = 3
    PILE_DECK = 4

    Pile_Objects = {
        PILE_DECK: "self.cards.deck",
        PILE_PICK: "self.cards.pick_stack",
        PILE_PLAYED: "self.cards.played_cards",
        PILE_BURN: "self.cards.burn_pile"
    }

    Pile_Counts = {
        PILE_DECK: "self.state.pile_deck_size",
        PILE_PICK: "self.state.pile_pick_size",
        PILE_PLAYED: "self.cards.pile_played_size",
        PILE_BURN: "self.cards.pile_burn_size"
    }

    game_properties = {
        "special_cards": [
            {
                "code": "less",
                "display": "Less than card",
                "value": '7',
                "play_on_anything": False
            },
            {
                "code": "transparent",
                "display": "Transparent card",
                "value": 'None',
                "play_on_anything": True
            },
            {
                "code": "burn",
                "display": "Burn card",
                "value": '10',
                "play_on_anything": True
            },
            {
                "code": "reset",
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
        self.state = self.State(number_of_players)
        self.cards = self.Cards()
        self.state.this_player_id = this_player_id
        self.players = []
        if this_player_id:
            self.players.append(Player(this_player_id))

    def add_players_to_game(self, player_id, database_connection):
        """Checks if there's enough space left in this game, and
           that this player is not already in the list,
           adds the selected player ID"""

        if (not self.ready_to_start and
                len(list(set(player.ID for player in self.players) - set([player_id]))) == len(self.players)):

            player_to_add = Player(player_id)

            self.players.append(player_to_add)
            self.state.number_of_players_joined = len(self.players)
            self.state.play_order = [player.ID for player in self.players]
            self.save(database_connection)

            return True
        else:
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

    def parse_requested_config(self, requested_config):
        """parses a serialised configuraiton sent by the new game
           request and assigns the values to the game state object.
           Returns true or false depending on whether the process was successful"""
        less_on_anything, transparent_on_anything, burn_on_anything, reset_on_anything = False, False, False, False
        list_of_special_cards = []

        for config_item in requested_config:
            try:
                name = config_item["name"]
            except (KeyError, IndexError):
                message = "Unable to read 'name' key in config_item"
                return False, message
            except:
                raise
            try:
                value = config_item["value"]
            except (KeyError, IndexError):
                message = "Unable to read 'value' key in config_item"
                return False, message
            except:
                raise

            if name == "less-value":
                self.state.less_than_card = self.__parse_int_from_json(value)
            if name == "less-on-anything":
                less_on_anything = True
            if name == "transparent-value":
                self.state.transparent_card = self.__parse_int_from_json(value)
            if name == "transparent-on-anything":
                transparent_on_anything = True
            if name == "burn-value":
                self.state.burn_card = self.__parse_int_from_json(value)
            if name == "burn-on-anything":
                burn_on_anything = True
            if name == "reset-value":
                self.state.reset_card = self.__parse_int_from_json(value)
            if name == "reset-on-anything":
                reset_on_anything = True
            if name == "number-face-down":
                self.number_face_down_cards = self.__parse_int_from_json(
                    value, 3, 9)
            if name == "number-hand":
                self.state.number_hand_cards = self.__parse_int_from_json(
                    value, 3, 9)
            if name == "number-of-decks":
                self.state.number_of_decks = self.__parse_int_from_json(
                    value, 1, 2)
            if name == "number-of-players":
                self.state.number_of_players_requested = self.__parse_int_from_json(
                    value, 2, 6)

        if self.state.less_than_card > 0:
            list_of_special_cards.append(self.state.less_than_card)
        if self.state.transparent_card > 0:
            list_of_special_cards.append(self.state.transparent_card)
        if self.state.burn_card > 0:
            list_of_special_cards.append(self.state.burn_card)
        if self.state.reset_card > 0:
            list_of_special_cards.append(self.state.reset_card)

        # now parse the "play on anything" cards
        self.state.play_on_anything_cards = []
        if less_on_anything and self.state.less_than_card > 0:
            self.state.play_on_anything_cards.append(self.state.less_than_card)
        if transparent_on_anything and self.state.transparent_card > 0:
            self.state.play_on_anything_cards.append(
                self.state.transparent_card)
        if burn_on_anything and self.state.burn_card > 0:
            self.state.play_on_anything_cards.append(self.state.burn_card)
        if reset_on_anything and self.state.reset_card > 0:
            self.state.play_on_anything_cards.append(self.state.reset_card)

        no_duplicates = len(list_of_special_cards) == len(
            set(list_of_special_cards))
        if no_duplicates:
            message = "parsed successfully"
        else:
            message = "duplicate special play cards"
        return no_duplicates, message

    def __are_there_enough_players_to_start(self):
        """have enough players joined this game yet?"""
        self.state.number_of_players_joined = len(self.players)
        return self.state.number_of_players_requested == self.state.number_of_players_joined

    ready_to_start = property(fget=__are_there_enough_players_to_start)

    class State(object):
        """holds the current state of this game, excluding player hands and config"""

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
            self.all_special_cards = []

            # game state
            self.current_turn_number = 0
            self.last_player = None
            self.play_list = []
            self.pile_burn_size = 0
            self.pile_pick_size = 0
            self.pile_played_size = 0
            self.pile_deck_size = 0

        def get_all_special_cards(self):
            """returns all special cards"""
            cards = []
            cards.append(self.transparent_card)
            cards.append(self.less_than_card)
            cards.append(self.burn_card)
            cards.append(self.reset_card)

            while 0 in cards:
                cards.remove(0)

            return set(cards)

    class Cards(object):
        """stores cards separately from state to keep secret from client"""

        def __init__(self):
            # piles
            self.pile_burn = []
            self.pile_pick = []
            self.pile_played = []
            self.pile_deck = []

    def get_database_checksum(self, database_connection):
        """loads the 'checksum' field from teh database for the current game and returns it"""
        config = database_connection.execute('SELECT game_checksum FROM games WHERE gameid = :game_id',
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
        new_deck = Deck()

        # cards are shuffled and so it doesnt really matter that we dont
        # follow convention and deal each player's
        # face down, then face up, then hand cards
        for _ in range(self.state.number_face_down_cards):
            for player in self.players:
                player.face_down.append(new_deck.deal())
                player.face_up.append(new_deck.deal())
                player.hand.append(new_deck.deal())

        self.cards.pile_deck = new_deck.cards
        self.__update_pile_sizes()
        self.state.deal_done = True

    def save(self, database_connection):
        """saves the current state of the game, using a transaction to ensure
           that we can roll back if not successful. If this is a new game
           without an ID, it creates one, otherwise it updates the existing one"""
        print("beginning game save")

        Session = sessionmaker(bind=database_connection.engine)
        trans_connection = Session()

        print("started transaction")
        if not self.state.game_id:
            querystring = "INSERT INTO games (game_finished, players_requested, game_ready_to_start, game_checksum, players_finished, play_on_anything_cards, play_order, less_than_card, transparent_card, burn_card, reset_card, number_of_decks, number_face_down_cards, number_hand_cards, current_turn_number, players_ready_to_start, deal_done, gameid) VALUES (:game_finished, :number_of_players_requested, :game_ready_to_start, :game_checksum, :players_finished, :play_on_anything_cards,:play_order,:less_than_card,:transparent_card,:burn_card,:reset_card,:number_of_decks,:number_face_down_cards,:number_hand_cards,:current_turn_number,:players_ready_to_start, :deal_done, :game_id)"

        else:
            querystring = "UPDATE games SET game_finished = :game_finished, players_requested = :number_of_players_requested, game_ready_to_start = :game_ready_to_start, game_checksum = :game_checksum, players_finished = :players_finished, play_on_anything_cards = :play_on_anything_cards, play_order = :play_order, less_than_card = :less_than_card, transparent_card = :transparent_card, burn_card = :burn_card, reset_card = :reset_card, number_of_decks = :number_of_decks, number_face_down_cards = :number_face_down_cards ,number_hand_cards = :number_hand_cards,current_turn_number = :current_turn_number, players_ready_to_start = :players_ready_to_start, deal_done = :deal_done WHERE gameid = :game_id"

        print(f"calling database.execute for {querystring}")
        result = database_connection.execute(querystring,
                                             trans_connection=trans_connection,
                                             game_finished=self.state.game_finished,
                                             number_of_players_requested=self.state.number_of_players_requested,
                                             game_ready_to_start=self.ready_to_start,
                                             game_checksum=self.checksum(),
                                             players_finished=json.dumps(
                                                 self.state.players_finished),
                                             play_on_anything_cards=json.dumps(
                                                 self.state.play_on_anything_cards),
                                             play_order=json.dumps(
                                                 self.state.play_order),
                                             less_than_card=self.state.less_than_card,
                                             transparent_card=self.state.transparent_card,
                                             burn_card=self.state.burn_card,
                                             reset_card=self.state.reset_card,
                                             number_of_decks=self.state.number_of_decks,
                                             number_face_down_cards=self.state.number_face_down_cards,
                                             number_hand_cards=self.state.number_hand_cards,
                                             current_turn_number=self.state.current_turn_number,
                                             players_ready_to_start=json.dumps(
                                                 self.state.players_ready_to_start),
                                             deal_done=self.state.deal_done,
                                             game_id=self.state.game_id)

        print("returned from trans_connection.execute")
        if not result:
            print("no result in trans_connection.execute - rolling back")
            trans_connection.rollback()
            trans_connection.close()
            return None

        if not(self.state.game_id):
            self.state.game_id = int(result)

        if not self.__persist_cards_to_database(deck=self.cards.pile_deck,
                                                deck_type=str(Game.PILE_DECK),
                                                game_id=str(
                                                    self.state.game_id),
                                                database_connection=database_connection,
                                                trans_connection=trans_connection):
            trans_connection.rollback()
            trans_connection.close()
            raise ValueError('error persisting Game.PILE_DECK to database')
        if not self.__persist_cards_to_database(deck=self.cards.pile_burn,
                                                deck_type=str(Game.PILE_BURN),
                                                game_id=str(
                                                    self.state.game_id),
                                                database_connection=database_connection,
                                                trans_connection=trans_connection):
            trans_connection.rollback()
            trans_connection.close()
            raise ValueError('error persisting Game.PILE_BURN to database')
        if not self.__persist_cards_to_database(deck=self.cards.pile_played,
                                                deck_type=Game.PILE_PLAYED,
                                                game_id=self.state.game_id,
                                                database_connection=database_connection,
                                                trans_connection=trans_connection):
            trans_connection.rollback()
            trans_connection.close()
            raise ValueError('error persisting Game.PILE_PLAYED to database')
        if not self.__persist_cards_to_database(deck=self.cards.pile_pick,
                                                deck_type=str(Game.PILE_PICK),
                                                game_id=str(
                                                    self.state.game_id),
                                                database_connection=database_connection,
                                                trans_connection=trans_connection):
            trans_connection.rollback()
            trans_connection.close()
            raise ValueError('error persisting Game.PILE_PICK to database')

        for player in self.players:
            print("saving player:", jsonpickle.dumps(player, unpicklable=True))
            player.save(database_connection, self.state.game_id,
                        trans_connection=trans_connection)
            # store a reference to this player's object on the game itself
            if player.ID == self.state.this_player_id:
                self.this_player = player

        trans_connection.commit()
        trans_connection.close()
        # return the game_id for future use
        return self.state.game_id

    def rotate_player(self):
        """rotates the play list once a player has played"""
        last_player = self.state.play_order.pop(0)
        self.state.last_player = last_player
        self.state.play_order.append(last_player)

    def load(self, database_connection):
        """loads the configuration of the game defined by state.game_id"""
        if not self.state.game_id:
            raise ValueError('tried to load game without setting game_id.')
        if not len(self.players) > 0:
            raise ValueError('tried to load game without setting player IDs.')
        if not self.state.this_player_id:
            raise ValueError(
                'tried to load game without setting ID of current player or it doesnt exist in current instantiation.')

        # load game config
        # fields not retrieved: `last_move_at`, `gameid`,`checksum`,`game_ready_to_start`
        config = database_connection.execute("SELECT game_finished, players_requested, players_finished, play_on_anything_cards, play_order, less_than_card,transparent_card,burn_card,reset_card,number_of_decks,number_face_down_cards,number_hand_cards,current_turn_number,last_player, players_ready_to_start, deal_done FROM games WHERE gameid = :game_id",
                                             game_id=self.state.game_id)
        print("config", jsonpickle.dumps(config, unpicklable=False))
        config = config[0]
        print("config", jsonpickle.dumps(config, unpicklable=False))
        self.state.game_finished = int(config["game_finished"])
        self.state.number_of_players_requested = int(
            config["players_requested"])
        self.state.players_finished = json.loads(config["players_finished"])
        self.state.play_on_anything_cards = json.loads(
            config["play_on_anything_cards"])
        self.state.play_order = json.loads(config["play_order"])
        self.state.less_than_card = int(config["less_than_card"])
        self.state.transparent_card = int(config["transparent_card"])
        self.state.burn_card = int(config["burn_card"])
        self.state.reset_card = int(config["reset_card"])
        self.state.number_of_decks = int(config["number_of_decks"])
        self.state.number_face_down_cards = int(
            config["number_face_down_cards"])
        self.state.number_hand_cards = int(config["number_hand_cards"])
        self.state.current_turn_number = int(config["current_turn_number"])
        self.state.players_ready_to_start = json.loads(
            config["players_ready_to_start"])
        self.state.deal_done = int(config["deal_done"])

        # load decks
        self.cards.pile_deck = self.__load_cards_from_database(
            Game.PILE_DECK, self.state.game_id, database_connection)
        self.cards.pile_burn = self.__load_cards_from_database(
            Game.PILE_BURN, self.state.game_id, database_connection)
        self.cards.pile_played = self.__load_cards_from_database(
            Game.PILE_PLAYED, self.state.game_id, database_connection)
        self.cards.pile_pick = self.__load_cards_from_database(
            Game.PILE_PICK, self.state.game_id, database_connection)
        self.__update_pile_sizes()

        for player in self.players:
            player.load(database_connection, self.state.game_id)
            # store a reference to this player's object on the game itself
            if player.ID == self.state.this_player_id:
                self.this_player = player

    def __update_pile_sizes(self):
        """updates the summary count of each pile size, and copies the played pile to the active state"""
        self.state.pile_pick_size = len(self.cards.pile_pick)
        self.state.pile_played_size = len(self.cards.pile_played)
        self.state.pile_burn_size = len(self.cards.pile_burn)
        self.state.pile_deck_size = len(self.cards.pile_deck)
        self.state.play_list = self.cards.pile_played

    def calculate_player_allowed_actions(self):
        """calculates what action, if any, the current player is allowed to perform

            returns:
            always:
                "allowed_action": finished | lost | wait | swap | play,
                "action-message": to display to the end user

            depending on state:
                "allowed_cards": Card_Types.Short_Name,
                "allowed_players": a list of players allowed to play,
                "is_next_player": boolean,
        """
        response = {"allowed_action": "unknown", "allowed_players": "unknown"}
        all_player_id = set([player.ID for player in self.players])
        players_still_to_swap = (list(all_player_id - set(self.state.players_ready_to_start)))
        players_still_not_finished = (list(all_player_id - set(self.state.players_finished)))
        print("set(self.state.players_ready_to_start)", set(self.state.players_ready_to_start),"set(self.state.players_finished)",set(self.state.players_finished), "all_player_id", all_player_id, "players_still_to_swap", players_still_to_swap, "players_still_not_finished", players_still_not_finished)
        if len(players_still_to_swap) > 0:
            # still some players not yet ready to start --> must be swapping
            if self.state.this_player_id in players_still_to_swap:
                action = "swap"
                message = "You can choose to swap cards,"
            else:
                action = "wait"
                message = "You've swapped - but others are still swapping. Wait for them..."
            response = {"allowed_action": action,
                        "action-message": message,
                        "allowed_players": players_still_to_swap}
        elif len(players_still_not_finished) == 0:
            # all done
            response = {"allowed_action": "finished",
                        "action-message": "Game over"}
            self.state.game_finished = True
        elif (self.this_player.ID in players_still_not_finished and 
              len(players_still_not_finished) == 1):
            # you;re the last player
            response = {"allowed_action": "lost",
                        "action-message": "You lost!"}
        elif self.this_player.ID in self.state.players_finished :
            # this player finished, others havent
            response = {"allowed_action": "wait",
                        "action-message": "You've finished - but others are still playing. Please wait.",
                        "allowed_players": players_still_not_finished}
        elif self.this_player.ID in players_still_not_finished:
            # ok - so we've not finished the game overall
            # this player is still in play too
            # and everyone has swapped
            # so must be in game play
            # check if we're next or have to wait
            
            is_next_player = self.this_player.ID == self.state.play_order[0]
            if is_next_player:
                # can we actually play or do we have to pick up?
                card_type, card_stack = self.this_player.which_player_cards_can_player_use()
                can_player_play_a_card = self.__can_play_cards(card_stack)
                if can_player_play_a_card or card_type == Card_Types.CARD_FACE_DOWN:
                    # if we can play from visible cards on top of the played stack,
                    # or if we have only face down cards left
                    # let us play
                    action = "play"
                    action_message = "Please play your move"
                else:
                    action = "pick"
                    action_message = "You can't play - you must pick up cards."
                response = {"allowed_action": action,
                            "allowed_cards": Card_Types.Short_Name[card_type],
                            "action-message": action_message,
                            "allowed_players": players_still_not_finished,
                            "is_next_player": is_next_player}
            else:
                # someone else is the next player
                response = {"allowed_action": "wait",
                            "allowed_players": players_still_not_finished,
                            "is_next_player": is_next_player,
                            "action-message": "wait for others to finish their moves"}
        else:
            raise ValueError("Unable to calculate game allowed moves")
        return response

    def add_to_pile(self, deck_type, cards_to_add=[], *args):
        """add card to pile and update size"""
        if not cards_to_add:
            raise ValueError('tried to add a card to pile without a card.')

        if deck_type == Game.PILE_BURN:
            self.cards.pile_burn.extend(cards_to_add)
        elif deck_type == Game.PILE_PICK:
            self.cards.pile_pick.extend(cards_to_add)
        elif deck_type == Game.PILE_PLAYED:
            self.cards.pile_played.extend(cards_to_add)
        elif deck_type == Game.PILE_DECK:
            self.cards.pile_deck.extend(cards_to_add)
        else:
            raise ValueError(f'cant find pile for {deck_type}.')
        self.__update_pile_sizes()
        return

    def work_out_who_plays_first(self):
        """ looks at all the players 'hand' cards and finds the one with the lowest rank.
            that player starts the game, the others proceed in numerical order from them.
        """
        lowest_player = None
        lowest_rank = 999

        for player in self.players:
            this_player_lowest_rank = min([card.rank for card in player.hand])
            if (this_player_lowest_rank < lowest_rank and
                this_player_lowest_rank not in self.state.get_all_special_cards()):
                lowest_player = player.ID
                lowest_rank = this_player_lowest_rank

        while not self.state.play_order[0] == lowest_player:
            self.rotate_player()

    def play_no_swap(self):
        """plays the move 'dont swap, ready to start' at the beginning of the game"""
        self.state.players_ready_to_start.append(self.state.this_player_id)
        if len(self.state.players_ready_to_start) == len(self.players):
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
            response = self.__pick_up_cards()
        else:
            response = {'action': 'pick', 'action_result': False,
                        'action_message': "Could not pick up - either not an allowed move, or it's not your turn"}
        return response

    def __pick_up_cards(self):
            # --> not relevant?? card_type, cards  = self.this_player.which_player_cards_can_player_use()
            # when we pick up cards, they always go in our hand from the played pile
        self.this_player.add_cards_to_player_cards(
            self.cards.pile_played, Card_Types.CARD_HAND)
        self.cards.pile_played = []
        self.__update_pile_sizes()
        self.rotate_player()
        return {'action': 'pick', 'action_result': True}

    def play_move(self, cards_to_play):
        """ plays a given move"""
        # check game state
        # 1. is "play" a valid move?
        # 2. is it this player's turn?

        response = {'action': 'play', 'action_result': False,
                    'action_message': "You are not allowed to play right now (waiting for other?)"}
        # play
        allowed_actions = self.calculate_player_allowed_actions()
        print("allowed_actions", allowed_actions)
        if (allowed_actions["allowed_action"] == "play" and
                allowed_actions["is_next_player"] == True):
            if cards_to_play:
                allowed_actions = self.calculate_player_allowed_actions()
                allowed_card_type = Card_Types.Card_Type_From_Code.get(
                    allowed_actions["allowed_cards"])
                # validate that these cards are in this user's hand and are all the same type (face down, up, hand)
                response, validated_cards, card_type = self.__validate_cards_exist_in_type(
                    cards_to_play, allowed_card_type)

                if response:
                    return response
                elif not self.__are_all_cards_same_rank(validated_cards):
                    # check if all cards are the same rank:
                    result = {'action': 'play', 'action_result': False,
                              'action_message': f'If playing more than one card, they must all be the same rank (value).'}
                    return result

                can_play_cards = self.__can_play_cards(validated_cards)

                if can_play_cards:
                    response = self.play_validated_cards(
                        validated_cards, card_type)
                else:
                    if card_type == Card_Types.CARD_FACE_DOWN:
                        # tried to play a face down card but lost
                        # move this card to the player's hand
                        self.this_player.add_cards_to_player_cards(
                            validated_cards, Card_Types.CARD_HAND)
                        # pick up the rest of the played cards
                        self.__pick_up_cards()
                        self.this_player.remove_cards_from_player_cards(
                            validated_cards, card_type)
                        response = {'action': 'play',
                                    'action_result': True,
                                    'action_message': 'You played a face down card but lost'}
                    else:
                        response = {'action': 'play',
                                    'action_result': False,
                                    'action_message': f'Cannot play that move on the current stack'}

                    # return response
                # response = {'action':'play', 'action_result':True}
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
        self.cards.pile_played.extend(validated_cards)
        # remove these cards from teh player's hand/hidden/up cards and refill their hand if there are cards left in teh deck
        self.this_player.remove_cards_from_player_cards(
            validated_cards, card_type)
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
            print("have run out of cards")
            self.state.players_finished.append(self.this_player.ID)
            if (len(self.players) - len(self.state.players_finished)) < 2:
                # all players in players_finished
                self.state.game_finished = True
                message = "game over!"
            else:
                message = "You've finished. Wait for others."
            response = {'action': 'play',
                        'action_result': True,
                        "action_message": message}

        # check if last move clears the deck
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

        response = None

        card_types = [card_description[0]
                      for card_description in cards_to_play]
        card_type = Card_Types.Card_Type_From_Code.get(card_types[0])

        card_indexes = [int(card_description[2:])
                        for card_description in cards_to_play]

        if not card_type:
            response = {'action': 'play',
                        'action_result': False,
                        'action_message': f"Unknown card type '{card_type}'."}

        elif card_types.count(card_types[0]) != len(card_types):
            print("card_types.count(card_types[0]) != len(card_types)", card_types.count(
                card_types[0]) != len(card_types))
            response = {'action': 'play',
                        'action_result': False,
                        'action_message': 'You can only play cards of the same type (hand, face up, face down) in a single move.'}

        elif card_type != allowed_card_type:
            response = {'action': 'play',
                        'action_result': False,
                        'action_message': 'You cannot play that card type at this time.'}

        elif (card_type == Card_Types.CARD_FACE_DOWN and
              len(card_types) != 1):
                # can only play one face down card at a time
            response = {'action': 'play', 'action_result': False,
                        'action_message': f'You can only play one face down card at a time'}

        elif self.__check_card_index_over_deck_length(
                max(card_indexes), card_type):
            response = {'action': 'play', 'action_result': False,
                        'action_message': f'Attempted to play card which is above face card count in __validate_cards_exist_in_type.'}

        if not response:
            cards_being_played_from = self.this_player.get_cards(card_type)
            # validated_cards contains a list of Card objects which have been demonstated
            # to be the same rank and that actually exist in a given set of cards that a player has
            # (e.g. face down, face up, or hand).
            response = None
            validated_cards = list(
                cards_being_played_from[card_location] for card_location in card_indexes)
        else:
            validated_cards = None
        return response, validated_cards, card_type

    def __clears_deck(self, played_pile):
        all_match = False
        if len(played_pile) > 3:
            pile_played = played_pile[-4:]
            print("card1", pile_played[0], "card2", pile_played[1],
                  "card3", pile_played[2], "card4", pile_played[3])
            all_match = (pile_played[0].rank == pile_played[1].rank) and (
                pile_played[1].rank == pile_played[2].rank) and (pile_played[2].rank == pile_played[3].rank)
        print("self.cards.pile_played[0].rank", self.cards.pile_played[0].rank,
              "self.state.burn_card", self.state.burn_card)
        return ((self.cards.pile_played[-1].rank == self.state.burn_card) or
                all_match)

    def __are_all_cards_same_rank(self, cards):
        """checks whether all the cards in a given set are all of the same value"""
        # now check they're all the same
        last_card = None
        for card in cards:
            if last_card:
                if not card.rank == last_card.rank:
                    return False
            last_card = card
        return True

    def __can_play_cards(self, cards_to_check):
        """checks whether the card/cards can be played e.g. does
           the user have ANY cards in the set cards_to_check which can be played
           on the current played stack, or can the cards in the user's play
           list be played on teh current played stack"""
        print("cards", jsonpickle.dumps(cards_to_check))

        if not self.cards.pile_played:
            return True
        else:
            last_played_card = self.cards.pile_played[-1]
            if last_played_card.rank == self.state.transparent_card:
                return self.__can_play_cards(self.cards.pile_played[:-1])
            else:
                for card in cards_to_check:
                    if card.rank in self.state.play_on_anything_cards:
                        return True
                    elif last_played_card.rank == self.state.less_than_card:
                        if card.rank <= last_played_card.rank:
                            return True
                    elif card.rank >= last_played_card.rank:
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

            print("ready to swap")
            hand_cards = []
            face_cards = []

            for card in cards_to_swap:
                card_index = int(card[2:])
                print("swapping for index", card_index)
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
        print("swap response", jsonpickle.dumps(response, unpicklable=False))
        return response

    def __load_cards_from_database(self, deck_type, game_id, database_connection):
        """load a set of cards and return them in a sorted list"""
        cards = database_connection.execute("SELECT card_suit, card_rank FROM game_cards WHERE game_id = :game_id AND card_location = :deck_type ORDER BY card_sequence ASC",
                                            game_id=game_id, deck_type=deck_type)
        cards_to_return = []
        if len(cards) > 0:
            cards_to_return.extend(
                [Card(card["card_suit"], card["card_rank"]) for card in cards])
        return cards_to_return

    def __persist_cards_to_database(self, deck=[], *args, deck_type, game_id, database_connection, trans_connection=None):
        """persist a set of cards to the database as part of game state"""
        # first, clear all cards of this type for this game
        result = database_connection.execute("DELETE FROM game_cards WHERE card_location=:card_type AND game_id = :game_id;",
                                             trans_connection=trans_connection,
                                             card_type=int(deck_type),
                                             game_id=int(game_id))
        cards = []
        i = 0
        for card in deck:
            cards.append(
                f"({game_id}, {deck_type}, {card.suit}, {card.rank}, {i})")
            i += 1
        if cards:
            cards = ", ".join(cards)
            result = database_connection.execute(
                "INSERT INTO game_cards (game_id, card_location, card_suit, card_rank, card_sequence) VALUES " + cards + ";", trans_connection=trans_connection)
            if not result:
                print("result", result)
                return False
        print("finsihed - return true")
        return True


def get_users_for_game(game_id, database_connection):
    """load the list of users playing a game"""
    players = database_connection.execute("SELECT player_id FROM player_game WHERE game_id = :game_id",
                                          game_id=game_id)
    list_of_players = []
    if len(players) > 0:
        list_of_players.extend([player["player_id"] for player in players])
    return list_of_players


def get_list_of_games_looking_for_players(player_id, database_connection):
    """find all the games that this player is waiting to start"""
    sql = "SELECT games.gameid, player_counts.number_of_players, games.game_ready_to_start, games.game_finished, games.players_requested FROM games LEFT JOIN (SELECT player_game.game_id as game_id, count(player_game.player_id) as number_of_players FROM player_game group by player_game.game_id) as player_counts ON games.gameid = player_counts.game_id LEFT JOIN (select game_id from player_game where player_id = :player_id) AS games_to_exclude on games_to_exclude.game_id = games.gameid where games_to_exclude.game_id IS NULL"
    games = database_connection.execute(
        sql, player_id=player_id)
    return games


def get_list_of_games_for_this_user(player_id, database_connection, include_only_unready=False, include_finished=True):
    """find all the games that this player is waiting to start"""

    sql = "SELECT games.gameid, player_counts.number_of_players, games.game_ready_to_start, games.game_finished, games.players_requested FROM games join (select player_game.game_id from player_game where player_game.player_id = :player_id) as games_for_this_player on games.gameid = games_for_this_player.game_id LEFT JOIN (SELECT player_game.game_id as game_id, count(player_game.player_id) as number_of_players FROM player_game group by player_game.game_id) as player_counts ON games.gameid = player_counts.game_id"

    conditionals = []
    if include_only_unready:
        conditionals.append(
            "games.players_requested > player_counts.number_of_players")
    if not include_finished:
        conditionals.append("games.game_finished = true")

    if conditionals:
        sql = " WHERE ".join([sql, " AND ".join(conditionals)])

    games = database_connection.execute(
        sql, player_id=player_id)
    return games
