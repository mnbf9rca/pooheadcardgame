var card_types = {'f':"Face up", 'h':"in hand", 'd':"face down"}
$(document).ready(function(){
    $.getJSON("/getgamestate", function(result){
        console.log("state", JSON.stringify(result))
        if (result.game["active-game"]){
            render_game(result);
        } else {
            $('#game-id').text('There is NO active game');
        }

    });


});
function render_game(result){
    var state = result.game.state;
    var players_state = result.players_state;
    var allowed_moves = result.allowed_moves;

    $('#game-id').text('There is an active game with ID ' + state.game_id + '.');
    // find our player ID
    var this_player_id = state.this_player_id;

    $('#player-id').html('You are player ' + this_player_id + '. There are ' + state["number_of_players"] +  ' players in this game.');

    number_of_columns = state.number_of_players % 12

    // display player cards and return the current player's state as the return value
    this_player = display_players(players_state, this_player_id, allowed_moves)
   
    display_game_rules(state);
    display_data_about_player(this_player);
}

function display_players(players_state, this_player_id, allowed_moves){
    console.log("allowed_moves", JSON.stringify(allowed_moves))
    this_player = null;
    for (i = 0; i < players_state.length; i++){
        player = players_state[i];
        this_player_allowed_moves = null
        if (player.player_id == this_player_id) {
            this_player = player;
            this_player_allowed_moves = allowed_moves;
        }        
        display_player_cards(player, this_player_allowed_moves);
    }
    return this_player;
}

function display_player_cards(current_player, allowed_moves) {
    face_down_cards = lay_out_cards(current_player.face_down_cards, "d", current_player.player_id, allowed_moves);
    face_up_cards = lay_out_cards(current_player.face_up_cards, "f", current_player.player_id, allowed_moves);
    hand_cards = lay_out_cards(current_player.hand_cards, "h", current_player.player_id, allowed_moves);
    $('#game-row').append("<div class='col' id='player" + current_player.player_id.toString() + "'>Player " + current_player.player_id.toString() + " with face up cards " + face_down_cards + face_up_cards + hand_cards + "</div>");
    $("select").imagepicker()
    return;
}

function lay_out_cards(cards, card_type, player_id, allowed_moves){
    // figure out what teh current state of the game is
    
    if (allowed_moves){
        // this is this players cards
        // work out what the allowed move is
        switch(allowed_moves.allowed_action){
            case "play":{
                // allow the user to select only the type of card(s) they can play 
                allowed_cards = allowed_moves.allowed_cards;
                if (allowed_cards ==  card_type){
                    return lay_out_cards_with_selector(cards, card_type, player_id)
                }
                else {
                    return lay_out_cards_without_selector(cards, card_type, player_id)
                }
            break
            }   
            case "swap":{
                if (player_id in allowed_moves.allowed_players){
                    // let them pick hand and face up cards
                    if (card_type == "h" || card_type == "f"){
                        return lay_out_cards_with_selector(cards, card_type, player_id)
                    }
                    else {
                        return lay_out_cards_without_selector(cards, card_type, player_id)
                    }
                    break
                }else{
                    // they're not in the allowed list
                    return lay_out_cards_without_selector(cards, card_type, player_id)
                }
            }
                       
        }
        
    }
    else
    {
        return lay_out_cards_without_selector(cards, card_type, player_id)
    }

}

function lay_out_cards_with_selector(cards, card_type, player_id){
    var card_response = "<div class='card' id='p"+ player_id.toString() + "face'>";
    card_response += "<div class='card-header'>" + card_types[card_type] + "</div>"
    card_response += "<div class='card-group'>"
    card_response += "<select multiple='multiple' class='image-picker show-html' id='picker-" + card_type + "'>"
    if (cards){
        for (j = 0; j < cards.length; j++){
            card = cards[j]
            suit = card.suit;
            rank = card.rank;
            
            card_response += "<option data-img-class='card' data-img-src='/static/cards/" + get_card_key(suit, rank) +".svg' value='" + card_type + "-" + j.toString() + "' data-img-alt='" + describe_card(suit, rank) + "'>" + describe_card(suit, rank) + "</option>\n";
           //  card_response += "<div id='p" + player_id.toString() + "f" + j.toString() + "'>" + get_card_key(rank, suit) + "</div>"
        }
    }
    card_response +="</select></div>"
    return card_response;

}

function lay_out_cards_without_selector(cards, card_type, player_id){
    var card_response = "<div class='card' id='p"+ player_id.toString() + "face'>";
    
    card_response += "<div class='card-header'>" + card_types[card_type] + "</div>"
    card_response += "<div class='card-group'>"
    if (cards){
        for (j = 0; j < cards.length; j++){
            card = cards[j]
            suit = card.suit;
            rank = card.rank;
            card_response += "<div class='card'><div class='card-img-top'><img alt='" + describe_card(suit, rank) + "' src='/static/cards/" + get_card_key(suit, rank) +".svg'/></div></div>";
           //  card_response += "<div id='p" + player_id.toString() + "f" + j.toString() + "'>" + get_card_key(rank, suit) + "</div>"
        }
    }
    card_response +="</div></div>"
    return card_response;

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


function describe_card(suit, rank){
    var suits = {0: "a card", 1: "hearts", 2: "diamonds", 3: "clubs", 4: "spades" }
    var ranks = {1: "back", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine",
            10: "ten", 11: "jack", 12: "queen", 13: "king", 14: "ace"}
    return(ranks[rank] + " of " + suits[suit])
}


function get_card_key(suit, rank){
    var suits_short = {0:"B", 1:"H", 2: "D", 3: "C", 4: "S"}
    var rank_short = {10:"T", 11:"J", 12:"Q", 13:"K", 14:"A"}
    if (rank in rank_short){
        rank = rank_short[rank]
    }
    card_image_name = rank.toString() + suits_short[suit].toString()
    return card_image_name

}