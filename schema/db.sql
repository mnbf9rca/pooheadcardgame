CREATE TABLE "game_cards" (
  "game_id" int NOT NULL,
  "card_location" int NOT NULL,
  "card_suit" int NOT NULL,
  "card_rank" int NOT NULL,
  "card_sequence" int NOT NULL,
  PRIMARY KEY ("game_id","card_suit","card_rank","card_location","card_sequence")
)

CREATE TABLE "games" (
  "gameid" int4 NOT NULL DEFAULT nextval('games_gameid_seq'::regclass),
  "last_move_at" datetime DEFAULT NULL,
  "less_than_card" int DEFAULT NULL,
  "transparent_card" int DEFAULT NULL,
  "burn_card" int DEFAULT NULL,
  "reset_card" int DEFAULT NULL,
  "number_of_decks" int DEFAULT NULL,
  "number_face_down_cards" int DEFAULT NULL,
  "number_hand_cards" int DEFAULT NULL,
  "current_turn_number" int DEFAULT NULL,
  "last_player" int DEFAULT NULL,
  "players_ready_to_start" varchar(45) NULL,
  "play_order" varchar(45)  NULL,
  "play_on_anything_cards" varchar(45)  NULL,
  "players_finished" varchar(45)  NULL,
  "game_checksum" varchar(45)  NULL,
  "players_requested" int DEFAULT NULL,
  "game_ready_to_start" boolean DEFAULT NULL,
  "game_finished" boolean DEFAULT NULL,
  "deal_done" boolean DEFAULT NULL,
  PRIMARY KEY ("gameid")
)

CREATE TABLE "player_game" (
  "player_id" int NOT NULL,
  "game_id" int NOT NULL,
  PRIMARY KEY ("player_id","game_id")
)

CREATE TABLE "player_game_cards" (
  "player_id" int NOT NULL,
  "game_id" int NOT NULL,
  "card_type" int NOT NULL,
  "card_suit" int NOT NULL,
  "card_rank" int NOT NULL,
  "card_sequence" int NOT NULL,
  PRIMARY KEY ("player_id","game_id","card_suit","card_rank","card_type")
)

    CREATE TABLE "users" (
    "player_id" int4 NOT NULL DEFAULT nextval('users_player_id_seq'::regclass),
    "player_name" varchar(45)  NULL,
    "last_played_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
    "hash" varchar(200)  NULL,
    "username" varchar(45)  NULL,
    "is_admin" int DEFAULT '0',
    PRIMARY KEY ("player_id")
    )