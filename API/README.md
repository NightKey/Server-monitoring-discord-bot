# Server monitoring Discord bot API

This API can be used to interface with the server monitoring Discord bot, if the API is enabled on it. For this, the bot needs to run on the same PC, or the API needs to be set up to allow outside connections.

## Usage

To initiate the connection, use the validate command.

```
import smdb_api
API = smdb_api.API("Test", "80716cbfd9f90428cd308acc193b4b58519a4f10a7440b97aaffecf75e63ecec")
API.validate()
server_status = API.get_status()
```

To add a command to the bot, use the 'create_function' command, like shown here:

```
[...]
def my_callback(user_input):
    #Does something

API.create_function("MyScript", "Shome text to help\nUsage: &MyCommand <User input>\nCategory: SERVER", my_callback, return_value=[smbd_api.USER_INPUT])
```
To send message to someone, use the 'send_message' command:

```
[...]
discordId="##################"
API.send_message("Test message to a channel", discordId)
print(f"I sent a message to {my_user_name = API.get_username(discordId)}!")
```

Closing the connection safely, is easi with the 'close' command.

```
[...]
API.close("Some reason for the bot logger.")
```

## Avaleable commands

### validate

This function connect to the API server, and validates with it. If the validation was successfull, it starts a listener thread.

### get_status

This function retrives the bot's status, and returns it in a dictionary.

### get_username

This command returns the given Discord ID's username.

### send_message

This command allows you to send messages in the bot's name to selected users/channels, or the default channel.

### create_function

This command creates a function in the bot that can be called by a user.