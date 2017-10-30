# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import codecs
import tempfile
import unittest

import os

import shutil
from reprec import replace_recursive, unicode_error_hint
from reprec import diffdir
from reprec import ReplaceRecursive


class MyTestCase(unittest.TestCase):


    def test_with_regex(self):
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


    def test_no_regex(self):
        tempdir = tempfile.mktemp(prefix='reprec_unittest')
        os.mkdir(tempdir)
        data_start = 'abcdefg ü\n'
        for i in range(10):
            file_name = os.path.join(tempdir, str(i))
            with codecs.open(file_name, 'w', 'utf8') as fd:
                fd.write(data_start)
        counter = replace_recursive([tempdir], 'ü', 'ö', no_regex=True)
        assert counter == {'dirs': 1, 'files': 10, 'lines': 10, 'files-checked': 10}, counter
        shoulddir = tempfile.mktemp(prefix='reprec_unittest_should')
        os.mkdir(shoulddir)
        result_should = 'abcdefg \xf6\n'
        for i in range(10):
            file_name = os.path.join(shoulddir, str(i))
            with codecs.open(file_name, 'w', 'utf8') as fd:
                fd.write(result_should)
        diffdir(tempdir, shoulddir)
        print('Unittest no_regex: OK')
        shutil.rmtree(tempdir)
        shutil.rmtree(shoulddir)


    def test_file_has_ending_to_ignore(self):
        reprec = ReplaceRecursive('pattern', 'insert')
        assert not reprec.file_has_ending_to_ignore('foo.py')
        assert reprec.file_has_ending_to_ignore('foo.pyc')
        print('unittest_file_has_ending_to_ignore: OK')


    def test_unicode_error_hint(self):
        try:
            'before-ü-after'.encode('latin1').decode('utf8')
        except UnicodeError as exc:
            self.assertEqual(b'before-\xfc-after', unicode_error_hint(exc))
            return
        raise Exception('No unicode error?')


    def test_do_file_utf8(self):
        reprec = ReplaceRecursive('e', '_')
        temp = tempfile.mktemp(prefix=self.id())
        with open(temp, 'wb') as fd:
            fd.write('before-ü-after\n'.encode('utf8'))
        reprec.do_file(temp)
        self.assertEqual(b'b_for_-\xc3\xbc-aft_r\n', open(temp).read())

    def test_do_file_latin1(self):
        # Up to now latin1 is not supported. Feel free to improve this
        reprec = ReplaceRecursive('e', '_')
        temp = tempfile.mktemp(prefix=self.id())
        with open(temp, 'wb') as fd:
            fd.write('before-ü-after\n'.encode('latin1'))
        self.assertRaises(UnicodeDecodeError, reprec.do_file, temp)
