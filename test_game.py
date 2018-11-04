import pytest
import jsonpickle
import json

import game
import player
import cards


@pytest.fixture
def three_cards():
    '''return a list of 3 specific cards'''
    c = [cards.Card(1, 4), cards.Card(2, 3), cards.Card(3, 3)]
    return c


@pytest.fixture
def standard_request_json():
    '''return a JSON which represents teh default when a user clicks new game'''
    standard_request = '[{"name":"less_than_card","value":"7"},'\
        '{"name":"transparent_card","value":"None"},'\
        '{"name":"transparent_card_on_anything","value":"on"},'\
        '{"name":"burn_card","value":"10"},'\
        '{"name":"burn_card_on_anything","value":"on"},'\
        '{"name":"reset_card","value":"2"},'\
        '{"name":"reset_card_on_anything","value":"on"},'\
        '{"name":"number_face_down_cards","value":"3"},'\
        '{"name":"number_hand_cards","value":"3"},'\
        '{"name":"number_of_players_requested","value":"2"},'\
        '{"name":"number_of_decks","value":"1"},'\
        '{"name":"new","value":"1"}]'
    print("standard_request", standard_request)
    return json.loads(standard_request)


@pytest.fixture
def nonstandard_request_json():
    '''return a non-standard JSON, with almost every value changed'''
    nonstandard_request = '[{"name":"less_than_card","value":"3"},'\
        '{"name":"less_than_card_on_anything","value":"on"},'\
        '{"name":"transparent_card","value":"5"},'\
        '{"name":"burn_card","value":"6"},'\
        '{"name":"burn_card_on_anything","value":"on"},'\
        '{"name":"reset_card","value":"9"},'\
        '{"name":"reset_card_on_anything","value":"on"},'\
        '{"name":"number_face_down_cards","value":"4"},'\
        '{"name":"number_hand_cards","value":"2"},'\
        '{"name":"number_of_players_requested","value":"5"},'\
        '{"name":"number_of_decks","value":"2"},'\
        '{"name":"new","value":"1"}]'
    print("nonstandard_request:", nonstandard_request)
    return json.loads(nonstandard_request)


@pytest.fixture
def game_with_three_players():
    '''create a game with 3 active players'''
    g = game.Game(this_player_id=1, number_of_players=3)
    for id in range(2, 4):
        g.add_player(player.Player(id))
    return g


@pytest.fixture
def game_three_players_one_card_each(game_with_three_players, three_cards):
    ''' return a game with 3 players, each of which has 1 face_down card left, 
        from three_cards fixture - P1 Card(1, 4), P2 Card(2, 3), P3 Card(3, 3)'''
    g = game_with_three_players
    g.state.deal_done = True
    g.state.game_ready_to_start = True
    player_cards = three_cards
    for player in g.players:
        player.face_down = [player_cards.pop()]
    return g

def swap_to_player(game, player_id):
    g = game
    if not player_id in [p.ID for p in g.players]:
        raise ValueError("Requested player ID not in game")
    else:
        i = 0
        while not g.this_player.ID == player_id:
            g.this_player = g.players[i]
            g.state.this_player_id = g.this_player.ID
            i += 1
    return g


def test_can_create_game_with_no_players():
    '''can create empty game'''
    assert len(game.Game().players) == 0


def test_can_create_game_with_three_players(game_with_three_players):
    '''do we get a game with 3 players'''
    game = game_with_three_players
    assert len(game.players) == 3


def test_cant_play_no_swap_twice(game_with_three_players):
    '''P1 plays no_swap then plays it again'''
    g = game_with_three_players
    g.state.play_order = [1, 2, 3]
    g.state.number_of_players_requested = 3
    g.deal()
    g.state.this_player_id = 1

    errors = []
    response = g.play_no_swap()
    # should be ok this time
    if not response['action_result']:
        errors.append(response['action_message'])
    response = g.play_no_swap()
    # should fail this time
    if response['action_result']:
        errors.append(response['action_message'])
    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_never_require_pick_up_cards_from_face_down(game_three_players_one_card_each):
    '''P1 should not be able to pick up when they only have face down cards'''
    # P1 Card(1, 4), P2 Card(2, 3), P3 Card(3, 3)
    hand_cards = [cards.Card(1, 4), cards.Card(2, 3), cards.Card(3, 3)]

    g = game_three_players_one_card_each
    g.players[1].hand.append(hand_cards.pop())
    g.players[2].face_up.append(hand_cards.pop())
    g.state.number_of_players_requested = 3
    g.state.deal_done = True
    g.state.ready_to_play = [1, 2, 3]
    g.state.players_ready_to_start = [1, 2, 3]
    # create a played pile which P1 cannot beat
    g.cards.pile_played = [cards.Card(3, 9)]
    print(jsonpickle.encode(g, unpicklable=False))

    g.state.play_order = [1, 2, 3]
    g.state.this_player_id = 1
    play_result = g.play_pick_up()
    print(play_result)
    # expecting this to be accepted as P1 can always play (only has a hand card left)

    assert not play_result['action_result'], f"play_pick_up succeeded even but should always play face down cards: {play_result['action_message']}"


def test_reject_pick_up_cards_when_can_beat_with_hand(game_three_players_one_card_each):
    '''P2 should not be able to pick up because they can beat the pile card'''
    # P1 Card(1, 4), P2 Card(2, 3), P3 Card(3, 3)
    hand_cards = [cards.Card(1, 4), cards.Card(2, 3), cards.Card(3, 3)]

    g = game_three_players_one_card_each
    g.players[1].hand.append(hand_cards.pop())
    g.players[2].face_up.append(hand_cards.pop())
    g.state.number_of_players_requested = 3
    g.state.deal_done = True
    g.state.ready_to_play = [1, 2, 3]
    g.state.players_ready_to_start = [1, 2, 3]
    # create a played pile which P2 can beat
    g.cards.pile_played = [cards.Card(3, 3)]
    print(jsonpickle.encode(g, unpicklable=False))

    errors = []
    g.state.play_order = [2, 3, 1]
    g = swap_to_player(g, 2)

    play_result = g.play_pick_up()
    print(play_result)
    # expecting this to be rejected as P2 can beat the card
            
    assert not play_result['action_result'], f"play_pick_up succeeded even though we can beat the card: {play_result['action_message']}"

def test_allow_pick_up_cards_when_cannot_beat_with_hand(game_three_players_one_card_each):
    '''P2 should not be able to pick up because they can beat the pile card'''
    # P1 Card(1, 4), P2 Card(2, 3), P3 Card(3, 3)
    hand_cards = [cards.Card(1, 4), cards.Card(2, 3), cards.Card(3, 3)]

    g = game_three_players_one_card_each
    g.players[1].hand.append(hand_cards.pop())
    g.players[2].face_up.append(hand_cards.pop())
    g.state.number_of_players_requested = 3
    g.state.deal_done = True
    g.state.ready_to_play = [1, 2, 3]
    g.state.players_ready_to_start = [1, 2, 3]
    # create a played pile which P2 can't beat
    g.cards.pile_played = [cards.Card(3, 9)]
    print(jsonpickle.encode(g, unpicklable=False))

    g.state.play_order = [2, 3, 1]
    g = swap_to_player(g, 2)
    play_result = g.play_pick_up()
    print(play_result)
    # expecting this to be rejected as P2 can beat the card
            
    assert play_result['action_result'], f"play_pick_up failed even though we can't beat it: {play_result['action_message']}"

def test_reject_pick_up_cards_when_cannot_beat_with_face_up(game_three_players_one_card_each):
    '''P2 should not be able to pick up because they can beat the pile card with a face up card'''
    # P1 Card(1, 4), P2 Card(2, 3), P3 Card(3, 3)
    hand_cards = [cards.Card(1, 4), cards.Card(2, 3), cards.Card(3, 3)]

    g = game_three_players_one_card_each
    g.players[1].hand.append(hand_cards.pop())
    g.players[2].face_up.append(hand_cards.pop())
    g.state.number_of_players_requested = 3
    g.state.deal_done = True
    g.state.ready_to_play = [1, 2, 3]
    g.state.players_ready_to_start = [1, 2, 3]
    # create a played pile which P3 can beat
    g.cards.pile_played = [cards.Card(3, 3)]
    print(jsonpickle.encode(g, unpicklable=False))

    g.state.play_order = [3, 1, 2]
    g = swap_to_player(g, 3)
    play_result = g.play_pick_up()
    print(play_result)
    # expecting this to be acepted as P3 can beat this card with their face up card
            
    assert not play_result['action_result'], f"play_pick_up succeeded even though we can beat it: {play_result['action_message']}"

def test_allow_pick_up_cards_when_can_beat_with_face_up(game_three_players_one_card_each):
    '''P2 should not be able to pick up because they can beat the pile card with a face up card'''
    # P1 Card(1, 4), P2 Card(2, 3), P3 Card(3, 3)
    hand_cards = [cards.Card(1, 4), cards.Card(2, 3), cards.Card(3, 3)]

    g = game_three_players_one_card_each
    g.players[1].hand.append(hand_cards.pop())
    g.players[2].face_up.append(hand_cards.pop())
    g.state.number_of_players_requested = 3
    g.state.deal_done = True
    g.state.ready_to_play = [1, 2, 3]
    g.state.players_ready_to_start = [1, 2, 3]
    # create a played pile which P3 can beat
    g.cards.pile_played = [cards.Card(3, 3)]
    print(jsonpickle.encode(g, unpicklable=False))

    g.state.play_order = [3, 1, 2]
    g = swap_to_player(g, 3)
    play_result = g.play_pick_up()
    print(play_result)
    # expecting this to be acepted as P3 can beat this card with their face up card
            
    assert not play_result['action_result'], f"play_pick_up succeeded even though we can beat it: {play_result['action_message']}"


def test_first_player_plays_last_card(game_three_players_one_card_each):
    '''P1 plays last card, P2 and P3 are still playing'''
    g = game_three_players_one_card_each
    expected_card = [g.this_player.face_down[0]]
    g.state.play_order = [1, 2, 3]
    g.state.players_ready_to_start = [1, 2, 3]
    move_to_play = ["d-0"]
    play = g.play_move(move_to_play)
    errors = []
    if not play["action_result"]:
        errors.append(f"error from game.play_move: {play}")
    if len(g.cards.pile_played) != 1:
        errors.append(
            f"len(g.cards.pile_played) not equal to 1, actual length: {len(g.cards.pile_played)}")
    elif g.cards.pile_played != expected_card:
        errors.append(
            f"g.cards.pile_played != {str(expected_card)}: actual card was {str(g.cards.pile_played[0])}")
    if 1 in g.state.play_order:
        errors.append(f"player 1 still exists in play order: {g.state.play_order}")
    if not g.state.play_order == [2, 3]:
        errors.append(f"play order doesnt equal [2, 3]: {g.state.play_order}")
    if not 1 in g.state.players_finished:
        errors.append(f"player 1 not in g.state.players_finished: {g.state.players_finished}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_second_player_plays_last_card_and_one_player_left(game_three_players_one_card_each):
    '''What happens when P1 finishes, then P2 completes their game, but P3 has a card left'''
    g = game_three_players_one_card_each
    expected_card = g.this_player.face_down[:]
    g.state.play_order = [1, 2, 3]
    g.state.players_ready_to_start = [1, 2, 3]
    move_to_play = ["d-0"]
    play = g.play_move(move_to_play)
    # now move to 2nd player
    for p in g.players:
        if p.ID == 2:
            g.this_player = p
            g.state.this_player_id = 2
    expected_card += g.this_player.face_down[:]
    play = g.play_move(move_to_play)

    errors = []
    if not play["action_result"]:
        errors.append(f"error from game.play_move: {play}")

    if len(g.cards.pile_played) != 2:
        errors.append(
            f"g.cards.pile_played not equal to 2, actual length {len(g.cards.pile_played)}")
    elif g.cards.pile_played != expected_card:
        errors.append(
            f"g.cards.pile_played != expected_card {[card.card_key() for card in expected_card]}: actual card was {[card.card_key() for card in g.cards.pile_played]}")
    if 2 in g.state.play_order:
        errors.append(
            f"player 2 still exists in play order: {jsonpickle.encode(g.state.play_order)}")
    if not g.state.play_order == [3]:
        errors.append(f"play order doesnt equal [3]: {g.state.play_order}")
    if not 2 in g.state.players_finished:
        errors.append(f"player 2 not in g.state.players_finished: {g.state.players_finished}")
    if not g.state.game_finished:
        errors.append(f"g.state.finished != True")
    if not g.state.play_order == [3]:
        errors.append(f"play order doesnt equal [3]: {g.state.play_order}")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_create_new_game_from_standard_request_json(standard_request_json):
    '''can we create a new game from teh "default" json'''
    r = standard_request_json
    g = game.Game(1)

    parsed_values, message = g.parse_requested_config(r)
    errors = []
    if not parsed_values:
        errors.append(f"can't parse values: {message}")
    if g.state.less_than_card != 7:
        errors.append(f"less_than_card not 7: {g.state.less_than_card }")
    if g.state.less_than_card in g.state.play_on_anything_cards:
        errors.append(
            f"less_than_card '{g.state.less_than_card}' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.transparent_card != 0:
        errors.append(f"transparent_card not 0: {g.state.transparent_card}")
    if g.state.transparent_card in g.state.play_on_anything_cards:
        errors.append(
            f"transparent_card '{g.state.transparent_card}' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.burn_card != 10:
        errors.append(f"burn_card != 10: {g.state.burn_card}")
    if not g.state.burn_card in g.state.play_on_anything_cards:
        errors.append(
            f"burn_card '{g.state.burn_card}' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.reset_card != 2:
        errors.append(f"reset_card != 2: {g.state.reset_card }")
    if not g.state.reset_card in g.state.play_on_anything_cards:
        errors.append(
            f"reset_card '{g.state.reset_card }' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if 0 in g.state.play_on_anything_cards:
        errors.append(f"0 in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.number_face_down_cards != 3:
        errors.append(f"number_face_down_cards != 3: {g.state.number_face_down_cards}")
    if g.state.number_hand_cards != 3:
        errors.append(f"number_hand_cards != 3: {g.state.number_hand_cards}")
    if g.state.number_of_players_requested != 2:
        errors.append(f"number_of_players_requested != 2: {g.state.number_of_players_requested}")
    if g.state.number_of_decks != 1:
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


def test_duplicate_special_values_in_request_json(standard_request_json):
    '''check we detect duplicate special cards'''
    r = standard_request_json
    for item in r:
        if item["name"] == "transparent_card":
            item["value"] = "7"
    print(r)
    g = game.Game(1)

    parsed_values, _ = g.parse_requested_config(r)

    assert not parsed_values, "allowed addition of duplicate special play cards"


def test_create_new_game_non_standard_request_json(nonstandard_request_json):
    '''check that a JSON with non-standard values is correctly parsed and loaded'''
    r = nonstandard_request_json
    g = game.Game(1)

    parsed_values, message = g.parse_requested_config(r)
    errors = []
    if not parsed_values:
        errors.append(f"can't parse values: {message}")
    if g.state.less_than_card != 3:
        errors.append(f"less_than_card not 3: {g.state.less_than_card }")
    if not g.state.less_than_card in g.state.play_on_anything_cards:
        errors.append(
            f"less_than_card '{g.state.less_than_card}' in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.transparent_card != 5:
        errors.append(f"transparent_card not 5: {g.state.transparent_card}")
    if g.state.transparent_card in g.state.play_on_anything_cards:
        errors.append(
            f"transparent_card '{g.state.transparent_card}' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.burn_card != 6:
        errors.append(f"burn_card != 6: {g.state.burn_card}")
    if not g.state.burn_card in g.state.play_on_anything_cards:
        errors.append(
            f"burn_card '{g.state.burn_card}' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.reset_card != 9:
        errors.append(f"reset_card != 9: {g.state.reset_card }")
    if not g.state.reset_card in g.state.play_on_anything_cards:
        errors.append(
            f"reset_card '{g.state.reset_card }' not in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if 0 in g.state.play_on_anything_cards:
        errors.append(f"0 in play_on_anything_cards: {g.state.play_on_anything_cards}")
    if g.state.number_face_down_cards != 4:
        errors.append(f"number_face_down_cards != 4: {g.state.number_face_down_cards}")
    if g.state.number_hand_cards != 2:
        errors.append(f"number_hand_cards != 2: {g.state.number_hand_cards}")
    if g.state.number_of_players_requested != 5:
        errors.append(f"number_of_players_requested != 5: {g.state.number_of_players_requested}")
    if g.state.number_of_decks != 2:
        errors.append(f"number_of_decks != 2: {g.state.number_of_decks}")
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


def test_do_deal_standard_game(standard_request_json):
    ''' test that a standard game is correctly dealt, with the right number fo cards in each pile'''
    r = standard_request_json
    g = game.Game(1)

    parsed_values, message = g.parse_requested_config(r)
    g.deal()
    errors = []

    if not parsed_values:
        errors.append(f"can't parse values: {message}")
    if not g.state.deal_done == True:
        errors.append("state not deal_done")
    # check each player has 3 cards in hand
    num_hand_cards = [len(p.hand) for p in g.players]
    num_face_up_cards = [len(p.face_up) for p in g.players]
    num_face_down = [len(p.face_down) for p in g.players]
    if set(num_hand_cards) != {3}:
        errors.append(f"hand cards not all 3: {num_hand_cards}")
    if set(num_face_up_cards) != {3}:
        errors.append(f"face up cards not all 3: {num_face_up_cards}")
    if set(num_face_down) != {3}:
        errors.append(f"face down cards not all 3: {num_face_down}")
    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_rotate_players(game_with_three_players):
    '''test that the game correctly rotates players on request'''
    g = game_with_three_players
    g.state.play_order = [1, 2, 3]
    g.rotate_player()
    assert g.state.play_order == [2, 3, 1]


def test_work_out_who_plays_first(game_with_three_players):
    '''test that we can check who should start based on lowest hand card, 
       and that we rotate to that player'''
    g = game_with_three_players
    g.state.play_order = [1, 2, 3]
    # give each
    g.players[0].add_cards_to_player_cards(
        [cards.Card(1, 6), cards.Card(1, 4), cards.Card(1, 5)], cards.Card_Types.CARD_HAND)
    g.players[1].add_cards_to_player_cards(
        [cards.Card(2, 3), cards.Card(2, 4), cards.Card(2, 5)], cards.Card_Types.CARD_HAND)
    g.players[2].add_cards_to_player_cards(
        [cards.Card(3, 6), cards.Card(3, 4), cards.Card(3, 5)], cards.Card_Types.CARD_HAND)
    g.work_out_who_plays_first()
    assert g.state.play_order == [2, 3, 1]


def test_add_player_to_game_for_two():
    '''check that we can add 2 players, and game is ready to start when we do'''
    # 2 requested, one alrady
    # 3 requestd, one alredy
    # player already in game
    errors = []
    g = game.Game(1, [1])
    if len(g.players) != 1:
        errors.append("initial state of g.players != 1 player long")
    print(len(g.players))
    g.state.number_of_players_requested = 2

    add_result, message = g.add_players_to_game(2)

    if not add_result:
        errors.append(message)
    if not g.ready_to_start:
        errors.append("doesn't seem to be ready to start")
    if len(g.players) != 2:
        errors.append("don't appear to have added anyone to player list")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_add_player_to_game_for_two_which_is_full():
    '''check that we can add 2 players, and game is ready to start when we do'''
    # 2 requested, one alrady
    # 3 requestd, one alredy
    # player already in game
    errors = []
    g = game.Game(1, [1])
    if len(g.players) != 1:
        errors.append("initial state of g.players != 1 player long")
    print(len(g.players))
    g.state.number_of_players_requested = 2

    _, _ = g.add_players_to_game(2)
    add_result, _ = g.add_players_to_game(3)

    if add_result:
        errors.append("seem to have added player 3 to game where only 2 requested")
    if len(g.players) != 2:
        errors.append("seems to be > 2 players...")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_add_player_to_game_for_two_which_is_after_deal():
    '''check that we can add 2 players, and game is ready to start when we do'''
    # 2 requested, one alrady
    # 3 requestd, one alredy
    # player already in game
    errors = []
    g = game.Game(1, [1])
    if len(g.players) != 1:
        errors.append("initial state of g.players != 1 player long")
    print(len(g.players))
    g.state.number_of_players_requested = 2

    _, _ = g.add_players_to_game(2)
    g.deal()
    g.state.number_of_players_requested = 3
    add_result, _ = g.add_players_to_game(3)

    if add_result:
        errors.append("seem to have added player 3 to game after deal is done")
    if len(g.players) != 2:
        errors.append("seems to be > 2 players...")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_add_existing_player_to_game_for_two():
    '''should refuse to add exisitng player to game'''
    # 2 requested, one alrady
    # 3 requestd, one alredy
    # player already in game
    errors = []
    g = game.Game(1, [1])
    if len(g.players) != 1:
        errors.append("initial state of g.players != 1 player long")
    print(len(g.players))
    g.state.number_of_players_requested = 2
    add_result, _ = g.add_players_to_game(1)
    if add_result:
        errors.append("added existing player to game")
    if g.ready_to_start:
        errors.append("ready to start is true, but contains same 2 players")
    if len(g.players) != 1:
        errors.append("appear to have added anyone to player list")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_add_two_player_to_game_for_three():
    '''check that we can add 3 players, and game is ready to start when we do'''
    # 2 requested, one alrady
    # 3 requestd, one alredy
    # player already in game
    errors = []
    g = game.Game(1, [1])
    if len(g.players) != 1:
        errors.append("initial state of g.players != 1 player long")
    print(len(g.players))
    g.state.number_of_players_requested = 3

    add_result, message = g.add_players_to_game(2)

    if not add_result:
        errors.append(message)
    if g.ready_to_start:
        errors.append("game ready to start with 2 of 3 players")
    if len(g.players) != 2:
        errors.append("don't appear that player list contains only 2 players")
    add_result, message = g.add_players_to_game(3)

    if not add_result:
        errors.append(message)
    if not g.ready_to_start:
        errors.append("doesn't seem to be ready to start")
    if len(g.players) != 3:
        errors.append("don't appear to have added 3 players to list")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_calculate_player_allowed_actions():
    assert True


def test_play_no_swap():
    assert True


def test_play_pick_up():
    assert True


def test_play_move():
    assert True


def test_swap_cards():
    assert True
