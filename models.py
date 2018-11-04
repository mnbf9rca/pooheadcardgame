from sqlalchemy import (TIMESTAMP, Boolean, Column, ForeignKey, Integer,
                        String, Sequence, UniqueConstraint)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, subqueryload
from sqlalchemy.sql.expression import false as sql_false

Base = declarative_base()

class Model_Player(Base):
    __tablename__ = 'users'
    player_id = Column(Integer, primary_key=True)
    player_name = Column(String)
    last_played_at = Column(TIMESTAMP(timezone=False))
    hash = Column(String)
    username = Column(String)
    is_admin = Column(Boolean, server_default=sql_false())

class Model_Player_Game(Base):
    __tablename__ = 'player_game'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer)
    game_id = Column(Integer)
    __table_args__ = (UniqueConstraint('player_id', 'game_id', name='uix_player_game'),)

class Model_Card(Base):
    __tablename__ = 'game_cards'
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('games.gameid'))
    player_id = Column(Integer, ForeignKey('users.player_id'))
    card_location = Column(Integer)
    card_suit = Column(Integer)
    card_rank = Column(Integer)
    belongs_to_game = relationship("Model_Game", back_populates='game_cards')

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
