from cards import Card, Deck
from player import Player
from game_helpers import persist_cards_to_database, get_users_for_game, load_cards_from_database

class Game:
    PILE_BURN = 1
    PILE_PICK = 2
    PILE_PLAYED = 3
    PILE_DECK = 4

    def __init__(self, player_IDs = None):

        #players
        self.numer_of_players = len(player_IDs)
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
        self.number_hand_cards = 3

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
        if not self.game_id:
            result = database_connection.execute('INSERT INTO "games" ("last_player_id","less_than_card","transparent_card","burn_card","reset_card","number_of_decks","number_face_down_cards","number_hand_cards","current_turn_number","last_player","gameid") VALUES (NULL,:less_than_card,:transparent_card,:burn_card,:reset_card,:number_of_decks,:number_face_down_cards,:number_hand_cards,:current_turn_number,:last_player,NULL)',
                        less_than_card = self.less_than_card ,
                        transparent_card = self.transparent_card,
                        burn_card = self.burn_card,
                        reset_card = self.reset_card,
                        number_of_decks = self.number_of_decks,
                        number_face_down_cards = self.number_face_down_cards,
                        number_hand_cards = self.number_hand_cards,
                        current_turn_number = self.current_turn_number,
                        last_player = self.last_player)
            self.game_id = result
        else:
            result = database_connection.execute('UPDATE "games" SET "less_than_card" = :less_than_card, "transparent_card" = :transparent_card, "burn_card" = :burn_card, "reset_card" = :reset_card, "number_of_decks" = :number_of_decks, "number_face_down_cards" = :number_face_down_cards ,"number_hand_cards" = :number_hand_cards,"current_turn_number" = :current_turn_number,"last_player" = :last_player WHERE game_id = :game_id)',
                        less_than_card = self.less_than_card ,
                        transparent_card = self.transparent_card,
                        burn_card = self.burn_card,
                        reset_card = self.reset_card,
                        number_of_decks = self.number_of_decks,
                        number_face_down_cards = self.number_face_down_cards,
                        number_hand_cards = self.number_hand_cards,
                        current_turn_number = self.current_turn_number,
                        last_player = self.last_player,
                        game_id = self.game_id)
        persist_cards_to_database(deck = self.deck, deck_type = str(Game.PILE_DECK), game_id = str(self.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.burn_pile, deck_type = str(Game.PILE_BURN), game_id = str(self.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.played_cards, deck_type = str(Game.PILE_PLAYED), game_id = str(self.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.pick_stack, deck_type = str(Game.PILE_PICK), game_id = str(self.game_id), database_connection = database_connection)

        for player in self.players:
            player.save(database_connection, self.game_id)

        return self.game_id

    def load(self, database_connection):
        if not self.game_id:
            raise ValueError('tried to load game without setting game_id.')
        if not len(self.players) > 0:
            raise ValueError('tried to load game without setting player IDs.')

        self.deck = load_cards_from_database(Game.PILE_DECK, self.game_id, database_connection)
        self.burn_pile = load_cards_from_database(Game.PILE_BURN, self.game_id, database_connection)
        self.played_cards = load_cards_from_database(Game.PILE_PLAYED, self.game_id, database_connection)
        self.pick_stack = load_cards_from_database(Game.PILE_PICK, self.game_id, database_connection)
        print("loaded config and stack for game ID :" + str(self.game_id))
        for player in self.players:
            player.load(database_connection, self.game_id)