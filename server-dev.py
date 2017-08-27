# Tarnished Tale Server
# Modernized, Security-Conscious MUD Client
# For full details, view the docs
global version
version = "DevBuild"

# Importing Key Modules
import asyncio
import bcrypt
import configparser
import datetime
import logging
import os
import ssl
import websockets as ws


# Defining Principal Classes


# Defining Functions
async def serveIn(sock, port):  # The basic runtime of the entire server goes into this function.
    print("New Connection by %s:%s" % (sock.remote_address[0], sock.remote_address[1]))
    await sock.send("Welcome to %s" % title) # TODO Generalize, call from config
    while True:  # This is stupid, never do this.
        msg = await sock.recv()
        response = await categorize(msg, sock)
        await taskTx(sock, response)

async def categorize(rx, sock):  # TODO testing only, should refactor and tweak in next build
    contentsRX = rx.split(" ")
    try:
        catRX = knownCommands[contentsRX[0]]
    except KeyError:
        catRX = None
    if catRX == "system":
        tx = await taskSys(rx, sock)  # refers to an as-yet unimplemented JoinableQueue
        return tx
    elif contentsRX[0] == "ATERM_MSG":  # this socket is attempting to authenticate as an admin terminal
        tx = await taskAdmin(rx, sock)
        return tx
    elif catRX is not None:
        tx = str("That request belongs to the %s category!" % catRX)
        return tx
    else:
        tx = str("I don't know how to do that!")
        return tx

def announce():
    # TODO implement a screen clear here.
    print("Welcome to Tarnished Tale Server %s" % version)
    print("Currently hosting %s" % title)
    print("Expecting connections on port %s" % portIn)

async def taskSys(message, requester):
    print("Made it to TaskSys")
    msg = message
    contents = msg.split(" ")
    operation = contents[0].lower()
    session = requester

    if operation == "register":  # expects "register user pass"
        print("%s is requesting to add user %s to the game." % (session.remote_address[0], contents[1]))
        if usersDB.has_option("Users", contents[1]):  #  Prevent overwrite of existing user entries
            print("Request cannot be completed - existing user.")
            tx = "This user already exists. Please change usernames and try again."
            return tx
        else:  # The user doesn't exist so let's add it
            salted = bcrypt.hashpw(contents[2].encode('utf8'), bcrypt.gensalt())
            salted = str(salted) # The next several lines are necessary or the salt/pw store is broken when read from config
            strip1 = salted.lstrip("b'")
            strip2 = strip1.rstrip("'")
            salted = strip2
            usersDB.set("Users", contents[1], str(salted)) #Stripping in this way before setting allows the value to be read back normally later
            with open(os.path.join(abspathHome, "Game Data/users.db"), "w") as db:
                usersDB.write(db)
            tx = "Your registration was successful. Please record your password for future reference."
            return tx
    elif operation == "login":  # expects "login user pass"
        print("%s is attempting to log in as %s" % (session.remote_address[0], contents[1]))
        try:
            pwdExpected = usersDB.get("Users", contents[1]).encode("utf8")
        except configparser.NoOptionError:
            pwdExpected = 0
        if bcrypt.checkpw(contents[2].encode('utf8'), pwdExpected):
            for user in sessions:  # Checks for an existing session logged in under that name
                if user == contents[1]:
                    tx = "Login failed"
                    return tx
            if usersDB.has_option("Banned", contents[1]):
                lifted = usersDB.getfloat("Banned", contents[1])
                now = datetime.datetime.now().timestamp()
                if lifted >= now:
                    usersDB.remove_option("Banned", contents[1])
                    with open(os.path.join(abspathHome, "Game Data/users.db"), "w") as f:
                        usersDB.write(f)
                else:
                    tx = "Login Failed"
                    return tx
            sessions.update(dict({contents[1]:session}))
            welcome = str("You are now %s" % contents[1])
            tx = welcome
            return tx
        else:
            tx = "Login Failed"  #Purposefully vague status
            return tx
    elif operation == "quit":
        tgt = sessions[session]
        del sessions[session]
        print("%s has quit" % tgt)
        tx = b"200"  # 200 closes connection "at client request".
        return tx

async def taskAdmin(message, sock):  # Handles messages from the admin console script
    bashed = message.lower()
    msg = bashed.split(" ")

    global sockAdmin
    if sock != sockAdmin:  # Authenticate this connection as the current admin console connection
        tx = await authAdmin(message, sock)
        return tx
    else:
        if msg[1] == "shutdown":  # Implements graceful shutdown!
            tx = await dieGracefully(bashed)
            return tx
        elif msg[1] == "fetch": # grab msg[2], one of a flavour of logs.
            pass
        elif msg[1] == "logging":  # Drop to a logging configuration editor
            pass
        elif msg[1] == "kick":  # Kick a player
            tx = await sysKick(msg[2], msg[3], msg[4], msg[5])
            return tx
        elif msg[1] == "chpwd":  # Change a user's password
            pass
        elif msg[1] == "unban":  # Remove a user ban
            tx = await sysUnban(msg[2])
        elif msg[1] == "quit":  # Disconnects the console and clears the admin socket
            sockAdmin = None
            tx = b"200"
            return tx
        else:
            tx = "Unrecognized Administrative Command"
            return tx
        tx = "You reached the fallthrough: this command must not be implemented"
        return tx

async def authAdmin(message, sock):  # simple authentication of the admin connection
    msg = message.split
    uid = msg[1]
    pwd = msg[2]

    if usersDB.has_option("SysAdmins", uid):  # checks if this user is allowed to be a sysadmin.
        if (sock.remote_address[0] == "172.0.0.1") or baseConfig.getboolean("Network Configuration", "Allow Remote Administration"):
            try:
                pwdExpected = usersDB.get("Users", uid).encode('utf8')
            except configparser.NoOptionError:
                pwdExpected = '0'.encode('utf8')
            if bcrypt.checkpw(pwd.encode("utf8"), pwdExpected):
                global sockAdmin; sockAdmin = sock
                tx = b"202"  # 202 "Request Accepted" indicates successful Auth.
                return tx
            else:
                tx = "Authentication Error, Please Retry Connection"
                return tx
        else:
            tx = "Remote administration is not enabled on this server"
            return tx

async def taskTx(sock, message):  # a poor implementation of an output coroutine.
    print("Made it to taskTX")
    if message == b"200":
        await sock.send("Goodbye.")
        await sock.close()
        return
    if message == b"202":
        await sock.send("Authentication Successful, you are now the admin terminal.")
    else:
        await sock.send(message)
        return

async def dieGracefully(message):  # This function performs all actions related to the graceful shutdown
    args = message.split("")
    delay = args[2]
    if delay == "now":
        delay = 0
    reason = args[3]  # TODO need to fix this, it's not right.

    while delay > 0:  # Do the delay routine
        if delay > 30:
            delay = await delay_by(300, delay)
        else:
            delay = await delay_by(30, delay)
    #Graceful Shutdown Starts Here
    broadcastGlobal(message)
    for player in sessions: # Alert players and then kick them
        sysKick(player, "Server Shutdown", False, 0)
    global running; running = False
    tx = "Shutdown Complete, exiting."
    print("Shutdown by admin console, exiting.")
    serving.stop()
    return tx

def startSSL():  # Start SSL Context by fetching some requisite items from the config files, if so configured
    if baseConfig.getboolean("Network Configuration", "TLS") is True:
        global ctx
        fCert = os.path.join(abspathHome, "Configuration/server.pem")
        fKey = os.path.join(abspathHome, "Configuration/server.pem")
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(certfile=fCert, keyfile=fKey)

async def delay_by(seconds, tofinal):
    if seconds < 60:
        message = ("[SERVER]A shutdown has been scheduled for %s seconds from now." % seconds)
    else:
        minutes = tofinal/60
        message = ("[SERVER]A shutdown has been scheduled for %s minutes from now." % minutes)
    broadcastGlobal(message)
    asyncio.sleep(seconds)
    newdelay = tofinal - seconds
    return newdelay

async def broadcastGlobal(message):
    for player in sessions:
        sock = sessions[player]
        await sock.send(message)


async def sysKick(player, reason, ban, lengthBan):
    try:
        sock = sessions[player]
    except KeyError:
        tx = "Failed to kick player - not logged in."
        return tx

    if not ban:
        sock.send("You have been kicked by the system for: %s" % reason)
    else:
        sock.send("You have been banned by the system for %s days for: %s" % (lengthBan, reason))
        now = datetime.datetime.now()
        future = datetime.timedelta(days=lengthBan)
        unbanned = now + future
        usersDB.set("Banned", player, str(unbanned.timestamp()))
        with open(os.path.join(abspathHome, "Game Data/users.db"), "w") as f:
            usersDB.write(f)
    del sessions[player]
    sock.close()
    tx = "Success"
    return tx

async def sysUnban(player):
    try:
        usersDB.remove_option("Banned", player)
        tx = ("%s has been unbanned" % player)
        return tx
    except configparser.NoOptionError:
        tx = ("%s was not banned!" % player)
        return tx

def startLogging():  # Initializes the various logging constructs, as globals.
    global userLogger  # The access record log
    global systemLogger # Logs access of and actions by the Admin Console

    userLogger = logging.getLogger("[USER]")
    userLogger.setLevel(logging.INFO)
    systemLogger = logging.getLogger("[SYSTEM]")
    if baseConfig.get("Logging Options", "Debugging"):
        systemLogger.setLevel(logging.DEBUG)
    else:
        systemLogger.setLevel(logging.INFO)

# Initialize the Config Parser&Fetch Globals, Build Queues, all that stuff
abspathHome = os.getcwd()
abspathBaseConfig = os.path.join(abspathHome, "Configuration/server_config.txt")
abspathModDats = os.path.join(abspathHome, "Configuration/Module Files")

baseConfig = configparser.ConfigParser()   # We need several parsers. This one will handle the basic config file.
baseConfig.read(abspathBaseConfig)

usersDB = configparser.ConfigParser()
usersDB.read(os.path.join(abspathHome, "Game Data/users.db"), encoding="utf8")

moduleConfig = configparser.ConfigParser()
# This reader will need to iterate over any and all .dat files in the Configuration/Module Files dir and integrate them
# into one namespace
sessions = {}
sockAdmin = None  # Global, gets set to the socket of the current admin console

title = baseConfig.get("Game Information", "Game Name")
portIn = baseConfig.get("Network Configuration", "Incoming Port")

knownCommands = {}
for foo, bar, files in os.walk(abspathModDats):  # crawls the module files looking for their command info.
    for file in files:
        moduleConfig.read(os.path.join(foo, file))
        if moduleConfig.has_section("Additional Commands"):
            options = moduleConfig.options("Additional Commands")
            for option in options:
                foo = moduleConfig.get("Additional Commands", option)
                newEntry = dict({str(option):str(foo)})
                knownCommands.update(newEntry)


# Runtime Time
announce()
startSSL()
startLogging()
global running; running = True
if baseConfig.getboolean("Network Configuration", "TLS") is True:
    start_server = ws.serve(serveIn, 'localhost', portIn, ssl=ctx)
else:
    start_server = ws.serve(serveIn, 'localhost', portIn)
serving = asyncio.get_event_loop().run_until_complete(start_server)
serving.run_forever()
