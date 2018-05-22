# Tarnished Tale Websockets MUD Server
**Tarnished Tale (TT)** is a modernized MUD server (and bundled testing client) written in Python 3.6 and currently under development by Patch Savage (PS) Labs. By moving to the Websockets protocol and away from the traditional telnet interface of MUD servers, Tarnished Tale hopes to keep the genre alive for years to come.

To be honest, it's also a decent learning project and object lesson.

***Important***: *Tarnsihed Tale is, as of the time of writing, "shelved" indefinitely. While it remains an interesting project to pick away at the edges of no serious effort is currently being made to develop TT at this time. The development and last stable branches are preserved and set aside for future attempts at completion.*

## Objectives
Tarnished Tale has the following objectives:
 - Implement a Full-Featured MUD server accessable by any websockets client;
 - Allow for the use of TLS/SSL by providing for Secure Websockets (WSS) to be configured by the administrator;
 - Allow for the expansion of the core functions of the server with the addition of add-on "modules";
 - Provide a learning process for the developer(s) in asyncronous programming, multiprocessing, and network applications, and;
 - Provide the framework for a future game to be released using TT as its engine.

## What Tarnished Tale is Not
For one, Finished. Tarnished Tale is under active development. What you see in this repo isn't even a demo or an alpha implementation. We are introducing bugs into empty text files until a game engine is created.

More seriously:
 - A re-implemntation of classic engines like SMAUG (at least not on purpose);
 - An implementation of any common Pen and Paper RPG system in python;
 - A web server;
 - A 'statistical core' for a later graphic RPG, or;
 - Intended to be packaged for sale.

## The Future of Tarnished Tale
Tarnished Tale started as a joke on the NationStates discord about creating a roguelike/MUD "penetration testing" game in which the players would be tasked with storming various securized installations. Increasing levels of abstraction resulted in the desire to build a generalized engine first and implement any games on top of that second. The final version of Tarnished Tale will be packaged under some form or another of a Freeware Open Source license and available for use by anyone who would like to try their hand at building and running a MUD.

### Current Features
The current featureset of Tarnished Tale is extremely limited, implementing only some basic configuration parsing and limited "Player Management" controls. Currently, the server code can:
 - Run indefinitely on a supported architecture
 - Print status and error messages to the console
 - with the (correct) use of the HTML/JS client:
   - register new users
   - login as an existing user
   - gracefully logout as a user.

Password protection in transit is achieved using SSL, which is natively implemented by the modules Tarnished Tale depends on. In storage, passwords are handled by `bcrypt` and stored as uniquely-salted hashes.

### Roadmap for the Future
A limited roadmap for the future of Tarnished Tale exists, with the following progression yet to be achieved, more or less in the order listed:
 - Establish a parallel process to the server's async-loop which serves to control the server as an administrative console, which would be accessable to an administrator locally, or remotely via SSH to the host;
 - Establish the player state tracking system (formerly called playerLoader) to track individual character sheets and persistance information;
 - Establish the in-game communications channels one would expect (global, /say, etc)
 - Establish the room state tracking system (with its mapping concepts and linkages) to allow movement and interaction with a statically-generated (non-roguelike) environment;
 - Establish the mechanisms needed for presence, interactivity, and status-tracking of NPCs;
 - Implement an items system;
 - Implement the combat system;
 - Implement limited NPC "botting", and;
 - Establish the mechanisms necessary for parsing code from item descriptors and "module" files, not to be confused with python modules.

The completion of these immediate objectives and any fixes or additions to appear necessary during their development would constitute completion of the core game, whereupon the various modules could begin development. Current modules under consideration are:
 - Races defintion/tracking module;
 - Magic Module
 - Roguelike Module

## Want to Help?
Tarnished Tale is a huge project and we're known to get wedged. There's a few different ways you could help with development! Check out our contributing guide in `/docs/`.
