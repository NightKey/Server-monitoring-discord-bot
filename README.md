# Server-monitoring-discord-bot

This bot monitors the computer that it's running on.
For it to work, you will need to create one [Discord bot account](https://discordapp.com/developers/applications/).
Both the watchdog, and the bot is capable of running without one another.

*This version is a Windows only version!*

## The bot

This application is a chat-bot that is capable of telling the status of the computer, the watchlist's status (what application is and isn't running), and it can send a notification message of a process suddenly stopping (If the watchdog process is running).

This bot, needs the following permissions to function properly:

* Read Text Channels & See Voice Channels
* Send Messages
* Read Messages
* Manage Messages - Optional for the '&clear' command
* Mention @everyone, @here, and All Roles

## Arguments

 - --nowd - Disables the watchdog
 - --nodcc - Disables the disconnect checker
 - --api - Enables the API server
 - --remote - Sets the bot to remote modefor multiple computers (Disables watchdog and disconnect checker)
    - --ip - Sets the remote discord bot's IP adress
    - --auth - Sets the authentication code for the bot
    - --name - Sets the name to use with the remote discord bot
 - --scilent - Disables startup messages on the discord server

## API

The bot uses a tcp server as it's API, where plaintext messages will yield results. The API can be turned on with the `-api` switch.
 -  default port: `9600`
 -  default IP: `127.0.0.1`

The messages should be sent as a json. The keys are `Command` and `Value`. The `Command` should contain the request, and `Value` should contain the request's data or `None` These parameters must be in the given order to work. A message should be sent in two parts:
 -  first a one byte long value for the length of the message
 -  the message itself. 
The responses will be sent the same way.

### Example request

```javascript
{
    "Command": "Create",
    "Value": ["name", "help text", "callback value", [return_value]]
}
```

Responses are in json format and they have the following structure:

```javascript
{
    "Response": "Bad request" or "Success" or "Internal error" or "Denied" or "Accepted",
    "Data": None or "Explanation",
    "Code": 1 or 2 or 3 or 4 or 5
}
```

Upon validation, the response can be two:
 -  "Accepted" - When the connection was accepted, and the client was added to the client list.
 -  "Denied" - The second message will contain the reason: "Bad API Key" or "Already connected".

|Request                                          |Return Value  |Content                                        |
|:------------------------------------------------|:-------------|:---------------------------------------------:|
|[Status](#Status)                                |Json          |The PC's status as it gets sent to the servers |
|[Send](#Send)<sup><sub>1</sub></sup>             |Boolean       |If the message was sent successfully           |
|[Create](#Create)<sup><sub>2</sub></sup>         |Boolean       |If the function was added successfully         |
|[Username](#Username)<sup><sub>3</sub></sup>     |String        |Returns the username connected to the ID       |
|[Remove](#Remove)<sup><sub>4</sub></sup>         |Boolean       |Rempves the selected command from the list     |
|[Disconnect](#Disconnect)<sup><sub>5</sub></sup> |Nothing       |Safely disconnect, with an optional reason     |
|[Is Admin](#Is_Admin)<sub>3</sub>                |Boolean       |Returns if user is an admin of the discord bot |

The messages are case sensitive, and 'Bad request' message will be sent, when a message is not applicable.

#### Keys:
 -  <sub>1</sub>: Send {text_to_send [string], user_id* [string]}
 -  <sub>2</sub>: Create {name [string], help_text [string], callback [string], return_key** [integer]}
 -  <sub>3</sub>: Username {user_id [string]}
 -  <sub>4</sub>: Remove {command_name** [string]}
 -  <sub>5</sub>: Disconnect {reason***}

<sub>* Optional, format: username#1234</sub>
<sub>** Optional, default value: [NOTHING]</sub>
<sub>*** Optional, default value: None</sub>

## Status

The Status' Json value has the following format:

```javascript
{
    "Network":"Available/Unavailable"[str],
    "SupportingFunctions":{
        "Watchdog":"Active/Inactive"[str], "DisconnectChecker":"Active/Inactive"[str]
    },
    "Ping":"ping delay in ms"[int]
}
```

## Send

This command allows the program to send messages to the servers the bot is connected to, or to individual users. This message can be formatted, but can only be string message.
To send message to a specific user, the user's ID must be provided in the 'user_id'. For specific channels, the channel ID must be provided.

## Create

When using the `Create` command, the parameters will describe the following:
 -  name - The name to call on Discord
 -  help_text - The text to show in the help command
 -  callback - The value to send to the program (alongside with the value from the user, if it's required)
 -  return_value - What to send back with the command. It excepts a list of values (if nothing, then a list containing 0) of what needs to be returned.

#### Options to return_value

|Key              |Value|What's sent back with the command               |
|:----------------|:---:|:-----------------------------------------------|
|NOTHING          |0    |Nothing                                         |
|USER_INPUT       |1    |Text after the '&[command]' part of the call.   |
|SENDER           |2    |Only the sender's user ID.                      |
|CHANNEL          |4    |The cannel's ID get's returned.                 |

The `help_text` value can be a long text, but if you want to use any specifications on the input it should look the following:

```
Help text goes here. This will be displayed when the help command is used.
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
|USER              |Anything that interacts with the users.                                |

### Returns

When it's called, it returns with the following values, in the following order:
 - The name given in the create call
 - Channel ID, if required
 - User ID, if required
 - User Input, if required

## Username

Returns the current name of the selected user, where the user's ID is match the given ID.

## Remove

Can be called with or without a specific name. If called with a command name, it attempts to remove the selected function. When called without any name, removes all functions linked to the socket it was called from.

## Disconnect

Can be used to remove every created command from the server, and close the connection between the server, and the client.

## Is Admin

Checks if a user is registered as an administrator for the bot