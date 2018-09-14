from random import shuffle


class Card:
    """defines a playing card"""
    suits = {1: "hearts", 2: "diamonds", 3: "clubs", 4: "spades" }
    ranks = {2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine",
            10: "ten", 11: "jack", 12: "queen", 13: "king", 14: "ace"}

    def __init__(self, suit, rank):
        self.rank = rank
        self.suit = suit


    def __str__(self):
        """Return a description of the card name"""
        return ((Card.ranks[self.rank]) +  ' of ' + (Card.suits[self.suit]))


    def __lt__(self, other):
        """less than"""
        return self.rank < other.rank

    def __eq__(self, other):
        """equal to"""
        return self.rank == other.rank and self.suit == other.suit



class Deck:
    """defines a deck of playing cards.
       by default a new deck is shuffled but optionally can be empty"""
    def __init__(self, new_game = True, number_of_decks = 1):
        self.cards = []
        self.current = 0

        if (new_game):
            # we're asking for a newly shuffled deck for a new game
            for i in range(number_of_decks):
                self.cards.extend([Card(s,r) for s in Card.suits for r in Card.ranks])
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
            raise StopIteration
        else:
            card = self.cards[self.current]
            self.current += 1
            return card

