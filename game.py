from cards import Card, Deck
from player import Player
from game_helpers import persist_cards_to_database, get_users_for_game, load_cards_from_database
import json

class Game(object):
    PILE_BURN = 1
    PILE_PICK = 2
    PILE_PLAYED = 3
    PILE_DECK = 4

    Pile_Objects = {
        PILE_DECK : "self.cards.deck",
        PILE_PICK : "self.cards.pick_stack",
        PILE_PLAYED : "self.cards.played_cards",
        PILE_BURN : "self.cards.burn_pile"
    }

    Pile_Counts = {
        PILE_DECK : "self.state.pile_deck_size",
        PILE_PICK : "self.state.pile_pick_size",
        PILE_PLAYED : "self.cards.pile_played_size",
        PILE_BURN : "self.cards.pile_burn_size"
    }

    class State(object):
        """holds the current state of this game, excluding player hands and config"""
        def __init__(self, player_IDs):
            self.number_of_players = len(player_IDs)
            self.play_order = player_IDs
            #game config
            self.game_id = None
            self.less_than_card = 7
            self.transparent_card = 0
            self.burn_card = 10
            self.reset_card = 2
            self.number_of_decks = 1
            self.number_face_down_cards = 3
            self.number_hand_cards = 7
            self.players_ready_to_start = []
            self.play_on_anything_cards = [2, 10]

            # game state
            self.current_turn_number = 0
            self.last_player = None
            self.play_list = []
            self.pile_burn_size = 0
            self.pile_pick_size = 0
            self.pile_played_size = 0
            self.pile_deck_size = 0

    class Cards(object):
        """stores cards separately from state to keep secret from client"""
        def __init__(self):
            # piles
            self.pile_burn = []
            self.pile_pick = []
            self.pile_played = []
            self.pile_deck = []

    def __init__(self, player_IDs = []):
        self.state = self.State(player_IDs)
        self.cards = self.Cards()
        #players

        self.players = []
        if player_IDs:
            for ID in player_IDs:
                player = Player(ID)
                self.players.append(player)



    def deal(self):
        """creates a new deck of cards, deals to each player, then puts the remaining cards in the pick stack"""
        new_deck = Deck()

        # although cards are shuffled and so it doesnt really matter
        # follow convention and deal face down, then face up, then hand cards
        for deal in range(self.state.number_face_down_cards):
            for player in self.players:
                player.face_down.append(new_deck.deal())

        # number face down cards = number face up cards
        for deal in range(self.state.number_face_down_cards):
            for player in self.players:
                player.face_up.append(new_deck.deal())

        # hand cards
        for deal in range(self.state.number_hand_cards):
            for player in self.players:
                player.hand.append(new_deck.deal())

        self.cards.pile_deck = new_deck.cards
        self.__update_pile_sizes()


    def save(self, database_connection):
        """saves the current state of the game. If this is a new game without an ID, it creates one, otherwise it updates the existing one"""
        play_order = []
        if not self.state.game_id:
            result = database_connection.execute("INSERT INTO games (play_on_anything_cards, play_order, less_than_card, transparent_card, burn_card, reset_card, number_of_decks, number_face_down_cards, number_hand_cards, current_turn_number, last_player, players_ready_to_start, last_player_id, gameid) VALUES (:play_on_anything_cards,:play_order,:less_than_card,:transparent_card,:burn_card,:reset_card,:number_of_decks,:number_face_down_cards,:number_hand_cards,:current_turn_number,:last_player,:players_ready_to_start, NULL, NULL)",
                        play_on_anything_cards = json.dumps(self.state.play_on_anything_cards),
                        play_order = json.dumps(self.state.play_order),
                        less_than_card = self.state.less_than_card,
                        transparent_card = self.state.transparent_card,
                        burn_card = self.state.burn_card,
                        reset_card = self.state.reset_card,
                        number_of_decks = self.state.number_of_decks,
                        number_face_down_cards = self.state.number_face_down_cards,
                        number_hand_cards = self.state.number_hand_cards,
                        current_turn_number = self.state.current_turn_number,
                        last_player = self.state.last_player,
                        players_ready_to_start = json.dumps(self.state.players_ready_to_start))
            self.state.game_id = result
        else:
            result = database_connection.execute("UPDATE games SET play_on_anything_cards = :play_on_anything_cards, play_order = :play_order, less_than_card = :less_than_card, transparent_card = :transparent_card, burn_card = :burn_card, reset_card = :reset_card, number_of_decks = :number_of_decks, number_face_down_cards = :number_face_down_cards ,number_hand_cards = :number_hand_cards,current_turn_number = :current_turn_number,last_player = :last_player, players_ready_to_start = :players_ready_to_start WHERE gameid = :game_id",
                        play_on_anything_cards = json.dumps(self.state.play_on_anything_cards),
                        play_order = json.dumps(self.state.play_order),
                        less_than_card = self.state.less_than_card ,
                        transparent_card = self.state.transparent_card,
                        burn_card = self.state.burn_card,
                        reset_card = self.state.reset_card,
                        number_of_decks = self.state.number_of_decks,
                        number_face_down_cards = self.state.number_face_down_cards,
                        number_hand_cards = self.state.number_hand_cards,
                        current_turn_number = self.state.current_turn_number,
                        last_player = self.state.last_player,
                        game_id = self.state.game_id,
                        players_ready_to_start = json.dumps(self.state.players_ready_to_start))
        persist_cards_to_database(deck = self.cards.pile_deck, deck_type = str(Game.PILE_DECK), game_id = str(self.state.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.cards.pile_burn, deck_type = str(Game.PILE_BURN), game_id = str(self.state.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.cards.pile_played, deck_type = str(Game.PILE_PLAYED), game_id = str(self.state.game_id), database_connection = database_connection)
        persist_cards_to_database(deck = self.cards.pile_pick, deck_type = str(Game.PILE_PICK), game_id = str(self.state.game_id), database_connection = database_connection)


        for player in self.players:
            player.save(database_connection, self.state.game_id)
        # return the game_id for future use
        return self.state.game_id

    def rotate_player(self):
        print("started with: " + json.dumps(self.state.play_order))
        last_player = self.state.play_order.pop(0)
        print("last player: " + json.dumps(last_player))
        self.state.last_player = last_player

        self.state.play_order.append(last_player)

        print("ended with: " + json.dumps(self.state.play_order))


    def load(self, database_connection):
        if not self.state.game_id:
            raise ValueError('tried to load game without setting game_id.')
        if not len(self.players) > 0:
            raise ValueError('tried to load game without setting player IDs.')

        # load game config
        config = database_connection.execute('SELECT "play_order","last_player_id","less_than_card","transparent_card","burn_card","reset_card","number_of_decks","number_face_down_cards","number_hand_cards","current_turn_number","last_player", "players_ready_to_start" FROM games WHERE gameid = :game_id',
                        game_id = self.state.game_id)
        config = config[0]
        self.state.play_order = json.loads(config["play_order"])
        self.state.less_than_card = config["less_than_card"]
        self.state.transparent_card = config["transparent_card"]
        self.state.burn_card = config["burn_card"]
        self.state.reset_card = config["reset_card"]
        self.state.number_of_decks = config["number_of_decks"]
        self.state.number_face_down_cards = config["number_face_down_cards"]
        self.state.number_hand_cards = config["number_hand_cards"]
        self.state.current_turn_number = config["current_turn_number"]
        self.state.last_player = config["last_player"]
        self.state.players_ready_to_start = json.loads(config["players_ready_to_start"])
        print("ready to start: " + str(self.state.players_ready_to_start))

        # load decks
        self.cards.pile_deck = load_cards_from_database(Game.PILE_DECK, self.state.game_id, database_connection)
        self.cards.pile_burn = load_cards_from_database(Game.PILE_BURN, self.state.game_id, database_connection)
        self.cards.pile_played = load_cards_from_database(Game.PILE_PLAYED, self.state.game_id, database_connection)
        self.cards.pile_pick = load_cards_from_database(Game.PILE_PICK, self.state.game_id, database_connection)
        self.__update_pile_sizes()

        print("loaded config and card stacks for game ID :" + str(self.state.game_id))
        for player in self.players:
            player.load(database_connection, self.state.game_id)

    def __update_pile_sizes(self):
        self.state.pile_pick_size = len(self.cards.pile_pick)
        self.state.pile_played_size = len(self.cards.pile_played)
        self.state.pile_burn_size = len(self.cards.pile_burn)
        self.state.pile_deck_size = len(self.cards.pile_deck)

    def add_to_pile(self, deck_type, cards_to_add = [], *args):
        """add card to pile and update size"""
#        pile_object = self.Pile_Objects.get(deck_type, None)
#        if not pile_object:
#            raise ValueError(f'cant find object name for {deck_type}.')
#        pile_count = self.Pile_Counts.get(deck_type, None)
#        if not pile_count:
#            raise ValueError(f'cant find pile size object for {deck_type}.')

#        deck = getattr(self, pile_object)
#        deck.extend(cards_to_add)
#        pile_count = len(deck)
        if not cards_to_add:
            raise ValueError('tried to add a card to pile without a card.')

        if deck_type == Game.PILE_BURN:
            self.cards.pile_burn = cards_to_add
            self.state.pile_burn_size = len(self.cards.pile_burn)
        elif deck_type == Game.PILE_PICK:
            self.cards.pile_pick = cards_to_add
            self.state.pile_pick_size = len(self.cards.pile_pick)
        elif deck_type == Game.PILE_PLAYED:
            self.cards.pile_played = cards_to_add
            self.state.pile_played_size = len(self.cards.pile_played)
        elif deck_type == Game.PILE_DECK:
            self.cards.pile_deck = cards_to_add
            self.state.pile_deck_size = len(self.cards.pile_deck)
        else:
            raise ValueError(f'cant find pile for {deck_type}.')
        return


    def swap_cards(self, cards_to_swap, player):
        """swaps cards in hand with face up"""
        # TODO
        # check game state - has this user already committed cards?
        # if not, then just swap the cards
        return
