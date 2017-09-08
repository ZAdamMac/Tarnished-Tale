#Tarnished Tale Server Administration Console
version = 'devBuild'

#Importing Modules
import asyncio
import os
import ssl
import websockets as ws

#Definitions
async def remoteListen(tgt):  # listens to some tgt websockets socket object
    global hasQuit
    while not hasQuit:
        msg = await tgt.recv()
        print(msg)
    return

async def stdinListen(tgt): # listens for input on stdin and transmits on websockets object tgt
    global hasQuit
    while not hasQuit:
        msg = await getInput("> ")
        if msg.lower() == "quit":
            hasQuit = True
            break
        else:
            fullmsg = ("ATERM_MSG %s" % msg)
            await tgt.send(fullmsg)
    return

async def getInput(prompt):
    await asyncio.sleep(5)
    resp = input(prompt)  # This is actually blocking. Another method will be required.
    return resp

async def authenticate(tgt):  # sends the authentication message to sock
    global instanceContext
    async with ws.connect(tgt, ssl=instanceContext) as sock:
        socket = sock
        print("Connection successful at %s" % tgt)
        msg =await sock.recv()
        print(msg)
        global authed; authed = False

        while not authed:
            user = input("Username:")
            pwd = input("Password:")
            msg = ("ATERM_MSG %s %s" % (user, pwd))
            await sock.send(msg)
            resp = await sock.recv()
            print(resp)
            if resp == "Authentication Successful, you are now the admin terminal.":
                authed = True
                await asyncio.gather(remoteListen(sock), stdinListen(sock))
            else:
                authed = False

#Runtime
instanceContext = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=os.path.join(os.getcwd(), "Configuration/server.pem"))  # TODO document me!
global hasQuit; hasQuit = False
print("Welcome to the Tarnished Tale Admin Console")
print("Please enter the address of the server you wish to connect to, with port.")
tgt = input(">(address:port):")
loop = asyncio.get_event_loop()
sock = loop.run_until_complete(authenticate(tgt))
# loop.run_until_complete(asyncio.gather(remoteListen(sock), stdinListen(sock)))
loop.close()