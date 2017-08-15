# Tarnished Tale Server
# Modernized, Security-Conscious MUD Client
# For full details, view the docs

# Importing Key Modules
import asyncio
import configparser
import multiprocessing as mp
import os
import websockets as ws

# Defining Principal Classes

# Defining Functions
async def serve(sock, port):  # The basic runtime of the entire server goes into this function.
    print("New Connection on port: %s" % port)
    await sock.send("Welcome to %s" % ns.title)
    while True:  # This is stupid, never do this.
        msg = await sock.recv()
        tx = categorize(msg)
        await sock.send(tx)

def categorize(rx): #TODO testing only, should refactor and tweak in next build
    contentsRX = rx.split(" ")
    try:
        catRX = ns.dictKnownCommands[contentsRX[0]]
    except KeyError:
        catRX = None
    if catRX is not None:
        tx = str("That request belongs to the %s category!" % catRX)
    else:
        tx = str("I don't know how to do that!")
    return tx

# Initialize the Config Parser&Fetch Globals
abspathHome = os.getcwd()
abspathBaseConfig = os.path.join(abspathHome, "Configuration/server_config.txt")
abspathModDats = os.path.join(abspathHome, "Configuration/Module Files")

baseConfig = configparser.ConfigParser()   # We need several parsers. This one will handle the basic config file.
baseConfig.read(abspathBaseConfig)

moduleConfig = configparser.ConfigParser()
# This reader will need to iterate over any and all .dat files in the Configuration/Module Files dir and integrate them
# into one namespace
global ns

if __name__ == '__main__':  # We also need to set up a manager process and a namespace for future builds
    manager = mp.Manager()
    ns = manager.Namespace()

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
# Runtime Time

start_server = ws.serve(serve, 'localhost', ns.portIn)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
