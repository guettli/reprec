reprec: Recursively replace strings in files and other goodies
==================================================================

Command line tool for text files.

https://github.com/guettli/reprec

Tools
=====

Up to now there are these tools:

 * reprec: Replace strings in text files. Can work recursive in a directory tree
 * setops: Set operations (union, intersection, ...) for line based files.
 
reprec
======

The tool reprec replaces strings in text files::

    ===> reprec --help
    Usage: reprec
             [-p|--pattern] p
             [-i|--insert] i
             [-f|--filename regex]
             [-n|--no-regex]
             [-v|--verbose]
             [-a|--ask]
             [--print-lines]
             [--dotall]
             [--ignorecase]
             [--no-std-exclude]
             [--files-from file|-]
             [--ignore regex]
             [--print-std-exclude]

             dirs

        dirs:        Directories or files for replacing. Use is '.' for current dir.

        pattern:     Regex pattern.

        insert:      Text which gets inserted

        filename:    Regex matching the filename. E.g. '.*\.py'

        no-regex:    Normal string replacement will be used.
                     This means you can use '.', '*', '[' without quoting

        verbose:     Print the number of changes for each file

        print-lines: Print the old and the new line for each change.
                     Not available if --dotall is used.

        dotall:      In regular expressions '.' matches newlines, too.
                     Not supported with --ask and --print-lines.

        ignorecase:  ...

        no-std-exclude: Don't exclude the directories called '.git' or '.tox'.
                     By default they get ignored.

        ask:         Aks before replacing (interactive).

        files-from:  Read filenames from file or stdin if '-'.
                     Skip directories.

        ignore:      Ignore lines that match a regular expression.
                     This options can be given several times.

        print-std-exclude: print the directories which get ignored (use --no-std-exclude to
                     not ignore them)

        Example:
         reprec --pattern '(xml)' --insert '\1\1' .
         -->This will replace all 'xml' with 'xmlxml'

         Or, shorter:
         reprec '(xml)' '\1\1'

        Example2:
         find -mtime -1 -name '*.py' | reprec --files-from=- foo bar


        The Perl Compatible Regular Expresssions are explained here:
          http://docs.python.org/lib/re-syntax.html

        The files are created by moving (os.rename()) FILE_RANDOMINTEGER
        to FILE. This way no half written files will be left, if the
        process gets killed. If the process gets killed one FILE_RANDOMINTEGER
        may be left in the filesystem.



setops
======
The tool setops provides set operations (union, intersection, ...) for line based files::

    usage: setops [-h] set1 operator set2

    Operators:
      union Aliases: | + or
      intersection Aliases: & and
      difference Aliases: - minus
      symmetric_difference Aliases: ^

    Examples

    #Show all files in directory "a" which are not in directory "b":
    setops <(cd a; find ) - <(cd b; find )

    # Create some files for testing
    echo foo > foo.txt
    echo bar > bar.txt
    echo foobar > foobar.txt

    # All files minus files containing "foo"
    user@host$ setops <(ls *.txt) - <(grep -l foo *.txt)

    # All files containing "foo" or "bar" minus files which contain "foobar"
    setops <(setops <(grep -l bar *.txt) + <(grep -l foo *.txt)) - <(grep -l foobar *.txt)



    positional arguments:
      set1
      operator
      set2

    optional arguments:
      -h, --help  show this help message and exit

Install
=======

Install from `pypi <https://pypi.python.org/pypi/reprec/>`_::

    pip install reprec
