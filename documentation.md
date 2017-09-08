# Tarnished Tale Documentation


## Overall
All executable parts of this project are written in python 3.6, which must be installed on your system for the software to run correctly.

Tarnished Tale relies heavily on the Websockets and TLS technologies to provide communications and security, respectively. These functions are provided by the python modules `websockets` and `ssl` respectively. `websockets` is not a standard python module and must be installed with `pip install websockets`.

Network connections between `server-dev.py`, `admin.py` and the web client use TCP port 5050 by default. You will have to forward this port if your server is behind a NAT and add exceptions in your firewall. This port is configurable - see the section on the server.
 ***
## Server
***Note: Server-dev.py is development-grade software. No warranty is made of its fitness for purpose.***

The majority of function on a Tarnished Tale-based MUD takes place serverside, with the various client types relegated purely to I/O. Accordingly, the software is designed with this in mind.

The server has a special dependency in the python module for `bcrypt`. The computer acting as server must have this module installed, which is done using pip as usual.

### Configuration
The configuration subdirectory contains most of the information the server needs to know about its expected operation. Specifically, it contains the server's TLS certificate, a `server_config.txt` ini file, and a subdirectory for loading module files.

#### server_config.txt
This file controls all configuration options of the server, here discussed in full.

##### Game Information
`Game Name`: Set the name of the game. This is used in various announce and welcome variables and is intended for other future purposes.

##### Network Configuration
`Incoming Port`: Int which sets the TCP port the server will accept incoming client connections on. If this value is changed, it will also have to be changed for any clients users are expected to connect with. The default value is 5050, and not known to be assigned to any other program.

`TLS`: Boolean that controls the server's use of TLS. It is strongly discouraged to set this value to false except during local development. Without TLS, all communications, including passwords, are transmited in the plain.

`Allow Remote Administration`: Boolean that controls whether or not a remote host running `admin.py` can connect to the server and issue admin commands. If set to false, admin.py must be run from localhost. Remote administration is still possible if False by using an SSH session to the server's host, which may be more secure.

##### Logging Options
`Debugging`: Boolean that elevates the log detail level to "debugging", generating more output.

#### server.pem
A PEM-format SSL certificate of any valid type which much be provided if the server is to be run in SSL mode. **It is important to note that this certificate must be the same certificate used to host the web client for a connection to be established under many modern browsers**

#### Module Files
A directory in which future expansion modules are placed to install their functionality to the server. This directory also contains data files that teach the server its known_commands list during startup and aid in module handling. This feature is not fully implemented

### Game Data
A directory in which the various data for making up the game world and playerbase will live.

#### users.db
`users.db` is a configparser file used as a database which contains various user information, as described below.

##### Users
A general category that contains all users, player or otherwise, listed by their name, with their value set to an encoded string which describes their relationship with their password's salted hash and salt. Passwords are stored as salted hashes using bcrypt.

##### SysAdmins
Category listing `user = True`. Users in this category have System Admin privledges and can authenticate to the admin console functions. This is not the same as Demigod or God privledges in-game, though there is some overlap.

##### Banned
Category listing users who are banned; their value is a unix timestamp of the expiration of their ban. Currently, only time-based bans of individual users is supported. Support for IP bans and indefinite bans is under development.

### Logs
Logs are stored in the log directory. They are rotating binary files.

### Server Functions
#### Userspace-Accessable Functions
At present all userspace-accessable functions are hidden in the KnownCommands list. Only the system commands are enumerated at present.
 - `login user pwd` will authenticate a user to the system. If an unregistered user or wrong password is given, or the user is banned, the login attempt will fail. If successful, the user and their socket are registered as active. Failure messages are purposefully non-specific.
 - `register user pwd` will register a new user with the specified password, provided that user does not already exist. Registrations are currently stupid - that is, no confirmation of the password is made and no provision for lost password recovery is made. At present, a user who loses their password must have that password reset by admin. This is a focus of further development.
 - `quit` deregisters the current connection and has the socket closed from the server side.

Other functions for userspace are enumerated in knownCommands but are not yet defined and possess no utility.

#### Admin Console Functions
***Note: these functions are all accessable by the web client if prefixed with `ATERM_MSG`!***

 - `user pass` is the mandatory first message as the server will first wish to authenticate a connection as a valid sysadmin, regardless of actual client type. If successful (right password AND privledged user), the socket is registered as the admin socket.
 - `shutdown delay some-message` initiates a graceful shutdown after some delay (if `now` is provided, delay=0) in seconds. At regular intervals during the delay the reason message is broadcast to all registered-active users. This provides time for the queue of user activities to execute which will also be sufficient to save the game state before shutdown. Even if shutdown=0, the server will not come down until all enqueued tasks complete.
 - `logging level` changes the logging level to `level`. Debugging and Info are the only currently used levels. This change is saved into config.
 - `kick player reason banning? length` kicks a player, deregistering them as active and closing their socket after informing them of `reason`. If `banning`, bans the player for `length` days. Note that a ban will not clear until the next time that player attempts to log in. Even if expired, they will appear in the banned list until they attempt to log in, at which point the ban clears and the login continues.
 - `chpwd user pwd` changes the password of `user` to `pwd` and is intended to be used as a rudimentary method of password recovery.
 - `unban player` removes player from the banned list regardless of ban length remaining.
 - `quit` deregisters the admin socket and, if connected over admin.py, implicitly shuts down the admin console as well.

Any commands issued from the admin console apart from this will return the error "Unrecognized Administrative Command", including if the admin for some reason attempts to use userspace commands from the admin console.

