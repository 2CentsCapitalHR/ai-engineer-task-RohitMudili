import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.checklist import ChecklistProcessor

class TestChecklistProcessing(unittest.TestCase):
    """Test checklist processing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = ChecklistProcessor()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_checklist_loading(self):
        """Test checklist loading functionality"""
        # Test that checklists are loaded
        self.assertIsInstance(self.processor.checklists, dict)
        
        # Test that incorporation checklist is available
        incorporation_checklist = None
        for process_name, checklist in self.processor.checklists.items():
            if "incorporation" in process_name.lower():
                incorporation_checklist = checklist
                break
        
        if incorporation_checklist:
            self.assertIn("process", incorporation_checklist)
            self.assertIn("requirements", incorporation_checklist)
    
    def test_applicable_checklist_selection(self):
        """Test applicable checklist selection"""
        # Test incorporation process
        process = "Company Incorporation"
        entity_type = "Private Company Limited by Shares (Non-Financial)"
        
        checklist = self.processor.get_applicable_checklist(process, entity_type)
        
        if checklist:
            self.assertIn("process", checklist)
            self.assertIn("requirements", checklist)
        
        # Test unknown process
        unknown_process = "Unknown Process"
        checklist = self.processor.get_applicable_checklist(unknown_process, entity_type)
        
        # Should return None for unknown process
        self.assertIsNone(checklist)
    
    def test_requirement_checking(self):
        """Test requirement checking functionality"""
        # Create test documents
        documents = [
            {
                "filename": "articles_of_association.docx",
                "full_text": "Articles of Association for ABC Company"
            },
            {
                "filename": "register_of_members.docx", 
                "full_text": "Register of Members and Directors"
            }
        ]
        
        # Create a mock checklist
        mock_checklist = {
            "process": "Company Incorporation",
            "entity_type": "Private Company Limited by Shares (Non-Financial)",
            "requirements": [
                {
                    "name": "Articles of Association",
                    "mandatory": True,
                    "applies_if": "always",
                    "sources": ["https://example.com"]
                },
                {
                    "name": "Register of Members and Directors",
                    "mandatory": True,
                    "applies_if": "always",
                    "sources": ["https://example.com"]
                },
                {
                    "name": "UBO Declaration",
                    "mandatory": True,
                    "applies_if": "always",
                    "sources": ["https://example.com"]
                }
            ]
        }
        
        # Test requirement checking
        results = self.processor.check_requirements(documents, mock_checklist)
        
        self.assertIn("total_requirements", results)
        self.assertIn("found_requirements", results)
        self.assertIn("missing_requirements", results)
        self.assertIn("compliance_score", results)
        
        # Should find 2 requirements and miss 1
        self.assertEqual(results["total_requirements"], 3)
        self.assertEqual(len(results["found_requirements"]), 2)
        self.assertEqual(len(results["missing_requirements"]), 1)
        
        # Compliance score should be 2/3 = 0.67
        self.assertAlmostEqual(results["compliance_score"], 0.67, places=2)
    
    def test_requirement_presence_detection(self):
        """Test requirement presence detection"""
        doc_names = ["articles.docx", "register.docx", "other.docx"]
        doc_contents = [
            "Articles of Association content",
            "Register of Members content", 
            "Some other content"
        ]
        combined_content = " ".join(doc_contents)
        
        # Test finding a requirement
        found = self.processor._check_requirement_presence(
            "Articles of Association", doc_names, doc_contents, combined_content
        )
        
        self.assertIsNotNone(found)
        self.assertIn("found_in", found)
        self.assertIn("confidence", found)
        self.assertGreater(found["confidence"], 0)
        
        # Test not finding a requirement
        not_found = self.processor._check_requirement_presence(
            "Non-existent Requirement", doc_names, doc_contents, combined_content
        )
        
        self.assertIsNone(not_found)
    
    def test_requirement_patterns(self):
        """Test requirement pattern generation"""
        # Test articles patterns
        patterns = self.processor._get_requirement_patterns("Articles of Association")
        self.assertIn("articles of association", patterns)
        self.assertIn("memorandum of association", patterns)
        
        # Test register patterns
        patterns = self.processor._get_requirement_patterns("Register of Members")
        self.assertIn("register of members", patterns)
        self.assertIn("register of directors", patterns)
        
        # Test declaration patterns
        patterns = self.processor._get_requirement_patterns("UBO Declaration")
        self.assertIn("ubo declaration", patterns)
        self.assertIn("ultimate beneficial owner", patterns)
    
    def test_gap_report_generation(self):
        """Test gap report generation"""
        # Create test analysis result
        analysis_result = {
            "documents": [
                {
                    "filename": "articles.docx",
                    "full_text": "Articles of Association"
                }
            ],
            "process": "Company Incorporation",
            "entity_type": "Private Company Limited by Shares (Non-Financial)",
            "redflags": []
        }
        
        # Generate gap report
        report = self.processor.generate_gap_report(analysis_result)
        
        # Check if report was generated successfully
        if "error" not in report:
            self.assertIn("process", report)
            self.assertIn("entity_type", report)
            self.assertIn("documents_uploaded", report)
            self.assertIn("requirement_analysis", report)
            self.assertIn("suggestions", report)
            self.assertIn("regulatory_context", report)
            self.assertIn("compliance_status", report)
        else:
            # If no applicable checklist found, should return error
            self.assertIn("error", report)
            self.assertIn("available_checklists", report)
    
    def test_suggestion_generation(self):
        """Test suggestion generation for missing requirements"""
        requirement_results = {
            "missing_requirements": [
                {
                    "name": "Articles of Association",
                    "mandatory": True,
                    "sources": ["https://example.com"]
                },
                {
                    "name": "Register of Members",
                    "mandatory": False,
                    "sources": ["https://example.com"]
                }
            ]
        }
        
        mock_checklist = {
            "process": "Company Incorporation",
            "requirements": []
        }
        
        suggestions = self.processor._generate_suggestions(requirement_results, mock_checklist)
        
        self.assertEqual(len(suggestions), 2)
        
        # Check first suggestion (mandatory)
        first_suggestion = suggestions[0]
        self.assertEqual(first_suggestion["requirement"], "Articles of Association")
        self.assertEqual(first_suggestion["priority"], "High")
        self.assertIn("estimated_time", first_suggestion)
        self.assertIn("sources", first_suggestion)
        self.assertIn("notes", first_suggestion)
        
        # Check second suggestion (non-mandatory)
        second_suggestion = suggestions[1]
        self.assertEqual(second_suggestion["priority"], "Medium")
    
    def test_compliance_status_determination(self):
        """Test compliance status determination"""
        # Test compliant
        compliant_results = {"compliance_score": 0.95}
        status = self.processor._get_compliance_status(compliant_results)
        self.assertEqual(status, "Compliant")
        
        # Test mostly compliant
        mostly_compliant_results = {"compliance_score": 0.75}
        status = self.processor._get_compliance_status(mostly_compliant_results)
        self.assertEqual(status, "Mostly Compliant")
        
        # Test partially compliant
        partially_compliant_results = {"compliance_score": 0.60}
        status = self.processor._get_compliance_status(partially_compliant_results)
        self.assertEqual(status, "Partially Compliant")
        
        # Test non-compliant
        non_compliant_results = {"compliance_score": 0.30}
        status = self.processor._get_compliance_status(non_compliant_results)
        self.assertEqual(status, "Non-Compliant")
    
    def test_requirement_applies_logic(self):
        """Test requirement applies logic"""
        documents = [{"filename": "test.docx", "full_text": "test content"}]
        
        # Test always applies
        applies = self.processor._requirement_applies("always", documents)
        self.assertTrue(applies)
        
        # Test other conditions (placeholder for future implementation)
        applies = self.processor._requirement_applies("some_condition", documents)
        self.assertTrue(applies)  # Currently returns True for all conditions
    
    def test_checklist_applies_logic(self):
        """Test checklist applies logic"""
        # Test exact match
        checklist = {"entity_type": "Private Company Limited by Shares (Non-Financial)"}
        entity_type = "Private Company Limited by Shares (Non-Financial)"
        applies = self.processor._checklist_applies(checklist, entity_type)
        self.assertTrue(applies)
        
        # Test partial match
        checklist = {"entity_type": "Private Company Limited by Shares"}
        entity_type = "Private Company Limited by Shares (Non-Financial)"
        applies = self.processor._checklist_applies(checklist, entity_type)
        self.assertTrue(applies)
        
        # Test no entity type restriction
        checklist = {"entity_type": ""}
        entity_type = "Any Entity Type"
        applies = self.processor._checklist_applies(checklist, entity_type)
        self.assertTrue(applies)
        
        # Test no match
        checklist = {"entity_type": "Different Entity Type"}
        entity_type = "Private Company Limited by Shares (Non-Financial)"
        applies = self.processor._checklist_applies(checklist, entity_type)
        self.assertFalse(applies)

if __name__ == "__main__":
    unittest.main()
