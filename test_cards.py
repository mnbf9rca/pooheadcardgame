import pytest

import cards


@pytest.fixture
def all_cards_sorted():
    import cards
    return [cards.Card(s, r) for s in range(4) for r in range(13)]

def test_card_types():
    # these keys are critical to ensuring that the right cards
    # are restored to the correct place in the DB and game state
    # so we need to check that teh values dont get changed
    card_types = cards.Card_Types()
    errors = []
    if card_types.CARD_FACE_DOWN != 1:
        errors.append("card_types.CARD_FACE_DOWN != 1")
    if card_types.CARD_FACE_UP != 2:
        errors.append("card_types.CARD_FACE_UP != 2")
    if card_types.CARD_HAND != 3:
        errors.append("card_types.CARD_HAND != 3")
    if card_types.CARD_NONE != 4:
        errors.append("card_types.CARD_NONE != 4")
    if card_types.CARD_BURN != 5:
        errors.append("card_types.CARD_BURN != 5")
    if card_types.CARD_DECK != 6:
        errors.append("card_types.CARD_DECK != 6")
    if card_types.CARD_PLAYED != 7:
        errors.append("card_types.CARD_PLAYED != 7")
    if card_types.CARD_PICK != 8:
        errors.append("card_types.CARD_PICK != 8")        
    
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_same_rank():
    card1 = cards.Card(2,9)
    card2 = cards.Card(3,9)
    assert card1.same_rank(card2) == True

def test_card_equals():
    card1 = cards.Card(2,5)
    card2 = cards.Card(2,5)
    assert card1 == card2

def test_card_not_equals():
    card1 = cards.Card(2,5)
    card2 = cards.Card(2,6)
    assert card1 != card2

def test_six_less_than_seven():
    card1 = cards.Card(3,6)
    card2 = cards.Card(3,7)
    assert card1 < card2

def test_card_keys(all_cards_sorted):
    expected_result = ['0B', '1B', '2B', '3B', '4B', 
                        '5B', '6B', '7B', '8B', '9B', 
                        'TB', 'JB', 'QB', '0H', '1H', 
                        '2H', '3H', '4H', '5H', '6H', 
                        '7H', '8H', '9H', 'TH', 'JH', 
                        'QH', '0D', '1D', '2D', '3D', 
                        '4D', '5D', '6D', '7D', '8D', 
                        '9D', 'TD', 'JD', 'QD', '0C', 
                        '1C', '2C', '3C', '4C', '5C', 
                        '6C', '7C', '8C', '9C', 'TC', 
                        'JC', 'QC']
    card_keys = [card.card_key() for card in all_cards_sorted]
    assert expected_result == card_keys

def test_one_deck_length():
    d = cards.Deck(newgame=True, number_of_decks=1)
    assert len(d) == 52

def test_two_deck_length():
    d = cards.Deck(newgame=True, number_of_decks=2)
    assert len(d) == 104

def test_new_deck_is_shuffled(all_cards_sorted):
    d = cards.Deck(newgame=True, number_of_decks=1)
    sorted_all_card_keys = [card.card_key() for card in all_cards_sorted]
    deck_all_card_keys = [card.card_key() for card in d.cards]
    assert sorted_all_card_keys != deck_all_card_keys
