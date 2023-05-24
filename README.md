# Server-monitoring-discord-bot

This application is a chat-bot that is capable of monitoring the status of the computer as well as the running state of watch listed applications. 
If the watchdog process is in use, a notification message can be sent.
For it to work, you will need to create one [Discord bot account](https://discordapp.com/developers/applications/).
If you want to use the Telegramm bot API, you will need to create a [Telegramm bot](https://core.telegram.org/api/obtaining_api_id) as well.
The watchdog and bot processes are capable of running without one another.

## The bot

This application is a chat-bot that is capable of telling the status of the computer, the watchlist's status (what application is and isn't running), and it can send a notification message of a process suddenly stopping (If the watchdog process is running).

This bot, needs the following permissions to function properly:

* Read Text Channels & See Voice Channels
* Send Messages
* Read Messages
* Read Message History
* Use External Emojis
* Mention @everyone, @here, and All Roles
* Manage Messages - Optional for the '&clear' command
* Connect, Speake - Optional if a musicbot is connected to it's API

## Arguments

 - --nowd - Disables the watchdog
 - --nodcc - Disables the disconnect checker
 - --api - Enables the API server
 - --telegramm - Enables Telegramm bot API
 <!-- - --remote - Sets the bot to remote modefor multiple computers (Disables watchdog and disconnect checker) 
    - --ip - Sets the remote discord bot's IP adress
    - --auth - Sets the authentication code for the bot                                                     This function needs to be developed first!
    - --name - Sets the name to use with the remote discord bot -->
 - --scilent - Disables startup messages on the discord server

# API

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

Upon validation, the response can be two:
 -  "Accepted" - When the connection was accepted, and the client was added to the client list.
 -  "Denied" - The second message will contain the reason: "Bad API Key" or "Already connected".

### Available commands

|Request                                                                     |Return Value                                             |Content                                                     |
|:---------------------------------------------------------------------------|:--------------------------------------------------------|:----------------------------------------------------------:|
|[Status](#status)                                                           |Json                                                     |The PC's status as it gets sent to the servers              |
|[Send](#send)<sup><sub>1</sub></sup>                                        |Boolean                                                  |If the message was sent successfully                        |
|[Create](#create)<sup><sub>2</sub></sup>                                    |[Response](#resopnse-object)                             |If the function was added successfully                      |
|[Username](#username)<sup><sub>3</sub></sup>                                |[MessageSendignResponse](#message-sendign-response)      |Returns the username connected to the ID                    |
|[Remove](#remove)<sup><sub>4</sub></sup>                                    |[Response](#response-object)                             |Rempves the selected command from the list                  |
|[Disconnect](#disconnect)<sup><sub>5</sub></sup>                            |Nothing                                                  |Safely disconnect, with an optional reason                  |
|[Is Admin](#is-admin)<sup><sub>3</sub></sup>                                |Boolean                                                  |Returns if user is an admin of the discord bot              |
|[Connect To User](#connect-to-user)<sup><sub>3</sub></sup>                  |[Response](#response-object)                             |Response from the action                                    |
|[Disconnect From Voice](#disconnect-from-user)                              |[Response](#response-object)                             |Response from the action                                    |
|[Play Audio File](#play-audio-file)<sup><sub>7</sub></sup>                  |Boolean                                                  |If the audio file was started                               |
|[Add Audio File](#add-audio-file)<sup><sub>6</sub></sup>                    |Boolean                                                  |If the audio file was added                                 |
|[Pause Currently Playing](#pause-currently-playing)<sup><sub>3</sub></sup>  |Boolean                                                  |If the audio file was paused                                |
|[Resume Paused](#resume-paused)<sup><sub>3</sub></sup>                      |Boolean                                                  |If the audio file was resumed                               |
|[Skip Currently Playing](#skip-currently-playing)<sup><sub>3</sub></sup>    |Boolean                                                  |If a skip could be made                                     |
|[Stop Currently Playing](#stop-currently-playing)<sup><sub>3</sub></sup>    |Boolean                                                  |If the audio file was stopped                               |
|[List Queue](#list-queue)                                                   |List                                                     |Returns a list of filenames currently queued                |
|[Set As Track Finished](#set-as-track-finished)                             |[Response](#response-object)                             |Sets the client as a callback when a track finishes playing |
|[Subscribe To Event](#subscribe-to-event)<sup><sub>8</sub></sup>            |[Response](#response-object)                             |Subscribes to a specified event                             |

The messages are case sensitive, and 'Bad request' message will be sent, when a message is not applicable.

#### Keys:
 -  <sub>1</sub>: {text_to_send [string], user_id* [string]}
 -  <sub>2</sub>: {name [string], help_text [string], callback [string], return_key** [integer]}
 -  <sub>3</sub>: {user_id [string]}
 -  <sub>4</sub>: {command_name** [string]}
 -  <sub>5</sub>: {reason***}
 -  <sub>6</sub>: {path [string]}
 -  <sub>7</sub>: {user_id [string], path [string]}
 -  <sub>8</sub>: [Events](#events)

<sub>* Optional, format: username#1234</sub>
<sub>** Optional, default value: [NOTHING]</sub>
<sub>*** Optional, default value: None</sub>

## Objects

### Response object

Responses are in json format and they have the following structure:

```javascript
{
    "Response": "Bad request" or "Success" or "Internal error" or "Denied" or "Accepted",
    "Data": None or "Explanation" or "Response value",
    "Code": 1 or 2 or 3 or 4 or 5
    "bool": True if code is 2 or 5 False otherwise
}
```

### Message

This class is used to send complex messages between the bot and the connected API-s.

|Property name|Types                          |Description                            |
|:-----------:|:------------------------------|--------------------------------------:|
|sender       |String                         |The name of the sender                 |
|content      |String                         |The message the user provided          |
|channel      |String                         |The channel name where it was used     |
|attachment   |[attachment](#attachment)/None |The attachment sent with the message   |
|called       |String                         |The metthod called by the user         |
|interface    |[interface](#interface)/None   |The interface used to send this message|

The class is sent as a Json object.

### Attachment

A class used to represent attachments sent by the user.

|Property or method name|Type or return type|Description                                            |
|:---------------------:|:------------------|------------------------------------------------------:|
|filename               |String             |The sent file's name with extention                    |
|url                    |String             |The url from where the file can be downloaded          |
|size/size()            |Int                |The size of the file                                   |
|download()             |bite like          |Returns the file's bite like representation            |
|save(valid_path)       |String             |Returns the full path to where the file was downloaded |


### Interface

An enum class used to tell what interface was used for triggering the message sending.

|Name value | Int value |
|:---------:|:----------|
|Discord    |0          |
|Telegramm  |1          |

### Message sending response

A class that contains the results of a message sending request.

|Property name|Prooperty value                     |Description                |
|:-----------:|:-----------------------------------|--------------------------:|
|state        |[Response code](#response-code)     |The state of the response  |
|message      |String/None                         |The optional message/reason|

Json example

```Javascript
{
    'state': 0
    'message': 'Example'
}
```

### Response code

An enum class to represent the success of a message sending request

|Name value    | Int value |Meaning                    |
|:------------:|:----------|--------------------------:|
|Success       |0          |Message successfully sent  |
|BadRequest    |1          |Bad request was retrived   |
|InternalError |2          |An internal error happaned |
|Denied        |3          |The request was denied     |
|Accepted      |4          |The request was accepted   |
|Failed        |5          |Failed to send message     |
|NotFound      |6          |User/Channel not found     |

### Events

An enum class to represent possible events to subscribe to

|Name value      | Int value |
|:--------------:|:----------|
|presence_update |0          |
|activity        |1          |

## Commands

### Status

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

### Send

This command allows the program to send messages to the servers the bot is connected to, or to individual users. This message can be formatted, but can only be string message.
To send message to a specific user, the user's ID must be provided in the 'user_id'. For specific channels, the channel ID must be provided.

### Create

When using the `Create` command, the parameters will describe the following:
 -  name - The name to call on Discord
 -  help_text - The text to show in the help command
 -  callback - The value to send to the program (alongside with the value from the user, if it's required)
 -  return_value - What to send back with the command. It excepts a list of values (if nothing, then a list containing 0) of what needs to be returned.

The `help_text` value can be a long text, but if you want to use any specifications on the input it should look the following:

```
Help text goes here. This will be displayed when the help command is used.
With linebreak, it will still be displayed, however, you should only use '\n' as linebreak, not actually break a line.
Usage: &{command_name} <optional input with explanation>
Category: {a category from the list below}
The 'Usage: ' line is optional, but if present, it should be formated like that, and be on it's own line.
```

#### Categories

|Category name     |What comes here                                                        |
|:----------------:|:----------------------------------------------------------------------|
|HARDWARE          |Anything that interacts with the host machine.                         |
|SERVER            |Anything that interacts with the discord server.                       |
|NETWORK           |Anything that interacts with the host's network.                       |
|SOFTWARE          |Anything that interacts with the programs running on the host machine. |
|BOT               |Anything that interacts with the bot's workings.                       |
|USER              |Anything that interacts with the users.                                |
|AUDIO             |Anything that plays audio trough the bot.                              |

#### Returns

When it's called, it returns a [message](#message) object.

### Username

Returns the current name of the selected user, where the user's ID is match the given ID.

### Remove

Can be called with or without a specific name. If called with a command name, it attempts to remove the selected function. When called without any name, removes all functions linked to the socket it was called from.

### Disconnect

Can be used to remove every created command from the server, and close the connection between the server, and the client.

#### Is Admin

Checks if a user is registered as an administrator for the bot.

### Connect To User

Connect the client to the user's current active voice channel if there is one.

### Disconnect From User

Disconnect the client from the current voice channel, if the user is present on that channel.

### Play Audio File

Starts the audio file on the path provided. If the file is not supported error is returned. Will connect if the bot is not yet connected, will only allow to be used by member in the same channel.

### Add Audio File

Adds the audio file to the play list on the path provided. If the file is not supported error is returned.

### Pause Currently Playing

Pauses the currently playing track. Will only succeed, if the requesting member is in the same voice channel.

### Resume Paused

Resumes playing the paused track. Will only succeed, if the requesting member is in the same voice channel.

### Skpi Currently Playing

Skips the current track if other tracks are in the play list. Will only succeed, if the requesting member is in the same voice channel.

### Stop Currently Playing

Stops the currently playing track. Will only succeed, if the requesting member is in the same voice channel.

### List Queue

Lists the names of the items in the playlist, starting with the currently playing file.

### Set As Track Finished

Sets the callback for when the current tack finished playing for possible file removal. Allows triggering of [Track finished](#track-finished)

### Subscribe To Event

Subscribes to a specified event. Allows triggering of [Event trigger](#event-trigger).

## Callbacks

Here will be some callbacks listed that will be sent out when subscribed to them

### Update

Sent when an update is requested from the bot. Contains no usefull data. :exclamation: This is an automatic callback. :exclamation:

Data ([Message object](#message)): 
```javascript
{
    "sender": "0000000000",
    "content": "",
    "channel": "0000000000",
    "called": "UPDATE",
    "attachments": [],
    "interface": None,
    "random_id": Random Integer
}
```

### Track finished

Sent when the client is subscribed to [Set As Track Finished](#set-as-track-finished).
Data ([Message object](#message)): 
```javascript
{
    "sender": "Bot",
    "content": String,
    "channel": None,
    "called": "TRACK FINISHED",
    "attachments": [],
    "interface": Interface.Discord,
    "random_id": Random Integer
}
```

### Event trigger

Sent when the client is subscribed to [Subscribe To Event](#subscribe-to-event).
Data ([Message object](#message)): 
```javascript
{
    "sender": "Bot",
    "content": String with the following values and formatting: "{event.value}|{before value}|{after value}",
    "channel": User DM Channel,
    "called": "EVENT",
    "attachments": [],
    "interface": Interface.Discord,
    "random_id": Random Integer
}
```
