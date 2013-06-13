### The Premise ###
Did you ever play MUDs, MUCKs, or MUSHes--any kind of multiplayer text-based
roleplaying game--back in the day? Did you ever build, or especially code,
on one? It was kind of a drag, wasn't it? MU\* engines are hard to read and
harder to modify, especially without tacking on even more new kludge. Let's
face it: even now, the MU\*s which are still up and running are built on
code which is a fork of a fork of a fork of some C written by a geek in their
dorm room in the eighties. Not to slam that geek--we are in your debt! It's
just that software engineering has come a long way since then.

What would a MU\* look like if it was written from scratch in 2013? Processing
speed for a program that's just serving text over telnet is no longer
a concern--you could write it in a high-level interpreted language. That
along with clean modern design patterns would support an engine that's easy
to read and friendly enough for even non-programmers to modify. Rather than
implementing an awkward custom scripting language, you could give builders
an interface into the game's code itself, safely sandboxed to respect their
in-game limitations. You could store your world in a source repository,
composing in your favorite editor and then uploading changes to the live game
without shutting it down. In short, you could have the gameplay experience
you love with all the conveniences of modern design.

You could have MUSS!


### Quick Command Reference ###
 * **Exploring and Interacting**
   * `look` around at players, items, and rooms.
   * Type part of an exit name or use `go` to travel.
   * Use `chat`, `say`, `emote`, and `tell` to express yourself to players.
   * `retell` speeds up ongoing conversations.
   * `take` and `drop` all kinds of items.
   * `wear` and `remove` equipment.
 * **Building**
   * Use `dig` to make rooms and `open` for extra exits.
   * Use `create` to make objects. (Opposite: `destroy`.)Helpful object types:
     * `muss.db.Object` for generic props.
     * `muss.db.Container` for items you can put other items in.
     * `muss.equipment.Equipment` for items you can wear.
   * Use `set` to change things that already exist (*me* and *here* are
     keywords.) Examples:
     * set here.description = "A small island in the middle of the flowing
       river ..."
     * set #4.name = "ornate diamond bracelet"
   * The `python` REPL fills in where commands haven't been built yet.
 * **Getting More Help**
   * `usage` provides a quick reminder of command syntax.
   * `help` has more description and examples of how to use commands.
