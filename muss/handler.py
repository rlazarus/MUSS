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
        Okay, I'm calling it: this is a parser, bitches.
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
            for name in command().nospace_names:
                # can't use find_by_name because we can't find the end of a nospace command
                if line.startswith(name):
                    # no partial matching for nospace names.
                    # without spaces, how would you know where to split them?
                    arguments = line.split(name, 1)[1]
                    perfect_matches.append((name, command))

        if len(perfect_matches) == 1 or (len(partial_matches) == 1 and not perfect_matches):
            if perfect_matches:
                name, command = perfect_matches[0]
            else:
                name, command = partial_matches[0]
            try:
                args = command.args.parseString(arguments, parseAll=True).asDict()
                command().execute(player, args)

            except pyparsing.ParseException as e:
                if e.line:
                    expected_token = e.parserElement.name
                    if expected_token[0] in "aeiou":
                        article = "an"
                    else:
                        article = "a"

                    if e.column >= len(e.line):
                        where = "at the end of that."
                    else:
                        # get the first word that failed to parse
                        if e.column:
                            rtoken_start = e.column - 1
                        else:
                            rtoken_start = 0
                        received_token = e.line[rtoken_start:].split()[0]
                        where = 'where you put "{}."'.format(received_token)
                    complaint = "I was expecting {} {} {}".format(article, expected_token, where)
                else:
                    complaint = "That command has required arguments."
                complaint += ' (Try "help {}.")'.format(name)
                player.send(complaint)
        
        elif perfect_matches or partial_matches:
            # it's not clear from the name which command the user intended,
            # so see if any of their argument specs match what we got
            parsable_matches = []
            if perfect_matches:
                test_matches = perfect_matches
                # wait, aren't "test matches" a cricket thing?
            else:
                test_matches = partial_matches
            for name, command in test_matches:
                try:
                    args = command.args.parseString(arguments, parseAll=True).asDict()
                    # then, if we didn't raise a parse exception and are still here:
                    parsable_matches.append((command, args))
                except pyparsing.ParseException:
                    # user probably didn't intend this command; skip it.
                    # when we have other kinds of parse errors we'll catch those separately.
                    pass
            if len(parsable_matches) == 1:
                command, args = parsable_matches[0]
                command().execute(player, args)
            else:
                # either multiple commands would parse, or none do. either way:
                if perfect_matches:
                    player.send("I don't know which \"{}\" you mean!".format(first))
                    # when we're getting commands from different objects, etc.
                    # we'll be able to give a more useful error message
                else:
                    # we had no perfect matches and were testing partial matches
                    name_matches = [match[0] for match in sorted(partial_matches)]
                    player.send("I don't know which one you mean: {}?".format(", ".join(name_matches)))
        else:
            player.send("I don't know what you mean by \"{}.\"".format(first))


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
