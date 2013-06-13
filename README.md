### Goal ###
Build a modern MU* engine from scratch which is easy to use, read, and
modify, even for novice programmers.

### Features ###

* Python modules make it easy to add and change basic functionality.
* Scripting interface hooks directly into the game code, in a sandbox.
* Build in the game, or use a local editor and upload to the server.
* Modify and update the live game without resetting or restarting.
* Compatible with all standard MU* clients.

### Quick Command Reference ###
 * **Exploring and Interacting**
   * `look` around at players, items, and rooms.
   * Type part of an exit name or use `go` to travel.
   * Use `chat`, `say`, `emote`, and `tell` to express yourself.
   * `retell` speeds up ongoing conversations.
   * `take` and `drop` all kinds of items.
   * `wear` and `remove` equipment.
 * **Building**
   * Use `dig` to make rooms and `open` for extra exits.
   * Use `create` to make objects. (Opposite: `destroy`.) Helpful object types:
     * `muss.db.Object` for generic props.
     * `muss.db.Container` for items you can put other items in.
     * `muss.equipment.Equipment` for items you can wear.
   * Use `set` to change things that already exist (`me` and `here` are
     keywords.) Examples:
     * set here.description = "A small island in the middle of the flowing
       river ..."
     * set #4.name = "ornate diamond bracelet"
   * The `python` REPL fills in where commands haven't been built yet.
 * **Getting More Help**
   * `usage` provides a quick reminder of command syntax.
   * `help` has more description and examples of how to use commands.
