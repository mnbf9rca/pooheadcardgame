from cards import Card_Types, Card

class Player:
    def __init__(self, ID):
        self.name = ""
        self.ID = ID
        self.face_down = []
        self.face_up = []
        self.hand = []

    def persist_player_cards_to_database(self, deck = [], *args, database_connection, game_id, deck_type):
        """save a given deck"""
        # clear existing records
        result = database_connection.execute("DELETE FROM player_game_cards WHERE player_id = :player_id AND card_type=:card_type AND game_id = :game_id",
                                            player_id = self.ID,
                                            card_type = deck_type,
                                            game_id = game_id)
        # persist each card
        i = 0
        for card in deck:
            result = database_connection.execute("INSERT INTO player_game_cards (player_id, game_id, card_type, card_suit, card_rank, card_sequence) VALUES (:player_id, :game_id, :card_type, :card_suit, :card_rank, :card_sequence)",
                                                    player_id = self.ID,
                                                    game_id = game_id,
                                                    card_type = deck_type,
                                                    card_suit = card.suit,
                                                    card_rank = card.rank,
                                                    card_sequence = i)
            i += 1

    def load_player_cards(self, database_connection, game_id, deck_type):
        print("about to load cards for player ID " + str(self.ID) + " for game " + str(game_id) + " with type " + str(deck_type) + ".")
        cards = database_connection.execute("SELECT card_suit, card_rank FROM player_game_cards WHERE player_id = :player_id AND card_type = :card_type AND game_id = :game_id ORDER BY card_sequence ASC",
                                            player_id = self.ID,
                                            card_type = deck_type,
                                            game_id = game_id)
        cards_to_return = []
        if len(cards) > 0:
            cards_to_return.extend([Card(card["card_suit"],card["card_rank"]) for card in cards])
        print("returning " + str(len(cards_to_return)))
        return cards_to_return

    def save(self, database_connection, game_id):
        """saves the current player's cards"""
        self.persist_player_cards_to_database(self.face_down, database_connection = database_connection, game_id = game_id, deck_type = Card_Types.CARD_FACE_DOWN)
        self.persist_player_cards_to_database(self.face_up, database_connection = database_connection, game_id = game_id, deck_type = Card_Types.CARD_FACE_UP)
        self.persist_player_cards_to_database(self.hand, database_connection = database_connection, game_id = game_id, deck_type = Card_Types.CARD_HAND)
        return

    def load(self, database_connection, game_id):
        """loads the cards for each card type for the current player"""
        if not self.ID:
            raise ValueError('tried to load game without setting a player ID.')

        print("loading cards...")
        self.face_down = self.load_player_cards(database_connection, game_id, Card_Types.CARD_FACE_DOWN)
        print("loaded face down")
        self.face_up = self.load_player_cards(database_connection, game_id, Card_Types.CARD_FACE_UP)
        print ("loaded face up")
        self.hand = self.load_player_cards(database_connection, game_id, Card_Types.CARD_HAND)
        print("loaded hand")
        return