from random import shuffle

'''defines a playing card'''
class Card:

    suits = {1: "hearts", 2: "diamonds", 3: "clubs", 4: "spades" }
    ranks = {2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine",
            10: "ten", 11: "jack", 12: "queen", 13: "king", 14: "ace"}

    def __init__(self, suit, rank):
        self.rank = rank
        self.suit = suit

    '''Return a description of the card name'''
    def __str__(self):
        return ((Card.ranks[self.rank]) +  ' of ' + (Card.suits[self.suit]))

    '''less than'''
    def __lt__(self, other):
        return self.rank < other.rank

    '''equal to'''
    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit


'''defines a deck of playing cards, by default shuffled'''
class Deck:
    def __init__(self, new_game = True, number_of_decks = 1):
        self.cards = []
        self.current = 0

        if (new_game):
            # we're asking for a newly shuffled deck for a new game
            for i in range(number_of_decks):
                self.cards.extend([Card(s,r) for s in Card.suits for r in Card.ranks])
            self.shuffle()

    '''shuffle the current deck'''
    def shuffle(self):
        shuffle(self.cards)

    '''deal one card'''
    def deal(self):
        card = self.cards.pop()
        return card

    '''return len = how many cards left in deck'''
    def __len__(self):
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

