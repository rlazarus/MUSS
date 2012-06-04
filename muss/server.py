from twisted.internet import protocol, reactor
from twisted.protocols.basic import LineReceiver

import muss.db
from muss.handler import Mode, NormalMode


class WorldProtocol(LineReceiver):

    """
    Protocol that handles the (line-based) connection between a user and the server. All methods are standard Twisted callbacks.

    Attributes:
        player: The Player at the other end (or None if we're in LoginMode or AccountCreateMode).
        mode: Whatever Mode we're currently in.
    """

    def __init__(self):
        class DummyPlayer:
            pass
        self.player = DummyPlayer()  # We'll populate this properly upon login; for now, we just need a dummy to hold a mode attribute.

    def connectionMade(self):
        """Respond to a new connection by dropping directly into LoginMode."""
        self.player.mode = LoginMode(self)

    def lineReceived(self, line):
        """Respond to a received line by passing to whatever mode is current."""
        self.player.mode.handle(self.player, line)
        # self.player.send("")
        # ^this works, but breaks a bit of test I'm not familiar with

    def connectionLost(self, reason):
        """Respond to a dropped connection by dropping reference to this protocol."""
        if self.player and self.factory.allProtocols[self.player.name] == self:
            # The second condition is important: if we're dropping this connection because another has taken its place, we shouldn't delete the new one.
            self.player.emit("{} has disconnected.".format(self.player.name), exceptions=[self.player])
            del self.factory.allProtocols[self.player.name]

factory = None

class WorldFactory(protocol.Factory):

    """
    Factory responsible for generating WorldProtocols and for maintaining server state.

    Attributes:
        allProtocols: A dict mapping names of Player objects to their currently open protocols. Unconnected players are not represented.
    """

    protocol = WorldProtocol

    def __init__(self):
        global factory
        factory = self

        # Maintain a list of all open connections
        self.allProtocols = {}

    def stopFactory(self):
        """
        When stopping the factory, save the database.
        """
        muss.db.backup()

    def sendToAll(self, line):
        """Send a line to every connected player."""
        for protocol in self.allProtocols.values():
            protocol.sendLine(line)


class LoginMode(Mode):

    """The mode first presented to users upon connecting. They are prompted to log in, create an account, or disconnect."""

    def __init__(self, protocol):
        self.protocol = protocol
        self.protocol.sendLine("Hello!")
        self.protocol.sendLine("To log in, type your username and password, separated by a space.")
        self.protocol.sendLine("To create an account, type 'new' and follow the prompts.")
        self.protocol.sendLine("To disconnect, type 'quit'.")

    def handle(self, player, line):
        # The player arg will be a dummy, since no one is logged in yet.
        if line.lower() == "new":
            player.mode = AccountCreateMode(self.protocol)
            return

        if line.lower() == "quit":
            self.protocol.sendLine("Bye!")
            self.protocol.transport.loseConnection()
            return

        if line.find(" ") == -1:
            # No space, but not a command we recognize
            self.protocol.sendLine("Eh?\nLog in with your username, a space, and your password. Type 'new' to create an account, or 'quit' to disconnect.")
            return
        
        # Must be a login attempt
        (name, password) = line.split(" ", 1)

        try:
            player = muss.db.player_by_name(name)
        except KeyError:
            # That name is unregistered
            self.protocol.sendLine("Invalid login.")
            return

        if player.hash(password) == player.password:
            # Associate this protocol with this player, dropping any existing one
            if factory.allProtocols.has_key(player.name):
                factory.allProtocols[player.name].transport.loseConnection()
            factory.allProtocols[player.name] = self.protocol
            self.protocol.player = player

            # Drop into normal mode
            self.protocol.sendLine("Hello, {}!".format(player.name))
            player.emit("{} has connected.".format(player.name), exceptions=[player])
            player.mode = NormalMode()
        else:
            # Wrong password
            self.protocol.sendLine("Invalid login.")
            return


class AccountCreateMode(Mode):

    """
    The mode presented to users creating a new account. They are prompted for a username and password.

    Attributes:
        stage: Either 'name', 'password1', or 'password2' to keep track of the state of the creation process: waiting for a username, waiting for a password, or waiting for the password repetition.
    """

    def __init__(self, protocol):
        self.protocol = protocol
        self.stage = 'name'
        self.protocol.sendLine("Welcome! What username would you like?")

    def handle(self, player, line):
        # Just as in LoginMode, the player arg will be None since no one is logged in.
        if line == 'cancel':
            player.mode = LoginMode(self.protocol)
            return

        if self.stage == 'name':
            if line.find(" ") > -1:
                self.protocol.sendLine("Please type only the username; it may not contain any spaces. Try again:")
                return
            if muss.db.player_name_taken(line):
                self.protocol.sendLine("That name is already taken. If it's yours, type 'cancel' to log in. Otherwise, try another name:")
                return
            self.name = line
            self.protocol.sendLine("Welcome, {}! Please enter a password.".format(self.name))
            self.stage = 'password1'
            return

        elif self.stage == 'password1':
            self.password = line
            self.protocol.sendLine("Please enter it again.")
            self.stage = 'password2'
            return

        elif self.stage == 'password2':
            if self.password == line:
                self.protocol.player = muss.db.Player(self.name, self.password)
                muss.db.store(self.protocol.player)
                factory.allProtocols[self.name] = self.protocol
                self.protocol.player.mode = NormalMode()
                self.protocol.sendLine("Hello, {}!".format(self.name))
                return
            else:
                self.protocol.sendLine("Passwords don't match; try again. Please enter a password.")
                self.stage = 'password1'
                return
