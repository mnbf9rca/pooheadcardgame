$(document).ready(function(){
    $.getJSON("/getgamestate", function(result){

        if (result.game["active-game"]){
            render_game(result);
        } else {
            $('#jq-id').text('There is NO active game');
        }

    });


});
function render_game(result){
    var state = result.game.state;
    console.log("state", JSON.stringify(state))

    $('#jq-id').text('There is an active game');
    // find our player ID
    var this_player_id = state.this_player_id;

    $('#player-id').html('You are player ' + this_player_id + '. There are ' + state["number_of_players"] +  ' players in this game.');

    number_of_columns = state.number_of_players % 12

    // display player cards and return the current player's state as the return value
    var this_player = disaply_player_cards(result.players_state, this_player_id);
    display_game_rules(state);
    display_data_about_player(this_player);
}

function disaply_player_cards(player_state, this_player_id) {
    for (var i = 0; i < player_state.length; i++) {
        current_player = player_state[i];
        if (current_player.player_id == this_player_id) {
            this_player = current_player;
        }
        face_down_cards = lay_out_cards(current_player.face_down_cards, "d", current_player.player_id);
        face_up_cards = lay_out_cards(current_player.face_up_cards, "f", current_player.player_id);
        hand_cards = lay_out_cards(current_player.hand_cards, "h", current_player.player_id);
        $('#game-row').append("<div class='col' id='player" + current_player.player_id.toString() + "'>Player " + current_player.player_id.toString() + " with face up cards " + face_down_cards + face_up_cards + hand_cards + "</div>");
    }
    return this_player;
}

function display_data_about_player(player){
    $('#face-down-count').html('You have ' + player["number_face_down"] + ' face down cards.');
    $('#face-up-count').html('You have ' + player["number_face_up"] + ' face up cards.');
    $('#hand-count').html('You have ' + player["number_in_hand"] + ' cards in your hand.');
}

function display_game_rules(state){
                // populate game rules
                game_rules="<p class='card-text'>Burn card: " + check_card(state.burn_card) +"</p>"
                game_rules+="<p class='card-text'>Less than card: " + check_card(state.less_than_card) +"</p>"
                game_rules+="<p class='card-text'>Reset card: " + check_card(state.reset_card) +"</p>"
                game_rules+="<p class='card-text'>Transparent card: " + check_card(state.transparent_card) +"</p>";
                game_rules+="<p class='card-text'>Cards you can play on anything: " + check_card(state.play_on_anything_cards) +"</p>"
                $('#game-rules').append(game_rules);
}

function check_card(card_to_check){
    if (card_to_check){
        return (card_to_check)
    } else {
        return "none"
    }
}

function lay_out_cards(cards, card_type, player_id){
    var card_response = "<div class='card' id='p"+ player_id.toString() + "face'>";
    var card_types = {'f':"Face up", 'h':"in hand", 'd':"face down"}
    card_response += "<div class='card-header'>" + card_types[card_type] + "</div>"
    card_response += "<div class='card-group'>"
    if (cards){
        for (j = 0; j < cards.length; j++){
            card = cards[j]
            suit = card.suit;
            rank = card.rank;
            card_response += "<div class='card'><div class='card-img-top'><img alt='" + describe_card(rank, suit) + "' src='/static/cards/" + get_card_key(rank, suit) +".svg'/></div></div>";
           //  card_response += "<div id='p" + player_id.toString() + "f" + j.toString() + "'>" + get_card_key(rank, suit) + "</div>"
        }
    }
    card_response +="</div></div>"
    return card_response;

}

function describe_card(rank, suit){
    var suits = {0: "a card", 1: "hearts", 2: "diamonds", 3: "clubs", 4: "spades" }
    var ranks = {1: "back", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine",
            10: "ten", 11: "jack", 12: "queen", 13: "king", 14: "ace"}
    return(ranks[rank] + " of " + suits[suit])
}


function get_card_key(rank, suit){
    var suits_short = {0:"B", 1:"H", 2: "D", 3: "C", 4: "S"}
    var rank_short = {10:"T", 11:"J", 12:"Q", 13:"K", 14:"A"}
    if (rank in rank_short){
        rank = rank_short[rank]
    }
    card_image_name = rank.toString() + suits_short[suit].toString()
    return card_image_name

}