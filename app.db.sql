BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS `users` (
	`player_id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`player_name`	TEXT,
	`last_played_at`	DATETIME DEFAULT CURRENT_TIMESTAMP,
	`hash`	TEXT,
	`username`	TEXT
);
CREATE TABLE IF NOT EXISTS `player_game_cards` (
	`player_id`	INTEGER NOT NULL,
	`game_id`	INTEGER NOT NULL,
	`card_type`	INTEGER NOT NULL,
	`card_suit`	INTEGER NOT NULL,
	`card_rank`	INTEGER NOT NULL,
	`card_sequence`	INTEGER NOT NULL,
	PRIMARY KEY(`player_id`,`game_id`,`card_suit`,`card_rank`,`card_type`)
);
CREATE TABLE IF NOT EXISTS `player_game` (
	`player_id`	INTEGER NOT NULL,
	`game_id`	INTEGER NOT NULL,
	PRIMARY KEY(`player_id`,`game_id`)
);
CREATE TABLE IF NOT EXISTS `games` (
	`last_move_at`	DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	`last_player_id`	INTEGER,
	`less_than_card`	INTEGER,
	`transparent_card`	INTEGER,
	`burn_card`	INTEGER,
	`reset_card`	INTEGER,
	`number_of_decks`	INTEGER,
	`number_face_down_cards`	INTEGER,
	`number_hand_cards`	INTEGER,
	`current_turn_number`	INTEGER,
	`last_player`	INTEGER,
	`gameid`	INTEGER NOT NULL,
	`players_ready_to_start`	TEXT,
	`play_order`	TEXT,
	`play_on_anything_cards`	TEXT,
	`players_finished`	TEXT,
	`checksum`	TEXT,
	PRIMARY KEY(`gameid`)
);
CREATE TABLE IF NOT EXISTS `game_cards` (
	`game_id`	INTEGER NOT NULL,
	`card_location`	INTEGER NOT NULL,
	`card_suit`	INTEGER NOT NULL,
	`card_rank`	INTEGER NOT NULL,
	`card_sequence`	INTEGER NOT NULL,
	PRIMARY KEY(`game_id`,`card_suit`,`card_rank`,`card_location`,`card_sequence`)
);
COMMIT;
