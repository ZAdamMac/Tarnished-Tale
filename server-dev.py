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
import logging.handlers
import os
import ssl
import sqlite3
import websockets as ws


# Defining Principal Classes


# Defining Functions
async def serveIn(sock, foo):  # The basic runtime of the entire server goes into this function.
    print("New Connection by %s:%s" % (sock.remote_address[0], sock.remote_address[1]))
    await sock.send("Welcome to %s" % title) # TODO Generalize, call from config
    global running
    while running:  # This is stupid, never do this.
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
        if extantUser(contents[1]):  #  Prevent overwrite of existing user entries
            print("Request cannot be completed - existing user.")
            tx = "This user already exists. Please change usernames and try again."
            return tx
        else:  # The user doesn't exist so let's add it
            salted = bcrypt.hashpw(contents[2].encode('utf8'), bcrypt.gensalt())
            salted = str(salted) # The next several lines are necessary or the salt/pw store is broken when read from config
            strip1 = salted.lstrip("b'")
            strip2 = strip1.rstrip("'")
            salted = strip2
            addargs = ([ contents[1], salted, False, False, False, False, False ])
            conUsers.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)', addargs)
            conUsers.commit()
            tx = "Your registration was successful. Please record your password for future reference."
            return tx
    elif operation == "login":  # expects "login user pass"
        print("%s is attempting to log in as %s" % (session.remote_address[0], contents[1])) # TODO change to log entry
        fooargs = (contents[1].lower())
        curse = conUsers.cursor()
        curse.execute('SELECT userID, passHash, isAdmin, isBanned, banExpy, MFAEnabled, token FROM users WHERE userID=?', (fooargs,))
        record = curse.fetchall()
        if len(record) == 0:
            tx = "Login Failed"
            return tx
        uid, hash, admin, banned, expyBan, MFA, tokenMFA = record[0]

        if banned:
            now = datetime.datetime.now().timestamp()
            if expyBan >= now:
                conUsers.execute('UPDATE users SET banned=False WHERE userid=?', uid)
            else:
                tx = "Login Failed"
                return tx

        authed = False # You must always start with the decision that Alice is actually Mallory
        authed = bcrypt.checkpw(contents[2].encode('utf8'), hash)
        if authed:
            sessions.update(dict({contents[1]:session}))
            welcome = str("You are now known as %s." % contents[1])
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

def extantUser(uname):
    conUsers.execute('SELECT userID FROM users WHERE userID = ?', (uname,))
    ret = conUsers.cursor().fetchall()
    if len(ret) == 0:
        return False
    else:
        return True

async def taskAdmin(message, sock):  # Handles messages from the admin console script
    bashed = message.lower()
    msg = bashed.split(" ")

    global sockAdmin
    if sock != sockAdmin:  # Authenticate this connection as the current admin console connection
        tx = await authAdmin(message, sock)
        return tx
    else:
        if msg[1] == "shutdown":  # Implements graceful shutdown!
            #Expects some arguments in the order shutdown now/delay reason
            tx = await dieGracefully(message)
            return tx
        elif msg[1] == "logging":  # Drop to a logging configuration editor
            tx = await setLoggingLevel(msg[2])
            return tx
        elif msg[1] == "kick":  # Kick a player
            tx = await sysKick(msg[2], msg[3], msg[4], msg[5])
            return tx
        elif msg[1] == "chpwd":  # Change a user's password
            tx = await adminChpwd(msg[2], message.split()[3])
            return tx
        elif msg[1] == "unban":  # Remove a user ban
            tx = await sysUnban(msg[2])
            return tx
        elif msg[1] == "quit":  # Disconnects the console and clears the admin socket
            sockAdmin = None
            tx = b"200"
            return tx
        else:
            tx = "Unrecognized Administrative Command"
            return tx

async def authAdmin(message, sock):  # simple authentication of the admin connection
    msg = message.split()
    user = msg[1]
    pwd = msg[2]

    conUsers.execute("SELECT userID, passHash, isAdmin, isBanned, MFAEnabled, token FROM users WHERE userID=?", user)
    result = conUsers.cursor().fetchone()
    uid, hash, isAdmin, isBanned, MFA, tokenMFA = result
    if len(result) == 0:
        tx = "Authentication Error, Please Retry Connection"
        return tx

    if isAdmin:  # checks if this user is allowed to be a sysadmin.
        if (sock.remote_address[0] == '127.0.0.1') or baseConfig.getboolean("Network Configuration", "Allow Remote Administration"):
            if bcrypt.checkpw(pwd.encode("utf8"), hash):
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
    args = message.split(" ")
    delay = args[2]
    if delay.lower() == "now":
        delay = 0
    reason = " ".join(args[3:])
    delay = int(delay)
    while delay > 0:  # Do the delay routine
        if delay > 300:
            delay = await delay_by(300, delay)
        else:
            delay = await delay_by(delay, delay)
    #Graceful Shutdown Starts Here
    await broadcastGlobal("[SERVER] This server has been shut down for the following: %s" % reason)
    thing = sessions.copy()
    for player in thing:
        await sysKick(player, "Server Shutdown", False, 0)
    global running; running = False
    tx = "Shutdown Complete, exiting."
    print("Shutdown by admin console, exiting.")
    asyncio.get_event_loop().stop()
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
    await broadcastGlobal(message)
    await asyncio.sleep(seconds)
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
        args = [unbanned, player]
        conUsers.execute('UPDATE users SET isBanned=True, banexpy =? WHERE userID=?', args)
        conUsers.commit()
    del sessions[player]
    sock.close()
    tx = "Success"
    return tx

async def sysUnban(player):
    conUsers.execute('UPDATE users SET isBanned=False, banExpy=False WHERE userID=?', player)
    conUsers.commit()
    tx = ("%s has been unbanned" % player)
    return tx

def startLogging():  # Initializes the various logging constructs, as globals.
    global userLogger  # The access record log
    global systemLogger # Logs access of and actions by the Admin Console
    global abspathDirLogs
    global baseConfig

    userLogger = logging.getLogger("[USER]")
    userLogger.setLevel(logging.INFO)
    systemLogger = logging.getLogger("[SYSTEM]")
    if baseConfig.get("Logging Options", "Debugging"):
        systemLogger.setLevel(logging.DEBUG)
    else:
        systemLogger.setLevel(logging.INFO)

    userLogger.addHandler(logging.handlers.TimedRotatingFileHandler(os.path.join(abspathDirLogs, "access.log"), when='midnight'))
    systemLogger.addHandler(logging.handlers.TimedRotatingFileHandler(os.path.join(abspathDirLogs, "system.log"), when='midnight'))

async def adminChpwd(target, newpass):
    salted = bcrypt.hashpw(newpass.encode('utf8'), bcrypt.gensalt())
    salted = str(salted)  # The next several lines are necessary or the salt/pw store is broken when read from config
    strip1 = salted.lstrip("b'")
    strip2 = strip1.rstrip("'")
    salted = strip2
    directions = salted, target
    conUsers.execute('UPDATE users SET passHash=? WHERE userID=?', directions)
    conUsers.commit()
    tx = ("Password reset successful; notify %s their password is reset!" % target)
    return tx

async def setLoggingLevel(level):
    if level == "debug":
        userLogger.setLevel(logging.DEBUG)
        systemLogger.addHandler(logging.DEBUG)
    elif level == "info":
        userLogger.setLevel(logging.INFO)
        systemLogger.setLevel(logging.INFO)
    else:
        tx = "That is not a valid logging level. Supported: info, debug"
        return tx
    tx = "Logging level set. This is not permanent - if a permenent change is desired, change the config."
    return tx

def startDB():  # We need to initialize a few databases using sqlite3
    isDB = os.path.isfile('Game Data/users.db')
    global conUsers
    conUsers = sqlite3.connect('Game Data/users.db')

    if not isDB:
        print("Couldn't find existing users.db, generating new.")
        conUsers.execute('''CREATE TABLE users
                            (userID, passHash, isAdmin, isBanned, banExpy, MFAEnabled, token)''')
        print("Naturally you will need an admin account.")
        uid = input("Username:")
        match = False
        while not match:
            pass1 = input("Password:")
            pass2 = input("Repeat Password:")
            if pass1 != pass2:
                print("Password's don't match!")
            else:
                match = True
        fooargs = [uid, bcrypt.hashpw(pass1.encode('utf8'), bcrypt.gensalt()), True, False, 0, False, 0]
        conUsers.execute('INSERT INTO users (userID, passHash, isAdmin, isBanned, banExpy, MFAEnabled, token) VALUES (?,?,?,?,?,?,?)', fooargs)
        conUsers.commit()

# Initialize the Config Parser&Fetch Globals, Build Queues, all that stuff
abspathHome = os.getcwd()
abspathBaseConfig = os.path.join(abspathHome, "Configuration/server_config.txt")
abspathModDats = os.path.join(abspathHome, "Configuration/Module Files")
abspathDirLogs = os.path.join(abspathHome, "Logs")

baseConfig = configparser.ConfigParser()   # We need several parsers. This one will handle the basic config file.
baseConfig.read(abspathBaseConfig)

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
startDB()
global running; running = True
if baseConfig.getboolean("Network Configuration", "TLS") is True:
    start_server = ws.serve(serveIn, 'localhost', portIn, ssl=ctx)
else:
    start_server = ws.serve(serveIn, 'localhost', portIn)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
