import os
import re
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path

from .utils import setup_logging, load_yaml_config, safe_get
from .retrieval import DocumentRetriever

logger = setup_logging()

class ChecklistProcessor:
    def __init__(self, rules_path: str = "rules", config_path: str = "config/settings.yml"):
        self.rules_path = rules_path
        self.config = load_yaml_config(config_path)
        self.retriever = DocumentRetriever()
        
        # Load checklists
        self.checklists = self._load_checklists()
    
    def _load_checklists(self) -> Dict[str, Any]:
        """Load all checklist YAML files"""
        checklists = {}
        checklists_dir = Path(self.rules_path) / "checklists"
        
        logger.info(f"Loading checklists from: {checklists_dir}")
        
        if checklists_dir.exists():
            for yaml_file in checklists_dir.glob("*.yml"):
                if yaml_file.name != "redflags":  # Skip redflags directory
                    try:
                        logger.info(f"Loading checklist: {yaml_file}")
                        checklist = load_yaml_config(str(yaml_file))
                        process_name = checklist.get("process", yaml_file.stem)
                        checklists[process_name] = checklist
                        logger.info(f"Loaded checklist: {process_name} -> {checklist.get('entity_type', 'N/A')}")
                    except Exception as e:
                        logger.error(f"Error loading checklist {yaml_file}: {e}")
        else:
            logger.error(f"Checklists directory does not exist: {checklists_dir}")
        
        logger.info(f"Total checklists loaded: {len(checklists)}")
        return checklists
    
    def get_applicable_checklist(self, process: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """Get the applicable checklist for the detected process and entity type"""
        logger.info(f"Looking for checklist: process='{process}', entity_type='{entity_type}'")
        logger.info(f"Available checklists: {list(self.checklists.keys())}")
        
        # First try exact match
        if process in self.checklists:
            checklist = self.checklists[process]
            logger.info(f"Found exact process match: {process}")
            if self._checklist_applies(checklist, entity_type):
                logger.info(f"Checklist applies to entity type: {entity_type}")
                return checklist
            else:
                logger.warning(f"Checklist found but doesn't apply to entity type: {entity_type}")
        
        # Try partial matches
        for checklist_name, checklist in self.checklists.items():
            if (process.lower() in checklist_name.lower() or 
                checklist_name.lower() in process.lower()):
                logger.info(f"Found partial process match: {checklist_name}")
                if self._checklist_applies(checklist, entity_type):
                    logger.info(f"Checklist applies to entity type: {entity_type}")
                    return checklist
        
        # Try matching by checklist process field
        for checklist_name, checklist in self.checklists.items():
            checklist_process = checklist.get("process", "")
            if checklist_process and process.lower() == checklist_process.lower():
                logger.info(f"Found checklist by process field: {checklist_process}")
                if self._checklist_applies(checklist, entity_type):
                    logger.info(f"Checklist applies to entity type: {entity_type}")
                    return checklist
        
        logger.warning(f"No applicable checklist found for process: {process}, entity_type: {entity_type}")
        return None
    
    def _checklist_applies(self, checklist: Dict[str, Any], entity_type: str) -> bool:
        """Check if a checklist applies to the given entity type"""
        checklist_entity_type = checklist.get("entity_type", "")
        
        if not checklist_entity_type:
            return True  # No entity type restriction
        
        # Check for exact match or partial match
        return (entity_type == checklist_entity_type or 
                entity_type.lower() in checklist_entity_type.lower() or
                checklist_entity_type.lower() in entity_type.lower())
    
    def check_requirements(self, documents: List[Dict[str, Any]], 
                          checklist: Dict[str, Any]) -> Dict[str, Any]:
        """Check uploaded documents against checklist requirements"""
        requirements = checklist.get("requirements", [])
        results = {
            "total_requirements": len(requirements),
            "found_requirements": [],
            "missing_requirements": [],
            "compliance_score": 0.0
        }
        
        # Get all document names and content
        doc_names = [doc.get('filename', '').lower() for doc in documents]
        doc_contents = [doc.get('full_text', '').lower() for doc in documents]
        combined_content = " ".join(doc_contents)
        
        for requirement in requirements:
            req_name = requirement.get("name", "")
            req_mandatory = requirement.get("mandatory", True)
            req_applies_if = requirement.get("applies_if", "always")
            
            # Check if requirement applies
            if not self._requirement_applies(req_applies_if, documents):
                continue
            
            # Check if requirement is found
            found = self._check_requirement_presence(
                req_name, doc_names, doc_contents, combined_content
            )
            
            if found:
                results["found_requirements"].append({
                    "name": req_name,
                    "mandatory": req_mandatory,
                    "found_in": found.get("found_in", []),
                    "confidence": found.get("confidence", 0.0)
                })
            else:
                results["missing_requirements"].append({
                    "name": req_name,
                    "mandatory": req_mandatory,
                    "sources": requirement.get("sources", [])
                })
        
        # Calculate compliance score
        mandatory_requirements = [r for r in requirements if r.get("mandatory", True)]
        mandatory_found = len([r for r in results["found_requirements"] if r["mandatory"]])
        mandatory_missing = len([r for r in results["missing_requirements"] if r["mandatory"]])
        
        if mandatory_requirements:
            results["compliance_score"] = mandatory_found / len(mandatory_requirements)
        
        return results
    
    def _requirement_applies(self, applies_if: str, documents: List[Dict[str, Any]]) -> bool:
        """Check if a requirement applies based on conditions"""
        if applies_if == "always":
            return True
        
        # Add more condition logic as needed
        # For now, just return True for all conditions
        return True
    
    def _check_requirement_presence(self, req_name: str, doc_names: List[str], 
                                  doc_contents: List[str], combined_content: str) -> Optional[Dict[str, Any]]:
        """Check if a requirement is present in the documents"""
        req_lower = req_name.lower()
        
        # Check document names first
        found_in_names = []
        for i, doc_name in enumerate(doc_names):
            if req_lower in doc_name or any(word in doc_name for word in req_lower.split()):
                found_in_names.append(doc_names[i])
        
        # Check document contents
        found_in_content = []
        for i, content in enumerate(doc_contents):
            if req_lower in content:
                found_in_content.append(f"Document {i+1}")
        
        # Check combined content for broader patterns
        content_patterns = self._get_requirement_patterns(req_name)
        pattern_matches = []
        
        for pattern in content_patterns:
            if re.search(pattern, combined_content, re.IGNORECASE):
                pattern_matches.append(pattern)
        
        # Determine confidence and found status
        confidence = 0.0
        found_in = []
        
        if found_in_names:
            confidence += 0.6
            found_in.extend(found_in_names)
        
        if found_in_content:
            confidence += 0.3
            found_in.extend(found_in_content)
        
        if pattern_matches:
            confidence += 0.1
            found_in.append(f"Pattern matches: {', '.join(pattern_matches)}")
        
        if confidence > 0.0:
            return {
                "found_in": found_in,
                "confidence": min(confidence, 1.0)
            }
        
        return None
    
    def _get_requirement_patterns(self, req_name: str) -> List[str]:
        """Get regex patterns for detecting requirement presence"""
        patterns = []
        
        # Common patterns for different requirement types
        if "articles" in req_name.lower():
            patterns.extend([
                r"articles of association",
                r"memorandum of association",
                r"constitution"
            ])
        
        if "register" in req_name.lower():
            patterns.extend([
                r"register of members",
                r"register of directors",
                r"share register",
                r"member register"
            ])
        
        if "declaration" in req_name.lower():
            patterns.extend([
                r"ubo declaration",
                r"ultimate beneficial owner",
                r"beneficial ownership"
            ])
        
        if "application" in req_name.lower():
            patterns.extend([
                r"incorporation application",
                r"application form",
                r"registration application"
            ])
        
        if "reservation" in req_name.lower():
            patterns.extend([
                r"name reservation",
                r"reserved name",
                r"company name"
            ])
        
        # Add the requirement name itself as a pattern
        patterns.append(re.escape(req_name))
        
        return patterns
    
    def generate_gap_report(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive gap report"""
        documents = analysis_result.get("documents", [])
        process = analysis_result.get("process", "")
        entity_type = analysis_result.get("entity_type", "")
        
        # Get applicable checklist
        checklist = self.get_applicable_checklist(process, entity_type)
        
        if not checklist:
            return {
                "error": f"No applicable checklist found for process: {process}, entity_type: {entity_type}",
                "available_checklists": list(self.checklists.keys())
            }
        
        # Check requirements
        requirement_results = self.check_requirements(documents, checklist)
        
        # Generate suggestions for missing requirements
        suggestions = self._generate_suggestions(requirement_results, checklist)
        
        # Get relevant regulatory context
        regulatory_context = self._get_regulatory_context(process, entity_type)
        
        return {
            "process": process,
            "entity_type": entity_type,
            "checklist_used": checklist.get("process", ""),
            "documents_uploaded": len(documents),
            "requirement_analysis": requirement_results,
            "suggestions": suggestions,
            "regulatory_context": regulatory_context,
            "compliance_status": self._get_compliance_status(requirement_results)
        }
    
    def _generate_suggestions(self, requirement_results: Dict[str, Any], 
                            checklist: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions for missing requirements"""
        suggestions = []
        
        for missing_req in requirement_results.get("missing_requirements", []):
            req_name = missing_req["name"]
            sources = missing_req.get("sources", [])
            
            suggestion = {
                "requirement": req_name,
                "action": f"Obtain or prepare {req_name}",
                "priority": "High" if missing_req["mandatory"] else "Medium",
                "sources": sources,
                "estimated_time": self._estimate_completion_time(req_name),
                "notes": self._get_requirement_notes(req_name)
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _estimate_completion_time(self, req_name: str) -> str:
        """Estimate completion time for a requirement"""
        time_estimates = {
            "articles of association": "1-2 days",
            "register of members": "1 day",
            "register of directors": "1 day",
            "ubo declaration": "2-3 days",
            "incorporation application": "1 day",
            "name reservation": "1 day"
        }
        
        req_lower = req_name.lower()
        for key, time_est in time_estimates.items():
            if key in req_lower:
                return time_est
        
        return "1-3 days"
    
    def _get_requirement_notes(self, req_name: str) -> str:
        """Get helpful notes for a requirement"""
        notes = {
            "articles of association": "Must comply with ADGM Companies Regulations 2020",
            "register of members": "Must be maintained and updated within 14 days of changes",
            "register of directors": "Must include residential address and date of birth",
            "ubo declaration": "Must identify ultimate beneficial owners with 25%+ ownership",
            "incorporation application": "Must be signed by all proposed directors",
            "name reservation": "Name must be available and comply with naming conventions"
        }
        
        req_lower = req_name.lower()
        for key, note in notes.items():
            if key in req_lower:
                return note
        
        return "Please refer to ADGM guidance for specific requirements."
    
    def _get_regulatory_context(self, process: str, entity_type: str) -> Dict[str, Any]:
        """Get relevant regulatory context for the process and entity type"""
        # Search for relevant regulatory documents
        query = f"{process} {entity_type} ADGM requirements"
        relevant_docs = self.retriever.retrieve_and_rerank(query)
        
        context = {
            "relevant_sources": [],
            "key_regulations": [],
            "compliance_deadlines": []
        }
        
        for doc in relevant_docs[:3]:  # Top 3 most relevant
            metadata = doc.get('metadata', {})
            context["relevant_sources"].append({
                "title": metadata.get('title', 'Unknown'),
                "url": metadata.get('source_url', ''),
                "relevance_score": doc.get('similarity_score', 0)
            })
        
        return context
    
    def _get_compliance_status(self, requirement_results: Dict[str, Any]) -> str:
        """Determine overall compliance status"""
        compliance_score = requirement_results.get("compliance_score", 0.0)
        
        if compliance_score >= 0.9:
            return "Compliant"
        elif compliance_score >= 0.7:
            return "Mostly Compliant"
        elif compliance_score >= 0.5:
            return "Partially Compliant"
        else:
            return "Non-Compliant"
