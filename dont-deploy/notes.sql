/* find the details   */

SELECT
    games.gameid,
    player_counts.number_of_players,
    games.game_ready_to_start,
    games.game_finished,
    games.players_requested
FROM games
    join (select
        player_game.game_id
    from player_game
    where player_game.player_id = 1) as games_for_this_player on games.gameid = games_for_this_player.game_id
    LEFT JOIN (SELECT
        player_game.game_id as game_id,
        count(player_game.player_id) as number_of_players
    FROM player_game
    group by player_game.game_id) as player_counts ON games.gameid = player_counts.game_id
WHERE games.players_requested > player_counts.number_of_players AND games.game_finished = 0;



SELECT games.gameid, player_counts.number_of_players, games.game_ready_to_start, games.game_finished, games.players_requested
FROM games
    LEFT JOIN (SELECT
        player_game.game_id as game_id,
        count(player_game.player_id) as number_of_players
    FROM player_game
    LEFT JOIN (select game_id
    from player_game
    where player_id = 3) AS games_to_exclude on games_to_exclude.game_id = games.gameid
    group by player_game.game_id) as player_counts ON games.gameid = player_counts.game_id
where otherplayer.game_id IS NULL