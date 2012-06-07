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
                perfect_matches.append(obj)
            elif test_objname.startswith(test_name):
                partial_matches.append((objname, obj))

    return (perfect_matches, partial_matches)
