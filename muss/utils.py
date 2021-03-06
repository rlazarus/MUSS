class UserError(Exception):
    def __init__(self, string=""):
        if string:
            self.msg = string

    def __str__(self):
        return self.msg


def find_one(name, objects, attributes=["name"], case_sensitive=False):
    """
    Wrapper for find_by_name that attempts to return the best single match: a
    perfect match, if there is exactly one, or a partial match if there is
    exactly one and no perfect match. Otherwise, it raises an AmbiguityError or
    NotFoundError.
    """
    from muss.parser import AmbiguityError, NotFoundError
    perfect_matches, partial_matches = find_by_name(name, objects, attributes,
                                                    case_sensitive)
    perfect_matches = set(perfect_matches)
    partial_matches = set(partial_matches)
    if len(perfect_matches) == 1:
        return perfect_matches.pop()
    if perfect_matches:
        raise AmbiguityError(name, 0, "", None, list(perfect_matches))
    if len(partial_matches) == 1:
        return partial_matches.pop()
    if partial_matches:
        raise AmbiguityError(name, 0, "", None, list(partial_matches))
    raise NotFoundError(name, 0, "", None)


def find_by_name(name, objects, attributes=["name"], case_sensitive=False):
    """
    Finds all the objects in a list on which a given attribute matches a given
    string. Returns two lists of (name, object) tuples, one for perfect matches
    and one for partial.

    Args:
        * name (string to search for)
        * objects (list of objects)
        * attributes (list of attributes to check, defaults to ["name"])
        * case_sensitive (boolean, defaults to False)

    A "perfect" match is one where the attribute value exactly matches the
    given string (case sensitivity optional).

    A "partial" match is one where the attribute value either starts with the
    given string, or has the given string as a subset which begins at a word
    boundary.

    For example, given an object named "big blue cat":
        * "big blue cat" is a perfect match
        * "blue" and "big blue" and "blue cat" are all partial matches
        * "big cat" and "lue" do not match at all.
    """
    perfect_matches = []
    partial_matches = []

    for obj in objects:
        for attribute in attributes:
            if isinstance(obj, type):
                test_obj = obj()
            else:
                test_obj = obj
            test_attr = getattr(test_obj, attribute)
            if not isinstance(test_attr, list):
                test_attr = [test_attr]
            for objname in test_attr:
                if case_sensitive:
                    test_objname = objname
                    test_name = name
                else:
                    test_objname = objname.lower()
                    test_name = name.lower()

                if test_objname == test_name:
                    perfect_matches.append((objname, obj))
                elif (test_objname.startswith(test_name) or
                      " " + test_name in test_objname):
                    partial_matches.append((objname, obj))

    return (perfect_matches, partial_matches)


def get_terminal_size():
    return "beats me."


def article(string):
    """
    Returns the most-likely correct indefinite article for a given string ("a"
    if the string begins with a consonant, "an" if it begins with a vowel).
    """
    if string[0] in "aeiou":
        return "an"
    else:
        return "a"


def comma_and(strings):
    """
    Takes a list of strings and returns a single string with a comma-separated
    list, including "and" in the appropriate place.
    """
    if not strings:
        return ""
    elif len(strings) == 1:
        return strings[0]
    elif len(strings) == 2:
        return "{} and {}".format(strings[0], strings[1])
    else:
        return ", ".join(strings[:-1]) + ", and " + strings[-1]
