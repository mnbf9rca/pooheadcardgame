$(document).ready(function(){
    $.getJSON("/getgamestate", function(result){

        if (result.game["active-game"]){
            var state = result.game.state;
            console.log("state", JSON.stringify(state))
            $('#jq-id').text('There is an active game');
            // find our player ID
            var this_player_id = state.this_player_id;
            var this_player = null;

            $('#player-id').html('You are player ' + this_player_id + '. There are ' + state["number_of_players"] +  ' players in this game.');
            var player_state = result.players_state;

            number_of_columns = state.number_of_players % 12

            for (var i = 0; i < player_state.length; i++){

                current_player = player_state[i];
                if (current_player.player_id == this_player_id){
                    this_player = current_player
                }

                face_down_cards = new Array(current_player.number_face_down);
                for (var a = 0; a < face_down_cards.length; a++) {
                    face_down_cards[a] = {"rank":1,"suit":0};
                }

                face_down_cards = lay_out_cards(face_down_cards,"d",current_player.player_id)
                face_up_cards = lay_out_cards(current_player.face_up_cards, "f", current_player.player_id)
                hand_cards = lay_out_cards(current_player.hand_cards, "h", current_player.player_id)


                $('#game-row').append("<div class='col' id='player" + current_player.player_id.toString() + "'>Player " + current_player.player_id.toString() + " with face up cards " + face_down_cards + face_up_cards + hand_cards + "</div>")


            }

            // populate game rules
            game_rules="<p class='card-text'>Burn card: " + check_card(state.burn_card) +"</p>"
            game_rules+="<p class='card-text'>Less than card: " + check_card(state.less_than_card) +"</p>"
            game_rules+="<p class='card-text'>Reset card: " + check_card(state.reset_card) +"</p>"
            game_rules+="<p class='card-text'>Transparent card: " + check_card(state.transparent_card) +"</p>";
            game_rules+="<p class='card-text'>Cards you can play on anything: " + check_card(state.play_on_anything_cards) +"</p>"
            $('#game-rules').append(game_rules);

            $('#face-down-count').html('You have ' + this_player["number_face_down"] + ' face down cards.');
            $('#face-up-count').html('You have ' + this_player["number_face_up"] + ' face up cards.');
            $('#hand-count').html('You have ' + this_player["number_in_hand"] + ' cards in your hand.');



        } else {
            $('#jq-id').text('There is NO active game');
        }

    });


});

function check_card(card_to_check){
    if (card_to_check){
        return card_to_check
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