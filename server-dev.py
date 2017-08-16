# Tarnished Tale Server
# Modernized, Security-Conscious MUD Client
# For full details, view the docs
global version
version = "DevBuild"

# Importing Key Modules
import asyncio
import bcrypt
import configparser
import multiprocessing as mp
import os
import websockets as ws


# Defining Principal Classes
class taskSys(object):
    def __init__(self, message, requester):
        self.msg = message
        self.contents = message.split(" ")
        self.operation = self.contents[0].lower()
        self.session = requester

    def __call__(self):
        if self.operation == "register":  # expects "register user pass"
            print("%s is requesting to add user %s to the game." % self.session, self.contents[1])
            salted = bcrypt.hashpw(bin(self.contents[2]), bcrypt.gensalt())
            usersDB.set("Users", self.contents[1], salted)
            output.put(taskTx(self.session, "Your registration was successful. Please record your password for future reference."))
        elif self.operation == "login":  # expects "login user pass"
            print("%s is attempting to log in as %s" % self.session, self.contents[1])
            pwdExpected = usersDB.get("Users", self.session[1])
            if bcrypt.checkpw(self.contents[2], pwdExpected):
                sessions.update(dict({self.session:self.contents[1]}))
                welcome = str("You are now %s" % self.contents[1])
                output.put(taskTx(self.session, welcome))
            else:
                output.put(taskTx(self.session, "Login Failed"))
        elif self.operation == "quit":
            for user, remote in sessions:
                if remote == self.session:
                    tgt = user
            del sessions[tgt]
            print("%s has quit" % tgt)
            output.put(taskTx(self.session, b"200"))  # 200 closes connection "at client request".

class taskTx(object):
    def __init__(self, sock, message):
        self.sock = sock
        self.message = message

    def __call__(self):
        if self.message == b"200":
            self.sock.send("Goodbye.")
            self.sock.close()
        else:
            self.sock.send(self.message)

class intProc(mp.Process):
    def __init__(self, queue):
        mp.Process.__init__(self)
        self.qTask = queue

    def run(self):
        while True:
            next_task = self.qTask.get()
            if next_task is None:
                self.qTask.task_done()
                break
            next_task()
            self.qTask.task_done()
        return

# Defining Functions
async def serveIn(sock, port):  # The basic runtime of the entire server goes into this function.
    print("New Connection by %r at %s" % (sock, port))
    await sock.send("Welcome to %s" % ns.title)
    while True:  # This is stupid, never do this.
        msg = await sock.recv()
        categorize(msg, sock)

def categorize(rx, sock): #TODO testing only, should refactor and tweak in next build
    contentsRX = rx.split(" ")
    try:
        catRX = ns.dictKnownCommands[contentsRX[0]]
    except KeyError:
        catRX = None
    if catRX is not None:
        tx = str("That request belongs to the %s category!" % catRX)
        output.put(taskTx(sock, tx))
    elif catRX is "system":
        pending.put(taskSys(rx, sock))  # refers to an as-yet unimplemented JoinableQueue
    else:
        tx = str("I don't know how to do that!")
        output.put(taskTx(sock, tx))

def announce():
    # TODO implement a screen clear here.
    print("Welcome to Tarnished Tale Server %s" % version)
    print("Currently hosting %s" % ns.title)
    print("Expecting connections on port %s" % ns.portIn)

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
global ns

if __name__ == '__main__':  # We also need to set up a manager process and a namespace for future builds
    manager = mp.Manager()
    ns = manager.Namespace()
    sessions = manager.dict()

    ns.title = baseConfig.get("Game Information", "Game Name")
    ns.portIn = baseConfig.get("Network Configuration", "Incoming Port")

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

    ns.dictKnownCommands = knownCommands.copy()

    global pending
    pending = mp.JoinableQueue()
    global output
    output = mp.JoinableQueue()
    internalWorkers = []
    transmitters = []
    for i in range(os.cpu_count()):
        internalWorkers.append(intProc(pending))
    for i in range(os.cpu_count()):
        transmitters.append(intProc(output))
    for w in internalWorkers:
        w.start()
    for w in transmitters:
        w.start()

# Runtime Time
    announce()
    start_server = ws.serve(serveIn, 'localhost', ns.portIn)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
