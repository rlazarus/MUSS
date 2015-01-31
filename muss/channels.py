class Channel(object):
    def __init__(self, name):
        if name in _channels:
            raise ValueError("There's already a channel named {}.".format(name))
        _channels[name] = self
        self.name = name
        self.players = set()

    def __repr__(self):
        return "Channel({})".format(self.name)

    def __str__(self):
        return self.name

    def delete(self):
        self.send_all("Channel {} has been deleted.".format(self))
        del _channels[self]

    def join(self, player):
        if player in self.players:
            raise ValueError("{} is already in {}.".format(player, self))
        self.players.add(player)

    def leave(self, player):
        if player not in self.players:
            raise ValueError("{} is not in {}.".format(player, self))
        self.players.remove(player)

    def _send_all(self, line):
        for player in self.players:
            player.send(line)

    def say(self, player, line):
        for i in self.players:
            if i is not player:
                i.send('[{}] {} says, "{}"'.format(self, player, line))
        player.send('[{}] You say, "{}"'.format(self, line))

    def pose(self, player, line):
        self._send_all('[{}] {} {}'.format(self, player, line))

    def semipose(self, player, line):
        self._send_all('[{}] {}{}'.format(self, player, line))


# Mapping from channel names to channels
_channels = dict()

# If a player refers to a channel by partial name, figure out which one they
# mean. All this logic should be a parse element instead.
def find_prefix(prefix, player):
    matches = [c for name, c in _channels.items()
               if name.lower().startswith(prefix.lower())]
    channels = filter(lambda c: player in c.players, matches)
    if not channels:
        # The player isn't in any matching channels. Can we work out which one
        # they meant?
        if not matches:
            raise KeyError("There's no channel {}.".format(prefix))
        if len(matches) == 1:
            raise KeyError("You're not in channel {}.".format(matches[0]))
        raise KeyError('Did you mean: {}?'.format(', '.join(matches)))
    if len(channels) > 2:
        raise KeyError('Did you mean: {}?'.format(', '.join(channels)))
    return channels[0]

# Until there's a command to create channels, create one automatically.
Channel('Public')
