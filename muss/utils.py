class UserError(Exception):
    def __init__(self, string=""):
        if string:
            self.msg = string

    def __str__(self):
        # you could probably skip this definition by putting a lambda in __init__
        # but I couldn't seem to get the syntax right
        return self.msg


def find_one(name, objects, attributes=["name"], case_sensitive=False):
    """
    Wrapper for find_by_name that attempts to return the best single match: a perfect match, if there is exactly one, or a partial match if there is exactly one and no perfect match. Otherwise, it raises an AmbiguityError or NotFoundError.
    """
    from muss.parser import AmbiguityError, NotFoundError
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
        raise AmbiguityError(name, 0, "", None, matches)
    else:
        raise NotFoundError(name, 0, "", None)


def find_by_name(name, objects, attributes=["name"], case_sensitive=False):
    """
    Finds all the objects in a list on which a given attribute matches a given string. Returns two lists of (name, object) tuples, one for perfect matches and one for partial.

    Args:
        * name (string to search for)
        * objects (list of objects)
        * attributes (list of attributes to check, defaults to ["name"])
        * case_sensitive (boolean, defaults to False)

    A "perfect" match is one where the attribute value exactly matches the given string (case sensitivity optional).

    A "partial" match is one where the attribute value either starts with the given string, or has the given string as a subset which begins at a word boundary.

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
                elif (test_objname.startswith(test_name) or " " + test_name in test_objname) and not (hasattr(test_obj, "require_full") and test_obj.require_full):
                    partial_matches.append((objname, obj))

    return (perfect_matches, partial_matches)

def get_terminal_size():
    return "beats me."

def article(string):
    """
    Returns the most-likely correct indefinite article for a given string ("a" if the string begins with a consonant, "an" if it begins with a vowel).
    """
    if string[0] in "aeiou":
        return "an"
    else:
        return "a"
