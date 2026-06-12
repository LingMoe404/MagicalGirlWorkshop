from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingConfigTests(unittest.TestCase):
    def test_workflow_builds_standalone_portable_and_installer_artifacts(self):
        workflow = (ROOT / ".github" / "workflows" / "autobuild.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("--standalone", workflow)
        self.assertNotIn("--onefile", workflow)
        self.assertIn("build/nuitka/main.dist", workflow)
        self.assertIn("MagicalGirlWorkshop-Portable", workflow)
        self.assertIn("MagicalGirlWorkshop-Installer", workflow)
        self.assertIn("installer/MagicalGirlWorkshop.iss", workflow)

    def test_installer_uses_user_scope_and_shared_staging_directory(self):
        installer = (ROOT / "installer" / "MagicalGirlWorkshop.iss").read_text(
            encoding="utf-8"
        )

        self.assertIn(r"DefaultDirName={localappdata}\Programs\MagicalGirlWorkshop", installer)
        self.assertIn("PrivilegesRequired=lowest", installer)
        self.assertIn(r'Source: "{#SourceDir}\*"', installer)
        self.assertIn(r'Name: "{autoprograms}\MagicalGirlWorkshop"', installer)
        self.assertIn(r'Name: "{autodesktop}\MagicalGirlWorkshop"', installer)
        self.assertIn(r'Name: "{app}\cache"', installer)
        self.assertIn(r'Name: "{app}\config.ini"', installer)


if __name__ == "__main__":
    unittest.main()
