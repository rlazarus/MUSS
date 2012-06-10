import inspect
import pyparsing
from utils import find_by_name

class Mode(object):

    """
    Dummy class to be extended by classes acting as modes.

    In-game interaction is modal: when a client sends a line, the resulting behavior will be different depending on what's going on. The user may be logging in, or sending an ordinary command, or responding to a prompt.

    Mode classes should override the handle() method, which the protocol will call on the active mode when a line is received from the client.
    """

    def handle(self, player, line):
        """
        Respond, in whatever way is appropriate, to a line from the client.

        Subclasses are expected to implement this method; the default implementation raises NotImplementedError.

        Args:
            factory: The instance of server.WorldFactory responsible for maintaining state.
            player: The db.Player that sent the line.
            line: The line that was sent.
        """
        raise NotImplementedError("Current mode did not override handle()")


class NormalMode(Mode):

    """
    Our usual mode of behavior. When nothing else has taken over the input, this is what will handle it.
    """

    def handle(self, player, line):
        """
        This is starting to look suspiciously like a command parser!
        """

        line = line.strip()
        if not line:
            return

        import muss.commands
        commands = muss.commands.all_commands()

        if " " in line:
            first, arguments = line.split(None, 1)
        else:
            first, arguments = (line, "")

        perfect_matches, partial_matches = find_by_name(first, commands)

        for command in commands:
            # not using find_by_name for this because the way it tests
            # doesn't work the way we want for nospace names.
            for name in command().nospace_names:
                if line.startswith(name):
                    # no partial matching for nospace names, because
                    # without spaces, how would you know where to split them?
                    arguments = line.split(name, 1)[1]
                    perfect_matches.append((name, command))

        if len(perfect_matches) == 1 or (len(partial_matches) == 1 and not perfect_matches):
            if perfect_matches:
                command = perfect_matches[0][1]
            else:
                command = partial_matches[0][1]
            args = command.args.parseString(arguments).asDict()
            command().execute(player, args)
        elif len(perfect_matches):
            # this in particular will need to be more robust
            player.send("I don't know which \"{}\" you meant!".format(first))
        elif len(partial_matches):
            name_matches = [match[0] for match in sorted(partial_matches)]
            player.send("I don't know which one you meant: {}?".format(", ".join(name_matches)))
        else:
            player.send("I don't understand that.")


class Command(object):

    """
    The superclass for all commands -- local or global, built-in or user-defined.
    """
    args = pyparsing.LineEnd() # By default, expect no arguments

    @property
    def names(self):
        # Command.name could be a string or a list. This provides a list.
        if hasattr(self, "name"):
            if isinstance(self.name, list):
                return self.name
            else:
                return [self.name]
        else:
            return []

    @property
    def nospace_names(self):
        # Command.nospace_name could be a string or a list. This provides a list.
        if hasattr(self, "nospace_name"):
            if isinstance(self.nospace_name, list):
                return self.nospace_name
            else:
                return [self.nospace_name]
        else:
            return []
