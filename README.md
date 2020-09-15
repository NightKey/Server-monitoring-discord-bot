# Server-monitoring-discord-bot

This bot monitors the server that it's running on.
For it to work, you will need to create at least one [Discord bot accont](https://discordapp.com/developers/applications/).
Both the watchdog, and the bot is capable of running without one another.

*This version is a Windows only version!*

## The bot

This application is a chat-bot, that is capable of telling the status of the computer, and the watchlist's status (what application is and is not running), it can send a notification message of a process suddenly stopping (If the watchdog process is running).

This bot, to function properly needs the following permissions:

* Read Text Channels & See Voice Channels
* Send Messages
* Read Messages
* Manage Messages - Optional for the '&clear' command
* Mention @everyone, @here, and All Roles

## API

The bot uses a tcp server as it's API, where plaintext messages will yield results. The API can be turned on with the `-api` switch.
 -  default port: `9600`
 -  default IP: `127.0.0.1`

The messages should be sent in two parts. First for the command, and a list of paramaters. These parameters must be in the given order to work. A message should be sent in two parts:
 -  first a one byte long length value for the length of the message
 -  and after the message itself. 
The responses will be sent the same way.

Upon connections the bot can respond in two ways:
 -  Accepted - When the connection was acepted, and the client was added to the client list.
 -  Denied - The second message will contain the reason: 'Bad API Key' or 'Already connected'.

|Request                                  |Return Value  |Content                                        |
|:----------------------------------------|:-------------|:---------------------------------------------:|
|[Status](#Status)                        |Json          |The PC's status as it get's sent to the servers|
|[Send](#Send)<sup><sub>1</sub></sup>     |Boolean       |If the message was sent successfully           |
|[Create](#Create)<sup><sub>2</sub></sup> |Boolean       |If the function was added successfully         |

The messages are case sensitive, and 'Bad request' message will be sent, when a message is not applicable.

#### Keys:
 -  <sub>1</sub>: Send {text_to_send [string], user_name* [string]}
 -  <sub>2</sub>: Create {name [string], help_text [string], call_back [string], user_value** [bool]}

<sub>* Optional, format: @username#1234 or @everyone/@here</sub>
<sub>** Optional, default value: `False`</sub>

## Status

The Status' Json value has the following format:

```javascript
{
    "Network":"Avaleable/Unavaleable"[str],
    "SupportingFunctions":{
        "Watchdog":"Active/Inactive"[str], "DisconnectChecker":"Active/Inactive"[str]
    },
    "Ping":"ping delay in ms"[int]
}
```

## Send

This command allows the program to send messages to the servers the bot is connected to, or to individual users. This message can be formatted, but can only be string message.

## Create

When using the `Create` command, the parameters will describe the following:
 -  name - The name to call on Discord
 -  help_text - The text to show in the help command
 -  call_back - The value to send to the program (along side with the value from the user, if it's required)
 -  user_value - Whether to send a user value with the command.

The `help_text` value can be a long text, but if you want to use any specifications on the input it should look the following:

```
Help text goes here. This will be displayed, when the help command is used.
With linebreak, it will still be displayed, however, you should only use '\n' as linebreak, not actually break a line.
Usage: &{command_name} <optional input with explanation>
Category: {a category from the list below}
The 'Usage: ' line is optional, but if present, it should be formated like that, and be on it's own line.
```

### Categories

|Category name     |What comes here                                                        |
|:----------------:|:----------------------------------------------------------------------|
|HARDWARE          |Anything that interacts with the host machine.                         |
|SERVER            |Anything that interacts with the discord server.                       |
|NETWORK           |Anything that interacts with the host's network.                       |
|SOFTWARE          |Anything that interacts with the programs running on the host machine. |
|BOT               |Anything that interacts with the bot's workings.                       |
