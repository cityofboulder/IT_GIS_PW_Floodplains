import os
import shutil
import unittest
import managedisk

from pathlib import Path


class TestListFiles(unittest.TestCase):

    def setUp(self):
        test_files = [f'.{os.sep}listfiles{os.sep}testfile.txt',
                      f'.{os.sep}listfiles{os.sep}testfile.py',
                      f'.{os.sep}otherlistfiles{os.sep}test1.txt',
                      f'.{os.sep}otherlistfiles{os.sep}test.html']
        for f in test_files:
            Path(os.path.abspath(f)).touch()

    def takeDown(self):
        test_folders = [f'.{os.sep}listfiles', f'.{os.sep}otherlistfiles']
        for f in test_folders:
            shutil.rmtree(os.path.abspath(f))

    def test_uniqueness(self):
        """Tests if the include and exclude variables do not contain
        overlapping keywords."""
        pass

    def test_include(self):
        """Tests the include variable."""
        pass

    def test_exclude(self):
        """Tests the exclude variable."""
        pass

    def test_delete(self):
        """Tests the delete flag."""
        pass


if __name__ == '__main__':
    unittest.main()
