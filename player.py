import jsonpickle
from sqlalchemy import (TIMESTAMP, Boolean, Column, Integer, String,
                        create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from cards import Card, Card_Types
import common_db

Base = declarative_base()


class Model_Player(Base):
    __tablename__ = 'users'
    player_id = Column(Integer, primary_key=True)
    player_name = Column(String)
    last_played_at = Column(TIMESTAMP(timezone=False))
    hash = Column(String)
    username = Column(String)
    is_admin = Column(Boolean)

    def __repr__(self):
        return f"<User(id='{self.player_id}', username='{self.username}' name='{self.player_name}', last_played_at='{self.last_played_at}')>"

class Model_Player_Game(Base):
    __tablename__ = 'player_game'
    player_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, primary_key=True)

class Model_Player_Cards(Base):
    __tablename__ = 'player_game_cards'
    player_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, primary_key=True)
    card_type = Column(Integer, primary_key=True)
    card_suit = Column(Integer, primary_key=True)
    card_rank = Column(Integer, primary_key=True)
    card_sequence = Column(Integer)

    def __repr__(self):
        return f"<Player Card(Player_ID='{self.player_id}', game_id='{self.game_id}' type='{self.type}', rank='{self.rank}', suit='{self.suit}')>"


def get_player_for_username(username):
    login_session = common_db.Common_DB().common_Session()

    query = login_session.query(Model_Player).filter(
        Model_Player.username == username).order_by(Model_Player.player_id)

    login_session.close()

    return query


class Player:
    def __init__(self, ID):
        self.name = ""
        self.ID = ID
        self.face_down = []
        self.face_up = []
        self.hand = []

    def summarise(self, player_id):
        # check if this is us - if so send our hand, otherwise send empty
        hand_cards = []
        if self.ID == player_id:
            hand_cards = self.hand
        face_down_cards = []
        face_down_cards.extend([Card(0, 1)
                                for i in range(len(self.face_down))])
        player_summary = {'player_id': self.ID,
                          'number_face_down': len(self.face_down),
                          'number_face_up': len(self.face_up),
                          'face_up_cards': self.face_up,
                          'number_in_hand': len(self.hand),
                          'face_down_cards': face_down_cards,
                          'hand_cards': hand_cards}
        return player_summary

    def persist_player_cards_to_database(self, deck=[], *args, database_connection, game_id, deck_type, trans_connection=None):
        """save a given deck"""
        # clear existing records
        result = False
        database_connection.execute("DELETE FROM player_game_cards WHERE player_id = :player_id AND card_type=:card_type AND game_id = :game_id",
                                    trans_connection=trans_connection,
                                    player_id=self.ID,
                                    card_type=deck_type,
                                    game_id=game_id)
        i = 0
        cards = []
        for card in deck:
            cards.append(
                f"({self.ID}, {game_id}, {deck_type}, {card.suit}, {card.rank}, {i})")
            i += 1
        if cards:
            cards = ", ".join(cards)
            result = database_connection.execute(
                f"INSERT INTO player_game_cards (player_id, game_id, card_type, card_suit, card_rank, card_sequence) VALUES {cards};",
                trans_connection=trans_connection)
        else:
            # no cards - return true
            result = True

        if not result:
            trans_connection.rollback()
            trans_connection.close()
            raise ValueError(
                f"error persisting cards for game_id '{game_id}' and player_id '{self.ID}' and card_type '{deck_type}''",)
        else:
            return result

    def persist_player_cards_to_database_orm(self, session, game_id, deck_type, deck=[], *args) :
        """save a given deck"""
        # clear existing records

        _ = session.query(Model_Player_Cards).\
        filter(Model_Player_Cards.player_id == self.ID).\
        filter(Model_Player_Cards.card_type == deck_type).\
        filter(Model_Player_Cards.game_id == game_id).\
        delete()


        i = 0
        player_cards = []
        for card in deck:
            player_cards.append(Model_Player_Cards(player_id = self.ID, game_id = game_id, card_type = deck_type, card_suit = card.suit, card_rank = card.rank, card_sequence = i) )
        if player_cards:
            session.add_all(player_cards)
        print(f"done persisting cards for game_id '{game_id}' and player_id '{self.ID}' and card_type '{deck_type}''")
        return

    def load_player_cards_orm(self, card_session, game_id, deck_type):
        print("about to use ORM to load cards for player ID " + str(self.ID) +
              " for game " + str(game_id) + " with type " + str(deck_type) + ".")

        
        cards = card_session.query(Model_Player_Cards).\
            filter(Model_Player_Cards.player_id == self.ID).\
            filter(Model_Player_Cards.card_type == deck_type).\
            filter(Model_Player_Cards.game_id == game_id)

        cards_to_return = []
        # if cards.count() > 0:
        cards_to_return.extend(
            [Card(card.card_suit, card.card_rank) for card in cards])
        print("returning " + str(len(cards_to_return)) + ' cards')

        
        return cards_to_return

    def save(self, database_connection, game_id, trans_connection=None):
        """saves the current player's game state, including registering this player as playing this game"""
        print("saving player:", jsonpickle.dumps(self, unpicklable=False))
        player_session = common_db.Common_DB().common_Session()
        self.persist_player_cards_to_database_orm(player_session, game_id, Card_Types.CARD_FACE_DOWN, self.face_down)
        self.persist_player_cards_to_database_orm(player_session, game_id, Card_Types.CARD_FACE_UP, self.face_up)
        self.persist_player_cards_to_database_orm(player_session, game_id, Card_Types.CARD_HAND, self.hand)

        this_player_game = player_session.query(Model_Player_Game).filter(Model_Player_Game.player_id == self.ID).filter(Model_Player_Game.game_id == game_id).first()
        this_player_game = Model_Player_Game(player_id = self.ID, game_id = game_id)
        player_session.add(this_player_game)
        print("about to commit")
        player_session.commit()
        print("committed")
        return

    def save_old(self, database_connection, game_id, trans_connection=None):
        """saves the current player's game state, including registering this player as playing this game"""
        print("saving player:", jsonpickle.dumps(self, unpicklable=True))
        self.persist_player_cards_to_database(self.face_down,
                                              database_connection=database_connection,
                                              trans_connection=trans_connection,
                                              game_id=game_id,
                                              deck_type=Card_Types.CARD_FACE_DOWN)
        self.persist_player_cards_to_database(self.face_up,
                                              database_connection=database_connection,
                                              trans_connection=trans_connection,
                                              game_id=game_id,
                                              deck_type=Card_Types.CARD_FACE_UP)
        self.persist_player_cards_to_database(self.hand,
                                              database_connection=database_connection,
                                              trans_connection=trans_connection,
                                              game_id=game_id,
                                              deck_type=Card_Types.CARD_HAND)

        database_connection.execute('INSERT INTO player_game (player_id, game_id) VALUES (:user_id, :game_id) ON CONFLICT (player_id, game_id) DO UPDATE SET player_id = :user_id, game_id = :game_id',
                                    trans_connection=trans_connection,
                                    user_id=self.ID,
                                    game_id=game_id)
        return

    def load(self, database_connection, game_id):
        """loads the cards for each card type for the current player"""
        if not self.ID:
            raise ValueError('tried to load game without setting a player ID.')
        card_session = common_db.Common_DB().common_Session()
        print("loading cards...")
        self.face_down = self.load_player_cards_orm(card_session, game_id, Card_Types.CARD_FACE_DOWN)
        print("loaded face down")
        self.face_up = self.load_player_cards_orm(card_session, game_id, Card_Types.CARD_FACE_UP)
        print("loaded face up")
        self.hand = self.load_player_cards_orm(card_session, game_id, Card_Types.CARD_HAND)
        print("loaded hand")
        card_session.close()
        return

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

        return cards_to_play, play_cards
