# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
import io
import os
import shutil
import tempfile
import unittest

from reprec import ReplaceRecursive, diffdir, replace_recursive, unicode_error_hint


class MyTestCase(unittest.TestCase):

    def test_with_regex(self):
        tempdir = tempfile.mktemp(prefix='reprec_unittest_dir')
        os.mkdir(tempdir)
        data_start = 'abcdefg ü\n'
        for i in range(10):
            file_name = os.path.join(tempdir, str(i))
            with codecs.open(file_name, 'w', 'utf8') as fd:
                fd.write(data_start)
        counter = replace_recursive([tempdir], b'[cd]+', b'12')
        assert counter == {'dirs': 1, 'files': 10, 'lines': 10, 'files-checked': 10}
        shoulddir = tempfile.mktemp(prefix='reprec_unittest_should2')
        os.mkdir(shoulddir)
        result_should = 'ab12efg ü\n'
        for i in range(10):
            file_name = os.path.join(shoulddir, str(i))
            with codecs.open(file_name, 'w', 'utf8') as fd:
                fd.write(result_should)
        diffdir(tempdir, shoulddir)
        shutil.rmtree(tempdir)
        shutil.rmtree(shoulddir)

    def test_no_regex(self):
        tempdir = tempfile.mktemp(prefix='reprec_unittest')
        os.mkdir(tempdir)
        data_start = 'abcdefg ü\n'
        for i in range(10):
            file_name = os.path.join(tempdir, str(i))
            with codecs.open(file_name, 'w', 'utf8') as fd:
                fd.write(data_start)
        counter = replace_recursive([tempdir], 'ü'.encode('utf8'), 'ö'.encode('utf8'), no_regex=True)
        assert counter == {'dirs': 1, 'files': 10, 'lines': 10, 'files-checked': 10}, counter
        shoulddir = tempfile.mktemp(prefix='reprec_unittest_should')
        os.mkdir(shoulddir)
        result_should = 'abcdefg \xf6\n'
        for i in range(10):
            file_name = os.path.join(shoulddir, str(i))
            with codecs.open(file_name, 'w', 'utf8') as fd:
                fd.write(result_should)
        diffdir(tempdir, shoulddir)
        shutil.rmtree(tempdir)
        shutil.rmtree(shoulddir)

    def test_file_has_ending_to_ignore(self):
        reprec = ReplaceRecursive(b'pattern', b'insert')
        assert not reprec.file_has_ending_to_ignore('foo.py')
        assert reprec.file_has_ending_to_ignore('foo.pyc')

    def test_file_has_ending_to_ignore__unicode(self):
        ReplaceRecursive._file_has_ending_to_ignore('umlaut-ü.pdf', ['.gz'])

    def test_unicode_error_hint(self):
        try:
            'before-ü-after'.encode('latin1').decode('utf8')
        except UnicodeError as exc:
            self.assertEqual(b'before-\xfc-after', unicode_error_hint(exc))
            return
        raise Exception('No unicode error?')

    def test_do_file_utf8(self):
        reprec = ReplaceRecursive(b'e', b'_')
        temp = tempfile.mktemp(prefix=self.id())
        with open(temp, 'wb') as fd:
            fd.write('before-ü-after\n'.encode('utf8'))
        reprec.do_file(temp)
        self.assertEqual('b_for_-ü-aft_r\n', io.open(temp, 'rt', encoding='utf8').read())

    def test_do_file_latin1(self):
        reprec = ReplaceRecursive(b'e', b'_')
        temp = tempfile.mktemp(prefix=self.id())
        with open(temp, 'wb') as fd:
            fd.write('before-ü-after\n'.encode('latin1'))
        reprec.do_file(temp)
        self.assertEqual('b_for_-ü-aft_r\n', io.open(temp, 'rt', encoding='latin1').read())
