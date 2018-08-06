# Welcome to the Tarnished Tale Contributor Guidelines!
Hey, thanks for checking us out! Tarnished Tale is someone's spare-time hobby project, and ambitious at best, which means we're always looking for contributors to come in and help us make a best effort at producing something really solid - a well-made, security-first MUD server/client bundle made for the modern internet!

First off, let me just say that any contribution matters - from pull-requesting in new functions, to requesting new features, or even just reporting your crashes and bugs. Right now a lot of development is underway. A lot of our framework is super minimal. TT doesn't have automated crash and bug reporting. I'm just one guy with a few spare hours in the evening trying to put this thing together. Everything you contribute helps.

Secondly, we do have a few resources for first timers:
- [**Discord Server:**](https://discord.gg/56msGFT) easily the fastest way to join in the conversation or ask a question;
- [Email Development Team](mailto:ttdev@psavlabs.com);
- and, of course, this guide!

# CORE Development Team
While everyone who contributes to the project is part of our development team, the capital-letters Development Team currently consists of github user ZAdamMac.

# Feature Requests
We're always happy to have a look at requests for new features - from the outset, it was always intended for Tarnished Tale to be modular and easily-expanded by anyone who would want to mod it.

## Should This be a Sub-Module?
Not every feature should be added directly to Tarnished Tale CORE, if only to minimize the amount of overhead required to run it and development time required on it. CORE's intended featureset is fairly comprehensive. A list of intended CORE features is part of [the project's wiki](https://www.github.com/ZAdamMac/Tarnished-Tale/wiki). At the moment, only features which enhance/round out those core features or which can only operate from the main thread are being accepted for adoption into CORE.

However, several modules are under development right from the outset, including RACES and MAGIC.

## Filing a Feature Request
If you have a feature request for CORE, go ahead and open a new issue at this repo. Be sure to head the title of the request with `[RFC]`. The development team for CORE will cross-post your request in announcements to the discord and any other contact trains we happen to be using at the time, opening the request up for commentary by other members. **A minimum of 30 days later**, the same group will decide whether or not to include the feature, or some version of it, into the development process. If the feature is complicated or discussion over it is lively, this decision process may be extended as necessary to allow the matter to resolve.

# Bug Reports
We kind of can't overstate the importance of providing your bug reports to us. It's so important we've made a template for them. As stated above, Tarnished Tale CORE has no built-in error reporting. When you're developing on CORE or using it to run a game yourself, if it crashes, we have no idea what happened or why. Please be encouraged to file an issue and fill out the bugs form. Super important stuff.

# Contributing with Code: The Pull Request!
Here at TT we use Fork and Request. If you want to contribute to the TTCore development process with your code, the preferred method is to first fork the repo, make your changes there, and then submit a pull request. For obvious reasons all submissions are subject to review. To make this whole process easier, be sure to use nice, clear, descriptive code. Provide documentation or comments as needed.

In general though, we're super happy to have any help that we can. People who contribute with code are being kept track of and will be included in the credits.

## Testing
Currently, no unit test construct exists for TT. This is wildly regarded as a huge mistake and will be rectified in the coming future. In the meantime, please be very thorough in your testing. Include a TESTS.md or TESTS.txt file that explain what you tested and what result you got to make our testing on our end faster, at least until the unit test methodology is released.

# Contributing with Coins
Lastely, as a hobby project, we're obviously working with the bare minimum funding possible - luckily, this sort of thing also doesn't take much. If you'd like to donate to keep TT's development alive, the current money repo is [ko-fi.com](https://ko-fi.com/PSavLabs). Obviously, if a permanent developer team is adopted, this model will have to change.

At present, we simply have no way for you to contribute with cryptocurrencies. 
