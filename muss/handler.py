import inspect
import pyparsing
from utils import AmbiguityError, NotFoundError, find_by_name
from pyparsing import ParseException

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
        Parse the input line for a command and arguments, reporting any errors or unresolvable ambiguity.
        """

        line = line.strip()
        if not line:
            return

        split_line = line.split(None, 1)
        if len(split_line) == 1:
            split_line.append("")
        first, rest_of_line = split_line

        name = ""
        command = None

        # check for nospace commands
        nospace_matches = []
        import muss.commands
        commands = muss.commands.all_commands()
        for command in commands:
            for name in command().nospace_names:
                # can't use find_by_name because we don't know where the nospace command ends
                if line.startswith(name):
                    # no partial matching, for the same reason
                    nospace_matches.append((name, command))
        if len(nospace_matches) == 1:
            name, command = nospace_matches[0]
        elif nospace_matches:
            # augh why would you do this?
            # I will figure out how to deal with it later
            nospace_matches = []

        # check for normal command matches
        try:
            from muss.commands import CommandName
            parse_result = CommandName(fullOnly=True)("command").parseString(first, parseAll=True).asDict()
            matched = parse_result["command"].items()[0]
            if nospace_matches:
                raise AmbiguityError("", token="command", matches=nospace_matches + [matched])
            else:
                name, command = parse_result["command"].items()[0]
        except NotFoundError as e:
            if not nospace_matches:
                player.send(e.verbose())
                return
        except AmbiguityError as e:
            # it's not clear from the name which command the user intended,
            # so see if any of their argument specs match what we got
            parsable_matches = []
            for possible_name, possible_command in e.matches + nospace_matches:
                try:
                    if nospace_matches and (possible_name, possible_command) == nospace_matches[0]:
                        test_arguments = line.split(possible_name, 1)[1]
                    else:
                        test_arguments = rest_of_line
                    args = possible_command.args.parseString(test_arguments, parseAll=True).asDict()
                    parsable_matches.append((possible_name, possible_command))
                except (AmbiguityError, NotFoundError):
                    # data error, not a real parse error, so maybe this is right! 
                    parsable_matches.append((possible_name, possible_command))
                except pyparsing.ParseException:
                    # user probably didn't intend this command; skip it.
                    pass
            if len(parsable_matches) == 1:
                name, command = parsable_matches[0]
            else:
                if parsable_matches:
                    # we can at least narrow the field a little
                    e.matches = parsable_matches
                player.send(e.verbose())
                return

        # okay! we have a command! let's parse it.
        try:
            if nospace_matches and (name, command) == nospace_matches[0]:
                arguments = line.split(name, 1)[1]
            else:
                arguments = rest_of_line
            args = command.args.parseString(arguments, parseAll=True).asDict()
            command().execute(player, args)
        except (AmbiguityError, NotFoundError) as e:
            player.send(e.verbose())
        except ParseException as e:
            # catch-all for generic parsing errors
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
