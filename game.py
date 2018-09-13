from cards import Card, Deck

class Player:
    def __init__(self, name):
        self.name = name
        self.face_down = []
        self.face_up = []
        self.hand = []


class Game:

    pile_types = {1: "burn pile", 2: "pick stack", 3: "played cards", 4: "deck"}
    pile_types_inverse = {"burn": 1, "pick": 2, "played": 3, "deck": 4}

    def __init__(self, player_names):

        #players
        self.numer_of_players = len(player_names)
        self.players = []
        for name in player_names:
            player = Player(name)
            self.players.append(player)

        #game config
        self.game_id = None
        self.less_than_card = 7
        self.transparent_card = None
        self.burn_card = 10
        self.reset_card = 2
        self.number_of_decks = 1
        self.number_face_down_cards = 3
        self.number_hand_cards = 3

        # piles
        self.burn_pile = []
        self.pick_stack = []
        self.played_cards = []
        self.deck = []

        # game state
        self.current_turn_number = 0
        self.last_player = None
        self.play_list = []

    '''creates a new deck of cards, deals to each player, then puts the remaining cards in the pick stack'''
    def deal(self):
        self.deck = Deck()

        # although cards are shuffled and so it doesnt really matter
        # follow convention and deal face down, then face up, then hand cards
        for deal in range(self.number_face_down_cards):
            for player in self.players:
                player.face_down.append(self.deck.deal())

        # number face down cards = number face up cards
        for deal in range(self.number_face_down_cards):
            for player in self.players:
                player.face_up.append(self.deck.deal())

        # hand cards
        for deal in range(self.number_hand_cards):
            for player in self.players:
                player.hand.append(self.deck.deal())