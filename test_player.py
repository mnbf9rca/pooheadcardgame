import json

import jsonpickle
import pytest

import cards
import player


@pytest.fixture
def three_cards():
    c = [cards.Card(1,4), cards.Card(2,3), cards.Card(3,3)]
    return c

@pytest.fixture
def test_player_one_card_each_deck(three_cards):
    p = player.Player(1)
    p.add_cards_to_player_cards([three_cards[0]], cards.Card_Types.CARD_FACE_DOWN)
    p.add_cards_to_player_cards([three_cards[1]], cards.Card_Types.CARD_FACE_UP)
    p.add_cards_to_player_cards([three_cards[2]], cards.Card_Types.CARD_HAND)
    return p


def test_which_cards_has_three(test_player_one_card_each_deck):
    '''test which cards a player can play when they have 3 cards'''
    p = test_player_one_card_each_deck
    c = [cards.Card(1,4), cards.Card(2,3), cards.Card(3,3)]
    c_face_down = [c[0]]
    c_face_up = [c[1]]
    c_hand = [c[2]]
 

    cards_to_play, play_cards = p.which_player_cards_can_player_use()
 
    errors = []

    if play_cards != list(c_hand):
        errors.append(f"cards_to_play != c_hand: {cards_to_play}, {c_hand}")
    if cards_to_play != cards.Card_Types.CARD_HAND:
        errors.append(f"play_cards != cards.Card_Types.CARD_HAND: {cards_to_play} (cards.Card_Types.CARD_HAND = {cards.Card_Types.CARD_HAND}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_which_cards_has_two(test_player_one_card_each_deck):
    # TODO what is this doing??
    p = test_player_one_card_each_deck
    c = [cards.Card(1,4), cards.Card(2,3), cards.Card(3,3)]
    c_face_down = [c[0]]
    c_face_up = [c[1]]
    c_hand = [c[2]]
    p.remove_cards_from_player_cards(c_hand, cards.Card_Types.CARD_HAND)

    cards_to_play, play_cards = p.which_player_cards_can_player_use()

    errors = []
    if play_cards != list(c_face_up):
        errors.append(f"cards_to_play != c_face_up: {cards_to_play}, {c_face_up}")
    if cards_to_play != cards.Card_Types.CARD_FACE_UP:
        errors.append(f"play_cards != cards.Card_Types.CARD_FACE_UP: {cards_to_play} (cards.Card_Types.CARD_FACE_UP = {cards.Card_Types.CARD_FACE_UP}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_which_cards_has_only_face_down(test_player_one_card_each_deck):
    '''which cards can the player play when they only have face down cards'''
    p = test_player_one_card_each_deck
    c = [cards.Card(1,4), cards.Card(2,3), cards.Card(3,3)]
    c_face_down = [c[0]]
    c_face_up = [c[1]]
    c_hand = [c[2]]
    p.remove_cards_from_player_cards(c_hand, cards.Card_Types.CARD_HAND)
    p.remove_cards_from_player_cards(c_face_up, cards.Card_Types.CARD_FACE_UP)
    cards_to_play, play_cards = p.which_player_cards_can_player_use()
    errors = []
    if play_cards != list(c_face_down):
        errors.append(f"cards_to_play != c_face_down: {cards_to_play}, {c_face_down}")
    if cards_to_play != cards.Card_Types.CARD_FACE_DOWN:
        errors.append(f"play_cards != cards.Card_Types.CARD_FACE_DOWN: {cards_to_play} (cards.Card_Types.CARD_FACE_DOWN = {cards.Card_Types.CARD_FACE_DOWN}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_which_cards_has_no_cards(test_player_one_card_each_deck):
    '''test which cards they can play when they have no cards left??'''
    p = test_player_one_card_each_deck
    c = [cards.Card(1,4), cards.Card(2,3), cards.Card(3,3)]
    c_face_down = [c[0]]
    c_face_up = [c[1]]
    c_hand = [c[2]]
    p.remove_cards_from_player_cards(c_hand, cards.Card_Types.CARD_HAND)
    p.remove_cards_from_player_cards(c_face_up, cards.Card_Types.CARD_FACE_UP)
    p.remove_cards_from_player_cards(c_face_down, cards.Card_Types.CARD_FACE_DOWN)
    cards_to_play, play_cards = p.which_player_cards_can_player_use()
    errors = []
    #TODO these checks are wrong...
    if play_cards != []:
        errors.append(f"cards_to_play != c_face_down: {cards_to_play}, {c_face_down}")
    if cards_to_play != cards.Card_Types.CARD_NONE:
        errors.append(f"play_cards != cards.Card_Types.CARD_NONE: {cards_to_play} (cards.Card_Types.CARD_NONE = {cards.Card_Types.CARD_NONE}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_add_card(test_player_one_card_each_deck):
    '''check that we can add cards to a player ok'''
    p = test_player_one_card_each_deck
    # https://stackoverflow.com/questions/40382487/copy-a-list-of-list-by-value-and-not-reference/40382592
    c_face_down = getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_FACE_DOWN])[:]
    c_face_up  = getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_FACE_UP])[:]
    c_hand =  getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_HAND])[:]

    c = [cards.Card(2,4), cards.Card(4,3), cards.Card(3,4)]
    
    p.add_cards_to_player_cards(c, cards.Card_Types.CARD_FACE_DOWN)
    p.add_cards_to_player_cards(c, cards.Card_Types.CARD_FACE_UP)
    p.add_cards_to_player_cards(c, cards.Card_Types.CARD_HAND)

    errors = []

    if getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_FACE_DOWN]) != c_face_down + c:
        errors.append(f"cards.Card_Types.CARD_FACE_DOWN != c_face_down + c - player: {getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_FACE_DOWN])}, expected {c_face_down + c}")
    if getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_FACE_UP]) != c_face_up + c:
        errors.append(f"cards.Card_Types.PLAYER_FACE_UP != c_face_up + c - player: {getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_FACE_UP])}, expected {c_face_up + c}")
    if getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_HAND]) != c_hand + c:
        errors.append(f"cards.Card_Types.PLAYER_HAND != c_hand + c - player: {getattr(p, p.Pile_Objects[p.Card_Pile_ID.PLAYER_HAND])}, expected {c_hand + c}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))
    
def test_get_cards_returns_correct_card(test_player_one_card_each_deck):
    p = test_player_one_card_each_deck
    c = [cards.Card(1,4), cards.Card(2,3), cards.Card(3,3)]
    c_face_down = [c[0]]
    c_face_up = [c[1]]
    c_hand = [c[2]]
    errors = []
    if p.get_cards(cards.Card_Types.CARD_FACE_DOWN) != list(c_face_down):
        errors.append(f"p.get_cards(cards.Card_Types.CARD_FACE_DOWN) != list(c_face_down): {p.get_cards(cards.Card_Types.CARD_FACE_DOWN)} (c_face_down = {c_face_down}")
    if p.get_cards(cards.Card_Types.CARD_FACE_UP) != list(c_face_up):
        errors.append(f"p.get_cards(cards.Card_Types.CARD_FACE_UP) != list(c_face_up): {p.get_cards(cards.Card_Types.CARD_FACE_UP)} (c_face_up = {c_face_up}")
    if p.get_cards(cards.Card_Types.CARD_HAND) != list(c_hand):
        errors.append(f"p.get_cards(cards.Card_Types.CARD_HAND) != list(c_hand): {p.get_cards(cards.Card_Types.CARD_HAND)} (c_hand = {c_hand}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_player_correctly_summarised(test_player_one_card_each_deck):
    p = test_player_one_card_each_deck
    expected_summary = '{"face_down_cards": [{"rank": 1, "suit": 0}], '\
                        '"face_up_cards": [{"rank": 3, "suit": 2}], '\
                        '"hand_cards": [{"rank": 3, "suit": 3}], '\
                        '"number_face_down": 1, '\
                        '"number_face_up": 1, '\
                        '"number_in_hand": 1, '\
                        '"player_id": 1}'
                        
    assert jsonpickle.encode(p.summarise(1), unpicklable=False) == expected_summary
