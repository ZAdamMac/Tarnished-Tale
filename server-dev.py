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
import ssl
import websockets as ws


# Defining Principal Classes


# Defining Functions
async def serveIn(sock, port):  # The basic runtime of the entire server goes into this function.
    print("New Connection by %r at %s" % (sock, port))
    await sock.send("Welcome to %s" % title)
    while True:  # This is stupid, never do this.
        print("Awaiting new Message")  # Todo Del
        msg = await sock.recv()
        response = await categorize(msg, sock)
        await taskTx(sock, response)

async def categorize(rx, sock):  # TODO testing only, should refactor and tweak in next build
    print("Made it to Categorize")  # Todo Del
    contentsRX = rx.split(" ")
    try:
        catRX = knownCommands[contentsRX[0]]
    except KeyError:
        catRX = None
    if catRX == "system":
        tx = await taskSys(rx, sock)  # refers to an as-yet unimplemented JoinableQueue
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
        print("%s is requesting to add user %s to the game." % (session, contents[1]))
        if usersDB.has_option("Users", contents[1]):  #  Prevent overwrite of existing user entries
            print("Request cannot be completed - existing user.")
            tx = "This user already exists. Please change usernames and try again."
            return tx
        else:  # The user doesn't exist so let's add it
            salted = bcrypt.hashpw(contents[2].encode('utf8'), bcrypt.gensalt())
            salted = str(salted)
            strip1 = salted.lstrip("b'")
            strip2 = strip1.rstrip("'")
            salted = strip2
            usersDB.set("Users", contents[1], str(salted))
            with open(os.path.join(abspathHome, "Game Data/users.db"), "w") as db:
                usersDB.write(db)
            tx = "Your registration was successful. Please record your password for future reference."
            return tx
    elif operation == "login":  # expects "login user pass"
        print("%s is attempting to log in as %s" % (session, contents[1]))
        try:
            pwdExpected = usersDB.get("Users", contents[1]).encode("utf8")
        except configparser.NoOptionError:
            pwdExpected = 0
        if bcrypt.checkpw(contents[2].encode('utf8'), pwdExpected):
            sessions.update(dict({session:contents[1]}))
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

async def taskTx(sock, message):  # a poor implementation of an output coroutine.
    print("Made it to taskTX")
    if message == b"200":
        await sock.send("Goodbye.")
        await sock.close()
        return
    else:
        await sock.send(message)
        return

def startSSL():  # Start SSL Context by fetching some requisite items from the config files, if so configured
    if baseConfig.getboolean("Network Configuration", "TLS") is True:
        global ctx
        fCert = os.path.join(abspathHome, "Configuration/ssl_cert.pem")
        fKey = os.path.join(abspathHome, "Configuration/ssl_key.key")  # Todo find out what the default extension for this actually is
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(certfile=fCert, keyfile=fKey)


# Initialize the Config Parser&Fetch Globals, Build Queues, all that stuff
abspathHome = os.getcwd()
abspathBaseConfig = os.path.join(abspathHome, "Configuration/server_config.txt")
abspathModDats = os.path.join(abspathHome, "Configuration/Module Files")

baseConfig = configparser.ConfigParser()   # We need several parsers. This one will handle the basic config file.
baseConfig.read(abspathBaseConfig)

usersDB = configparser.ConfigParser()  # TODO implement salted storage
usersDB.read(os.path.join(abspathHome, "Game Data/users.db"), encoding="utf8")

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
    startSSL()
    if baseConfig.getboolean("Network Config", "TLS") is True:
        start_server = ws.serve(serveIn, 'localhost', portIn, ssl=ctx)
    else:
        start_server = ws.serve(serveIn, 'localhost', portIn)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
