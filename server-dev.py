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
import html5lib
from html5lib.filters import sanitizer
import json
import logging
import logging.handlers
import os
import ssl
import sqlite3
import websockets as ws


# Defining Principal Classes
class worldLoader(object): #A handler class for worlds used in first-time spin up and world generation
    def __init__(self, name): # On init, we need to determine some internal variables using configparser
        self.name = name

        tempParser = configparser.ConfigParser()
        tempParser.read(os.path.join(abspathHome,"Game Data/World Templates/%s/worldconfig" % self.name))

        #  The initial properties of the worldobject are the contents of worldconfig
        self.scry = tempParser.get("Map Controls", "Scry Hint")
        self.roguelike = tempParser.getboolean("Map Controls", "Roguelike")
        self.Dynamic = tempParser.getboolean("Map Controls", "Dynamic")
        self.rateRefresh = tempParser.getint("Map Controls", "Dynamic Rate")

    def rebuild(self):
        global conWorld
        global curWorld
        systemLogger.info("Now Loading World: %s", self.name)
        if not extantWorld(self.name):
            args = (self.name, self.roguelike, self.Dynamic, self.rateRefresh, self.scry)
            curUsers.execute("INSERT INTO worlds (name, roguelike, dynamic, rateDynamic, scryHint) VALUES (?,?,?,?,?,)", args)
            curUsers.execute("SELECT worldSID FROM worlds WHERE name=?", (self.name,))
            self.worldSID = curUsers.fetchall()
        rooms = []
        roomNums = []
        for root, null, roomfiles in os.walk(os.path.join(abspathWorlds, self.name)):
            for room in roomfiles:
                if room == "worldconfig":
                    pass
                else:
                    roomNums.append(room)  # Also adds the roomnumber to an index to be used in a later step.
        curWorld.execute("SELECT fileRoom FROM rooms WHERE world=?", (self.worldSID,))
        extantRooms = curWorld.fetchall()
        newRooms = diff(roomNums, extantRooms)
        if self.Dynamic:
            work = roomNums
            systemLogger.info("%s is Dynamic, updating all rooms.", self.name)
        else:
            work = newRooms
            systemLogger.info("%s is Static, updating only newly-added rooms", self.name)
        for r in work:
            rooms.append(roomLoader(r, self.name, self.worldSID))
        counter = 0
        for r in rooms:
            counter =+ 1
            r.insert() # calls the room object's magic parsing function
        systemLogger.info("World complete with %s changes", counter)

class roomLoader(object):

    def __init__(self, fname, parent, worldSID):
        self.fname = fname
        self.world = parent
        self.worldSID = worldSID

    def insert(self):
        systemLogger.debug("Starting to parse %s in world %s", self.fname, self.world)

        tempParser = configparser.ConfigParser()
        tempParser.read(os.path.join(abspathWorlds, os.path.join(self.world, self.fname)))
        id = self.fname
        roomName = tempParser.get("Description", "Name")
        descr = tempParser.get("Description", "Description")
        listContents = None # Inventory is unsupported and therefore nope.
        npcs = None #  npcs temporarily unimplemented
        scripts = None  # not implemented obviously.
        stmnt = ("SELECT roomUUID FROM rooms WHERE worldSID=? AND fileRoom=?")
        confuser = curWorld.execute(stmnt, (self.worldSID, self.fname,)).fetchall()
        exits = getListExits(tempParser, confuser)
        if len(confuser) == 0:
            systemLogger.debug("This is a new room, inserting.")
            stmnt=("INSERT INTO rooms (fileRoom, titleRoom, description, world, stringScripts) VALUES (?,?,?,?,?)")
            curWorld.execute(stmnt, (id, roomName, descr, self.worldSID, scripts) )
            conWorld.commit()
        else:
            systemLogger.debug("This room already exists, updating.")
            stmnt=("UPDATE rooms SET name=?, descr=?, stringScripts=? WHERE roomUUID=?" % self.world)
            curWorld.execute(stmnt, (roomName, descr, listContents, npcs, exits, scripts, confuser, ))
            conWorld.commit()
        tempParser = None

class characterSheet(object):  #  A temporary object to hold a character for manipulations from ability, and other checks.

    def __init__(self, targetCharacter):  # on init, briefly grab read from the SQL db and process accordingly
        self.target = targetCharacter #TODO Implement in full
        curUsers.execute("SELECT * FROM characters WHERE name=?", (targetCharacter,))
        self.compressed = curUsers.fetchall()
        self.target, self.owner, self.strConsumables, self.strAptitudes, self.strDerived, self.strFlavour, self.strCurrency, self.strRep, self.strSwitches, self.strSkills, self.strAttributes, self.strEquipment = self.compressed


class skillLoader(object):

    def __init__(self, path):
        self.abs = path
        self.reader = configparser.ConfigParser()

    def refresh(self):
        self.reader.read(self.abs)
        listSkills = self.reader.sections()

        curUsers.execute("SELECT nameSkill FROM skillbase")
        extantSkills = curUsers.fetchall()

        for skill in listSkills:
            options = self.reader.options(skill)
            desc = self.reader.get(skill, "desc")
            scoreBase = self.reader.get(skill,"base")
            hasAbilities = self.reader.getboolean(skill, "hasAbilities")
            strAbilities = "‽"
            if hasAbilities:
                for option in options:
                    if option in ["desc", "base", "hasabilities", "hasAbilities"]:
                        continue
                    else:
                        nameAbility = option
                        descAbility = self.reader.get(skill, option)
                        entry = str(nameAbility+"§"+descAbility)
                        strAbilities = strAbilities+str(entry+"‽")
            if (skill,) in extantSkills:
                fullEntry = (strAbilities, desc, scoreBase, skill)
                curUsers.execute("UPDATE skillbase SET strAbilities=?, desc=?, scoreBase=? WHERE name=?", fullEntry)
            else:
                fullEntry = (skill, strAbilities, desc, scoreBase)
                curUsers.execute("INSERT INTO skills (name, strAbilities, desc, scoreBase) VALUES (?,?,?,?)", fullEntry)
        conUsers.commit()

# Defining Functions
def getListExits(parser, parent):  # A function that parses the exit syntax to build the right list.
    listExits = parser.options("Exits")
    for door in listExits:
        nameDoor = door
        doorString = parser.get("Exits", door)
        firstSplits = doorString.split("§")
        desc, identifiers, isClosed, isLocked, lockDF, burstDF = firstSplits
        worldName, fileRoom = identifiers.split("/")
        curUsers.execute("SELECT worldSID FROM worlds WHERE name=?", (worldName,))
        worldSID = curUsers.fetchall()
        curUsers.execute("SELECT roomUUID FROM rooms WHERE fileRoom=? AND world=?", (fileRoom, worldSID))
        roomA = curUsers.fetchall()
        roomB = parent
        existanceCheck = curUsers.execute("SELECT doorID FROM doors WHERE linkA=? AND linkB=?", (roomA, roomB))
        args = (desc, roomA, roomB, isClosed, isLocked, lockDF, burstDF)
        if len(existanceCheck) == 0:
            curUsers.execute("INSERT INTO doors (description, linkA, linkB, isClosed, isLocked, lockDF, burstDF) VALUES (?,?,?,?,?,?,?)", args)
        else:
            args = (desc, roomA, roomB, isClosed, isLocked, lockDF, burstDF, existanceCheck)
            curUsers.execute('''UPDATE doors
                                SET description=?, linkA=?, linkB=?, isClosed=?, isLocked=?, lockDF=?, burstDF=?
                                WHERE doorID=?''', args)
    conUsers.commit()

def diff(first, second):  # simple function for diffing two lists.
    second = set(second)
    return [item for item in first if item not in second]

async def serveIn(sock, foo):  # The basic runtime of the entire server goes into this function.
    await sock.send(baseConfig.get("Game Information", "Welcome"))
    global running
    while running:  # This is stupid, never do this.
        msg = await sock.recv()
        response, mtype = await categorize(msg, sock)
        await taskTx(sock, response, mtype)

async def categorize(rx, sock):
    contentsRX = rx.split(" ")
    try:
        catRX = knownCommands[contentsRX[0]]
    except KeyError:
        catRX = None
    if catRX == "system":
        tx = await taskSys(rx, sock)  # refers to an as-yet unimplemented JoinableQueue
        return (tx, "ROOM")
    elif contentsRX[0] == "ATERM_MSG":  # this socket is attempting to authenticate as an admin terminal
        tx = await taskAdmin(rx, sock)
        return (tx, "SYS")
    elif catRX == "movement":
        tx = await taskMovement(rx, sock)
        return (tx, "ROOM")
    elif catRX == "ability":
        tx = await taskAbility(rx, sock)
        return (tx, "ROOM")
    elif catRX is not None:
        tx = str("That request belongs to the %s category!" % catRX)
        return tx
    else:
        tx = str("I don't know how to do that!")
        return tx

def announce():
    os.system("cls" if os.name=="nt" else "clear")
    print("Welcome to Tarnished Tale Server %s" % version)
    print("Currently hosting %s" % title)
    print("Expecting connections on port %s" % portIn)

async def taskAbility(message, requester):
    # TODO define this process. Something like:
    # From requester, fetch relevant charsheet object
    # Figure out which operation to do
    # Do it
    pass

async def taskMovement(message, requester):  # TODO test
    msg = message
    contents = msg.split(" ")
    operation = contents[0].lower()
    session = requester
    curAddy = positions[requester]
    posWorld = curAddy.split("/")[0]
    posRoom = curAddy.split("/")[1]
    stmnt = ("SELECT * FROM %s WHERE room=?" % posWorld)
    roomentry = curWorld.execute(stmnt, (posRoom,)).fetchall()
    roomid, name, descr, listContents, listNPCs, strExits, listScripts = roomentry[0]
    listExits = strExits.split("‽")

    if operation == "look":
        try:
            bar = contents[1]
        except IndexError:
            tx = await roomFormat(roomentry[0])
            return tx
        else: #We're looking at another room!
            targetRoom = contents[1].lower
            for direction in listExits:
                path = direction.split("§")[0].lower()
                if targetRoom == path:
                    isClosed = direction.split("§")[3].lower()
                    if isClosed == "true":
                        tx = "That door is closed."
                        return tx
                    else:
                        tx = await remoteViewer(direction.split("§")[2])
                        return tx
            tx = "You can't see there from here."
            return tx
    elif operation == "go":
        try:
            bar = contents[1]
        except IndexError:
            tx = "Where are you trying to go?"
            return tx
        destination = contents[1].lower
        for direction in listExits:
            way = direction.split("§")[0].lower()
            if destination == way:
                isClosed = direction.split("§")[3].lower
                if isClosed == "true":
                    tx = "That door is closed."
                    return tx
                else:
                    positions.update({session:direction.split("§")[2]})
                    tx = await remoteViewer(direction.split("§")[2])
                    return tx
        tx = "You don't know how to get there!"
        return tx
    elif operation == "open": # TODO implement
        tx = "Nobody's taught you to open doors yet!"
        return tx

async def roomFormat(roomentry): # Special function that formats a whole room for prettyprint
    roomID, name, descr, listContents, listNPCs, stringExits, listScripts = roomentry
    header = ("<br>%s (%s)<br>" % (name, roomID))
    body = ("%s</br>" % descr)
    listExits = stringExits.split("‽")
    listExitsPretty = []
    for door in listExits:
        try:
            direction,description,destination,isClosed,isLocked,lockDF = door.split("§")
            doorstring = ("To the <strong>%s<strong>: %s (%s)" % (direction, description, isClosed))
            listExitsPretty.append(doorstring)
        except ValueError:
            pass
    exits = ""
    if len(listExitsPretty) > 0:
        for door in listExitsPretty:
            newexits = exits+door
            exits = newexits
    if exits == "":
        exits = "<br>There are no visible exits from this room."
    tx = header+body+exits
    return tx

async def remoteViewer(target): # as roomFormat, but takes a target room for input.
    tWorld,tRoom = target.split("/")
    stmnt = ("SELECT * FROM %s WHERE room=?" % tWorld)
    roomentry = curWorld.execute(stmnt, (tRoom,)).fetchall()
    txReturned = await roomFormat(roomentry[0])
    tx, dropped = txReturned.split("<br>There are no visible exits from this room.")
    return tx

async def taskSys(message, requester):
    print("Made it to TaskSys")
    msg = message
    contents = msg.split(" ")
    operation = contents[0].lower()
    session = requester

    if operation == "register":  # expects "register user pass"
        userLogger.info("%s is requesting to add user %s to the game." % (session.remote_address[0], contents[1]))
        if extantUser(contents[1]):  #  Prevent overwrite of existing user entries
            userLogger.info("Request cannot be completed - existing user.")
            tx = "This user already exists. Please change usernames and try again."
            return tx
        else:  # The user doesn't exist so let's add it
            salted = bcrypt.hashpw(contents[2].encode('utf8'), bcrypt.gensalt())
            salted = str(salted) # The next several lines are necessary or the salt/pw store is broken when read from config
            strip1 = salted.lstrip("b'")
            strip2 = strip1.rstrip("'")
            salted = strip2
            addargs = ([ contents[1].lower(), salted, False, False, False, False, False ])
            conUsers.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)', addargs)
            conUsers.commit()
            tx = "Your registration was successful. Please record your password for future reference."
            return tx
    elif operation == "login":  # expects "login user pass"
        userLogger.info("%s is attempting to log in as %s" % (session.remote_address[0], contents[1]))
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
                conUsers.execute('UPDATE users SET banned=False WHERE userID=?', uid)
            else:
                tx = "Login Failed"
                return tx

        authed = False # You must always start with the decision that Alice is actually Mallory
        authed = bcrypt.checkpw(contents[2].encode('utf8'), hash.encode('utf8'))
        if authed:
            sessions.update(dict({session:contents[1]}))
            positions.update(dict({session:logroom}))
            welcome = str("You are now known as %s." % contents[1])
            tx = welcome
            userLogger.info("They were successful")
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
    curUsers.execute(''' SELECT userID FROM users WHERE userID=? ''', (uname,))
    ret = curUsers.fetchall()
    if len(ret) == 0:
        return False
    else:
        return True

def extantWorld(wname):
    curWorld.execute("SELECT name FROM worlds WHERE name=?", (wname,))
    extant = curWorld.fetchall()
    if len(extant) == 0:
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
            systemLogger.info("Admin has registered a shutdown for reason: %s" % msg[3])
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

    c = conUsers.cursor()
    c.execute("SELECT userID, passHash, isAdmin, isBanned, MFAEnabled, token FROM users WHERE userID=?", (user,))
    result = c.fetchone()
    uid, hash, isAdmin, isBanned, MFA, tokenMFA = result
    if len(result) == 0:
        tx = "Authentication Error, Please Retry Connection"
        return tx

    if isAdmin:  # checks if this user is allowed to be a sysadmin.
        if (sock.remote_address[0] == '127.0.0.1') or baseConfig.getboolean("Network Configuration", "Allow Remote Administration"):
            if bcrypt.checkpw(pwd.encode("utf8"), hash):
                global sockAdmin; sockAdmin = sock
                tx = b"202"  # 202 "Request Accepted" indicates successful Auth.
                systemLogger.info("%s authed as admin from %s" % (user, sock.remote_address[0]))
                return tx
            else:
                tx = "Authentication Error, Please Retry Connection"
                return tx
        else:
            tx = "Remote administration is not enabled on this server"
            return tx

async def taskTx(sock, message, mtype):  # a poor implementation of an output coroutine.
    global revertProtocol
    tp = html5lib.getTreeBuilder("dom")
    p = html5lib.HTMLParser(tree=tp)
    tw = html5lib.getTreeWalker("dom")
    parsedTX = p.parseFragment(message)
    cleanTX = sanitizer.Filter(tw(parsedTX))
    s = html5lib.serializer.HTMLSerializer()
    pretx = s.serialize(cleanTX)
    tx = ''
    for item in pretx:
        tx += item
    if message == b"200":
        await sock.send("Goodbye.")
        await sock.close()
        return
    if message == b"202":
        await sock.send("Authentication Successful, you are now the admin terminal.")
    else:
        if revertProtocol:
            await sock.send(tx)
            return
        else:
            await sock.send(json.dumps({"MSG_TYPE":mtype, "MSG":tx}))
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
    conUsers.commit()
    conWorld.commit()
    tx = "Shutdown Complete, exiting."
    print("Shutdown by admin console, exiting.")

    asyncio.get_event_loop().stop()
    return tx

def startSSL():  # Start SSL Context by fetching some requisite items from the config files, if so configured
    print("Configuring base SSL Context. You will be asked for the key for your certificate.")
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
        tx = message
        await sock.send(tx)

async def sysKick(player, reason, ban, lengthBan):
    try:
        sock = sessions[player]
    except KeyError:
        tx = "Failed to kick player - not logged in."
        return tx

    if not ban:
        sock.send("You have been kicked by the system for: %s" % reason)
        userLogger.info("%s kicked by admin because %s" % (player, reason))
    else:
        userLogger.info("Admin has banned %s for %s days because: %s" % (player, lengthBan, reason))
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
    userLogger.info("%s was unbanned by administrative override" % player)
    return tx

def startLogging():  # Initializes the various logging constructs, as globals.
    print("Starting the loggers. Logs are stored at %s" % abspathDirLogs)
    global userLogger  # The access record log
    global systemLogger # Logs access of and actions by the Admin Console

    logging.basicConfig(format='%(asctime)s %(message)s')

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
    userLogger.info("The Admin changed %s's password!" % target)
    systemLogger.info("The current Admin changed the password of %s" % target)
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
    tx = "Logging level set. This is not permanent - if a permanent change is desired, change the config."
    return tx

def startDB():  # We need to initialize a few databases using sqlite3
    print("Fetching the Databases")
    isDB = os.path.isfile('Game Data/game.db')
    global conUsers
    global curUsers
    global abspathWorlds
    conUsers = sqlite3.connect('Game Data/game.db')
    curUsers = conUsers.cursor()

    if not isDB:
        print("Couldn't find existing users table, the database is missing. Generating new.")
        conUsers.execute('''CREATE TABLE users (
                            userSID int NOT NULL AUTO_INCREMENT,
                            userID,
                            passHash,
                            isAdmin,
                            isBanned,
                            banExpy,
                            MFAEnabled,
                            token,
                            PRIMARY KEY (userSID)
                        );''')
        print("Naturally you will need an admin account.")
        uid = input("Username:")
        match = False
        while not match:
            pass1 = input("Password:") #TODO lets turn this into something more secure shall we!
            pass2 = input("Repeat Password:")
            if pass1 != pass2:
                print("Password's don't match!")
            else:
                match = True
        fooargs = [uid, bcrypt.hashpw(pass1.encode('utf8'), bcrypt.gensalt()), True, False, 0, False, 0]
        conUsers.execute('INSERT INTO users (userID, passHash, isAdmin, isBanned, banExpy, MFAEnabled, token) VALUES (?,?,?,?,?,?,?)', fooargs)
        conUsers.execute('''CREATE TABLE skillbase
                            (skillSID int NOT NULL AUTO_INCREMENT,
                            nameSkill, 
                            strAbilities, 
                            desc, 
                            scoreBase,
                            PRIMARY KEY (skillSID))''')
        conUsers.execute('''CREATE TABLE characters
                            (charSID int NOT NULL AUTO_INCREMENT, 
                            nameCharacter,
                            position, 
                            ownerSID,
                            shortDesc,
                            longDesc,
                            raceSID,
                            gender,
                            HPMax,
                            HPcurrent,
                            STR,
                            DEX,
                            CON,
                            INT,
                            WIS,
                            CHA,
                            FOR,
                            WIL,
                            LUCK,
                            factorDef,
                            dodgeChance,
                            PRIMARY KEY (charSID)
                            FOREIGN KEY (ownerSID) REFERENCES users(userSID)
                            FOREIGN KEY (position) REFERENCES rooms(roomUUID)
                            FOREIGN KEY (raceSID) REFERENCES races(raceSID)
                            );''')
        conUsers.execute('''CREATE TABLE races(
                            raceSID int NOT NULL AUTO_INCREMENT,
                            nameRace,
                            helpText,
                            dSTR,
                            dDEX,
                            dCON,
                            dINT,
                            dWIS,
                            dCHA,
                            nativeAttributes,
                            PRIMARY KEY (raceSID)
                            );''')
        conUsers.execute('''CREATE TABLE skillscores(
                            character,
                            skill,
                            score,
                            FOREIGN KEY (character) REFERENCES characters(characterSID)
                            FOREIGN KEY (skill) REFERENCES skillbase(skillSID)
                            );''')
        conUsers.execute('''CREATE TABLE switchbase(
                            switch int NOT NULL AUTO_INCREMENT,
                            purpose,
                            PRIMARY KEY (switch)
                            );''')
        conUsers.execute('''CREATE TABLE charswitches(
                            character,
                            switch,
                            state
                            FOREIGN KEY (character) REFERENCES characters(characterSID)
                            FOREIGN KEY (switch) REFERENCES switchbase(switch) 
                            );''')
        conUsers.execute('''CREATE TABLE cashbase(
                            currepID int NOT NULL AUTO_INCREMENT,
                            currepName,
                            currepHelpText,
                            PRIMARY KEY (currepID)
                            );''')
        conUsers.execute('''CREATE TABLE cashbase(
                            character,
                            currepID,
                            score,
                            FOREIGN KEY (character) REFERENCES characters(characterSID)
                            FOREIGN KEY (currepID) REFERENCES cashbase(currepID)
                            );''')
        conUsers.execute('''CREATE TABLE atribbase(
                            atribID int NOT NULL AUTO_INCREMENT,
                            atribName,
                            atribHelp,
                            PRIMARY KEY (atribID)
                            );''')
        conUsers.execute('''CREATE TABLE atribscores(
                            character,
                            npc,
                            attribute,
                            expy,
                            FOREIGN KEY (character) REFERENCES characters(characterSID)
                            FOREIGN KEY (attribute) REFERENCES atribbase(atribID)
                            FOREIGN KEY (npc) REFERENCES instmobs(mobInstID)
                            );''')
        conUsers.execute('''CREATE TABLE itembase(
                            itemSID int NOT NULL AUTO_INCREMENT,
                            itemName,
                            lookDesc,
                            helpText,
                            startingUses,
                            equipsTo,
                            isWeapon,
                            attack,
                            defense,
                            stringEffects,
                            PRIMARY KEY (itemSID)
                            );''')
        conUsers.execute('''CREATE TABLE globalinventory(
                            itemInstanceID int NOT NULL AUTO_INCREMENT,
                            item,
                            owner,
                            location,
                            remainingUses,
                            equippedSlot,
                            modDef,
                            modAtk,
                            modEffect,
                            PRIMARY KEY (itemInstanceID),
                            FOREIGN KEY (item) REFERENCES itembase(itemSID),
                            FOREIGN KEY (owner) REFERENCES characters(characterSID),
                            FOREIGN KEY (location) REFERENCES rooms(roomUUID),
                            );''')
        conUsers.execute('''CREATE TABLE mobsbase(
                            mobSpecSID int NOT NULL AUTO_INCREMENT,
                            mobName,
                            maxHP,
                            ATK,
                            DEF,
                            DMG,
                            hostility,
                            stringDropsTable,
                            stringDefaultAtribs,
                            PRIMARY KEY (mobSpecSID),
                            );''')
        conUsers.execute('''CREATE TABLE instmobs(
                            mobInstID int NOT NULL AUTO_INCREMENT
                            curHP
                            position,
                            hostility,
                            PRIMARY KEY (mobInstID),
                            FOREIGN KEY (position) REFERENCES rooms(roomUUID),
                            );''')
        conUsers.execute('''CREATE TABLE worlds(
                            worldSID int NOT NULL AUTO_INCREMENT,
                            name,
                            roguelike,
                            dynamic,
                            rateDynamic,
                            scryHint,
                            PRIMARY KEY (worldSID),
                            );''')
        conUsers.execute('''CREATE TABLE rooms(
                            roomUUID int NOT NULL AUTO_INCREMENT,
                            world,
                            fileRoom,
                            titleRoom,
                            description,
                            stringScripts,
                            PRIMARY KEY (roomUUID),
                            FOREIGN KEY (world) REFERENCES worlds(worldSID),
                            );''')
        conUsers.execute('''CREATE TABLE doors(
                            doorID int NOT NULL AUTO_INCREMENT,
                            description,
                            linkA,
                            linkB,
                            isClosed,
                            isLocked,
                            lockDF,
                            burstDF,
                            PRIMARY KEY (doorID),
                            FOREIGN KEY (linkA) REFERENCES rooms(roomUUID),
                            FOREIGN KEY (linkB) REFERENCES rooms(roomUUID),
                            );''')
        conUsers.commit()
        print("Database tables created.")
    print("Users Database Loaded")

    global conWorld
    global curWorld
    conWorld = sqlite3.connect('Game Data/game.db')
    curWorld = conWorld.cursor()
    if not isDB:
        print("Warning: The world database was not found.")
        print("Beginning first-pass world gen. This could take some time.")
    bootRenew()
    print("World Database Loaded.")

    loadSkills()
    print("Skills Database Loaded")

def bootRenew():  # Special world-renew called only on server launch.
    worlds = []
    for currentDir, subdirs, files in os.walk("Game Data/World Templates"):
        if currentDir.endswith("Game Data/World Templates"):
            continue
        else:
            thisWorld = worldLoader(os.path.basename(currentDir))
            worlds.append(thisWorld)
    for w in worlds:
        w.rebuild()
    conWorld.commit()

def loadSkills():  # Crawl for skill description files and load them into the db.
    skillbooks = []
    for currentDir, subdirs, files in os.walk("Configuration/Module Files"):
        for file in files:
            if file.endswith("skills.dat"):
                thisSkillBook = skillLoader(os.path.join(currentDir, file))
                skillbooks.append(thisSkillBook)
    for b in skillbooks:
        b.refresh()

# Initialize the Config Parser&Fetch Globals, Build Queues, all that stuff
global abspathHome; abspathHome = os.getcwd()
global abspathBaseconfig; abspathBaseConfig = os.path.join(abspathHome, "Configuration/server_config.txt")
global abspathModDats; abspathModDats = os.path.join(abspathHome, "Configuration/Module Files")
global abspathDirLogs; abspathDirLogs = os.path.join(abspathHome, "Logs")
global abspathWorlds; abspathWorlds = os.path.join(abspathHome, "Game Data/World Templates")

baseConfig = configparser.ConfigParser()   # We need several parsers. This one will handle the basic config file.
baseConfig.read(abspathBaseConfig)

moduleConfig = configparser.ConfigParser()
# This reader will need to iterate over any and all .dat files in the Configuration/Module Files dir and integrate them
# into one namespace
sessions = {}
positions = {}
sockAdmin = None  # Global, gets set to the socket of the current admin console

title = baseConfig.get("Game Information", "Game Name")
portIn = baseConfig.get("Network Configuration", "Incoming Port")
logroom = baseConfig.get("World Controls", "CHAR Room")
revertProtocol = baseConfig.getboolean("Network Configuration", "Revert to Old Protocol")

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
print("Great, starting service.")
global running; running = True
if baseConfig.getboolean("Network Configuration", "TLS") is True:
    start_server = ws.serve(serveIn, 'localhost', portIn, ssl=ctx)
else:
    start_server = ws.serve(serveIn, 'localhost', portIn)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

# TODO future pushing goes to DEV you idiot!
# TODO Fix characterSheet, have it Do The Things Right.