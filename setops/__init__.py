from __future__ import absolute_import, division, print_function, unicode_literals

import argparse


def string_to_set(string_value):
    return set(open(string_value).read().splitlines())


class Operator(object):
    def __init__(self, name_of_set_operation, aliases):
        self.name_of_set_operation = name_of_set_operation
        self.aliases = aliases

    def execute(self, set1, set2):
        return getattr(set1, self.name_of_set_operation)(set2)


class OperatorReturningSet(Operator):
    pass


class OperatorReturningBool(Operator):
    pass


operators = [
    # OperatorReturningBool('isdisjoint', []),
    # OperatorReturningBool('issubset', []),
    # OperatorReturningBool('issuperset', []),
    OperatorReturningSet('union', ['|', '+', 'or']),
    OperatorReturningSet('intersection', ['&', 'and']),
    OperatorReturningSet('difference', ['-', 'minus']),
    OperatorReturningSet('symmetric_difference', ['^']),
]


def string_to_operator(string_value):
    for operator in operators:
        if string_value == operator.name_of_set_operation or string_value in operator.aliases:
            return operator
    raise argparse.ArgumentTypeError('Unknown operator: %r' % string_value)


def description():
    return '''Operators: \n%s

Example 1: Show all files in directory "a" which are not in directory "b": 
setops <(cd a; find ) - <(cd b; find )

Example 2: Show file which do not containt "foo"

setops <(ls -1 mydir/*.txt) - <(grep -l mydir/*.txt)

    ''' % ('\n'.join(['  %s Aliases: %s' % (
        operator.name_of_set_operation,

        ' '.join(operator.aliases)) for operator in operators]))


def main():
    parser = argparse.ArgumentParser(description=description(),
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('set1', type=string_to_set)
    parser.add_argument('operator', type=string_to_operator)
    parser.add_argument('set2', type=string_to_set)
    args = parser.parse_args()
    for item in sorted(args.operator.execute(args.set1, args.set2)):
        print(item)
