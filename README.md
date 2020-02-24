# Server-monitoring-discord-bot

This bot monitors the server that it's running on.
For it to woek, you will need to create at least one [Discord bot accont](https://discordapp.com/developers/applications/).
Both the watchdog, and the bot is capable of running without one an other.

## The bot

This application is a chat-bot, that is capable of telling the status of the computer, and the watchlist's status (what application is and is not running), however, it can't send notification message of a process suddenly stopping.

This bot, to function properly needs the following permissions:

* Read Tex Channels & See Voice Channels
* Send Messages
* Read Messages
* Manage Messages - Optional for the '&clear' command

## The watchdog

This application is a watchdog application, that checks the running processes every 10 secunds and notifys the designated channel if something stops working.

This bot needs the following permissions:

* Read Text Channels & See Voice Channels
* Send Messages
* Mention @everyone, @here, and All Roles
