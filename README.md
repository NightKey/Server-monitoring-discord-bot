# Server-monitoring-discord-bot

This bot monitors the server that it's running on.
For it to woek, you will need to create at least one [Discord bot accont](https://discordapp.com/developers/applications/).
Both the watchdog, and the bot is capable of running without one an other.

*This version is a Windows only version!*

## The bot

This application is a chat-bot, that is capable of telling the status of the computer, and the watchlist's status (what application is and is not running), however, it can't send notification message of a process suddenly stopping.

This bot, to function properly needs the following permissions:

* Read Tex Channels & See Voice Channels
* Send Messages
* Read Messages
* Manage Messages - Optional for the '&clear' command
* Mention @everyone, @here, and All Roles

## API

The bot uses a tcp server as it's API, where plaintext messages will yield resoults. The API can be turned on with the `-api` switch.
 -  default port: `9600`
 -  default IP: `127.0.0.1`

The messages should be sent in two parts. First for the command, and the secund, and optional, for the other values. A message should be sent in two parts, first a one byte long length value for the length of the message, and after the message itself. The responses will be sent the same way.

|Request                       |Value  |Content                                        |
|:-----------------------------|:------|:---------------------------------------------:|
|Status                        |Json   |The PC's status as it get's sent to the servers|
|Send<sup><sub>1</sub></sup>   |Boolean|If the message was sent successfully           |
|Create<sup><sub>2</sub></sup> |Boolean|If the function was added successfully         |

#### Usages:
 -  <sup><sub>1</sub></sup>: Send {value_to_send}
 -  <sup><sub>2</sub></sup>: Create {name, help_text, user_value*}
<sub>The * values are optional</sub>

The `help_text` value can be a long text, but if you want to use any specifications on the input it should look the following:
```
Help text goes here. This will be displayed, when the help command is used.
With linebreak, it will still be displayed, how ever, you should only use '\n' as linebreak, not actually break a line.
Usage: &{command_name} <optional input with explanation>
The 'Usage: ' Line should be formated like that, and be on it's own line.
```