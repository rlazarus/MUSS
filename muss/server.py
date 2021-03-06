import traceback

from twisted.conch import telnet
from twisted.internet import protocol, reactor
from twisted.python import log

from muss import db, handler, locks


class LineTelnetProtocol(telnet.TelnetProtocol):
    """
    Using an underlying TelnetProtocol for telnet-specific functionality like
    feature negotiation, split everything up into lines in the style of
    Twisted's own LineReceiver.
    """
    def __init__(self):
        self._buffer = ""

    def dataReceived(self, data):
        """
        Buffer incoming data. When one or more complete lines are received,
        strip them from the buffer and pass them individually to lineReceived,
        sans delimiter.
        """
        self._buffer += data
        # TODO: handle the various line delimiters well
        lines = self._buffer.split("\r\n")
        for line in lines[:-1]:
            self.lineReceived(line)
        self._buffer = lines[-1]

    def sendLine(self, line):
        """
        Slap a delimiter on it and ship it out.
        """
        self.transport.write(line + "\r\n")


class WorldProtocol(LineTelnetProtocol):
    """
    Protocol that handles the (line-based) connection between a user and the
    server. We reimplement some of the functionality of LineReceiver: our
    dataReceived() (a Twisted callback) calls lineReceived(), so we don't act
    on any input until the line delimiter is received.

    Attributes:
        player: The Player at the other end (or None if we're in LoginMode or
            AccountCreateMode).
    """

    def __init__(self):
        LineTelnetProtocol.__init__(self)

        class DummyPlayer:
            def __init__(self):
                self._buffer = ""
                self.mode_stack = []

            @property
            def mode(self):
                return self.mode_stack[-1]

            def enter_mode(self, mode):
                self.mode_stack.append(mode)

            def exit_mode(self):
                self.mode_stack.pop()

        # We'll populate this properly upon login; for now, we just need a
        # dummy to hold a mode attribute.
        self.player = DummyPlayer()

    def connectionMade(self):
        """Respond to a new connection by dropping directly into LoginMode."""
        self.player.enter_mode(LoginMode(self))

    def lineReceived(self, line):
        """
        Respond to a received line by passing to whatever mode is current.

        Args:
            line: The line received, without a trailing delimiter.
        """
        try:
            with locks.authority_of(self.player):
                self.player.mode.handle(self.player, line)
        except Exception:
            # Exceptions are supposed to be caught somewhere lower down and
            # handled specifically. If we catch one here, it's a code error.
            log.err()

            if hasattr(self.player, "debug") and self.player.debug:
                for line in traceback.format_exc().split("\n"):
                    self.player.send(line)
            else:
                self.player.send("Sorry! Something went wrong. We'll look into "
                                 "it.")

        if self.player.mode.blank_line:
            self.player.send("")

    def connectionLost(self, reason):
        """
        Respond to a dropped connection by dropping reference to this protocol.
        """
        if (isinstance(self.player, db.Player) and
                self.factory.allProtocols[self.player.name] == self):
            # The second condition is important: if we're dropping this
            # connection because another has taken its place, we shouldn't
            # delete the new one.
            self.player.emit("{} has disconnected.".format(self.player.name),
                             exceptions=[self.player])
            with locks.authority_of(locks.SYSTEM):
                self.player.mode_stack = []
            del self.factory.allProtocols[self.player.name]


factory = None


class WorldFactory(protocol.Factory):
    """
    Factory responsible for generating WorldProtocols and for maintaining
    server state.

    Attributes:
        allProtocols: A dict mapping names of Player objects to their currently
            open protocols. Unconnected players are not represented.
    """

    protocol = WorldProtocol

    def __init__(self):
        global factory
        factory = self

        # Maintain a list of all open connections.
        self.allProtocols = {}

    def stopFactory(self):
        """
        When stopping the factory, save the database.
        """
        with locks.authority_of(locks.SYSTEM):
            db.backup()

    def sendToAll(self, line):
        """Send a line to every connected player."""
        for protocol in self.allProtocols.values():
            protocol.sendLine(line)


class LoginMode(handler.Mode):
    """
    The mode first presented to users upon connecting. They are prompted to log
    in, create an account, or disconnect.
    """

    blank_line = False

    def __init__(self, protocol):
        self.protocol = protocol
        self.greet()

    def greet(self):
        self.protocol.sendLine("Hello!")
        self.protocol.sendLine("To log in, type your username and password, "
                               "separated by a space.")
        self.protocol.sendLine("To create an account, type 'new' and follow "
                               "the prompts.")
        self.protocol.sendLine("To disconnect, type 'quit'.")

    def handle(self, player, line):
        # The player arg will be a dummy, since no one is logged in yet.
        if line.lower() == "new":
            player.enter_mode(AccountCreateMode(self.protocol))
            return

        if line.lower() == "quit":
            self.protocol.sendLine("Bye!")
            self.protocol.transport.loseConnection()
            return

        if line.find(" ") == -1:
            # No space, but not a command we recognize.
            self.protocol.sendLine("Eh?")
            self.protocol.sendLine("Log in with your username, a space, and "
                                   "your password. Type 'new' to create an "
                                   "account, or 'quit' to disconnect.")
            return

        # Must be a login attempt
        (name, password) = line.split(" ", 1)

        try:
            player = db.player_by_name(name)
        except KeyError:
            # That name is unregistered
            self.protocol.sendLine("Invalid login.")
            return

        if player.hash(password) == player.password:
            # Associate this protocol with this player, dropping any existing
            # one.
            if player.name in factory.allProtocols:
                factory.allProtocols[player.name].transport.loseConnection()
                reconnect = True
            else:
                reconnect = False
            factory.allProtocols[player.name] = self.protocol
            self.protocol.player = player

            # Drop into normal mode
            with locks.authority_of(player):
                self.protocol.sendLine("Hello, {}!".format(player.name))
                self.protocol.sendLine("")
                from muss.commands.world import Look
                # Exit LoginMode and enter NormalMode
                player.enter_mode(handler.NormalMode())
                Look().execute(player, {"obj": player.location})
                if reconnect:
                    player.emit("{} has reconnected.".format(player.name),
                                exceptions=[player])
                else:
                    player.emit("{} has connected.".format(player.name),
                                exceptions=[player])
        else:
            # Wrong password
            self.protocol.sendLine("Invalid login.")
            return


class AccountCreateMode(handler.Mode):

    """
    The mode presented to users creating a new account. They are prompted for a
    username and password.

    Attributes:
        stage: Either 'name', 'password1', or 'password2' to keep track of the
            state of the creation process: waiting for a username, waiting for a
            password, or waiting for the password repetition.
    """

    blank_line = False

    def __init__(self, protocol):
        self.protocol = protocol
        self.stage = 'name'
        self.protocol.sendLine("Welcome! What username would you like?")

    def handle(self, player, line):
        # Just as in LoginMode, the player arg will be None since no one is
        # logged in.
        if line == 'cancel':
            player.exit_mode()  # Drop back to LoginMode
            player.mode.greet()
            return

        if self.stage == 'name':
            if line.find(" ") > -1:
                self.protocol.sendLine("Please type only the username; it may "
                                       "not contain any spaces. Try again:")
                return
            if db.player_name_taken(line):
                self.protocol.sendLine("That name is already taken. If it's "
                                       "yours, type 'cancel' to log in. "
                                       "Otherwise, try another name:")
                return
            self.name = line
            self.protocol.sendLine("Welcome, {}! Please enter a password."
                                   .format(self.name))
            self.stage = 'password1'
            return

        elif self.stage == 'password1':
            self.password = line
            self.protocol.sendLine("Please enter it again.")
            self.stage = 'password2'
            return

        elif self.stage == 'password2':
            if self.password == line:
                player = db.Player(self.name, self.password)
                self.protocol.player = player
                db.store(player)
                factory.allProtocols[player.name] = self.protocol
                with locks.authority_of(player):
                    player.enter_mode(handler.NormalMode())
                    self.protocol.sendLine("Hello, {}!".format(player.name))
                    self.protocol.sendLine("")
                    from muss.commands.world import Look
                    Look().execute(player, {"obj": player.location})
                    player.emit("{} has connected for the first time."
                                .format(player.name), exceptions=[player])
                return
            else:
                self.protocol.sendLine("Passwords don't match; try again. "
                                       "Please enter a password.")
                self.stage = 'password1'
                return
