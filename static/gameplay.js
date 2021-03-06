const card_types = {
    'f': "face up",
    'h': "in hand",
    'd': "face down",
    'p': "played cards",
    'e': "deck",
    'b': "burn pile",
    'i': "pick pile"
};

let timer;
let this_player_id;

let prior_database_checksum = "";

function enable_refresh_timer() {
    timer = setInterval(
        function () {
            check_state_change();
        },
        500  /* 1000 ms = 1 sec */
    );
};

function check_state_change() {
    // stop timer to avoid race
    clearInterval(timer);
    let data = "get_checksum";
    $.postJSON("/checkstate", data, function (result) {
        if (result["database_checksum"] != prior_database_checksum) {
            console.log("checksum changed");
            prior_database_checksum = result["database_checksum"];
            update_game_state();
        } else {
            // not changed; re-enable timer
            enable_refresh_timer();
        }
    });
};

$(document).ready(function () {
    update_game_state();
    $('#ready-to-play-info').on('click', '#action_button', function () {
        submit_action(this.value);
    });


});

$.postJSON = function (url, data, success, dataType) {
    // modified from https://gist.github.com/padcom/1557142/7ebb6a9c632f02ecb10a57e18340c5eae86b251e
    if (typeof data != 'string') {
        data = JSON.stringify(data);
    }
    $.ajax({
        url: url,
        type: "post",
        data: data,
        dataType: dataType || "json",
        contentType: "application/json",
        success: success,
        error: function (xhr, status, error) {
            console.error("status", status, "error", error);
        }
    });
};

function submit_action(action) {
    let json_request = null;
    $('#alert-pane').remove();
    switch (action.toLowerCase()) {
        case "swap": {
            console.log("swap");
            let picked_cards = identify_selected_cards();
            json_request = { "action": "swap", "action_cards": picked_cards };
            break;
        };
        case "ready": {
            console.log("skip swapping cards");
            json_request = { "action": "no_swap" };
            break;
        }
        case "play": {
            console.log("play");
            json_request = { "action": "play", "action_cards": identify_selected_cards() };
            break;
        }
        case "refresh": {
            update_game_state();
            break;
        }
        case "pick up cards": {
            console.log("picking up cards");
            json_request = { "action": "pick" };
        }
    };
    if (json_request) {
        $.postJSON("/playcards", JSON.stringify(json_request), function (data, textStatus, jqXHR) {
            if (data.action_result) {
                update_game_state();
            } else {
                // got an error back. Shoudl be in action_message
                display_alert(data.action_message, "alert-danger");
            }
        }, 'json');
    };
};

function identify_selected_cards() {
    // Retrieve the picker
    let picked_cards = [];
    $("select").each(function (i, obj) {
        picked_cards = picked_cards.concat($(obj).data('picker').selected_values());
    });
    return picked_cards;
};

function display_alert(alert_message, alert_class = "alert-primary") {
    $("#alert-pane").remove();
    let div = document.createElement("div");
    div.setAttribute("id", "alert-pane");
    div.className = "alert " + alert_class;
    let newContent = document.createTextNode(alert_message);
    div.appendChild(newContent);
    $('#ready-to-play-info').append(div);
};


function update_game_state() {
    $.getJSON("/getgamestate", function (result) {
        console.log("state", JSON.stringify(result));
        if (result.game["active-game"]) {
            render_game(result);
        } else {
            $('#game-id').text('There is NO active game');
        };
    });
};

function render_game(result) {
    let state = result.game.state;
    let players_state = result.players_state;
    let allowed_moves = result.allowed_moves;
    $('#game-id').text('There is an active game with ID ' + state.game_id + '.');
    // find our player ID
    this_player_id = state.this_player_id;
    let info_text = 'Your player ID is ' + this_player_id + '. There are ' + state["number_of_players_joined"] + ' players in this game.';
    if (state["play_order"]){
        info_text += ' The next player is player with ID ' + state["play_order"][0];
    };
    $('#player-id').html(info_text);

    // display player cards and return the current player's state as the return value
    let this_player = display_players(players_state, this_player_id, allowed_moves);
    display_game_rules(state);
    display_data_about_player(this_player);
    display_game_cards(state);
    display_game_actions(allowed_moves, this_player_id);
}

function display_players(players_state, this_player_id, allowed_moves) {
    let this_player = null;
    $('#game-row').empty();
    for (let i = 0; i < players_state.length; i++) {
        let player = players_state[i];
        if (player.player_id == this_player_id) {
            this_player = player;
        }
        display_player_cards(player, this_player_id, allowed_moves);
    }
    return this_player;
}

function display_player_cards(current_player, this_player_id, allowed_moves) {
    let game_row = $('#game-row');
    let this_player_div = document.createElement("div");
    this_player_div.className = "col";
    this_player_div.setAttribute('style', 'min-width:250px');
    this_player_div.setAttribute("id", "player" + current_player.player_id.toString());
    let header = document.createTextNode("Player " + current_player.player_id.toString());
    this_player_div.appendChild(header);
    this_player_div.appendChild(lay_out_cards(current_player.face_down_cards, "d", current_player.player_id, this_player_id, allowed_moves));
    this_player_div.appendChild(lay_out_cards(current_player.face_up_cards, "f", current_player.player_id, this_player_id, allowed_moves));
    this_player_div.appendChild(lay_out_cards(current_player.hand_cards, "h", current_player.player_id, this_player_id, allowed_moves, current_player.number_in_hand));
    game_row.append(this_player_div);
    $("select").imagepicker();
    return;
}
function display_game_actions(allowed_moves, player_id) {
    // figure out what teh current state of the game is
    if (!(allowed_moves === undefined || allowed_moves.length == 0)) {
        // this is this players cards
        // work out what the allowed move is
        clearInterval(timer);
        switch (allowed_moves.allowed_action) {
            case "play": {
                // allow the user to select only the type of card(s) they can play
                if (allowed_moves.is_next_player) { add_action_button("Play"); };
                add_action_button("refresh", clear_existing = !(allowed_moves.is_next_player));
                break;
            };
            case "swap": {
                if (allowed_moves.allowed_players.includes(player_id)) {
                    add_action_button("Swap");
                    add_action_button("Ready", clear_existing = false);
                    add_action_button("refresh", clear_existing = false);
                } else {
                    // they're not in the allowed list
                    add_action_button("refresh");
                    enable_refresh_timer();
                    display_alert("Waiting for other users to be ready. Try refreshing.");
                };
                break;
            }
            case "wait": {
                add_action_button("refresh");
                enable_refresh_timer();
                display_alert(allowed_moves.action_message);
                break;
            };
            case "pick": {
                add_action_button("Pick up cards");
                display_alert(allowed_moves.action_message);
                break;
            };
            case "lost": {
                $('#ready-to-play-info').empty();
                display_alert(allowed_moves.action_message);
                break;
            }
            case "finished": {
                $('#ready-to-play-info').empty();
                display_alert(allowed_moves.action_message);
                break;
            };
            default: {
                console.log("unrecognised allowed_moves.allowed_action");
                break;
            };
        }
        return;
    };
};
function lay_out_cards(cards, card_type, card_player_id, this_player_id, allowed_moves, number_in_hand = null) {
    // figure out what teh current state of the game is
    if (!(allowed_moves === undefined || allowed_moves.length == 0)) {
        // this is this players cards
        // work out what the allowed move is
        let return_value = null;
        clearInterval(timer);
        switch (allowed_moves.allowed_action) {
            case "play": {
                // allow the user to select only the type of card(s) they can play
                let allowed_cards = allowed_moves.allowed_cards;
                if (allowed_cards == card_type && allowed_moves.is_next_player && card_player_id == this_player_id) {
                    return_value = lay_out_cards_div(cards, card_type, card_player_id, number_in_hand, with_selector = true);
                }
                else {
                    return_value = lay_out_cards_div(cards, card_type, card_player_id, number_in_hand);
                };
                break;
            }
            case "swap": {
                if (allowed_moves.allowed_players.includes(this_player_id) && card_player_id == this_player_id) {
                    // let them pick hand and face up cards
                    if (card_type == "h" || card_type == "f") {
                        return_value = lay_out_cards_div(cards, card_type, card_player_id, number_in_hand, with_selector = true);
                    }
                    else {
                        return_value = lay_out_cards_div(cards, card_type, card_player_id, number_in_hand);
                    };
                } else {
                    // they're not in the allowed list
                    return_value = lay_out_cards_div(cards, card_type, card_player_id, number_in_hand);
                };
                break;
            }
            case "wait": // same as 'finished' - lay out everything
            case "pick": // same as 'finished' - lay out everything
            case "lost": // same as 'finished' - lay out everything
            case "finished": {
                return_value = lay_out_cards_div(cards, card_type, card_player_id, number_in_hand);
                break;
            };
            default: {
                console.error("unrecognised allowed_moves.allowed_action");
                break;
            };
        };
        return return_value;
    }
    else {
        return lay_out_cards_div(cards, card_type, player_id, number_in_hand);
    };
};


function add_action_button(button_text, clear_existing = true) {
    if (clear_existing) { $('#ready-to-play-info').empty(); }
    let $div = $('<div data-role="fieldcontain"/>');
    $("<input type='button' value='" + button_text + "' id='action_button' />").appendTo($div.clone()).appendTo('#ready-to-play-info');
};

function lay_out_cards_div(cards, card_type, player_id, number_in_hand = false, with_selector = false) {
    let card_div = document.createElement("div");
    card_div.className = "card";
    card_div.setAttribute("id", card_type.toString() + "p" + player_id.toString());
    card_div.className = "card";
    let child_div = document.createElement("div");
    child_div.className = "card-header";
    child_div.appendChild(document.createTextNode(card_types[card_type]));
    card_div.append(child_div);
    if (!(cards === undefined || cards.length == 0)) {
        if (with_selector) {
            let select = document.createElement("select");
            select.setAttribute("multiple", "multiple");
            select.className = "image-picker show-html";
            select.setAttribute("id", "picker-" + card_type);
            for (let j = 0; j < cards.length; j++) {
                let card = cards[j];
                let suit = card.suit;
                let rank = card.rank;
                let option = document.createElement("option");
                // option.setAttribute("data-img-class","flex-card")
                option.setAttribute("data-img-src", "/static/cards/" + get_card_key(suit, rank) + ".svg");
                option.setAttribute("data-img-alt", describe_card(suit, rank));
                option.setAttribute("value", card_type + "-" + j.toString());
                select.append(option);
            };
            card_div.append(select);
        }
        else {
            child_div = document.createElement("div");
            child_div.className = "flex-div";
            for (let j = 0; j < cards.length; j++) {
                let card = cards[j];
                let suit = card.suit;
                let rank = card.rank;
                let img = document.createElement("img");
                img.setAttribute("alt", describe_card(suit, rank));
                img.setAttribute("src", "/static/cards/" + get_card_key(suit, rank) + ".svg");
                let card_img = document.createElement("div");
                card_img.className = "card-img-top";
                card_img.appendChild(img);
                let this_card_div = document.createElement("div");
                this_card_div.className = "flex-card";
                this_card_div.appendChild(card_img);
                child_div.appendChild(this_card_div);
            };
            card_div.append(child_div);
            if (number_in_hand) { card_div.appendChild(document.createTextNode("Number of cards: " + number_in_hand.toString())); };
        };
    } else {
        child_div = document.createElement("div");
        child_div.className = "card-group";
        if (number_in_hand) { child_div.appendChild(document.createTextNode("Number of cards: " + number_in_hand.toString())); };
        card_div.append(child_div);
    };
    return card_div;;
}

function display_data_about_player(player) {
    $('#face-down-count').html('You have ' + player["number_face_down"] + ' face down cards.');
    $('#face-up-count').html('You have ' + player["number_face_up"] + ' face up cards.');
    $('#hand-count').html('You have ' + player["number_in_hand"] + ' cards in your hand.');
};

function display_game_cards(game_state) {
    let game_row = $('#game-row');
    let this_player_div = document.createElement("div");
    this_player_div.className = "col";
    this_player_div.setAttribute("id", "game_info");
    let header = document.createTextNode("Game stacks");
    this_player_div.appendChild(header);

    // pile_deck_size --> e
    // pile_pick_size --> i
    // pile_played_size --> p
    // pile_burn_size --> b
    this_player_div.appendChild(lay_out_game_cards(game_state.pile_played_size, 'p', game_state.play_list));
    this_player_div.appendChild(lay_out_game_cards(game_state.pile_deck_size, 'e'));
    this_player_div.appendChild(lay_out_game_cards(game_state.pile_burn_size, 'b'));
    game_row.append(this_player_div);
    $("select").imagepicker();
    return;
};

function lay_out_game_cards(number_of_cards, card_type, card_list = null) {
    let card_div = document.createElement("div");
    card_div.setAttribute("id", "deck-" + card_type.toString());
    card_div.className = "card";
    let child_div = document.createElement("div");
    child_div.className = "card-header";
    child_div.appendChild(document.createTextNode(card_types[card_type]));
    child_div.appendChild(document.createElement("br"));
    child_div.appendChild(document.createTextNode("There are " + number_of_cards.toString() + " cards in this pile"));
    card_div.append(child_div);
    if ((number_of_cards) && (card_list)) {
        child_div = document.createElement("div");
        child_div.className = "flex-div";
        let max_cards = Math.max(number_of_cards - 4, 0);
        for (let i = number_of_cards - 1, j = 0; i >= max_cards; i--) {
            let card_header = document.createElement("div");
            card_header.appendChild(document.createTextNode((j--).toString()));
            let card = card_list[i];
            let suit = card.suit;
            let rank = card.rank;
            let img = document.createElement("img");
            img.setAttribute("alt", describe_card(suit, rank));
            img.setAttribute("src", "/static/cards/" + get_card_key(suit, rank) + ".svg");
            let card_img = document.createElement("div");
            card_img.className = "card-img-top";
            card_img.appendChild(img);
            let this_card_div = document.createElement("div");
            this_card_div.className = "flex-card";
            this_card_div.append(card_header);
            this_card_div.appendChild(card_img);
            child_div.appendChild(this_card_div);
        };
        card_div.append(child_div);
    };
    return card_div;
};

function display_game_rules(state) {
    // populate game rules
    $('#game-rules').empty();
    let game_rules = "<p class='card-text no-margin'>Burn card: " + check_card(state.burn_card) + "</p>";
    game_rules += "<p class='card-text no-margin'>Less than card: " + check_card(state.less_than_card) + "</p>";
    game_rules += "<p class='card-text no-margin'>Reset card: " + check_card(state.reset_card) + "</p>";
    game_rules += "<p class='card-text no-margin'>Transparent card: " + check_card(state.transparent_card) + "</p>";
    game_rules += "<p class='card-text no-margin'>Cards you can play on anything: " + check_card(state.play_on_anything_cards) + "</p>";
    $('#game-rules').append(game_rules);
};

function check_card(card_to_check) {
    if (card_to_check) {
        return (card_to_check);
    } else {
        return "none";
    }
};

function describe_card(suit, rank) {
    let suits = { 0: "a card", 1: "hearts", 2: "diamonds", 3: "clubs", 4: "spades" };
    let ranks = {
        1: "back", 2: "two", 3: "three", 4: "four", 5: "five",
        6: "six", 7: "seven", 8: "eight", 9: "nine",
        10: "ten", 11: "jack", 12: "queen", 13: "king", 14: "ace"
    };
    return (ranks[rank] + " of " + suits[suit]);
};

function get_card_key(suit, rank) {
    let suits_short = { 0: "B", 1: "H", 2: "D", 3: "C", 4: "S" };
    let rank_short = { 10: "T", 11: "J", 12: "Q", 13: "K", 14: "A" };
    if (rank in rank_short) {
        rank = rank_short[rank];
    };
    let card_image_name = rank.toString() + suits_short[suit].toString();
    return card_image_name;
};