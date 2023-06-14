# Server monitoring Discord bot API

This API can be used to interface with the server monitoring Discord bot only if the API is enabled on it. For this, the bot needs to run on the same PC, or the API needs to be set up to allow outside connections.

## Usage

To create an api, import the package, and use the required arguments.

```
import smdb_api
API = smdb_api.API("Test", "80716cbfd9f90428cd308acc193b4b58519a4f10a7440b97aaffecf75e63ecec")
```

Avaleable arguments:

- name: string | Used to identify the application to the api server.
- key: string | Used to verify identity with the api server.
- ip: string (optional) | Used to set the api server's IP address.
- port: integer (optional) | Used to set the api server's listening port.
- update_function: function (optional) | Sets a callback function to call, when the api server updates.

To initiate the connection, use the validate command. The validate function can get a timeout limit, so it won't hault the program, if the api server won't ansvear within a set time.

```
API.validate()
server_status = API.get_status()
```

To add a command to the bot, use the 'create_function' command, like shown here:

```
[...]
def my_callback(message):
    #Does something

API.create_function("MyScript", "Some text to help\nUsage: &MyScript <User input>\nCategory: SERVER", my_callback)
```

To send a message to someone, use the 'send_message' command:

```
[...]
discordId="##################"
API.send_message("Test message to a channel", discordId)
print(f"I sent a message to {API.get_username(discordId)}!")
```

Closing the connection safely is easy with the 'close' command.

```
[...]
API.close("Some reason for the bot logger.")
```

## Available commands

### validate

This function connects to the API server and validates itself with it. If the validation was successful, it starts a listener thread.

### get_status

This function retrieves the bot's status and returns it in a dictionary.

### get_username

This command returns the given Discord ID's username.

### is_admin

Determines if a user is admin in the bot's database.

### send_message

This command allows you to send messages in the bot's name to selected users/channels or the default channel.

### create_function

This command creates a function in the bot that can be called by a user.

### connect_to_voice

This command connects the client to the user's voice channel

### disconnect_from_voice

This command disconnects the client from the user's voice channel

### play_file

Starts the audio file on the path provided. If the file is not supported error is returned.

### add_file

Adds the audio file to the play list on the path provided. If the file is not supported error is returned.

### pause_currently_playing

Pauses the currently playing track.

### resume_paused

Resumes playing the paused track.

### skip_currently_playing

Skips the current track if other tracks are in the play list.

### stop_currently_playing

Stops the currently playing track.

### get_queue

Lists the names of the items in the playlist, starting with the currently playing file.

### set_as_hook_for_track_finished

Sets the callback for when the current tack finished playing for possible file removal. Returns the title of the finished track in a message object.

### subscribe_to_event

Subscribes a callback to an event. Returns a string that represents the string value of the previous state, string that represents the string value of the new state, and a message object containing the dm channel for the user with the discord interface.
