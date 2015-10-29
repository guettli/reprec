#!/usr/bin/env python
# -*- coding: utf-8 -*-
#(C) 2002-2015 Thomas Guettler http://www.thomas-guettler.de
#Feedback is Welcome! (Even hints to typos)
#This script is in the public domain
#
#Recursively replace strings in files
#
# Other Solution: rpl http://www.laffeycomputer.com/rpl.html
#
# Thanks to Reinhard Wobst for some hints.

# TODO:
#  - --verbose-lines: Print each changed line: old + new
#  - If root, new file is owned by root --> chown
#  - change ugly counter["lines"] to counter.lines
#  - Unittest for dotall.
#
# Changes:
#
# 2010-07-20:
#   - Don't skip symbolic links if given on the commandline or with --files-from
#
# 2008-08-01:
#   - Ignore lines. Option --ignore was added
#   - --ask: Handle Escape Character (Cursor up resulted in A (replace all) before)
#   - Warning if Newline at the end gets lost during replacement (only for --ask)
#
# 2007-04-05:
#   - Check for too many arguments, if --files-from is used.
#
# 2007-02-15:
#   - Added --files-from
#   - True and False instead of 1 and 0
#
# 2006-09-27:
#   - New option: --ask (interactive)
#   - use chmod() to set the access-mode like the old file (ie execute bit)
#
# 2006-06-28:
#   - ".svn" and "CVS" are ignored by default. Added Option --novcexclude
#
# 2004-11-03:
#   - Use a class instead of passing options again and again.
#   - Option "print-lines"

# Python Imports
import os
import re
import sys
import getopt
import random
import shutil
import tempfile


def usage():
    print \
"""Usage: %s
     [-p|--pattern] p
     [-i|--insert] i
     [-f|--filename regex]
     [-n|--no-regex]
     [-v|--verbose]
     [-a|--ask]
     [--print-lines]
     [--dotall]
     [--ignorecase]
     [--unittest]
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

dotall:      In regular expressions "." matches newlines, too.
             Not supported with --ask and --print-lines.

ignorecase:  ...

unittest:    Run the unittest. No other arguments are allowed.

novcexclude: Don't exclude the directories called '.svn' or 'CVS'.
             By default they get ignored.

ask:         Aks before replacing (interactive).

files-from:  Read filenames from file or stdin if "-".
             Skip directories.

ignore:      Ignore lines that match a regular expression.
             This options can be given several times.

no-skip-message: Don't print "Skipping ..."

Example:
 %s --pattern '(xml)' --insert '\\1\\1' .
 -->This will replace all "xml" with "xmlxml"

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
""" % (
     os.path.basename(sys.argv[0]),
     os.path.basename(sys.argv[0]),
     os.path.basename(sys.argv[0]),
     os.path.basename(sys.argv[0]))

def replace_recursive(dirname, pattern, text, filename_regex=None,
                      no_regex=None, counter=None, verbose=False,
                      dotall=False, print_lines=False, novcexclude=False, ask=False,
                      files_from=None, ignorecase=False, ignore_lines=[], no_skip_message=False
                      ):
    if ask and files_from:
        raise Exception("You can't use --ask and --files-from together since reading y/n from stdin is not possible")
    if dotall and ignore_lines:
        raise Exception("You can't use --dotall and --ignore together")

    rr=ReplaceRecursive(pattern, text, filename_regex,
                        no_regex, verbose, dotall,
                        print_lines, novcexclude, ask, ignorecase, ignore_lines, no_skip_message)

    if files_from:
        assert not dirname, dirname
        for line in files_from:
            file=line.rstrip()
            if os.path.isdir(file):
                if not self.no_skip_message:
                    print "Skipping", file
                continue
            rr.do(file, follow_symlink_files=[file])
        return rr.counter

    return rr.do(dirname, follow_symlink_files=dirname)

class ReplaceRecursive:
    def __init__(self, pattern, text, filename_regex=None,
                 no_regex=None, verbose=False,
                 dotall=False, print_lines=False, novcexclude=False, ask=False,
                 ignorecase=False, ignore_lines=[], no_skip_message=False,
                 ):
        self.pattern=pattern
        self.text=text
        self.filename_regex=filename_regex
        self.no_regex=no_regex
        self.verbose=verbose
        self.dotall=dotall
        self.print_lines=print_lines
        self.novcexclude=novcexclude
        self.ask=ask
        self.ignorecase=ignorecase
        self.ignore_lines=ignore_lines
        self.no_skip_message=no_skip_message

        self.counter={"dirs": 0, "files": 0, "lines": 0, "files-checked": 0}
        self.exit_after_this_file=False
        self.always_yes=False
        flags=0
        if not no_regex:
            if dotall:
                flags|=re.DOTALL
            if ignorecase:
                flags|=re.IGNORECASE
            try:
                self.regex=re.compile(pattern, flags)
            except re.error, e:
                print "regular expression has syntax error: '%s': %s (do you want --no-regex ?)" % (
                    pattern, str(e))
                sys.exit(3)
        else:
            self.regex=None

    def do(self, dirname, follow_symlink_files=[]):
        if isinstance(dirname, (tuple, list)):
            for dir in dirname:
                assert isinstance(dir, basestring), repr(dir)
                self.do(dir)
            return self.counter
        if (not dirname in follow_symlink_files) and os.path.islink(dirname):
            if not self.no_skip_message:
                print "Skipping symbolic link %s" % dirname
            return self.counter
        if os.path.isdir(dirname):
            dir_list=os.listdir(dirname)
            isdir=True
        else:
            dir_list=[dirname]
            isdir=False
        start_counter=self.counter["files"]
        for file in dir_list:
            if self.exit_after_this_file:
                break
            if isdir:
                file=os.path.join(dirname, file)
            if (not file in follow_symlink_files) and os.path.islink(file):
                if not self.no_skip_message:
                    print "Skipping symbolic link %s" % file
                continue
            if os.path.isdir(file):
                if (not self.novcexclude) and os.path.basename(file) in [".svn", "CVS", ".git", ".hg", ".bzr", ".idea"]:
                    if not self.no_skip_message:
                        print "Skipping", file
                    continue
                self.do(file)
            elif os.path.isfile(file):
                if self.file_has_ending_to_ignore(file):
                    continue
                if self.filename_regex and not re.match(self.filename_regex,
                                                        file):
                    continue
                fd=open(file, "rb")
                if self.verbose:
                    print "Opening %s" % file
                self.counter["files-checked"]+=1
                counter_start=self.counter["lines"]
                out=[]
                if not self.dotall:
                    while True:
                        line=fd.readline()
                        if not line:
                            break
                        ignore_this_line=False
                        for ignore_line in self.ignore_lines:
                            if ignore_line.search(line):
                                ignore_this_line=True
                                break
                        if ignore_this_line:
                            if self.verbose:
                                print "Ignoring %s line: %s" % (file, line.rstrip())
                            out.append(line)
                            continue
                        if self.no_regex:
                            line_replaced=line.replace(self.pattern, self.text)
                            if line_replaced!=line:
                                if self.ask and (not self.doask(file, line, line_replaced)):
                                    line_replaced=line
                                else:
                                    self.counter["lines"]+=1
                                    if self.print_lines:
                                        sys.stdout.write("%s old: %s%s new: %s" % (
                                            file, line, file, line_replaced))
                        else:
                            (line_replaced, n)=self.regex.subn(self.text, line)
                            if n:
                                if self.ask and (not self.doask(file, line, line_replaced)):
                                    line_replaced=line
                                else:
                                    self.counter["lines"]+=1
                                    if self.print_lines:
                                        sys.stdout.write("%s old: %s%s new: %s" % (
                                            file, line, file, line_replaced))
                        out.append(line_replaced)
                    out=''.join(out)
                else: # if self.dotall
                    assert not self.ask
                    content=fd.read()
                    (out, n)=self.regex.subn(self.text, content)
                    if n:
                        self.counter["lines"]+=n
                fd.close()
                counter_now=self.counter["lines"]
                if counter_now!=counter_start:
                    #Some lines where changed
                    self.counter["files"]+=1
                    temp="%s_%s" % (file, random.randint(100000, 999999))
                    fd=open(temp, "wb")
                    fd.write(out)
                    fd.close()
                    # os.rename: single system call, so no
                    # half written files will exist if to process gets
                    # killed.
                    mode=os.stat(file).st_mode
                    os.chmod(temp, mode)
                    os.rename(temp, file)
                    if self.verbose:
                        print "Changed %s lines in %s" % (
                            counter_now - counter_start, file)
            else:
                if not os.path.exists(file):
                    print "%s does not exist" % file
                else:
                    print "Ignoring %s: No directory and not a file" % file

        if self.counter["files"]!=start_counter:
            self.counter["dirs"]+=1

        return self.counter


    file_endings_to_ignore=['~', '.pyc', '.db']

    def file_has_ending_to_ignore(self, file):
        for ending in self.file_endings_to_ignore:
            if file.endswith(ending):
                if not self.no_skip_message:
                    print "Skipping", file
                return True
        return False

    def doask(self, file, line, line_replaced):
        if self.exit_after_this_file:
            #print "Default no"
            return False
        if self.always_yes:
            return True
        print "Replace in %s:" % (file)
        print line
        print "with:"
        print line_replaced
        if line.endswith('\n') and not line_replaced.endswith('\n'):
            print "WARNING: Newline at the end of line was stripped!"
        while True:
            print "Please choose one action:"
            print " y=yes"
            print " n=No"
            print " A=always yes (don't ask again)"
            print " q=quit (save changes in this file)"
            print " x=exit (exit now, discard changes in this file)"
            char=getch()
            if char=='\x1b':
                # Stupid things can happen:
                # Cursor-Up sends ESC [ A
                # --> all files get replaced!

                # Try to ignore Escape and following characters
                print "You send Escape, ignoring input until next character",
                sys.stdout.flush()
                while True:
                    next=getch()
                    if re.match(r'[a-zA-Z~]', next):
                        print
                        break
                    print "Ingoring %r" % (next),
                    sys.stdout.flush()
                continue
            if char in "yYjJ":
                return True
            elif char in "nN":
                return False
            elif char in "qQ":
                self.exit_after_this_file=True
                return False
            elif char in "xX":
                sys.exit(1)
            elif char in "A":
                # svn/cvs use 'a' for abort if you use an empty commit message
                self.always_yes=True
                return True
            print "%r is not a valid action." % char

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:i:f:vna",
                                   ["pattern=", "insert=", "no-regex", "noregex",
                                    "verbose", "print-lines",
                                    "filename=",
                                    "dotall", "ignorecase",
                                    "unittest", "novcexclude", "ask", "files-from=",
                                    "ignore=",
                                    "no-skip-message"])
    except getopt.GetoptError, e:
        usage()
        print e
        sys.exit(2)
    no_regex=None
    pattern=None
    text=None
    filename_regex=None
    verbose=False
    dotall=False
    ignorecase=False
    test=None
    print_lines=False
    novcexclude=False
    ask=False
    files_from=None
    no_skip_message=False
    ignore_lines=[]
    for opt, arg in opts:
        if opt in ["--pattern", "-p"]:
            pattern=arg
        elif opt in ["--insert", "-i"]:
            text=arg
        elif opt in ["--no-regex", "--noregex", "-n"]:
            no_regex=True
        elif opt in ["--filename", "-f"]:
            filename_regex=arg
        elif opt in ["--verbose", "-v"]:
            verbose=True
        elif opt=="--dotall":
            dotall=True
        elif opt=="--ignorecase":
            ignorecase=True
        elif opt=="--unittest":
            test=True
        elif opt=="--print-lines":
            print_lines=True
        elif opt=="--novcexclude":
            novcexclude=True
        elif opt in ["--ask", "-a"]:
            ask=True
        elif opt=="--files-from":
            if arg=="-":
                files_from=sys.stdin
            else:
                files_from=open(arg)
        elif opt=="--ignore":
            ignore_lines.append(re.compile(arg))
        elif opt=="--no-skip-message":
            no_skip_message=True
        else:
            raise Exception("There is a typo in this if ... elif ...: %s %s" % (opt, arg))

    if test:
        if len(opts)!=1 or args:
            print "--test allows no other args."
            sys.exit(1)
        return unittest()
    if (not pattern) and (not text) and len(args)>1:
        pattern=args[0]
        text=args[1]
        args=args[2:]

    if args and files_from:
        print "Too many arguments (--files-from is set): %s" % args
        sys.exit(1)
    for arg in args:
        if not os.path.exists(arg):
            print '%s does not exist' % arg
            sys.exit(2)

    if None in [pattern, text]:
        usage()
        sys.exit(2)
    if len(args)==0 and not files_from:
        # reprec.py  .... $(find ...) --> don't use "." if the find command returns nothing.
        print 'Use "." as last argument, if you want to replace recursive in the current directory.'
        sys.exit(2)
    counter=replace_recursive(args, pattern, text, filename_regex, no_regex,
                              verbose=verbose, dotall=dotall,
                              print_lines=print_lines, novcexclude=novcexclude, ask=ask,
                              files_from=files_from, ignorecase=ignorecase, ignore_lines=ignore_lines, no_skip_message=no_skip_message)
    dirs=counter["dirs"]
    files=counter["files"]
    lines=counter["lines"]
    files_checked=counter["files-checked"]
    print "Replaced %i directories %i files %i lines. %i files checked" % (dirs, files, lines, files_checked)

def diffdir(tempdir, shoulddir):
    #print "diffdir %s %s" % (tempdir, shoulddir)
    assert tempdir!=shoulddir
    tempfiles=os.listdir(tempdir)
    tempfiles.sort()
    shouldfiles=os.listdir(shoulddir)
    shouldfiles.sort()
    if not tempfiles==shouldfiles:
        raise Exception("diffdir(%s, %s): different files: %s %s" % (
            tempdir, shoulddir, tempfiles, shouldfiles))
    for filename in tempfiles:
        file=os.path.join(tempdir, filename)
        should=os.path.join(shoulddir, filename)
        if os.path.isdir(file):
            assert os.path.isdir(should)
            diffdir(file, should)
        else:
            fd=open(file)
            data_is=fd.read()
            fd.close()
            fd=open(should)
            data_should=fd.read()
            fd.close()
            if data_is!=data_should:
                raise Exception("Files different: %s %s" % (file, should))
            else:
                #print "Files are equal: %s %s" % (file, should)
                pass

def unittest_with_regex():
    tempdir=tempfile.mktemp(prefix='reprec_unittest_dir')
    os.mkdir(tempdir)
    data="abcdefg\n"
    for i in range(10):
        file=os.path.join(tempdir, str(i))
        fd=open(file, "w")
        fd.write(data)
        fd.close()
    counter=replace_recursive([tempdir], r"[cd]+", "12")
    assert counter=={'dirs': 1, 'files': 10, 'lines': 10, 'files-checked': 10}
    shoulddir=tempfile.mktemp(prefix='reprec_unittest_should2')
    os.mkdir(shoulddir)
    data="ab12efg\n"
    for i in range(10):
        file=os.path.join(shoulddir, str(i))
        fd=open(file, "w")
        fd.write(data)
        fd.close()
    diffdir(tempdir, shoulddir)
    print "Unittest regex: OK"
    shutil.rmtree(tempdir)
    shutil.rmtree(shoulddir)


def unittest_no_regex():
    tempdir=tempfile.mktemp(prefix='reprec_unittest')
    os.mkdir(tempdir)
    data="abcdefg\n"
    for i in range(10):
        file=os.path.join(tempdir, str(i))
        fd=open(file, "w")
        fd.write(data)
        fd.close()
    counter=replace_recursive([tempdir], "cd", "12", no_regex=True)
    assert counter=={'dirs': 1, 'files': 10, 'lines': 10, 'files-checked': 10}, counter
    shoulddir=tempfile.mktemp(prefix='reprec_unittest_should')
    os.mkdir(shoulddir)
    data="ab12efg\n"
    for i in range(10):
        file=os.path.join(shoulddir, str(i))
        fd=open(file, "w")
        fd.write(data)
        fd.close()
    diffdir(tempdir, shoulddir)
    print "Unittest no_regex: OK"
    shutil.rmtree(tempdir)
    shutil.rmtree(shoulddir)

def unittest_file_has_ending_to_ignore():
    reprec=ReplaceRecursive('pattern', 'insert')
    assert not reprec.file_has_ending_to_ignore('foo.py')
    assert reprec.file_has_ending_to_ignore('foo.pyc')
    print 'unittest_file_has_ending_to_ignore: OK'

def unittest():
    unittest_with_regex()
    unittest_no_regex()
    unittest_file_has_ending_to_ignore()

### Copied from: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/134892
class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


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
        import msvcrt
    def __call__(self):
        import msvcrt
        return msvcrt.getch()


getch = _Getch()
### Ende Kopie

if __name__ == '__main__':
    main()




