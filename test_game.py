import pytest
import jsonpickle
import json

import game
import player
import cards

@pytest.fixture
def three_cards():
    c = [cards.Card(1,4), cards.Card(2,3), cards.Card(3,3)]
    return c

@pytest.fixture
def standard_request_json():
    standard_request = '[{"name":"less_than_card","value":"7"},'\
                        '{"name":"transparent_card","value":"None"},'\
                        '{"name":"transparent_card_on_anything","value":"on"},'\
                        '{"name":"burn_card","value":"10"},'\
                        '{"name":"burn_card_on_anything","value":"on"},'\
                        '{"name":"reset_card","value":"2"},'\
                        '{"name":"reset_card_on_anything","value":"on"},'\
                        '{"name":"number-face-down","value":"3"},'\
                        '{"name":"number-hand","value":"3"},'\
                        '{"name":"number_of_players_requested","value":"2"},'\
                        '{"name":"number-of-decks","value":"1"},'\
                        '{"name":"new","value":"1"}]'
    return json.loads(standard_request)

@pytest.fixture
def game_with_three_players():
    g = game.Game(this_player_id=1, number_of_players = 3)
    for id in range(2, 4):
        g.add_player(player.Player(id))
    return g

@pytest.fixture
def game_three_players_one_card_each(game_with_three_players, three_cards):
    g = game_with_three_players
    g.state.deal_done = True
    g.state.game_ready_to_start = True
    player_cards = three_cards
    for player in g.players:
        player.face_down = [player_cards.pop()]
    return g

def test_can_create_game_with_no_players():
    assert len(game.Game().players) == 0

def test_can_create_game_with_three_players(game_with_three_players):
    game = game_with_three_players
    assert len(game.players) == 3

def test_first_player_plays_last_card(game_three_players_one_card_each):
    g = game_three_players_one_card_each
    expected_card = [g.this_player.face_down[0]]
    g.state.play_order = [1,2,3]
    g.state.players_ready_to_start = [1,2,3]
    move_to_play = ["d-0"]
    play = g.play_move(move_to_play)
    errors = []
    if len(g.cards.pile_played) != 1:
        errors.append(f"len(g.cards.pile_played) not equal to 1, actual length: {len(g.cards.pile_played)}")
    elif g.cards.pile_played != expected_card:
        errors.append(f"g.cards.pile_played != {str(expected_card)}: actual card was {str(g.cards.pile_played[0])}")
    if 1 in g.state.play_order:
        errors.append(f"player 1 still exists in play order: {g.state.play_order}")
    if not g.state.play_order == [2,3]:
        errors.append(f"play order doesnt equal [2, 3]: {g.state.play_order}")
    if not 1 in g.state.players_finished:
        errors.append(f"player 1 not in g.state.players_finished: {g.state.players_finished}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_second_player_plays_last_card_and_one_player_left(game_three_players_one_card_each):
    g = game_three_players_one_card_each
    expected_card = [g.this_player.face_down[0]]
    g.state.play_order = [1,2,3]
    g.state.players_ready_to_start = [1,2,3]
    move_to_play = ["d-0"]
    play = g.play_move(move_to_play)
    # now move to 2nd player
    for p in g.players:
        if p.ID == 2:
            g.this_player = p
            g.state.this_player_id = 2
    expected_card.append(g.this_player.face_down[0])
    play = g.play_move(move_to_play)
    
    errors = []
    if not play["action_result"]:
        errors.append(f"error from game.play_move: {play}")

    if len(g.cards.pile_played) != 2:
        errors.append(f"g.cards.pile_played not equal to 2, actual length {len(g.cards.pile_played)}")
    elif g.cards.pile_played != expected_card:
        errors.append(f"g.cards.pile_played != {[str(c) for c in expected_card]}: actual card was {[str(c) for c in g.cards.pile_played]}")
    if 2 in g.state.play_order:
        errors.append(f"player 2 still exists in play order: {jsonpickle.encode(g.state.play_order)}")
    if not g.state.play_order == [3]:
        errors.append(f"play order doesnt equal [3]: {g.state.play_order}")
    if not 2 in g.state.players_finished:
        errors.append(f"player 2 not in g.state.players_finished: {g.state.players_finished}")
    if not g.state.game_finished:
        errors.append(f"g.state.finished != True")
    if not g.state.play_order == [3]:
        errors.append(f"play order doesnt equal [3]: {self.state.play_order}")
    print(jsonpickle.encode(g, unpicklable=False))
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_create_new_game_from_request_json(standard_request_json):
    g = game.Game(1)
    print(standard_request_json)
    parsed_values, message = g.parse_requested_config(standard_request_json)
    errors = []
    if not parsed_values:
        errors.append(f"can't parse values: {message}")
    if g.state.less_than_card != 7:
        errors.append(f"less_than_card not 7: {g.state.less_than_card }")
    if g.state.less_than_card !=0 and g.state.less_than_card in g.state.play_on_anything_cards:
        errors.append(f"less_than_card '{g.state.less_than_card}' in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.transparent_card != 0:
        errors.append(f"transparent_card not 0: {g.state.transparent_card}")
    if g.state.transparent_card != 0 and not g.state.transparent_card in g.state.play_on_anything_cards:
        errors.append(f"transparent_card '{g.state.transparent_card}' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.burn_card != 10:
        errors.append(f"burn_card != 10: {g.state.burn_card}")
    if  g.state.burn_card != 0 and not g.state.burn_card in g.state.play_on_anything_cards:
        errors.append(f"burn_card '{g.state.burn_card}' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.reset_card != 2:
        errors.append(f"reset_card != 2: {g.state.reset_card }")
    if g.state.reset_card !=0 and not g.state.reset_card in g.state.play_on_anything_cards:
        errors.append(f"reset_card '{g.state.reset_card }' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if 0 in g.state.play_on_anything_cards:
        errors.append(f"0 in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.number_face_down_cards != 3:
        errors.append(f"number_face_down_cards != 3: {g.state.number_face_down_cards}")
    if g.state.number_hand_cards != 3:
        errors.append(f"number_hand_cards != 3: {g.state.number_hand_cards}")
    if g.state.number_of_players_requested != 2:
        errors.append(f"number_of_players_requested != 2: {g.state.number_of_players_requested}")
    if g.state.number_of_decks!= 1:
        errors.append(f"number_of_decks != 1: {g.state.number_of_decks}")
    if g.state.players_ready_to_start != []:
        errors.append(f"players_ready_to_start != []: {g.state.players_ready_to_start}")
    if g.state.players_finished != []:
        errors.append(f"layers_finished != []: {g.state.players_finished}")
    if g.state.deal_done != False:
        errors.append(f"deal_done != false: {g.state.deal_done}")
    if g.state.play_list != []:
        errors.append(f"play_list != []: {g.state.play_list}")
    if g.state.number_of_players_joined != 1:
        errors.append(f"number_of_players_joined != 1: {g.state.number_of_players_joined}")
    if g.state.game_finished != False:
        errors.append(f"game_finished != false: {g.state.game_finished}")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))
