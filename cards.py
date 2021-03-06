from random import shuffle


class Card_Types(object):
    CARD_FACE_DOWN = 1
    CARD_FACE_UP = 2
    CARD_HAND = 3
    CARD_NONE = 4
    CARD_BURN = 5
    CARD_DECK = 6
    CARD_PLAYED = 7
    CARD_PICK = 8
    
    Long_Name = {CARD_FACE_DOWN: "face down",
                 CARD_FACE_UP: "face up",
                 CARD_HAND: "hand",
                 CARD_NONE: "none"}
    Short_Name = {CARD_FACE_DOWN: "d",
                  CARD_FACE_UP: "f",
                  CARD_HAND: "h",
                  CARD_NONE: "n"}
                  
    Card_Type_From_Code = {"d": CARD_FACE_DOWN,
                           "f": CARD_FACE_UP,
                           "h": CARD_HAND,
                           "n": CARD_NONE}

    def __init__(self):
        return



class Card(object):
    """defines a playing card"""

    suits = {1: "hearts", 2: "diamonds", 3: "clubs", 4: "spades"}
    suits_short = {0: "B", 1: "H", 2: "D", 3: "C", 4: "S"}
    ranks = {2: "two", 3: "three", 4: "four", 5: "five",
             6: "six", 7: "seven", 8: "eight", 9: "nine",
             10: "ten", 11: "jack", 12: "queen", 13: "king", 14: "ace"}
    rank_short = {10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}

    def __init__(self, suit, rank):
        self.rank = rank
        self.suit = suit

    def __hash__(self):
        return(hash(str(self)))

    def same_rank(self, other):
        return self.rank == other.rank

    def describe(self):
        """callable to provide a string description of the card"""
        return str(self)

    def card_key(self):
        """returns a 2 character key for the card"""
        card_rank = self.rank
        if card_rank > 9:
            card_rank = Card.rank_short[card_rank]
        card_image_name = str(card_rank) + Card.suits_short[self.suit]
        return str(card_image_name)

    def __str__(self):
        """Return a description of the card name"""
        if self.rank == 1 and self.suit == 0:
            return "Back of card"
        else:
            return ((Card.ranks[self.rank]) + ' of ' + (Card.suits[self.suit]))

    def __lt__(self, other):
        """less than"""
        return self.rank < other.rank

    def __eq__(self, other):
        """equal to"""
        return self.rank == other.rank and self.suit == other.suit


class Deck(object):
    """defines a deck of playing cards.
       by default a new deck is shuffled but optionally can be empty"""

    def __init__(self, newgame=True, number_of_decks=1):
        self.cards = []
        self.current = 0

        if (newgame):
            # we're asking for a newly shuffled deck for a new game
            for _ in range(number_of_decks):
                self.cards.extend([Card(s, r) for s in Card.suits for r in Card.ranks])
            self.shuffle()

    def shuffle(self):
        """shuffle the current deck"""
        shuffle(self.cards)

    def deal(self):
        """deal one card, returning the card and removing it from the deck"""
        card = self.cards.pop()
        return card

    def __len__(self):
        """return len = how many cards left in deck"""
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)

    def __next__(self):
        if self.current < len(self.cards):
            self.current = 0
            raise StopIteration
        else:
            card = self.cards[self.current]
            self.current += 1
            return card
