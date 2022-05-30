# Server monitoring Discord bot Logger

## Possible log formats:

 * [COUNTER] [LEVEL]: DATA{END}
 * [COUNTER] [FILE_NAME->METHOD_1->...->CALLER]: DATA{END}
 * [COUNTER] [METHOD_1->...->CALLER]: DATA{END}

## Available log levels:

 * DEBUG
 * INFO
 * WARNING
 * ERROR
 * HEADER

## Options:

 | Variable name                      | Description                                                         | Default value      |
 |:-----------------------------------|:--------------------------------------------------------------------|:------------------:|
 | log_file                           | The name of the log file                                            | -                  |
 | log_folder                         | The path of the folder to save the log file                         | Current Directory  |
 | clear                              | Clears the log file every time it's initialized                     | False              |
 | level                              | Sets the minimum level for the logger to show                       | INFO               |
 | log_to_console                     | Sets to log to console too                                          | False              |
 | storage_life_extender_mode         | Limits the writes to the file by caching the data                   | False              |
 | max_logfile_size                   | Limits the size of one log file in MB                               | -1 (No limit)      |
 | max_logfile_lifetime               | Limits the time a log file can live (except the currently used one) | -1 (No limit)      |
 | __print                            | Callable for consol logging                                         | stdout.write       |
 | use_caller_name                    | Use the caller's name in consol logging instead of the level        | False              |
 | use_file_names                     | Use the file name whe using the caller name or not                  | True               |
 | level_only_valid_for_console       | Sets to log the unwanted levels but don't display them in console   | False              |

## Additional info

The consol logging uses colors for the different levels to be more recognisable at a glance. It also supports headers, after which it indents the logs to add some structure.

### DEBUG

 - ![](https://via.placeholder.com/150/000000/e600e5?text=E600E5) `#E600E5`

### INFO

 - ![](https://via.placeholder.com/150/000000/0bff00?text=0BFF00) `#0BFF00`

### WARNING

 - ![](https://via.placeholder.com/150/000000/feff00?text=FEFF00) `#FEFF00`

### ERROR

 - <span style="color: #FF0000">#FF0000</span>

### HEADER

 - ![](https://via.placeholder.com/150/000000/4182b7?text=4182B7) `#4182B7`

## Available methods

### get_buffer()

    Return sthe buffer's content in a list, if the logger is set to use buffers.

### flush_buffer()

    Forces a writes of the buffer to the log file.

### set_level(level)

    Sets the loggers leve to be used from this point onwards.

### log(level, data, counter = str(datetime.now()), end = "\n")

    Creates a log entry with the given level.

### header(data, counter = str(datetime.now()), end = "\n")

    Creates a HEADER level log entry.

### debug(data, counter = str(datetime.now()), end = "\n")
 
    Creates a DEBUG level log entry.

### warning(data, counter = str(datetime.now()), end = "\n")

    Creates a WARNING level log entry.

### info(data, counter = str(datetime.now()), end = "\n")

    Creates a INFO level log entry.

### error(data, counter = str(datetime.now()), end = "\n")

    Creates a ERROR level log entry.
 