BEGIN TRANSACTION;
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
	`players_requested`	INTEGER,
	`game_ready_to_start`	INTEGER,
	PRIMARY KEY(`gameid`)
);
COMMIT;
