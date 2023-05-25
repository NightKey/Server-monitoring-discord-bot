try:
    import os
    import inspect
    import sys
    import unittest
finally:
    currentdir = os.path.dirname(os.path.abspath(
        inspect.getfile(inspect.currentframe())))
    parentdir = os.path.dirname(currentdir)
    sys.path.insert(0, parentdir)
    parentdir = os.path.dirname(parentdir)
    sys.path.insert(0, parentdir)
    from smdb_version_controll import Version, Updater


class VersionTest(unittest.TestCase):
    v0 = Version(0, 0, 0)
    v1 = Version(0, 0, 1)
    v2 = Version(0, 1, 0)
    v3 = Version(1, 0, 0)

    def test_1_versions_compare_correctly(self):
        self.assertLess(self.v0, self.v1)
        self.assertLess(self.v1, self.v2)
        self.assertLess(self.v2, self.v3)
        self.assertLess(self.v0, self.v3)

    def test_2_version_file_created(self):
        self.v3.to_file()
        self.assertTrue(os.path.exists("version"))

    def test_3_version_correctly_created_from_file(self):
        vf = Version.from_version("version")
        self.assertEqual(vf, self.v3)

    def test_4_version_string_is_correct(self):
        self.assertEqual(str(self.v0), "0.0.0")

    def test_5_version_correctly_created_from_list(self):
        self.assertEqual(self.v0, Version.from_version(
            [Version.VERSION_HEADER, "0.0.0"]))


if __name__ == "__main__":
    unittest.main(exit=False)
    os.remove("version")
