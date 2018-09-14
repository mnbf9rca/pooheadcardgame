from cards import Card, Deck
from player import Player
from game_helpers import persist_cards_to_database, get_users_for_game, load_cards_from_database
import json

class Game:
    PILE_BURN = 1
    PILE_PICK = 2
    PILE_PLAYED = 3
    PILE_DECK = 4

    def __init__(self, player_IDs = []):

        #players
        self.numer_of_players = len(player_IDs)
        self.play_order = player_IDs
        self.players = []
        if player_IDs:
            for ID in player_IDs:
                player = Player(ID)
                self.players.append(player)

        #game config
        self.game_id = None
        self.less_than_card = 7
        self.transparent_card = None
        self.burn_card = 10
        self.reset_card = 2
        self.number_of_decks = 1
        self.number_face_down_cards = 3
        self.number_hand_cards = 7
        self.players_ready_to_start = []

        # piles
        self.burn_pile = []
        self.pick_stack = []
        self.played_cards = []
        self.deck = []

        # game state
        self.current_turn_number = 0
        self.last_player = None
        self.play_list = []

    def deal(self):
        """creates a new deck of cards, deals to each player, then puts the remaining cards in the pick stack"""
        self.deck = Deck()

        # although cards are shuffled and so it doesnt really matter
        # follow convention and deal face down, then face up, then hand cards
        for deal in range(self.number_face_down_cards):
            for player in self.players:
                player.face_down.append(self.deck.deal())

        # number face down cards = number face up cards
        for deal in range(self.number_face_down_cards):
            for player in self.players:
                player.face_up.append(self.deck.deal())

        # hand cards
        for deal in range(self.number_hand_cards):
            for player in self.players:
                player.hand.append(self.deck.deal())

    def save(self, database_connection):
        """saves the current state of the game. If this is a new game without an ID, it creates one, otherwise it updates the existing one"""
        play_order = []
        if not self.game_id:

            result = database_connection.execute("INSERT INTO games (play_order, last_player_id,less_than_card,transparent_card,burn_card,reset_card,number_of_decks,number_face_down_cards,number_hand_cards,current_turn_number,last_player,gameid, players_ready_to_start) VALUES (:play_order, NULL,:less_than_card,:transparent_card,:burn_card,:reset_card,:number_of_decks,:number_face_down_cards,:number_hand_cards,:current_turn_number,:last_player,NULL, :players_ready_to_start)",
                        play_order = json.dumps(self.play_order),
                        less_than_card = self.less_than_card,
                        transparent_card = self.transparent_card,
                        burn_card = self.burn_card,
                        reset_card = self.reset_card,
                        number_of_decks = self.number_of_decks,
                        number_face_down_cards = self.number_face_down_cards,
                        number_hand_cards = self.number_hand_cards,
                        current_turn_number = self.current_turn_number,
                        last_player = self.last_player,
                        players_ready_to_start = json.dumps(self.players_ready_to_start))
            self.game_id = result
        else:
            result = database_connection.execute("UPDATE games SET play_order = :play_order, less_than_card = :less_than_card, transparent_card = :transparent_card, burn_card = :burn_card, reset_card = :reset_card, number_of_decks = :number_of_decks, number_face_down_cards = :number_face_down_cards ,number_hand_cards = :number_hand_cards,current_turn_number = :current_turn_number,last_player = :last_player, players_ready_to_start = :players_ready_to_start WHERE gameid = :game_id",
                        play_order = json.dumps(self.play_order),
                        less_than_card = self.less_than_card ,
                        transparent_card = self.transparent_card,
                        burn_card = self.burn_card,
                        reset_card = self.reset_card,
                        number_of_decks = self.number_of_decks,
                        number_face_down_cards = self.number_face_down_cards,
                        number_hand_cards = self.number_hand_cards,
                        current_turn_number = self.current_turn_number,
                        last_player = self.last_player,
                        game_id = self.game_id,
                        players_ready_to_start = json.dumps(self.players_ready_to_start))
        persist_cards_to_database(deck = self.deck, deck_type = str(Game.PILE_DECK), game_id = str(self.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.burn_pile, deck_type = str(Game.PILE_BURN), game_id = str(self.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.played_cards, deck_type = str(Game.PILE_PLAYED), game_id = str(self.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.pick_stack, deck_type = str(Game.PILE_PICK), game_id = str(self.game_id), database_connection = database_connection)


        for player in self.players:
            player.save(database_connection, self.game_id)
        # return the game_id for future use
        return self.game_id

    def rotate_player(self):
        print("started with: " + json.dumps(self.play_order))
        last_player = self.play_order.pop(0)
        print("last player: " + json.dumps(last_player))
        self.last_player = last_player

        self.play_order.append(last_player)

        print("ended with: " + json.dumps(self.play_order))


    def load(self, database_connection):
        if not self.game_id:
            raise ValueError('tried to load game without setting game_id.')
        if not len(self.players) > 0:
            raise ValueError('tried to load game without setting player IDs.')

        # load game config
        config = database_connection.execute('SELECT "play_order","last_player_id","less_than_card","transparent_card","burn_card","reset_card","number_of_decks","number_face_down_cards","number_hand_cards","current_turn_number","last_player", "players_ready_to_start" FROM games WHERE gameid = :game_id',
                        game_id = self.game_id)
        config = config[0]
        self.play_order = json.loads(config["play_order"])
        self.less_than_card = config["less_than_card"]
        self.transparent_card = config["transparent_card"]
        self.burn_card = config["burn_card"]
        self.reset_card = config["reset_card"]
        self.number_of_decks = config["number_of_decks"]
        self.number_face_down_cards = config["number_face_down_cards"]
        self.number_hand_cards = config["number_hand_cards"]
        self.current_turn_number = config["current_turn_number"]
        self.last_player = config["last_player"]
        self.players_ready_to_start = json.loads(config["players_ready_to_start"])
        print("ready to start: " + str(self.players_ready_to_start))

        # load decks
        self.deck = load_cards_from_database(Game.PILE_DECK, self.game_id, database_connection)
        self.burn_pile = load_cards_from_database(Game.PILE_BURN, self.game_id, database_connection)
        self.played_cards = load_cards_from_database(Game.PILE_PLAYED, self.game_id, database_connection)
        self.pick_stack = load_cards_from_database(Game.PILE_PICK, self.game_id, database_connection)
        print("loaded config and card stacks for game ID :" + str(self.game_id))
        for player in self.players:
            player.load(database_connection, self.game_id)

    def swap_cards(self, cards_to_swap, player):
        """swaps cards in hand with face up"""
        # TODO
        # check game state - has this user already committed cards?
        # if not, then just swap the cards
        return
