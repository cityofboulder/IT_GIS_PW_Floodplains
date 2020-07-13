import os
import shutil
import unittest
import managedisk

from pathlib import Path


test_folders = [f'.{os.sep}listfiles', f'.{os.sep}otherlistfiles']
test_files = [f'.{os.sep}listfiles{os.sep}poo.js',
              f'.{os.sep}listfiles{os.sep}poo.html',
              f'.{os.sep}otherlistfiles{os.sep}poop.css',
              f'.{os.sep}otherlistfiles{os.sep}poo.html']


class TestListFiles(unittest.TestCase):
    """Class to test the list_files function

    A custom directory with files is set up and torn down for each
    test."""

    def setUp(self):
        for folder in test_folders:
            os.mkdir(os.path.abspath(folder))
        for f in test_files:
            Path(os.path.abspath(f)).touch()

    def tearDown(self):
        for f in test_folders:
            shutil.rmtree(os.path.abspath(f))

    def test_include(self):
        """Tests the include variable."""
        self.assertEqual(len(managedisk.list_files(['poo'])), 4)
        self.assertEqual(len(managedisk.list_files(['poop'])), 1)
        self.assertEqual(len(managedisk.list_files(['html'])), 2)

    def test_exclude(self):
        """Tests the exclude variable."""
        temp = managedisk.list_files(['otherlistfiles'], ['html'])[0]
        result = temp.split(os.sep).pop()
        self.assertEqual(result, 'poop.css')

    def test_case(self):
        """Tests whether case is controlled"""
        self.assertEqual(len(managedisk.list_files(['poOp'])), 1)

    def test_list(self):
        self.assertEqual(
            len(managedisk.list_files('otherlistfiles', '.css')), 1)


if __name__ == '__main__':
    unittest.main()
