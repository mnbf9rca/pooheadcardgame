from sqlalchemy import (TIMESTAMP, Boolean, Column, ForeignKey, Integer,
                        String, Sequence)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, subqueryload

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
        return f"<User(id='{self.player_id}', username='{self.username}' name='{self.player_name}', last_played_at='{self.last_played_at}', is_admin='{self.is_admin}')>"

class Model_Player_Game(Base):
    __tablename__ = 'player_game'
    player_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, primary_key=True)

    def __repr__(self):
        return f"<Player ID: {self.player_id} is in game {self.game_id}>"

class Model_Card(Base):
    __tablename__ = 'game_cards'
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('games.gameid'))
    player_id = Column(Integer, ForeignKey('users.player_id'))
    card_location = Column(Integer)
    card_suit = Column(Integer)
    card_rank = Column(Integer)
    card_sequence = Column(Integer)
    belongs_to_game = relationship("Model_Game", back_populates='game_cards')

    def __repr__(self):
        return f"<Card(game_id='{self.game_id}', card_location='{self.card_location}', player_id='{self.player_id}', rank='{self.card_rank}', suit='{self.card_suit}')>"

class Model_Game(Base):
    __tablename__ = 'games'
    gameid = Column(Integer, primary_key=True)
    less_than_card = Column(Integer)
    transparent_card = Column(Integer)
    burn_card = Column(Integer)
    reset_card = Column(Integer)
    number_of_decks = Column(Integer)
    number_face_down_cards = Column(Integer)
    number_hand_cards = Column(Integer)
    current_turn_number = Column(Integer)
    last_player = Column(Integer)
    players_ready_to_start = Column(String)
    play_order = Column(String)
    play_on_anything_cards = Column(String)
    players_finished = Column(String)
    game_checksum = Column(String)
    players_requested = Column(Integer)
    game_ready_to_start = Column(Boolean)
    game_finished = Column(Boolean)
    deal_done = Column(Boolean)
    game_cards = relationship("Model_Card", back_populates="belongs_to_game")
    

    def __depr__(self):
        return (f"<game(game_id='{self.gameid}', "
                "less_than_card='{self.less_than_card}', "
                "transparent_card='{self.transparent_card}', "
                "burn_card='{self.burn_card}', "
                "reset_card={self.reset_card}', " 
                "number_of_decks='{self.number_of_decks}', "
                "number_face_down_cards='{self.number_face_down_cards}', "
                "number_hand_cards='{self.number_hand_cards}', "
                "current_turn_number='{self.current_turn_number}', "
                "last_player='{self.last_player}', "
                "players_ready_to_start='{self.players_ready_to_start}', "
                "play_order='{self.play_order}', "
                "play_on_anything_cards='{self.play_on_anything_cards}', "
                "players_finished='{self.players_finished}', "
                "game_checksum='{self.game_checksum}', "
                "players_requested='{self.players_requested}', "
                "game_ready_to_start='{self.game_ready_to_start}', "
                "game_finished='{self.game_finished}', "
                "deal_done='{self.deal_done}')>")
