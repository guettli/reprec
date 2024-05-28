import os
import unittest

import subx


class Test(unittest.TestCase):
    def test_readme_rst_valid(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        subx.call(cmd=['python', os.path.join(base_dir, 'setup.py'), 'check', '--metadata', '--restructuredtext', '--strict'])
