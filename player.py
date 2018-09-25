from cards import Card_Types, Card
import jsonpickle


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

    def persist_player_cards_to_database(self, deck=[], *args, database_connection, trans_connection=None, game_id, deck_type):
        """save a given deck"""
        # clear existing records
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
        cards = ", ".join(cards)
        result = database_connection.execute(
            f"INSERT INTO player_game_cards (player_id, game_id, card_type, card_suit, card_rank, card_sequence) VALUES {cards};", 
            trans_connection=trans_connection)

        if result:
            raise ValueError(
                f"error persisting cards for game_id '{game_id}' and player_id '{self.ID}' and card_type '{deck_type}''")
        else:
            return result

    def load_player_cards(self, database_connection, game_id, deck_type):
        print("about to load cards for player ID " + str(self.ID) +
              " for game " + str(game_id) + " with type " + str(deck_type) + ".")
        cards = database_connection.execute("SELECT card_suit, card_rank FROM player_game_cards WHERE player_id = :player_id AND card_type = :card_type AND game_id = :game_id ORDER BY card_rank, card_suit ASC",
                                            player_id=self.ID,
                                            card_type=deck_type,
                                            game_id=game_id)
        cards_to_return = []
        if len(cards) > 0:
            cards_to_return.extend(
                [Card(card["card_suit"], card["card_rank"]) for card in cards])
        print("returning " + str(len(cards_to_return)))
        return cards_to_return

    def save(self, database_connection, game_id, trans_connection=None):
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
        database_connection.execute('REPLACE INTO player_game (player_id, game_id) VALUES (:user_id, :game_id)',
                                    trans_connection=trans_connection,
                                    user_id=self.ID,
                                    game_id=game_id)
        return

    def load(self, database_connection, game_id):
        """loads the cards for each card type for the current player"""
        if not self.ID:
            raise ValueError('tried to load game without setting a player ID.')

        print("loading cards...")
        self.face_down = self.load_player_cards(
            database_connection, game_id, Card_Types.CARD_FACE_DOWN)
        print("loaded face down")
        self.face_up = self.load_player_cards(
            database_connection, game_id, Card_Types.CARD_FACE_UP)
        print("loaded face up")
        self.hand = self.load_player_cards(
            database_connection, game_id, Card_Types.CARD_HAND)
        print("loaded hand")
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
