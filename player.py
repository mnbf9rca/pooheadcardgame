from enum import Enum

import jsonpickle
from sqlalchemy import (TIMESTAMP, Boolean, Column, ForeignKey, Integer,
                        String, create_engine)
from sqlalchemy.ext.declarative import declarative_base

import common_db
from cards import Card, Card_Types
from models import Model_Card, Model_Player, Model_Player_Game


def get_player_for_username(username):
    c = common_db.Common_DB()
    result = c.execute(c.common_engine,
                        "SELECT player_id, hash, is_admin FROM users WHERE username = :username",
                        username = username)

    return result


class Player:
    def __init__(self, this_player_id):
        self.name = ""
        self.ID = this_player_id
        self.face_down = []
        self.face_up = []
        self.hand = []

    class Card_Pile_ID(Enum):
        PLAYER_FACE_DOWN = Card_Types.CARD_FACE_DOWN
        PLAYER_FACE_UP = Card_Types.CARD_FACE_UP
        PLAYER_HAND = Card_Types.CARD_HAND
    
    
    Pile_Objects = {
        Card_Pile_ID.PLAYER_FACE_DOWN : "face_down",
        Card_Pile_ID.PLAYER_FACE_DOWN : "face_down",
        Card_Pile_ID.PLAYER_FACE_UP : "face_up",
        Card_Pile_ID.PLAYER_HAND : "hand"
        }

    def summarise(self, player_id):
        # check if this is us - if so send our hand, otherwise send empty
        hand_cards = []
        if self.ID == player_id:
            hand_cards = self.hand
        face_down_cards = []
        face_down_cards.extend([Card(0, 1) for i in range(len(self.face_down))])
        player_summary = {'player_id': self.ID,
                          'number_face_down': len(self.face_down),
                          'number_face_up': len(self.face_up),
                          'face_up_cards': self.face_up,
                          'number_in_hand': len(self.hand),
                          'face_down_cards': face_down_cards,
                          'hand_cards': hand_cards}
        return player_summary

    def load_player_cards(self, session, game_id, deck_type):
        """queries the database for a set of cards for a given player and game and type ande returns as a set"""
        print("about to load cards for player ID " + str(self.ID) + " for game " + str(game_id) + " with type " + str(deck_type) + ".")
        c = common_db.Common_DB()

        cards = c.execute(session,"SELECT card_suit, card_rank FROM game_cards WHERE player_id = :player_id AND card_location = :card_type AND game_id = :game_id ORDER BY card_rank, card_suit ASC",
                                            player_id = self.ID,
                                            card_type = deck_type,
                                            game_id = game_id)
        cards_to_return = []
        if len(cards) > 0:
            cards_to_return.extend([Card(card["card_suit"],card["card_rank"]) for card in cards])
        print("returning " + str(len(cards_to_return)))
        return cards_to_return

    def save(self, session, game_id):
        """saves the current player's gamew state, including registering this player as playing this game"""
        c = common_db.Common_DB()
        result = c.execute(session, 'INSERT INTO player_game (player_id, game_id) VALUES (:user_id, :game_id) ON CONFLICT (player_id, game_id) DO UPDATE SET player_id = :user_id, game_id = :game_id;',
                    user_id= self.ID,
                    game_id = game_id)
        if not result:
            print(f"unable to add or update player in to player_game for player {self.ID} and game {game_id}")
            return False, f"unable to add or update player in to player_game for player {self.ID} and game {game_id}"        

        result = c.execute(session, f"DELETE FROM game_cards WHERE game_id = {game_id} AND player_id = {self.ID};")
        if result == None:
            # some kind of exception
            print("unable to delete existing game cards")
            return False, f"unable to add or update player in to player_game for player {self.ID} and game {game_id}"

        cards_to_store = []
        for pile_id in self.Card_Pile_ID:
                for card in getattr(self, self.Pile_Objects[pile_id]):
                    cards_to_store.append(f"({game_id}, {self.ID}, {pile_id.value}, {card.suit}, {card.rank})")

        if cards_to_store:
            cards_to_store = ", ".join(cards_to_store)
            result = c.execute(session, f"INSERT INTO game_cards (game_id, player_id, card_location, card_suit, card_rank) VALUES {cards_to_store};")
            if not result:
                print("failed to save game cards, rolling back")
                return False, f"unable to save player cards for player {self.ID} and game {game_id}"


        return True, f"player {self.ID} saved successfully"

    def load(self, session, game_id):
        """loads the cards for each card type for the current player"""
        if not self.ID:
            raise ValueError('tried to load game without setting a player ID.')
        for pile_id in self.Card_Pile_ID:
            setattr(self, self.Pile_Objects[pile_id], self.load_player_cards(session, game_id, pile_id.value))

        return True

    def add_cards_to_player_cards(self, cards_to_add, card_type):
        if card_type == Card_Types.CARD_HAND:
            self.hand.extend(cards_to_add)
        elif card_type == Card_Types.CARD_FACE_DOWN:
            self.face_down.extend(cards_to_add)
        elif card_type == Card_Types.CARD_FACE_UP:
            self.face_up.extend(cards_to_add)
        else:
            raise ValueError(
                f"Tried to add cards to unknown hand '{card_type}'")

    def remove_cards_from_player_cards(self, cards_to_remove, card_type):
        if card_type == Card_Types.CARD_HAND:
            self.hand = list(set(self.hand) - set(cards_to_remove))
        elif card_type == Card_Types.CARD_FACE_DOWN:
            self.face_down = list(set(self.face_down) - set(cards_to_remove))
        elif card_type == Card_Types.CARD_FACE_UP:
            self.face_up = list(set(self.face_up) - set(cards_to_remove))
        else:
            raise ValueError(
                f"Tried to add cards to unknown hand '{card_type}'")

    def get_cards(self, card_type):
        if card_type == Card_Types.CARD_HAND:
            return self.hand
        elif card_type == Card_Types.CARD_FACE_DOWN:
            return self.face_down
        elif card_type == Card_Types.CARD_FACE_UP:
            return self.face_up

    def which_player_cards_can_player_use(self):
        if self.hand:
            # have hand cards left, so allow them to play them
            cards_to_play = Card_Types.CARD_HAND
            play_cards = self.hand
        elif self.face_up:
            # have face up cards
            cards_to_play = Card_Types.CARD_FACE_UP
            play_cards = self.face_up
        elif self.face_down:
            # none in hand or face up, must play down card
            cards_to_play = Card_Types.CARD_FACE_DOWN
            play_cards = self.face_down
        else:
            # no cards left
            cards_to_play = Card_Types.CARD_NONE
            play_cards = []

        return cards_to_play, list(play_cards)
