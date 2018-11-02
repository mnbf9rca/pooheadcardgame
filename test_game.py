import pytest
import jsonpickle

import game
import player
import cards

@pytest.fixture
def three_cards():
    c = [cards.Card(1,4), cards.Card(2,3), cards.Card(3,3)]
    return c

@pytest.fixture
def game_with_three_players():
    g = game.Game(this_player_id=1, number_of_players = 3)
    for id in range(2, 4):
        g.players.append(player.Player(id))
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
    print(play)
    errors = []
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