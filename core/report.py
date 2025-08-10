import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

from pydantic import BaseModel, Field
from .utils import setup_logging, load_yaml_config

logger = setup_logging(__name__)

# Pydantic models for structured output
class Issue(BaseModel):
    document: str = Field(..., description="Document where issue was found")
    section: Optional[str] = Field(None, description="Section of the document")
    issue: str = Field(..., description="Description of the issue")
    severity: str = Field(..., description="Severity level (High/Medium/Low)")
    suggestion: Optional[str] = Field(None, description="Suggested fix or action")

class Requirement(BaseModel):
    name: str = Field(..., description="Name of the requirement")
    mandatory: bool = Field(..., description="Whether the requirement is mandatory")
    found: bool = Field(..., description="Whether the requirement was found")
    confidence: Optional[float] = Field(None, description="Confidence score for detection")
    found_in: Optional[List[str]] = Field(None, description="Where the requirement was found")

class MissingRequirement(BaseModel):
    name: str = Field(..., description="Name of the missing requirement")
    mandatory: bool = Field(..., description="Whether the requirement is mandatory")
    priority: str = Field(..., description="Priority level for obtaining this requirement")
    estimated_time: str = Field(..., description="Estimated time to obtain")
    sources: List[str] = Field(default_factory=list, description="Regulatory sources")
    notes: Optional[str] = Field(None, description="Additional notes")

class RegulatoryContext(BaseModel):
    relevant_sources: List[Dict[str, Any]] = Field(default_factory=list, description="Relevant regulatory sources")
    key_regulations: List[str] = Field(default_factory=list, description="Key regulations applicable")
    compliance_deadlines: List[str] = Field(default_factory=list, description="Important compliance deadlines")

class AnalysisReport(BaseModel):
    process: str = Field(..., description="Detected process type")
    entity_type: str = Field(..., description="Detected entity type")
    documents_uploaded: int = Field(..., description="Number of documents uploaded")
    required_documents: int = Field(..., description="Number of required documents")
    missing_document: Optional[str] = Field(None, description="Most critical missing document")
    issues_found: List[Issue] = Field(default_factory=list, description="Issues found in documents")
    requirements_analysis: Optional[Dict[str, Any]] = Field(None, description="Detailed requirements analysis")
    compliance_score: float = Field(..., description="Overall compliance score (0-1)")
    compliance_status: str = Field(..., description="Overall compliance status")
    suggestions: List[MissingRequirement] = Field(default_factory=list, description="Suggestions for missing requirements")
    regulatory_context: RegulatoryContext = Field(default_factory=RegulatoryContext, description="Regulatory context")
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Analysis timestamp")
    citations: List[str] = Field(default_factory=list, description="All citations used")

class ReportBuilder:
    def __init__(self, schema_path: str = "docs/output_schema.json", config_path: str = "config/settings.yml"):
        self.schema_path = schema_path
        self.config = load_yaml_config(config_path)
        self.output_schema = self._load_output_schema()
    
    def _load_output_schema(self) -> Dict[str, Any]:
        """Load the output schema definition"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading output schema: {e}")
            return {}
    
    def build_report(self, analysis_result: Dict[str, Any], 
                    checklist_result: Dict[str, Any],
                    redflags: List[Dict[str, Any]]) -> AnalysisReport:
        """Build a comprehensive analysis report"""
        
        # Extract basic information
        process = analysis_result.get("process", "Unknown")
        entity_type = analysis_result.get("entity_type", "Unknown")
        documents = analysis_result.get("documents", [])
        documents_uploaded = len(documents)
        
        # Process requirements analysis
        requirements_analysis = checklist_result.get("requirement_analysis", {})
        required_documents = requirements_analysis.get("total_requirements", 0)
        
        # Find most critical missing document
        missing_requirements = requirements_analysis.get("missing_requirements", [])
        missing_document = self._get_most_critical_missing_document(missing_requirements)
        
        # Convert redflags to Issue objects
        issues_found = self._convert_redflags_to_issues(redflags, documents)
        
        # Get compliance information
        compliance_score = requirements_analysis.get("compliance_score", 0.0)
        compliance_status = checklist_result.get("compliance_status", "Unknown")
        
        # Convert suggestions
        suggestions = self._convert_suggestions(checklist_result.get("suggestions", []))
        
        # Get regulatory context
        regulatory_context = self._build_regulatory_context(checklist_result.get("regulatory_context", {}))
        
        # Collect all citations
        citations = self._collect_citations(redflags, checklist_result)
        
        return AnalysisReport(
            process=process,
            entity_type=entity_type,
            documents_uploaded=documents_uploaded,
            required_documents=required_documents,
            missing_document=missing_document,
            issues_found=issues_found,
            requirements_analysis=requirements_analysis,
            compliance_score=compliance_score,
            compliance_status=compliance_status,
            suggestions=suggestions,
            regulatory_context=regulatory_context,
            citations=citations
        )
    
    def _get_most_critical_missing_document(self, missing_requirements: List[Dict[str, Any]]) -> Optional[str]:
        """Get the most critical missing document"""
        if not missing_requirements:
            return None
        
        # Prioritize mandatory requirements
        mandatory_missing = [req for req in missing_requirements if req.get("mandatory", True)]
        
        if mandatory_missing:
            # Return the first mandatory missing requirement
            return mandatory_missing[0].get("name", "")
        
        # If no mandatory missing, return the first missing requirement
        return missing_requirements[0].get("name", "")
    
    def _convert_redflags_to_issues(self, redflags: List[Dict[str, Any]], 
                                  documents: List[Dict[str, Any]]) -> List[Issue]:
        """Convert redflags to Issue objects"""
        issues = []
        
        for redflag in redflags:
            # Map document name to actual document
            document_name = redflag.get("document", "Unknown")
            actual_document = self._find_document_by_name(documents, document_name)
            
            issue = Issue(
                document=actual_document.get("filename", document_name) if actual_document else document_name,
                section=redflag.get("section", ""),
                issue=redflag.get("issue", ""),
                severity=redflag.get("severity", "Medium"),
                suggestion=self._generate_suggestion_for_issue(redflag)
            )
            
            issues.append(issue)
        
        return issues
    
    def _find_document_by_name(self, documents: List[Dict[str, Any]], document_name: str) -> Optional[Dict[str, Any]]:
        """Find a document by name (with fuzzy matching)"""
        document_name_lower = document_name.lower()
        
        for doc in documents:
            doc_filename = doc.get("filename", "").lower()
            
            # Exact match
            if doc_filename == document_name_lower:
                return doc
            
            # Partial match
            if document_name_lower in doc_filename or doc_filename in document_name_lower:
                return doc
        
        return None
    
    def _generate_suggestion_for_issue(self, redflag: Dict[str, Any]) -> str:
        """Generate a suggestion for a redflag issue"""
        issue_text = redflag.get("issue", "").lower()
        
        if "jurisdiction" in issue_text:
            return "Update jurisdiction clause to reference ADGM laws and courts."
        
        if "signature" in issue_text:
            return "Ensure all required signatures are present with proper capacity and dates."
        
        if "register" in issue_text:
            return "Prepare and maintain the required register as per ADGM regulations."
        
        if "template" in issue_text:
            return "Complete all template fields and remove placeholder text."
        
        if "share capital" in issue_text:
            return "Remove references to share capital for companies limited by guarantee."
        
        return "Please review and address the identified issue according to ADGM requirements."
    
    def _convert_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[MissingRequirement]:
        """Convert suggestions to MissingRequirement objects"""
        missing_reqs = []
        
        for suggestion in suggestions:
            missing_req = MissingRequirement(
                name=suggestion.get("requirement", ""),
                mandatory=suggestion.get("priority", "") == "High",
                priority=suggestion.get("priority", "Medium"),
                estimated_time=suggestion.get("estimated_time", "1-3 days"),
                sources=suggestion.get("sources", []),
                notes=suggestion.get("notes", "")
            )
            
            missing_reqs.append(missing_req)
        
        return missing_reqs
    
    def _build_regulatory_context(self, context_data: Dict[str, Any]) -> RegulatoryContext:
        """Build regulatory context object"""
        return RegulatoryContext(
            relevant_sources=context_data.get("relevant_sources", []),
            key_regulations=context_data.get("key_regulations", []),
            compliance_deadlines=context_data.get("compliance_deadlines", [])
        )
    
    def _collect_citations(self, redflags: List[Dict[str, Any]], 
                         checklist_result: Dict[str, Any]) -> List[str]:
        """Collect all citations from redflags and checklist results"""
        citations = set()
        
        # Collect from redflags
        for redflag in redflags:
            redflag_citations = redflag.get("citations", [])
            citations.update(redflag_citations)
        
        # Collect from checklist results
        regulatory_context = checklist_result.get("regulatory_context", {})
        relevant_sources = regulatory_context.get("relevant_sources", [])
        
        for source in relevant_sources:
            url = source.get("url", "")
            if url:
                citations.add(url)
        
        return list(citations)
    
    def save_report(self, report: AnalysisReport, output_path: str) -> str:
        """Save the report to a JSON file"""
        try:
            # Convert to dict for JSON serialization
            report_dict = report.model_dump()
            
            # Ensure output directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as file:
                json.dump(report_dict, file, indent=2, ensure_ascii=False)
            
            logger.info(f"Report saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            raise
    
    def generate_summary_report(self, report: AnalysisReport) -> Dict[str, Any]:
        """Generate a summary version of the report"""
        return {
            "process": report.process,
            "entity_type": report.entity_type,
            "compliance_status": report.compliance_status,
            "compliance_score": report.compliance_score,
            "total_issues": len(report.issues_found),
            "critical_issues": len([i for i in report.issues_found if i.severity == "High"]),
            "missing_requirements": len(report.suggestions),
            "key_missing_document": report.missing_document,
            "analysis_timestamp": report.analysis_timestamp
        }
    
    def validate_report_against_schema(self, report: AnalysisReport) -> bool:
        """Validate that the report matches the expected schema"""
        try:
            # Basic validation using Pydantic
            report.model_validate(report.model_dump())
            
            # Additional schema validation could be added here
            # For now, just check that required fields are present
            
            required_fields = [
                "process", "entity_type", "documents_uploaded", 
                "required_documents", "issues_found", "compliance_score"
            ]
            
            report_dict = report.model_dump()
            for field in required_fields:
                if field not in report_dict:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Report validation failed: {e}")
            return False
    
    def create_report_filename(self, process: str, entity_type: str, timestamp: Optional[str] = None) -> str:
        """Create a standardized filename for the report"""
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean process and entity type for filename
        clean_process = process.replace(" ", "_").replace("/", "_").lower()
        clean_entity = entity_type.replace(" ", "_").replace("/", "_").lower()
        
        return f"adgm_analysis_{clean_process}_{clean_entity}_{timestamp}.json"
