from cards import Card, Deck
from player import Player

def get_users_for_game(game_id, database_connection):
    """load the list of users playing a game"""
    players = database_connection.execute("SELECT player_id FROM player_game WHERE game_id = :game_id",
                                            game_id=game_id)
    list_of_players = []
    if len(players) > 0:
        list_of_players.extend([Player(player["player_id"]) for player in players])
    return list_of_players

def load_cards_from_database(deck_type, game_id, database_connection):
    """load a set of cards and return them in a sorted list"""
    cards = database_connection.execute("SELECT card_suit, card_rank FROM game_cards WHERE game_id = :game_id AND card_location = :deck_type ORDER BY card_sequence ASC",
            game_id = game_id, deck_type = deck_type)
    cards_to_return = []
    if len(cards) > 0:
        cards_to_return.extend([Card(card["card_suit"],card["card_rank"]) for card in cards])
#        for card in cards:
#            c = Card()
#            c.suit = card.card_suit
#            c.rank = card.card_rank
#            cards_to_return.append(c)
    return cards_to_return

def persist_cards_to_database(deck = [], *args, deck_type, game_id, database_connection):
    """persist a set of cards to the database as part of game state"""
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