#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

# (C) 2002-2015 Thomas Guettler http://www.thomas-guettler.de
# Feedback is welcome! (Even hints to typos)
# Please use this URL for feedback: https://github.com/guettli/reprec

# Python Imports
import codecs
import os
import re
import sys
import getopt
import random
import shutil
import tempfile


def usage():
    print('''Usage: %s
             [-p|--pattern] p
             [-i|--insert] i
             [-f|--filename regex]
             [-n|--no-regex]
             [-v|--verbose]
             [-a|--ask]
             [--print-lines]
             [--dotall]
             [--ignorecase]
             [--test]
             [--novcexclude]
             [--files-from file|-]
             [--ignore regex]
             [--no-skip-message]

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

        test:    Run the test. No other arguments are allowed.

        novcexclude: Don't exclude the directories called '.svn' or 'CVS'.
                     By default they get ignored.

        ask:         Aks before replacing (interactive).

        files-from:  Read filenames from file or stdin if '-'.
                     Skip directories.

        ignore:      Ignore lines that match a regular expression.
                     This options can be given several times.

        no-skip-message: Don't print 'Skipping ...'

        Example:
         %s --pattern '(xml)' --insert '\\1\\1' .
         -->This will replace all 'xml' with 'xmlxml'

         Or, shorter:
         %s '(xml)' '\\1\\1'

        Example2:
         find -mtime -1 -name '*.py' | %s --files-from=- foo bar


        The Perl Compatible Regular Expresssions are explained here:
          http://docs.python.org/lib/re-syntax.html

        The files are created by moving (os.rename()) FILE_RANDOMINTEGER
        to FILE. This way no half written files will be left, if the
        process gets killed. If the process gets killed one FILE_RANDOMINTEGER
        may be left in the filesystem.
        ''' % (
        os.path.basename(sys.argv[0]),
        os.path.basename(sys.argv[0]),
        os.path.basename(sys.argv[0]),
        os.path.basename(sys.argv[0])))


def replace_recursive(dirname, pattern, text, filename_regex=None,
                      no_regex=None, verbose=False,
                      dotall=False, print_lines=False, novcexclude=False, ask=False,
                      files_from=None, ignorecase=False, ignore_lines=None, no_skip_message=False
                      ):
    if ignore_lines is None:
        ignore_lines = []
    if ask and files_from:
        raise Exception("You can't use --ask and --files-from together since reading y/n from stdin is not possible")
    if dotall and ignore_lines:
        raise Exception("You can't use --dotall and --ignore together")

    rr = ReplaceRecursive(pattern, text, filename_regex,
                          no_regex, verbose, dotall,
                          print_lines, novcexclude, ask, ignorecase, ignore_lines, no_skip_message)

    if files_from:
        assert not dirname, dirname
        for line in files_from:
            file_name = line.rstrip()
            if os.path.isdir(file_name):
                if not rr.no_skip_message:
                    print('Skipping', file_name)
                continue
            rr.do(file_name, follow_symlink_files=[file_name])
        return rr.counter

    return rr.do(dirname, follow_symlink_files=dirname)


class ReplaceRecursive:
    def __init__(self, pattern, text, filename_regex=None,
                 no_regex=None, verbose=False,
                 dotall=False, print_lines=False, novcexclude=False, ask=False,
                 ignorecase=False, ignore_lines=None, no_skip_message=False,
                 ):
        if ignore_lines is None:
            ignore_lines = []
        self.pattern = self.str_to_bytes(pattern)
        self.text = self.str_to_bytes(text)
        self.filename_regex = filename_regex
        self.no_regex = no_regex
        self.verbose = verbose
        self.dotall = dotall
        self.print_lines = print_lines
        self.novcexclude = novcexclude
        self.ask = ask
        self.ignorecase = ignorecase
        self.ignore_lines = ignore_lines
        self.no_skip_message = no_skip_message

        self.counter = {'dirs': 0, 'files': 0, 'lines': 0, 'files-checked': 0}
        self.exit_after_this_file = False
        self.always_yes = False
        flags = 0
        if not no_regex:
            if dotall:
                flags |= re.DOTALL
            if ignorecase:
                flags |= re.IGNORECASE
            try:
                self.regex = re.compile(pattern, flags)
            except re.error as e:
                print("regular expression has syntax error: '%s': %s (do you want --no-regex ?)" % (
                    pattern, str(e)))
                sys.exit(3)
        else:
            self.regex = None

    def str_to_bytes(self, my_string):
        try:
            return bytes(my_string)
        except UnicodeError as exc:
            raise UnicodeError('Failed to convert to bytes: %r. Exception: %s' % (my_string, exc))
    def do(self, dirname, follow_symlink_files=None):
        if follow_symlink_files is None:
            follow_symlink_files=[]
        if isinstance(dirname, (tuple, list)):
            for dir_name in dirname:
                assert isinstance(dir_name, basestring), repr(dir_name)
                self.do(dir_name)
            return self.counter
        if (not dirname in follow_symlink_files) and os.path.islink(dirname):
            if not self.no_skip_message:
                print('Skipping symbolic link %s' % dirname)
            return self.counter
        if os.path.isdir(dirname):
            dir_list = os.listdir(dirname)
            isdir = True
        else:
            dir_list = [dirname]
            isdir = False
        start_counter = self.counter['files']
        for file_name in dir_list:
            if self.exit_after_this_file:
                break
            if isdir:
                file_name = os.path.join(dirname, file_name)
            if (not file_name in follow_symlink_files) and os.path.islink(file_name):
                if not self.no_skip_message:
                    print('Skipping symbolic link %s' % file_name)
                continue
            if os.path.isdir(file_name):
                if (not self.novcexclude) and os.path.basename(file_name) in ['.svn', 'CVS', '.git', '.hg', '.bzr', '.idea']:
                    if not self.no_skip_message:
                        print('Skipping', file_name)
                    continue
                self.do(file_name)
            elif os.path.isfile(file_name):
                self.do_file(file_name)
            else:
                if not os.path.exists(file_name):
                    print('%s does not exist' % file_name)
                else:
                    print('Ignoring %s: No directory and not a file_name' % file_name)

        if self.counter['files'] != start_counter:
            self.counter['dirs'] += 1

        return self.counter

    def do_file(self, file_name):
        if self.file_has_ending_to_ignore(file_name):
            return
        if self.filename_regex and not re.match(self.filename_regex,
                                                file_name):
            return
        if self.verbose:
            print('Opening %s' % file_name)
        self.counter['files-checked'] += 1
        counter_start = self.counter['lines']
        with open(file_name, 'rb') as fd:
            if self.dotall:
                new_file_content = self.do_file__dot_all(fd)
            else:
                new_file_content = self.do_file__not_dot_all(fd, file_name)

        if self.counter['lines'] == counter_start:
            # no changes
            return

        self.update_file(file_name, new_file_content, counter_start)

    def do_file__not_dot_all(self, fd, file_name):
        new_file_content = []
        while True:
            line = fd.readline()
            if not line:
                break
            ignore_this_line = False
            for ignore_line in self.ignore_lines:
                if ignore_line.search(line):
                    ignore_this_line = True
                    break
            if ignore_this_line:
                if self.verbose:
                    print('Ignoring %s line: %s' % (file_name, line.rstrip()))
                new_file_content.append(line)
                continue

            line_replaced = self.replace_one_line(line, file_name)
            new_file_content.append(line_replaced)

        return b''.join(new_file_content)

    def replace_one_line(self, line, file_name):
        if self.no_regex:
            line_replaced = self.replace_one_line__no_regex(line)
        else:
            line_replaced = self.replace_one_line__regex(line)
        assert line_replaced is not None
        if line == line_replaced:
            return line
        if self.ask and (not self.doask(file_name, line, line_replaced)):
            return line
        self.counter['lines'] += 1
        if self.print_lines:
            sys.stdout.write('%s old: %s%s new: %s' % (
                file_name, line, file_name, line_replaced))
        return line_replaced

    def replace_one_line__no_regex(self, line):
        return line.replace(self.pattern, self.text)

    def replace_one_line__regex(self, line):
        return self.regex.sub(self.text, line)

    def do_file__dot_all(self, fd):
        assert not self.ask
        content = fd.read()
        (new_file_content, n) = self.regex.subn(self.text, content)
        if n:
            self.counter['lines'] += n
        return new_file_content

    def update_file(self, file_name, out, counter_start):
        counter_now = self.counter['lines']
        self.counter['files'] += 1
        temp = '%s_%s' % (file_name, random.randint(100000, 999999))
        with open(temp, 'wb') as fd:
            fd.write(out)
        # os.rename: single system call, so no
        # half written files will exist if to process gets
        # killed.
        mode = os.stat(file_name).st_mode
        os.chmod(temp, mode)
        os.rename(temp, file_name)
        if self.verbose:
            print('Changed %s lines in %s' % (
                counter_now - counter_start, file_name))

    file_endings_to_ignore = ['~', '.pyc', '.db']

    def file_has_ending_to_ignore(self, file_name):
        for ending in self.file_endings_to_ignore:
            if file_name.endswith(bytes(ending)):
                if not self.no_skip_message:
                    print('Skipping', file_name)
                return True
        return False

    def doask(self, file_name, line, line_replaced):
        if self.exit_after_this_file:
            return False
        if self.always_yes:
            return True
        print('Replace in %s:' % file_name)
        print(line)
        print('with:')
        print(line_replaced)
        if line.endswith('\n') and not line_replaced.endswith('\n'):
            print('WARNING: Newline at the end of line was stripped!')
        while True:
            self.do_ask_one_time()

    def do_ask_one_time(self):
        print('Please choose one action:')
        print(' y=yes')
        print(' n=No')
        print(' A=always yes (do not ask again)')
        print(' q=quit (save changes in this file)')
        print(' x=exit (exit now, discard changes in this file)')
        char = getch()
        if char == '\x1b':
            # Stupid things can happen:
            # Cursor-Up sends ESC [ A
            # --> all files get replaced!

            # Try to ignore Escape and following characters
            print('You send Escape, ignoring input until next_char character', end=' ')
            sys.stdout.flush()
            while True:
                next_char = getch()
                if re.match(r'[a-zA-Z~]', next_char):
                    print()
                    break
                print('Ingoring %r' % next_char, end=' ')
                sys.stdout.flush()
            return
        if char in 'yYjJ':
            return True
        elif char in 'nN':
            return False
        elif char in 'qQ':
            self.exit_after_this_file = True
            return False
        elif char in 'xX':
            sys.exit(1)
        elif char in 'A':
            # svn/cvs use 'a' for abort if you use an empty commit message
            self.always_yes = True
            return True
        print('%r is not a valid action.' % char)


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'p:i:f:vna',
                                   ['pattern=', 'insert=', 'no-regex', 'noregex',
                                    'verbose', 'print-lines',
                                    'filename=',
                                    'dotall', 'ignorecase',
                                    'test', 'novcexclude', 'ask', 'files-from=',
                                    'ignore=',
                                    'no-skip-message'])
    except getopt.GetoptError as e:
        usage()
        print(e)
        sys.exit(2)
    no_regex = None
    pattern = None
    text = None
    filename_regex = None
    verbose = False
    dotall = False
    ignorecase = False
    test = None
    print_lines = False
    novcexclude = False
    ask = False
    files_from = None
    no_skip_message = False
    ignore_lines = []
    for opt, arg in opts:
        if opt in ['--pattern', '-p']:
            pattern = arg
        elif opt in ['--insert', '-i']:
            text = arg
        elif opt in ['--no-regex', '--noregex', '-n']:
            no_regex = True
        elif opt in ['--filename', '-f']:
            filename_regex = arg
        elif opt in ['--verbose', '-v']:
            verbose = True
        elif opt == '--dotall':
            dotall = True
        elif opt == '--ignorecase':
            ignorecase = True
        elif opt == '--test':
            test = True
        elif opt == '--print-lines':
            print_lines = True
        elif opt == '--novcexclude':
            novcexclude = True
        elif opt in ['--ask', '-a']:
            ask = True
        elif opt == '--files-from':
            if arg == '-':
                files_from = sys.stdin
            else:
                files_from = open(arg)
        elif opt == '--ignore':
            ignore_lines.append(re.compile(arg))
        elif opt == '--no-skip-message':
            no_skip_message = True
        else:
            raise Exception('There is a typo in this if ... elif ...: %s %s' % (opt, arg))

    if test:
        if len(opts) != 1 or args:
            print('--test allows no other args.')
            sys.exit(1)
        return unittest()
    if (not pattern) and (not text) and len(args) > 1:
        pattern = args[0]
        text = args[1]
        args = args[2:]

    if args and files_from:
        print('Too many arguments (--files-from is set): %s' % args)
        sys.exit(1)
    for arg in args:
        if not os.path.exists(arg):
            print('%s does not exist' % arg)
            sys.exit(2)

    if None in [pattern, text]:
        usage()
        sys.exit(2)
    if len(args) == 0 and not files_from:
        # reprec.py  .... $(find ...) --> don't use '.' if the find command returns nothing.
        print('Use "." as last argument, if you want to replace recursive in the current directory.')
        sys.exit(2)
    counter = replace_recursive(args, pattern, text, filename_regex, no_regex,
                                verbose=verbose, dotall=dotall,
                                print_lines=print_lines, novcexclude=novcexclude, ask=ask,
                                files_from=files_from, ignorecase=ignorecase, ignore_lines=ignore_lines,
                                no_skip_message=no_skip_message)
    dirs = counter['dirs']
    files = counter['files']
    lines = counter['lines']
    files_checked = counter['files-checked']
    print('Replaced %i directories %i files %i lines. %i files checked' % (dirs, files, lines, files_checked))


def diffdir(tempdir, shoulddir):
    # print 'diffdir %s %s' % (tempdir, shoulddir)
    assert tempdir != shoulddir
    tempfiles = os.listdir(tempdir)
    tempfiles.sort()
    shouldfiles = os.listdir(shoulddir)
    shouldfiles.sort()
    if not tempfiles == shouldfiles:
        raise Exception('diffdir(%s, %s): different files: %s %s' % (
            tempdir, shoulddir, tempfiles, shouldfiles))
    for filename in tempfiles:
        file_name = os.path.join(tempdir, filename)
        should = os.path.join(shoulddir, filename)
        if os.path.isdir(file_name):
            assert os.path.isdir(should)
            diffdir(file_name, should)
        else:
            data_is = open(file_name).read()
            data_should = open(should).read()
            if data_is != data_should:
                raise Exception('Files different: %s %s' % (file_name, should))
            else:
                # print 'Files are equal: %s %s' % (file_name, should)
                pass


def unittest_with_regex():
    tempdir = tempfile.mktemp(prefix='reprec_unittest_dir')
    os.mkdir(tempdir)
    data_start = 'abcdefg ü\n'
    for i in range(10):
        file_name = os.path.join(tempdir, str(i))
        with codecs.open(file_name, 'w', 'utf8') as fd:
            fd.write(data_start)
    counter = replace_recursive([tempdir], r'[cd]+', '12')
    assert counter == {'dirs': 1, 'files': 10, 'lines': 10, 'files-checked': 10}
    shoulddir = tempfile.mktemp(prefix='reprec_unittest_should2')
    os.mkdir(shoulddir)
    result_should = 'ab12efg ü\n'
    for i in range(10):
        file_name = os.path.join(shoulddir, str(i))
        with codecs.open(file_name, 'w', 'utf8') as fd:
            fd.write(result_should)
    diffdir(tempdir, shoulddir)
    print('Unittest regex: OK')
    shutil.rmtree(tempdir)
    shutil.rmtree(shoulddir)


def unittest_no_regex():
    tempdir = tempfile.mktemp(prefix='reprec_unittest')
    os.mkdir(tempdir)
    data_start = 'abcdefg ü\n'
    for i in range(10):
        file_name = os.path.join(tempdir, str(i))
        with codecs.open(file_name, 'w', 'utf8') as fd:
            fd.write(data_start)
    counter = replace_recursive([tempdir], b'ü', b'ö', no_regex=True)
    assert counter == {'dirs': 1, 'files': 10, 'lines': 10, 'files-checked': 10}, counter
    shoulddir = tempfile.mktemp(prefix='reprec_unittest_should')
    os.mkdir(shoulddir)
    result_should = 'abcdefg ö\n'
    for i in range(10):
        file_name = os.path.join(shoulddir, str(i))
        with codecs.open(file_name, 'w', 'utf8') as fd:
            fd.write(result_should)
    diffdir(tempdir, shoulddir)
    print('Unittest no_regex: OK')
    shutil.rmtree(tempdir)
    shutil.rmtree(shoulddir)


def unittest_file_has_ending_to_ignore():
    reprec = ReplaceRecursive('pattern', 'insert')
    assert not reprec.file_has_ending_to_ignore('foo.py')
    assert reprec.file_has_ending_to_ignore('foo.pyc')
    print('unittest_file_has_ending_to_ignore: OK')


def unittest():
    unittest_with_regex()
    unittest_no_regex()
    unittest_file_has_ending_to_ignore()


### copy from: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/134892
class _Getch:
    '''Gets a single character from standard input.  Does not echo to the
screen.'''

    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self):
        return self.impl()


class _GetchUnix:
    def __call__(self):
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        pass

    def __call__(self):
        import msvcrt
        return msvcrt.getch()


getch = _Getch()
### Ende copy

if __name__ == '__main__':
    main()
