# pooheadcardgame  [![Build Status](https://travis-ci.org/mnbf9rca/pooheadcardgame.svg?branch=master)](https://travis-ci.org/mnbf9rca/pooheadcardgame)

My implementation of the card game https://en.wikipedia.org/wiki/Shithead_(card_game)

# Shithead
is a card game for 2-4 players popular among backpackers, which is where I learnt how to play.

Although there are many variations on the rules, the basic gameplay is the same.

Players start with 3 face down, 3 face up, and 3 hand cards. Before play, players can swap any card or cards from their hand with their face down cards to try and get a better hand for later in the game.

Players then take turns to place cards on a pile. Each card must match or beat the rank of the last played card (Aces are high).

Some cards have a special meaning - for example, 10 (usually) clears the pile and allows the player to start again.

If a player is unable to play, they must pick up the cards.

I built the back end in Python with SQLite as the database. The front end is built using Bootstrap and JQuery. I make use of asynchronous calls between the front end and the back end to keep gameplay going.

In future I intend to replace the DBMS (e.g. move to Google Cloud SQL), optimise some of the SQL and database activities (e.g. simplify some queries, implement transactions etc.), add some play instructions, and host the game online at pooheadcardgame.com

## LICENCE CREDITS

# playing card images 
from https://www.me.uk/cards/

# image-picker.{css|js}
Available for use under the MIT License

Copyright (c) 2013-2014 Rodrigo Vera

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# portions of common_db.py
Copyright 2012-2018 CS50

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.