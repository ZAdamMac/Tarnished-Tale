# Tarnished Tale Server
# Modernized, Security-Conscious MUD Client
# For full details, view the docs
global version
version = "DevBuild"

# Importing Key Modules
import asyncio
import bcrypt
import configparser
import os
import websockets as ws


# Defining Principal Classes


# Defining Functions
async def serveIn(sock, port):  # The basic runtime of the entire server goes into this function.
    print("New Connection by %r at %s" % (sock, port))
    await sock.send("Welcome to %s" % title)
    while True:  # This is stupid, never do this.
        msg = await sock.recv()
        await categorize(msg, sock)

async def categorize(rx, sock): #TODO testing only, should refactor and tweak in next build
    contentsRX = rx.split(" ")
    try:
        catRX = knownCommands[contentsRX[0]]
    except KeyError:
        catRX = None
    if catRX is not None:
        tx = str("That request belongs to the %s category!" % catRX)
        await taskTx(sock, tx)
        return
    elif catRX is "system":
        await taskSys(rx, sock)  # refers to an as-yet unimplemented JoinableQueue
        return
    else:
        tx = str("I don't know how to do that!")
        await taskTx(sock, tx)
        return

def announce():
    # TODO implement a screen clear here.
    print("Welcome to Tarnished Tale Server %s" % version)
    print("Currently hosting %s" % title)
    print("Expecting connections on port %s" % portIn)

async def taskSys(message, requester):
    msg = message
    contents = message.split(" ")
    operation = contents[0].lower()
    session = requester

    if operation == "register":  # expects "register user pass"
        print("%s is requesting to add user %s to the game." % (session, contents[1]))
        if usersDB.has_option("Users", contents[1]):  #  Prevent overwrite of existing user entries
            print("Request cannot be completed - existing user.")
            await taskTx(session, "This user already exists. Please change usernames and try again.")
            return
        else:  # The user doesn't exist so let's add it
            salted = bcrypt.hashpw(bin(contents[2]), bcrypt.gensalt())
            usersDB.set("Users", contents[1], salted)
            await taskTx(session, "Your registration was successful. Please record your password for future reference.")
            return
    elif operation == "login":  # expects "login user pass"
        print("%s is attempting to log in as %s" % (session, contents[1]))
        try:
            pwdExpected = usersDB.get("Users", contents[1])
        except configparser.NoOptionError:
            pwdExpected = 0
        if bcrypt.checkpw(contents[2], pwdExpected):
            sessions.update(dict({session:contents[1]}))
            welcome = str("You are now %s" % contents[1])
            await taskTx(session, welcome)
            return
        else:
            await taskTx(session, "Login Failed")  #Purposefully vague status
            return
    elif operation == "quit":
        tgt = sessions[session]
        del sessions[sessions]
        print("%s has quit" % tgt)
        taskTx(session, b"200")  # 200 closes connection "at client request".
        return

async def taskTx(sock, message):  # a poor implementation of an output coroutine.
    if message == b"200":
        sock.send("Goodbye.")
        sock.close()
        return
    else:
        sock.send(message)
        return


# Initialize the Config Parser&Fetch Globals, Build Queues, all that stuff
abspathHome = os.getcwd()
abspathBaseConfig = os.path.join(abspathHome, "Configuration/server_config.txt")
abspathModDats = os.path.join(abspathHome, "Configuration/Module Files")

baseConfig = configparser.ConfigParser()   # We need several parsers. This one will handle the basic config file.
baseConfig.read(abspathBaseConfig)

usersDB = configparser.ConfigParser()  # TODO implement salted storage
usersDB.read(os.path.join(abspathHome, "Game Data/users.db"))

moduleConfig = configparser.ConfigParser()
# This reader will need to iterate over any and all .dat files in the Configuration/Module Files dir and integrate them
# into one namespace
sessions = {}

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
    start_server = ws.serve(serveIn, 'localhost', portIn)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
