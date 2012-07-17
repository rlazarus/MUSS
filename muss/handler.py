from inspect import isclass
from pkgutil import walk_packages
import pyparsing

import muss.commands
from muss.locks import authority_of, LockFailedError
from muss.utils import UserError, article, find_by_name
from muss.parser import AmbiguityError, Command, CommandName, NotFoundError

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
        for command in all_commands():
            for name in command().nospace_names:
                # can't use find_by_name because we don't know where the nospace command ends
                if line.startswith(name):
                    # no partial matching, for the same reason
                    nospace_matches.append((name, command))
        if len(nospace_matches) == 1:
            name, command = nospace_matches[0]
            if len(line) > len(name):
                arguments = line[len(name):]
            else:
                arguments = ""

        # check for normal command matches
        try:
            if len(nospace_matches) > 1:
                raise AmbiguityError(line, 0, Command.errmsg, Command, nospace_matches)
            parse_result = CommandName(fullOnly=True)("command").parseString(first, parseAll=True).asDict()
            matched = parse_result["command"]
            arguments = rest_of_line
            if nospace_matches:
                # we found a regular command, but already had a nospace command
                raise AmbiguityError(line, 0, Command.errmsg, Command, nospace_matches + [matched])
            else:
                name, command = parse_result["command"]
        except NotFoundError as e:
            if not nospace_matches:
                message = e.verbose()
                # check whether a require_full command would have matched
                rf_commands = [c for c in all_commands() if c.require_full]
                # (ignoring perfect matches because we would have already seen them)
                rf_matches = find_by_name(e.pstr, rf_commands, attributes=["names"])[1]
                if len(rf_matches) == 1:
                    rf_name, rf_command = rf_matches[0]
                    message += " (If you mean \"{},\" you'll need to use the whole command name.)".format(rf_name)
                elif rf_matches:
                    rf_names = [c[0] for c in rf_matches]
                    message += " (If you meant one of these, you'll need to use the whole command name: {}.)".format(", ".join(rf_names))
                player.send(message)
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
                    args = possible_command.args(player).parseString(test_arguments, parseAll=True).asDict()
                    parsable_matches.append((possible_name, possible_command))
                except UserError:
                    parsable_matches.append((possible_name, possible_command))
                except pyparsing.ParseException:
                    # user probably didn't intend this command; skip it.
                    pass
            if len(parsable_matches) == 1:
                name, command = parsable_matches[0]
                if len(line) > len(name):
                    if parsable_matches[0] in nospace_matches:
                        arguments = line[len(name):]
                    else:
                        arguments = rest_of_line
                else:
                    arguments = ""
            else:
                if parsable_matches:
                    # we can at least narrow the field a little
                    e.matches = parsable_matches
                player.send(e.verbose())
                return

        # okay! we have a command! let's parse it.
        try:
            args = command.args(player).parseString(arguments, parseAll=True).asDict()
            with authority_of(player):
                command().execute(player, args)
        except UserError as e:
            if hasattr(e, "verbose"):
                player.send(e.verbose())
            else:
                player.send(str(e))
        except LockFailedError as e:
            player.send(str(e))
        except pyparsing.ParseException as e:
            # catch-all for generic parsing errors
            if e.line:
                expected_token = e.parserElement.name
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
                complaint = "I was expecting {} {} {}".format(article(expected_token), expected_token, where)
            else:
                complaint = "That command has required arguments."
            complaint += ' (Try "help {}.")'.format(name)
            player.send(complaint)


def all_command_modules():
    """
    Returns a generator yielding every module defined in muss.commands.
    """

    for module_loader, name, ispkg in walk_packages(muss.commands.__path__, prefix="muss.commands."):
        yield __import__(name, fromlist=[""])  # __import__("A.B") returns A unless fromlist is nonempty, in which case it returns A.B -- but we actually want the module, not to import anything from it


def all_commands():
    """
    Returns a generator yielding every command class defined in every module in muss.commands.
    """

    for module in all_command_modules():
        for name in dir(module):
            cls = getattr(module, name)
            if isclass(cls) and issubclass(cls, Command) and cls is not Command:
                yield cls
