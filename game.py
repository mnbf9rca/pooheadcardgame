from cards import Card, Deck, Card_Types
from player import Player
import json, jsonpickle
from zlib import crc32

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
    
    def get_database_checksum(self, database_connection):
        print("starting has_changed")
        config = database_connection.execute('SELECT "checksum" FROM games WHERE gameid = :game_id',
                        game_id = self.state.game_id)
        print ("got data")
        database_checksum = config[0]["checksum"]

        print ("database_checksum", database_checksum)

        return database_checksum

    def checksum(self):
        state_summary = jsonpickle.dumps({"play_order" : self.state.play_order,
                                          "cards": self.cards,
                                          "players_ready_to_start": self.state.players_ready_to_start,
                                          "players_finished": self.state.players_finished,
                                          "play_list": self.state.play_list} )
        return str(crc32(state_summary.encode()))


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
        if not self.state.game_id:
            querystring = "INSERT INTO games (checksum, players_finished, play_on_anything_cards, play_order, less_than_card, transparent_card, burn_card, reset_card, number_of_decks, number_face_down_cards, number_hand_cards, current_turn_number, last_player, players_ready_to_start, last_player_id, gameid) VALUES (checksum:, :players_finished, :play_on_anything_cards,:play_order,:less_than_card,:transparent_card,:burn_card,:reset_card,:number_of_decks,:number_face_down_cards,:number_hand_cards,:current_turn_number,:last_player,:players_ready_to_start, NULL, :game_id)"

        else:
            querystring = "UPDATE games SET checksum = :checksum, players_finished = :players_finished, play_on_anything_cards = :play_on_anything_cards, play_order = :play_order, less_than_card = :less_than_card, transparent_card = :transparent_card, burn_card = :burn_card, reset_card = :reset_card, number_of_decks = :number_of_decks, number_face_down_cards = :number_face_down_cards ,number_hand_cards = :number_hand_cards,current_turn_number = :current_turn_number,last_player = :last_player, players_ready_to_start = :players_ready_to_start WHERE gameid = :game_id"

        result = database_connection.execute(querystring,
                    checksum = self.checksum(),
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
        self.state.play_list = self.cards.pile_played

    def calculate_player_allowed_actions(self):
        response = {"allowed_action":"unknown", "allowed_players":"unknown"}
        print("self.this_player", jsonpickle.dumps(self.this_player))

        if len(self.state.players_finished) == len(self.players):
            # all done
            response = {"allowed_action":"finished",
                        "action-message": "Game over"}
        elif (not self.this_player.ID in self.state.players_finished) and ((len(self.players) - len(self.state.players_finished)) == 1):
            # you;re the last player
            response = {"allowed_action":"lost",
                        "action-message": "You lost!"} 
        elif self.this_player.ID in self.state.players_finished:
            # this player finished, others havent
            allowed_players = (list(set(player.ID for player in self.players) - set(self.state.players_finished)))
            response = {"allowed_action": "wait",
                        "allowed_players": allowed_players}
        elif len(self.state.players_ready_to_start) < len(self.players):
            # still some players waiting to swap
            # https://www.geeksforgeeks.org/python-difference-two-lists/
            allowed_players = (list(set(player.ID for player in self.players) - set(self.state.players_ready_to_start)))
            response = {"allowed_action":"swap", "allowed_players":allowed_players}
        else:
            # ok - so we've not finished the game
            # and everyone has swapped
            # so must be in game play
            # check if we're next or have to wait
            allowed_players = (list(set(player.ID for player in self.players) - set(self.state.players_finished)))
            is_next_player = self.state.this_player_id == self.state.play_order[0]
            if is_next_player:
                # can we actually play or do we have to pick up?
                card_type, card_stack = self.this_player.which_player_cards_can_player_use()
                can_player_play_a_card = self.__can_play_cards(card_stack)
                if can_player_play_a_card or card_type == Card_Types.CARD_FACE_DOWN:
                    # if we can play from visible cards on top of the played stack,
                    # or if we have only face down cards left
                    # let us play
                    action = "play"
                else:
                    action = "pick"
                response = {"allowed_action": action,
                            "allowed_cards": Card_Types.Short_Name[card_type],
                            "allowed_players": allowed_players,
                            "is_next_player" : is_next_player}
            else:
                # someone else is the next player
                response = {"allowed_action": "wait",
                            "allowed_players": allowed_players,
                            "is_next_player" : is_next_player,
                            "action-message": "wait for others to finish their moves"}


        return response


    def add_to_pile(self, deck_type, cards_to_add = [], *args):
        """add card to pile and update size"""
        if not cards_to_add:
            raise ValueError('tried to add a card to pile without a card.')

        if deck_type == Game.PILE_BURN:
            self.cards.pile_burn = cards_to_add
        elif deck_type == Game.PILE_PICK:
            self.cards.pile_pick = cards_to_add
        elif deck_type == Game.PILE_PLAYED:
            self.cards.pile_played = cards_to_add
        elif deck_type == Game.PILE_DECK:
            self.cards.pile_deck = cards_to_add
        else:
            raise ValueError(f'cant find pile for {deck_type}.')
        self.__update_pile_sizes()
        return

    def play_pick_up(self):
        """picks up the cards from the stack and puts them in the player's hand"""
        response = {'action':'pick', 'action_result':False, 'action_message':"You are not allowed to pick up cards right now"}
        allowed_actions = self.calculate_player_allowed_actions()
        if (allowed_actions["allowed_action"] == "pick" and
            allowed_actions["is_next_player"]):
            # we're allowed to pick up cards right now
            response = self.__pick_up_cards()
        return response
    
    def __pick_up_cards(self):
            # --> not relevant?? card_type, cards  = self.this_player.which_player_cards_can_player_use()
            # when we pick up cards, they always go in our hand from the played pile
            self.this_player.add_cards_to_player_cards(self.cards.pile_played, Card_Types.CARD_HAND)
            self.cards.pile_played = []
            self.__update_pile_sizes()
            self.rotate_player()
            return {'action':'pick', 'action_result':True}


    def play_move(self, cards_to_play, player):
        """ plays a given move"""
        # check game state
        # 1. is "play" a valid move?
        # 2. is it this player's turn?

        response = {'action':'play', 'action_result':False, 'action_message':"You are not allowed to play right now (waiting for other?)"}
        # play
        allowed_actions = self.calculate_player_allowed_actions()
        if (allowed_actions["allowed_action"] == "play" and
            allowed_actions["is_next_player"]):
                if cards_to_play:
                    # validate that these cards are in this user's hand
                    validated_card_indexes = []
                    card_type = ""
                    for card_description in cards_to_play:
                        card_index = int(card_description[2:])
                        print("card_index", card_index, "card_description", card_description)
                        allowed_cards = Card_Types.Get_Code[allowed_actions["allowed_cards"]]
                        try:
                            card_type = Card_Types.Get_Code[card_description[0]]
                        except KeyError:
                            result = {'action':'play', 'action_result':False, 'action_message':f'Unknown card type {card_description[0]}'}
                            return result
                        except:
                            raise

                        if (card_type == Card_Types.CARD_FACE_DOWN and
                            len(cards_to_play) != 1):
                            # can only play one face down card at a time
                            result = {'action':'play', 'action_result':False, 'action_message':f'You can only play one face down card at a time'}
                            return result
                        if card_type != allowed_cards:
                            response = {'action':'play', 'action_result':False, 'action_message':f'You can only play cards of type {Card_Types.Long_Name[allowed_cards]} but you sent card of type {Card_Types.Long_Name[card_type]}'}
                            return response
                        message = self.__check_card_index_not_over_deck_length(card_index, card_type, player)
                        if message:
                            response = {'action':'play', 'action_result':False, 'action_message':message}
                            return response
                        validated_card_indexes.append(card_index)

                    card_dict = self.this_player.get_cards(card_type)
                    validated_cards = list(card_dict[card_location] for card_location in validated_card_indexes)

                    # check if all cards are the same rank:
                    if not self.__are_all_cards_same_rank(validated_cards):
                        result = {'action':'play', 'action_result':False, 'action_message':f'If playing more than one card, they must all be the same rank (value).'}
                        return result

                    can_play_cards = self.__can_play_cards(validated_cards)
                    print("can_play_cards", can_play_cards)

                    if can_play_cards:
                        # great - play teh cards!
                        self.cards.pile_played.extend(validated_cards)
                        # remove these cards from teh player's hand/hidden/up cards and refill their hand if there are cards left in teh deck
                        self.this_player.remove_cards_from_player_cards(validated_cards, card_type)
                        if card_type == Card_Types.CARD_HAND:
                            while (len(player.hand) < self.state.number_hand_cards and
                                len(self.cards.pile_deck) > 0):
                                player.hand.append(self.cards.pile_deck.pop())
                        
                        # check if last move clears the deck
                        if self.__clears_deck(self.cards.pile_played):
                            self.cards.pile_burn.extend(self.cards.pile_played)
                            self.cards.pile_played = []
                        else:
                            self.rotate_player()
                        
                        if not player.face_down:
                            # have run out of cards
                            self.state.players_finished.append(player.ID)
                            response = {'action':'wait', 'action_result':True}
                        else:
                            response = {'action':'play', 'action_result':True}
                    else:
                        if card_type == Card_Types.CARD_FACE_DOWN:
                            # tried to play a face down card but lost
                            # move this card to the player's hand
                            player.add_cards_to_player_cards(validated_cards, Card_Types.CARD_HAND)
                            # pick up the rest of the played cards
                            self.__pick_up_cards()
                            self.this_player.remove_cards_from_player_cards(validated_cards, card_type)
                            response = {'action':'play', 'action_result':True, 'action_message': 'playing down cards not yet implemented'}
                        else:
                            response = {'action':'play', 'action_result':False, 'action_message':f'Cannot play that move on the current stack'}
                        self.__update_pile_sizes()
                        # return response
                    # response = {'action':'play', 'action_result':True}
                else:
                    response = {'action':'play', 'action_result':False, 'action_message':"Select one or more cards to play"}
        return response
    def __clears_deck(self, played_pile):
        all_match = False
        if len(played_pile) > 3:
            pile_played = played_pile[-4:]
            print("card1", pile_played[0], "card2", pile_played[1], "card3", pile_played[2], "card4", pile_played[3])
            all_match= (pile_played[0].rank == pile_played[1].rank) and (pile_played[1].rank == pile_played[2].rank) and (pile_played[2].rank == pile_played[3].rank)
        print("self.cards.pile_played[0].rank", self.cards.pile_played[0].rank, "self.state.burn_card", self.state.burn_card)
        return ((self.cards.pile_played[-1].rank == self.state.burn_card) or
                all_match)

    def __are_all_cards_same_rank(self, cards):
        # now check they're all the same         
        last_card = None
        for card in cards:
            if last_card:
                if not card.rank == last_card.rank:
                    return False
            last_card = card
        return True

    def __can_play_cards(self, cards_to_check):
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
