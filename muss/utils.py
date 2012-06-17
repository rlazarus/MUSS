class AmbiguityError(Exception):
    def __init__(self, token="one", test_string="", matches=[]):
        self.token = token
        self.matches = matches
        self.test_string = test_string

    def verbose(self):
        if self.matches and self.matches[0][0] != self.matches[1][0]:
            # i.e. we have some and they actually differ
            verbose = "Which {} do you mean?".format(self.token)
            match_names = sorted([t[0] for t in self.matches])
            verbose += " ({})".format(", ".join(match_names))
        else:
            verbose = 'I don\'t know which {} called "{}" you mean.'.format(self.token, self.test_string)
        return verbose


class NotFoundError(Exception):
    def __init__(self, token="thing", test_string=""):
        self.token = token
        self.test_string = test_string

    def verbose(self):
        verbose = "I don't know of a {} ".format(self.token)
        if self.test_string:
            verbose += 'called "{}."'.format(self.test_string)
        else:
            verbose += "by that name."
        return verbose


def find_one(name, objects, attributes=["names"], case_sensitive=False):
    perfect_matches, partial_matches = find_by_name(name, objects, attributes, case_sensitive)
    if len(perfect_matches) == 1 or (len(partial_matches) == 1 and not perfect_matches):
        if perfect_matches:
            return perfect_matches[0]
        else:
            return partial_matches[0]
    elif perfect_matches or partial_matches:
        if perfect_matches:
            matches = perfect_matches
        else:
            matches = partial_matches
        raise AmbiguityError(matches=matches)
    else:
        raise NotFoundError(test_string=name)


def find_by_name(name, objects, attributes=["names"], case_sensitive=False):
    perfect_matches = []
    partial_matches = []

    for obj in objects:
        for attribute in attributes:
            for objname in getattr(obj(), attribute):
                if case_sensitive:
                    test_objname = objname
                    test_name = name
                else:
                    test_objname = objname.lower()
                    test_name = name.lower()

                if test_objname == test_name:
                    perfect_matches.append((objname, obj))
                elif test_objname.startswith(test_name):
                    partial_matches.append((objname, obj))

    return (perfect_matches, partial_matches)
