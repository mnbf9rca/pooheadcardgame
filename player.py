from cards import Card_Types, Card

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
        face_down_cards.extend([Card(0,1) for i in range(len(self.face_down))])
        player_summary = { 'player_id': self.ID,
                            'number_face_down':len(self.face_down),
                            'number_face_up':len(self.face_up),
                            'face_up_cards':self.face_up,
                            'number_in_hand':len(self.hand),
                            'face_down_cards' : face_down_cards,
                            'hand_cards':hand_cards}
        return player_summary

    def persist_player_cards_to_database(self, deck = [], *args, database_connection, game_id, deck_type):
        """save a given deck"""
        # clear existing records
        result = database_connection.execute("DELETE FROM player_game_cards WHERE player_id = :player_id AND card_type=:card_type AND game_id = :game_id",
                                            player_id = self.ID,
                                            card_type = deck_type,
                                            game_id = game_id)
        # if not result == None:
        #     raise ValueError(f"error clearing cards for game_id '{game_id}' and player_id '{self.ID}' and card_type '{deck_type}' to database")

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
            if not(result):
                raise ValueError(f"error persisting cards for game_id '{game_id}' and player_id '{self.ID}' and card_type '{deck_type}' and card_suit '{card.suit}' and card_rank '{card.rank}' at sequence '{i}' to database")
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
        """saves the current player's gamew state, including registering this player as playing this game"""
        self.persist_player_cards_to_database(self.face_down, database_connection = database_connection, game_id = game_id, deck_type = Card_Types.CARD_FACE_DOWN)
        self.persist_player_cards_to_database(self.face_up, database_connection = database_connection, game_id = game_id, deck_type = Card_Types.CARD_FACE_UP)
        self.persist_player_cards_to_database(self.hand, database_connection = database_connection, game_id = game_id, deck_type = Card_Types.CARD_HAND)
        database_connection.execute('INSERT OR REPLACE INTO player_game (player_id, game_id) VALUES (:user_id, :game_id)',
                            user_id= self.ID,
                            game_id = game_id)
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