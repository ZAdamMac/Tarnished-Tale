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
    while True:  # This is stupid, never do this.
        print("New Connection on port: %s" % port)
        await sock.send("Welcome to: %s" % ns.title)  # TODO This needs to become an on-connect event!
        msg = await sock.recv()
        print("I have received %s" % msg)
        await sock.send(msg)

# Initialize the Config Parser&Fetch Globals
abspathHome = os.getcwd()
abspathBaseConfig = os.path.join(abspathHome, "Configuration/server_config.txt")
abspathModDats = os.path.join(abspathHome, "Configuration/Module_Files")

baseConfig = configparser.ConfigParser()   # We need several parsers. This one will handle the basic config file.
baseConfig.read(abspathBaseConfig)

moduleConfig = configparser.ConfigParser()
# This reader will need to iterate over any and all .dat files in the Configuration/Module Files dir and integrate them
# into one namespace

if __name__ == '__main__':  # We also need to set up a manager process and a namespace for future builds
    manager = mp.Manager()
    ns = manager.Namespace()
    global ns

    ns.title = baseConfig.get("Game Information", "Game Name")
    ns.portIn = baseConfig.get("Network Configuration", "Incoming Port")
    ns.dictKnownCommands = {}  # establishes an empty dictionary for commands and their corresponding "category"

    for foo, bar, files in os.walk(abspathModDats):  # crawls the module files looking for their command info.
        for file in files:
            moduleConfig.read(os.path.join(foo,file))
            if moduleConfig.has_section("Additional Commands"):
                for options in moduleConfig.options("Additional Commands"):
                    for option in options:
                        ns.dictKnownCommands.update(
                            str(option)+":"+str(moduleConfig.get("Additional Commands", option))
                        )

# Runtime Time
start_server = ws.serve(serve, 'localhost', ns.portIn)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
