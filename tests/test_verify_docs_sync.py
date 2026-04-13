import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.verify_docs_sync import evaluate_changed_files


class TestVerifyDocsSync(unittest.TestCase):
    def test_non_doc_change_requires_verification_checklist(self):
        missing = evaluate_changed_files(
            [
                "collectors/sampler.py",
                "docs/Architecture/SystemOverview.md",
                "docs/Wiki/ProjectStructure.md",
            ]
        )

        self.assertTrue(any("Baseline docs rule" in message for message in missing))
        self.assertTrue(any("VerificationChecklist.md" in message for message in missing))

    def test_agents_change_requires_only_documentation_workflow(self):
        missing = evaluate_changed_files(
            [
                "AGENTS.md",
            ]
        )

        self.assertEqual(
            [
                "- Rule 'agent-or-doc-workflow' triggered by AGENTS.md: update docs/Best Practices/DocumentationWorkflow.md"
            ],
            missing,
        )

    def test_ci_change_requires_reliability_report_and_verification_checklist(self):
        missing = evaluate_changed_files(
            [
                ".github/workflows/windows-ci.yml",
                "docs/Current Phase/VerificationChecklist.md",
            ]
        )

        self.assertTrue(any("ci-or-verification-automation" in message for message in missing))
        self.assertTrue(any("ReliabilityReport.md" in message for message in missing))
        self.assertFalse(any("Baseline docs rule" in message for message in missing))

    def test_packaging_change_requires_current_phase_and_reliability_report(self):
        missing = evaluate_changed_files(
            [
                "build.bat",
                "docs/Architecture/RuntimeAndPackaging.md",
                "docs/Wiki/Changelog.md",
                "docs/Current Phase/VerificationChecklist.md",
            ]
        )

        self.assertTrue(any("packaging-or-runtime" in message for message in missing))
        self.assertTrue(any("CurrentPhase.md" in message for message in missing))
        self.assertTrue(any("ReliabilityReport.md" in message for message in missing))

    def test_packaging_helper_script_requires_packaging_docs(self):
        missing = evaluate_changed_files(
            [
                "scripts/publish_release_to_share.ps1",
                "docs/Current Phase/VerificationChecklist.md",
            ]
        )

        self.assertTrue(any("packaging-or-runtime" in message for message in missing))
        self.assertTrue(any("RuntimeAndPackaging.md" in message for message in missing))
        self.assertTrue(any("CurrentPhase.md" in message for message in missing))
        self.assertTrue(any("ReliabilityReport.md" in message for message in missing))

    def test_playwright_regression_change_requires_runtime_reliability_and_verification_docs(self):
        missing = evaluate_changed_files(
            [
                "scripts/verify_playwright_prebuild_regression.js",
                "docs/Current Phase/VerificationChecklist.md",
            ]
        )

        self.assertTrue(any("playwright-or-regression-automation" in message for message in missing))
        self.assertTrue(any("RuntimeAndPackaging.md" in message for message in missing))
        self.assertTrue(any("ReliabilityReport.md" in message for message in missing))
        self.assertFalse(any("Baseline docs rule" in message for message in missing))

    def test_local_bug_logs_and_playwright_artifacts_are_ignored(self):
        missing = evaluate_changed_files(
            [
                "bug/operation_0319_north side grab.log",
                "tests/operation.log",
                "tools/playwright-mcp/01-home-desktop.png",
                "tools/playwright-mcp/03-main-screen-snapshot.md",
                "tools/playwright-mcp/console-errors.txt",
            ]
        )

        self.assertEqual([], missing)

    def test_expected_doc_set_passes(self):
        missing = evaluate_changed_files(
            [
                "build.bat",
                "scripts/verify_docs_sync.py",
                "scripts/doc_sync_rules.toml",
                "docs/Architecture/RuntimeAndPackaging.md",
                "docs/Best Practices/DocumentationWorkflow.md",
                "docs/Current Phase/CurrentPhase.md",
                "docs/Current Phase/VerificationChecklist.md",
                "docs/Wiki/Changelog.md",
                "docs/Wiki/ReliabilityReport.md",
            ]
        )

        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
