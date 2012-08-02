# Commands for testing purposes only.

from pyparsing import Optional, Word, alphas, SkipTo, StringEnd

from muss.parser import Command, PlayerName
from muss.locks import authority_of, SYSTEM
from muss.handler import PromptMode

class Break(Command):
    name = "break"
    help_text = "Emulate a code error."

    def execute(self, player, args):
        raise Exception("This is only a drill.")

class FooOne(Command):
    name = ["foobar", "test"]
    help_text = "A test command (foobar)."

    @classmethod
    def args(cls, player):
        return Word(alphas)

    def execute(self, player, args):
        player.send("You triggered FooOne.")


class FooTwo(Command):
    name = ["foobaz", "test"]
    help_text = "A test command (foobaz)."

    @classmethod
    def args(cls, player):
        return Word(alphas) + Optional(Word(alphas))

    def execute(self, player, args):
        player.send("You triggered FooTwo.")


class FooThree(Command):
    name = ["asdf"]
    help_text = "A test command (asdf)."

    @classmethod
    def args(cls, player):
        return Word(alphas) * 3 + Optional(Word(alphas) + Word(alphas))

    def execute(self, player, args):
        player.send("You triggered asdf.")


class Lorem(Command):
    name = "lorem"
    help_text = "Spams you with a whole bunch of example text."

    def execute(self, player, args):
        player.send("Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Nam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Typi non habent claritatem insitam; est usus legentis in iis qui facit eorum claritatem. Investigationes demonstraverunt lectores legere me lius quod ii legunt saepius. Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.")


class Poke(Command):
    name = "poke"
    help_text = "Pokes another player, at any location."

    @classmethod
    def args(cls, player):
        return PlayerName()("victim")

    def execute(self, player, args):
        victim = args["victim"]
        if player.location == victim.location:
            player.send("You poke {}!".format(victim))
            victim.send("{} pokes you!".format(player))
            player.emit("{} pokes {}!".format(player, victim), exceptions=[player, victim])
        else:
            player.send("From afar, you poke {}!".format(victim))
            victim.send("From afar, {} pokes you!".format(player))

class Ptest(Command):
    name = "ptest"
    help_text = "This tests prompt mode. It give you a prompt to say whatever you want."
    
    def execute(self, player, args):
        def handle_response(text):
            player.send(text)

        player.enter_mode(PromptMode(player,"Enter text", handle_response))
