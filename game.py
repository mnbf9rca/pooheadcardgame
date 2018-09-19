from cards import Card, Deck, Card_Types
from player import Player
import json, jsonpickle

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

    this_player = None

    class State(object):
        """holds the current state of this game, excluding player hands and config"""
        def __init__(self, player_IDs):
            self.number_of_players = len(player_IDs)
            self.play_order = player_IDs
            self.this_player_id = None
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
            self.players_finished = []
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

    def __init__(self, this_player_id, player_IDs = []):
        self.state = self.State(player_IDs)
        self.cards = self.Cards()
        self.state.this_player_id = this_player_id
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
            querystring = "INSERT INTO games (players_finished, play_on_anything_cards, play_order, less_than_card, transparent_card, burn_card, reset_card, number_of_decks, number_face_down_cards, number_hand_cards, current_turn_number, last_player, players_ready_to_start, last_player_id, gameid) VALUES (:players_finished, :play_on_anything_cards,:play_order,:less_than_card,:transparent_card,:burn_card,:reset_card,:number_of_decks,:number_face_down_cards,:number_hand_cards,:current_turn_number,:last_player,:players_ready_to_start, NULL, :game_id)"

        else:
            querystring = "UPDATE games SET players_finished = :players_finished, play_on_anything_cards = :play_on_anything_cards, play_order = :play_order, less_than_card = :less_than_card, transparent_card = :transparent_card, burn_card = :burn_card, reset_card = :reset_card, number_of_decks = :number_of_decks, number_face_down_cards = :number_face_down_cards ,number_hand_cards = :number_hand_cards,current_turn_number = :current_turn_number,last_player = :last_player, players_ready_to_start = :players_ready_to_start WHERE gameid = :game_id"

        result = database_connection.execute(querystring,
                    players_finished = json.dumps(self.state.players_finished),
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

        if not(self.state.game_id): self.state.game_id = result

        if not self.__persist_cards_to_database(deck = self.cards.pile_deck, deck_type = str(Game.PILE_DECK), game_id = str(self.state.game_id), database_connection = database_connection):
            raise ValueError('error persisting Game.PILE_DECK to database')
        if not self.__persist_cards_to_database(deck = self.cards.pile_burn, deck_type = str(Game.PILE_BURN), game_id = str(self.state.game_id), database_connection = database_connection):
            raise ValueError('error persisting Game.PILE_BURN to database')
        if not self.__persist_cards_to_database(deck = self.cards.pile_played, deck_type = str(Game.PILE_PLAYED), game_id = str(self.state.game_id), database_connection = database_connection):
            raise ValueError('error persisting Game.PILE_PLAYED to database')
        if not self.__persist_cards_to_database(deck = self.cards.pile_pick, deck_type = str(Game.PILE_PICK), game_id = str(self.state.game_id), database_connection = database_connection):
            raise ValueError('error persisting Game.PILE_PICK to database')


        for player in self.players:
            player.save(database_connection, self.state.game_id)
            # store a reference to this player's object on the game itself
            if player.ID == self.state.this_player_id: self.this_player = player

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
        if not self.state.this_player_id:
            raise ValueError('tried to load game without setting ID of current player and it doesnt exist in current instantiation.')

        # load game config
        config = database_connection.execute('SELECT "players_finished", "play_order","last_player_id","less_than_card","transparent_card","burn_card","reset_card","number_of_decks","number_face_down_cards","number_hand_cards","current_turn_number","last_player", "players_ready_to_start" FROM games WHERE gameid = :game_id',
                        game_id = self.state.game_id)
        config = config[0]
        self.state.players_finished = json.loads(config["players_finished"])
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
        self.cards.pile_deck = self.__load_cards_from_database(Game.PILE_DECK, self.state.game_id, database_connection)
        self.cards.pile_burn = self.__load_cards_from_database(Game.PILE_BURN, self.state.game_id, database_connection)
        self.cards.pile_played = self.__load_cards_from_database(Game.PILE_PLAYED, self.state.game_id, database_connection)
        self.cards.pile_pick = self.__load_cards_from_database(Game.PILE_PICK, self.state.game_id, database_connection)
        self.__update_pile_sizes()

        print("loaded config and card stacks for game ID :" + str(self.state.game_id))
        for player in self.players:
            player.load(database_connection, self.state.game_id)
            # store a reference to this player's object on the game itself
            if player.ID == self.state.this_player_id: self.this_player = player

    def __update_pile_sizes(self):
        self.state.pile_pick_size = len(self.cards.pile_pick)
        self.state.pile_played_size = len(self.cards.pile_played)
        self.state.pile_burn_size = len(self.cards.pile_burn)
        self.state.pile_deck_size = len(self.cards.pile_deck)

    def calculate_player_allowed_actions(self):
        response = {"allowed_action":"unknown", "allowed_players":"unknown"}
        print("self.this_player", jsonpickle.dumps(self.this_player))
        print()
        if len(self.state.players_ready_to_start) < len(self.players):
            # still some players waiting to swap
            # https://www.geeksforgeeks.org/python-difference-two-lists/
            allowed_players = (list(set(player.ID for player in self.players) - set(self.state.players_ready_to_start)))
            response = {"allowed_action":"swap", "allowed_players":allowed_players}
        elif (self.state.this_player_id in self.state.play_order and
                (self.this_player.hand or
                self.this_player.face_down or
                self.this_player.face_up)):
            # this player is the next player
            # and this player still has cards
            # work out which cards i can use
            action = "play"
            if self.this_player.hand:
                # have hand cards left, so allow them to play them
                cards_to_play = Card_Types.CARD_HAND
            elif self.this_player.face_up:
                # have face up cards
                cards_to_play = Card_Types.CARD_FACE_UP
            else:
                # none in hand or face up, must play down card
                cards_to_play = Card_Types.CARD_FACE_DOWN

            # check if the player's hand contains any cards which can be played on the current pile
            play_cards = []
            if cards_to_play ==  Card_Types.CARD_HAND:
                play_cards= self.this_player.hand
            elif cards_to_play == Card_Types.CARD_FACE_UP:
                play_cards = self.this_player.face_up



            allowed_players = (list(set(player.ID for player in self.players) - set(self.state.players_finished)))
            is_next_player = self.state.this_player_id == self.state.play_order[0]
            response = {"allowed_action":action,
                        "allowed_cards":Card_Types.Short_Name[cards_to_play],
                        "allowed_players": allowed_players,
                        "is_next_player" : is_next_player}


        return response


    def add_to_pile(self, deck_type, cards_to_add = [], *args):
        """add card to pile and update size"""
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

    def play_move(self, cards_to_play, player):
        """ plays a given move"""
        # check game state
        # 1. is "play" a valid move?
        # 2. is it this player's turn?

        response = None
        # play
        allowed_actions = self.calculate_player_allowed_actions()
        if (allowed_actions["allowed_action"] == "play" and
            player.ID in allowed_actions["allowed_players"]):
                if cards_to_play:
                    # validate that these cards are in this user's hand
                    validated_card_indexes = []
                    card_type = ""
                    for card_description in cards_to_play:
                        index = int(card_description[2:])
                        print("index", index)
                        allowed_cards = allowed_actions["allowed_cards"]
                        card_type = card_description[0]
                        if card_type != allowed_cards:
                            response = {'action':'play', 'action_result':False, 'action_message':f'You can only play cards of type {allowed_cards} but you sent card of type {card_type}'}
                            return response
                        message = self.__check_card_index_not_over_deck_length(index, Card_Types.Get_Code[card_type], player)
                        if message:
                            response = {'action':'play', 'action_result':False, 'action_message':message}
                            return response
                        validated_card_indexes.append(index)
                    # now check they're all the same

                    response = {'action':'play', 'action_result':True}
                else:
                    response = {'action':'play', 'action_result':False, 'action_message':"Select one or more cards to play"}
        else:
            response = {'action':'play', 'action_result':False, 'action_message':"You are not allowed to play right now"}

        return response

    def __check_card_index_not_over_deck_length(self, card_index, card_type, player):
        if card_type == Card_Types.CARD_FACE_UP:
            deck = player.face_up
        elif card_type == Card_Types.CARD_FACE_DOWN:
            deck = player.face_down
        elif card_type == Card_Types.CARD_HAND:
            deck = player.hand
        else:
            message = f'unknown card type {card_type}.'
            return  message

        if (card_index > len(deck) - 1):
            message = f'Attempted to play card {card_index} which is above face card count {len(deck) - 1}.'
            return message
        else:
            return None

    def swap_cards(self, cards_to_swap, player):
        """swaps cards in hand with face up"""
        # check game state - has this user already committed cards?
        # if not, then just swap the cards
        response = None
        # if not player.ID in self.state.players_ready_to_start:

        allowed_actions = self.calculate_player_allowed_actions()
        if (allowed_actions["allowed_action"] == "swap" and
            player.ID in allowed_actions["allowed_players"]):

                print("ready to swap")
                hand_cards = []
                face_cards = []
                for card in cards_to_swap:
                    index = int(card[2:])
                    print("index", index)
                    try:
                        print("Card_Types.Get_Code", jsonpickle.dumps(Card_Types.Get_Code))
                        card_type = Card_Types.Get_Code[card[0]]
                    except KeyError:
                        response = {'action':'swap', 'action_result':False, 'action_message':f"Unrecognised card type '{card[0]}'"}
                        return response
                    except:
                        raise

                    if card_type == Card_Types.CARD_FACE_UP:
                        # face card
                        message = self.__check_card_index_not_over_deck_length(index, card_type, player)
                        if message:
                            response = {'action':'swap', 'action_result':False, 'action_message':message}
                            return response
                        face_cards.append(index)
                    elif card_type == Card_Types.CARD_HAND:
                        # hand card
                        message = self.__check_card_index_not_over_deck_length(index, card_type, player)

                        if message:
                            response = {'action':'swap', 'action_result':False, 'action_message':message}
                            return response
                        hand_cards.append(index)
                    else:
                        response = {'action':'swap', 'action_result':False, 'action_message':'You can only swap hand and face up cards.'}
                        return response

                if len(hand_cards) != len(face_cards):
                    response = {'action':'swap', 'action_result':False, 'action_message':'You must select the same number of cards from your hand and face up sets.'}
                elif len(hand_cards) <= 0:
                    response = {'action':'swap', 'action_result':False, 'action_message':'Select the face up and hand cards you want to swap.'}
                else:
                    print("len hand", len(hand_cards), "len face", len(face_cards))
                    for i in range(len(hand_cards)):
                         player.hand[hand_cards[i]], player.face_up[face_cards[i]] = player.face_up[face_cards[i]], player.hand[hand_cards[i]]

                    response = {'action':'swap', 'action_result':True}

        else:
            response= {'action':'swap', 'action_result':False, 'action_message':'You can\'t swap cards right now'}

        return response


    def __load_cards_from_database(self, deck_type, game_id, database_connection):
        """load a set of cards and return them in a sorted list"""
        cards = database_connection.execute("SELECT card_suit, card_rank FROM game_cards WHERE game_id = :game_id AND card_location = :deck_type ORDER BY card_sequence ASC",
                game_id = game_id, deck_type = deck_type)
        cards_to_return = []
        if len(cards) > 0:
            cards_to_return.extend([Card(card["card_suit"],card["card_rank"]) for card in cards])
        return cards_to_return

    def __persist_cards_to_database(self, deck = [], *args, deck_type, game_id, database_connection):
        """persist a set of cards to the database as part of game state"""
        # first, clear all cards of this type for this game
        result = database_connection.execute("DELETE FROM game_cards WHERE card_location=:card_type AND game_id = :game_id",
                                    card_type = deck_type,
                                    game_id = game_id)
        if len(deck) > 0:

            i = 0
            for card in deck:
                    print(str(card) + " at position " + str(i))
                    result = database_connection.execute("INSERT INTO game_cards (game_id, card_location, card_suit, card_rank, card_sequence) VALUES (:game_id, :deck_type, :card_suit, :card_rank, :i)",
                                                            game_id = game_id,
                                                            deck_type = deck_type,
                                                            card_suit = card.suit,
                                                            card_rank = card.rank,
                                                            i = i)
                    if not result:
                        return False
                    i += 1
        return True

def get_users_for_game(game_id, database_connection):
    """load the list of users playing a game"""
    players = database_connection.execute("SELECT player_id FROM player_game WHERE game_id = :game_id",
                                            game_id=game_id)
    list_of_players = []
    if len(players) > 0:
        list_of_players.extend([player["player_id"] for player in players])
    return list_of_players
