#Tarnished Tale Server
#Modernized, Security-Conscious MUD Client
#For full details, view the docs

#Importing Key Modules
import asyncio
import websockets as ws

#Defining Principal Classes

#Defining Functions
async def echo(sock, port):  # A simple echo function currently included for testing reasons
    msg = await sock.recv()
    print("I have received %s" % msg)
    await sock.send(msg)

#Initialize the Config Parser&Fetch Globals

#Runtime Time
start_server = ws.serve(echo, 'localhost', portIn)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()