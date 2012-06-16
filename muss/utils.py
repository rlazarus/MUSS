from pyparsing import ParseException

class AmbiguityError(ParseException):
    def __init__(self, pstr, loc=0, msg=None, elem=None, token_name="one", tokens=[]):
        super(AmbiguityError, self).__init__(pstr, loc, msg, elem)
        self.token_name = token_name
        self.tokens = tokens

    def verbose(self):
        verbose = "Which {} did you mean?".format(self.token_name)
        if self.tokens:
            verbose += " ({})".format(", ".join(tokens))
        return verbose

def find_by_name(name, objects, attribute="names", case_sensitive=False):
    perfect_matches = []
    partial_matches = []

    for obj in objects:
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
