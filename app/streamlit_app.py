import streamlit as st
import os
import tempfile
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

# Add the project root to the path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.analyzer import DocumentAnalyzer
from core.checklist import ChecklistProcessor
from core.commenting import DocumentCommenter
from core.report import ReportBuilder
from core.ingest import DocumentIngester
from core.utils import setup_logging, is_docx_file

# Setup logging
logger = setup_logging()

# Page configuration
st.set_page_config(
    page_title="ADGM Corporate Agent",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
         .issue-card {
         background-color: #fff8e1;
         padding: 1rem;
         border-radius: 0.5rem;
         border-left: 4px solid #ff9800;
         margin-bottom: 1rem;
         color: #2c3e50;
         font-weight: 500;
         box-shadow: 0 2px 4px rgba(255, 152, 0, 0.1);
     }
    .success-card {
        background-color: #d1ecf1;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #17a2b8;
        margin-bottom: 1rem;
    }
    .error-card {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Sidebar
    with st.sidebar:
        st.title("🏢 ADGM Corporate Agent")
        st.markdown("---")
        
        # Navigation
        page = st.selectbox(
            "Navigation",
            ["Document Analysis", "Database Management", "Settings", "About"]
        )
        
        st.markdown("---")
        
        # Status indicators
        st.subheader("System Status")
        
        # Check if ChromaDB exists
        chroma_exists = Path("chroma_db").exists()
        if chroma_exists:
            st.success("✅ Document Database Ready")
        else:
            st.warning("⚠️ Database Not Found")
            if st.button("Initialize Database"):
                with st.spinner("Initializing database..."):
                    try:
                        ingester = DocumentIngester()
                        ingester.refresh()
                        st.success("Database initialized successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error initializing database: {e}")
    
    # Main content based on selected page
    if page == "Document Analysis":
        document_analysis_page()
    elif page == "Database Management":
        database_management_page()
    elif page == "Settings":
        settings_page()
    elif page == "About":
        about_page()

def document_analysis_page():
    """Document analysis main page"""
    
    # Header
    st.markdown('<h1 class="main-header">ADGM Corporate Agent</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">AI-Powered Corporate Document Analysis & Compliance Checking</p>', unsafe_allow_html=True)
    
    # File upload section
    st.markdown('<h2 class="sub-header">📄 Upload Documents</h2>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Upload your corporate documents (.docx files)",
        type=['docx'],
        accept_multiple_files=True,
        help="Upload one or more .docx files for analysis"
    )
    
    if uploaded_files:
        st.success(f"✅ Uploaded {len(uploaded_files)} document(s)")
        
        # Display uploaded files
        with st.expander("📋 Uploaded Documents", expanded=False):
            for i, file in enumerate(uploaded_files, 1):
                st.write(f"{i}. {file.name} ({file.size} bytes)")
        
        # Analysis button
        if st.button("🔍 Analyze Documents", type="primary", use_container_width=True):
            analyze_documents(uploaded_files)

def analyze_documents(uploaded_files):
    """Analyze uploaded documents"""
    
    with st.spinner("Analyzing documents..."):
        try:
            # Save uploaded files to temporary directory
            temp_dir = tempfile.mkdtemp()
            file_paths = []
            
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_paths.append(file_path)
            
            # Initialize components
            analyzer = DocumentAnalyzer()
            checklist_processor = ChecklistProcessor()
            commenter = DocumentCommenter()
            report_builder = ReportBuilder()
            
            # Step 1: Document Analysis
            st.markdown('<h3 class="sub-header">📊 Analysis Results</h3>', unsafe_allow_html=True)
            
            analysis_result = analyzer.analyze_documents(file_paths)
            
            # Display basic analysis results
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Process Detected", analysis_result["process"])
            
            with col2:
                st.metric("Entity Type", analysis_result["entity_type"])
            
            with col3:
                st.metric("Documents Analyzed", analysis_result["document_count"])
            
            # Step 2: Checklist Analysis
            st.markdown('<h3 class="sub-header">✅ Checklist Verification</h3>', unsafe_allow_html=True)
            
            checklist_result = checklist_processor.generate_gap_report(analysis_result)
            
            if "error" in checklist_result:
                st.error(checklist_result["error"])
                return
            
            # Display compliance metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                compliance_score = checklist_result.get("requirement_analysis", {}).get("compliance_score", 0)
                st.metric("Compliance Score", f"{compliance_score:.1%}")
            
            with col2:
                total_reqs = checklist_result.get("requirement_analysis", {}).get("total_requirements", 0)
                st.metric("Total Requirements", total_reqs)
            
            with col3:
                found_reqs = len(checklist_result.get("requirement_analysis", {}).get("found_requirements", []))
                st.metric("Found Requirements", found_reqs)
            
            with col4:
                missing_reqs = len(checklist_result.get("requirement_analysis", {}).get("missing_requirements", []))
                st.metric("Missing Requirements", missing_reqs)
            
            # Step 3: Red Flag Analysis
            st.markdown('<h3 class="sub-header">🚨 Red Flag Analysis</h3>', unsafe_allow_html=True)
            
            redflags = analysis_result.get("redflags", [])
            
            if redflags:
                # Group by severity
                high_issues = [rf for rf in redflags if rf.get("severity") == "High"]
                medium_issues = [rf for rf in redflags if rf.get("severity") == "Medium"]
                low_issues = [rf for rf in redflags if rf.get("severity") == "Low"]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("High Severity", len(high_issues), delta=None)
                
                with col2:
                    st.metric("Medium Severity", len(medium_issues), delta=None)
                
                with col3:
                    st.metric("Low Severity", len(low_issues), delta=None)
                
                # Display issues
                display_redflags(redflags)
            else:
                st.success("✅ No red flags detected!")
            
            # Step 4: Generate Report
            st.markdown('<h3 class="sub-header">📋 Analysis Report</h3>', unsafe_allow_html=True)
            
            # Build comprehensive report
            try:
                report = report_builder.build_report(analysis_result, checklist_result, redflags)
            except Exception as e:
                st.error(f"❌ Error building report: {str(e)}")
                import traceback
                st.error(f"Full error: {traceback.format_exc()}")
                return
            
            # Display JSON format report
            display_json_report(report, checklist_result)
            
        except Exception as e:
            st.error(f"❌ Analysis failed: {str(e)}")
            logger.error(f"Analysis error: {e}")

def display_redflags(redflags: List[Dict[str, Any]]):
    """Display red flags in an organized way"""
    
    # Create tabs for different severities
    tab1, tab2, tab3 = st.tabs(["🚨 High", "⚠️ Medium", "ℹ️ Low"])
    
    with tab1:
        high_issues = [rf for rf in redflags if rf.get("severity") == "High"]
        if high_issues:
            for issue in high_issues:
                with st.container():
                    st.markdown(f"""
                    <div class="error-card">
                        <strong>Document:</strong> {issue.get('document', 'Unknown')}<br>
                        <strong>Issue:</strong> {issue.get('issue', '')}<br>
                        <strong>Section:</strong> {issue.get('section', 'N/A')}<br>
                        <strong>Citations:</strong> {', '.join(issue.get('citations', []))}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.success("No high severity issues found!")
    
    with tab2:
        medium_issues = [rf for rf in redflags if rf.get("severity") == "Medium"]
        if medium_issues:
            for issue in medium_issues:
                with st.container():
                    st.markdown(f"""
                    <div class="issue-card">
                        <strong>Document:</strong> {issue.get('document', 'Unknown')}<br>
                        <strong>Issue:</strong> {issue.get('issue', '')}<br>
                        <strong>Section:</strong> {issue.get('section', 'N/A')}<br>
                        <strong>Citations:</strong> {', '.join(issue.get('citations', []))}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.success("No medium severity issues found!")
    
    with tab3:
        low_issues = [rf for rf in redflags if rf.get("severity") == "Low"]
        if low_issues:
            for issue in low_issues:
                with st.container():
                    st.markdown(f"""
                    <div class="success-card">
                        <strong>Document:</strong> {issue.get('document', 'Unknown')}<br>
                        <strong>Issue:</strong> {issue.get('issue', '')}<br>
                        <strong>Section:</strong> {issue.get('section', 'N/A')}<br>
                        <strong>Citations:</strong> {', '.join(issue.get('citations', []))}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.success("No low severity issues found!")

def display_json_report(report, checklist_result):
    """Display report in JSON format"""
    
    # Create the JSON structure as requested
    json_report = {
        "process": getattr(report, 'process', 'Unknown'),
        "documents_uploaded": getattr(report, 'documents_uploaded', 0),
        "required_documents": getattr(report, 'required_documents', 0),
        "missing_document": getattr(report, 'missing_document', None),
        "issues_found": [
            {
                "document": issue.document,
                "section": issue.section,
                "issue": issue.issue,
                "severity": issue.severity,
                "suggestion": issue.suggestion
            }
            for issue in getattr(report, 'issues_found', [])
        ]
    }
    
    # Display the JSON
    st.json(json_report)

def generate_commented_documents(file_paths: List[str], redflags: List[Dict[str, Any]], commenter: DocumentCommenter):
    """Generate commented versions of documents"""
    
    with st.spinner("Generating commented documents..."):
        try:
            commented_files = []
            
            for file_path in file_paths:
                # Filter redflags for this specific document
                doc_name = Path(file_path).name
                doc_redflags = [rf for rf in redflags if rf.get("document", "").lower() in doc_name.lower()]
                
                if doc_redflags:
                    # Generate commented version
                    commented_path = commenter.add_comments_to_document(file_path, doc_redflags)
                    commented_files.append(commented_path)
            
            if commented_files:
                st.success(f"✅ Generated {len(commented_files)} commented document(s)")
                
                # Provide download links
                for commented_file in commented_files:
                    with open(commented_file, "rb") as f:
                        st.download_button(
                            label=f"📄 Download {Path(commented_file).name}",
                            data=f.read(),
                            file_name=Path(commented_file).name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
            else:
                st.info("No issues found to comment on")
                
        except Exception as e:
            st.error(f"❌ Error generating commented documents: {str(e)}")

def export_json_report(report, report_builder: ReportBuilder):
    """Export the full JSON report"""
    
    try:
        # Check if report is valid
        if not report:
            st.error("❌ No report data available")
            return
        
        # Create a simple JSON report without using Pydantic serialization
        simple_report = {
            "process": getattr(report, 'process', 'Unknown'),
            "entity_type": getattr(report, 'entity_type', 'Unknown'),
            "documents_uploaded": getattr(report, 'documents_uploaded', 0),
            "required_documents": getattr(report, 'required_documents', 0),
            "missing_document": getattr(report, 'missing_document', None),
            "compliance_score": getattr(report, 'compliance_score', 0.0),
            "compliance_status": getattr(report, 'compliance_status', 'Unknown'),
            "analysis_timestamp": getattr(report, 'analysis_timestamp', datetime.now().isoformat()),
            "issues_found": [
                {
                    "document": issue.document,
                    "section": issue.section,
                    "issue": issue.issue,
                    "severity": issue.severity,
                    "suggestion": issue.suggestion
                }
                for issue in getattr(report, 'issues_found', [])
            ],
            "suggestions": [
                {
                    "requirement": suggestion.name,
                    "mandatory": suggestion.mandatory,
                    "priority": suggestion.priority,
                    "estimated_time": suggestion.estimated_time,
                    "sources": suggestion.sources,
                    "notes": suggestion.notes
                }
                for suggestion in getattr(report, 'suggestions', [])
            ],
            "regulatory_context": {
                "relevant_sources": getattr(report.regulatory_context, 'relevant_sources', []),
                "key_regulations": getattr(report.regulatory_context, 'key_regulations', []),
                "compliance_deadlines": getattr(report.regulatory_context, 'compliance_deadlines', [])
            },
            "citations": getattr(report, 'citations', [])
        }
        
        # Create filename
        filename = f"adgm_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert to JSON
        report_json = json.dumps(simple_report, indent=2, ensure_ascii=False)
        
        # Save to file
        output_path = f"reports/{filename}"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_json)
        
        # Provide download
        st.download_button(
            label="📄 Download Full JSON Report",
            data=report_json,
            file_name=filename,
            mime="application/json"
        )
        
        st.success("✅ Report exported successfully!")
        
    except Exception as e:
        st.error(f"❌ Error exporting report: {str(e)}")
        import traceback
        st.error(f"Full error: {traceback.format_exc()}")

def export_summary_report(report, report_builder: ReportBuilder):
    """Export a summary report"""
    
    try:
        # Check if report is valid
        if not report:
            st.error("❌ No report data available")
            return
            
        # Create a simple summary without using Pydantic serialization
        summary = {
            "process": getattr(report, 'process', 'Unknown'),
            "entity_type": getattr(report, 'entity_type', 'Unknown'),
            "compliance_status": getattr(report, 'compliance_status', 'Unknown'),
            "compliance_score": getattr(report, 'compliance_score', 0.0),
            "total_issues": len(getattr(report, 'issues_found', [])),
            "critical_issues": len([i for i in getattr(report, 'issues_found', []) if getattr(i, 'severity', 'Medium') == "High"]),
            "missing_requirements": len(getattr(report, 'suggestions', [])),
            "key_missing_document": getattr(report, 'missing_document', None),
            "analysis_timestamp": getattr(report, 'analysis_timestamp', datetime.now().isoformat())
        }
        
        # Convert to JSON
        summary_json = json.dumps(summary, indent=2, ensure_ascii=False)
        
        # Create filename
        filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        st.download_button(
            label="📊 Download Summary Report",
            data=summary_json,
            file_name=filename,
            mime="application/json"
        )
        
        st.success("✅ Summary exported successfully!")
        
    except Exception as e:
        st.error(f"❌ Error exporting summary: {str(e)}")
        import traceback
        st.error(f"Full error: {traceback.format_exc()}")

def database_management_page():
    """Database management page"""
    
    st.title("🗄️ Database Management")
    
    st.markdown("---")
    
    # Database status
    st.subheader("Database Status")
    
    chroma_exists = Path("chroma_db").exists()
    if chroma_exists:
        st.success("✅ Document database is ready")
        
        # Show database info
        try:
            from core.retrieval import DocumentRetriever
            retriever = DocumentRetriever()
            stats = retriever.get_collection_stats()
            
            if "error" not in stats:
                st.metric("Total Documents", stats.get("total_documents", 0))
                
                # Show tag distribution
                tag_dist = stats.get("tag_distribution", {})
                if tag_dist:
                    st.write("**Document Categories:**")
                    for tag, count in tag_dist.items():
                        st.write(f"• {tag}: {count} documents")
            else:
                st.warning("Could not retrieve database statistics")
        except Exception as e:
            st.error(f"Error accessing database: {e}")
    else:
        st.warning("⚠️ Document database not found")
    
    st.markdown("---")
    
    # Database operations
    st.subheader("Database Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Database", use_container_width=True):
            with st.spinner("Refreshing database..."):
                try:
                    ingester = DocumentIngester()
                    ingester.refresh()
                    st.success("✅ Database refreshed successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error refreshing database: {e}")
    
    with col2:
        if st.button("🗑️ Clear Database", use_container_width=True):
            if st.checkbox("I understand this will delete all documents"):
                with st.spinner("Clearing database..."):
                    try:
                        import shutil
                        if Path("chroma_db").exists():
                            shutil.rmtree("chroma_db")
                        st.success("✅ Database cleared successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error clearing database: {e}")

def settings_page():
    """Settings page"""
    
    st.title("⚙️ Settings")
    
    st.markdown("---")
    
    # Configuration display
    st.subheader("Current Configuration")
    
    try:
        from core.utils import load_yaml_config
        config = load_yaml_config("config/settings.yml")
        
        st.json(config)
        
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
    
    st.markdown("---")
    
    # Environment variables
    st.subheader("Environment Variables")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        st.success("✅ OpenAI API key configured")
    else:
        st.warning("⚠️ OpenAI API key not found")
        st.info("Set OPENAI_API_KEY environment variable to use OpenAI models")

def about_page():
    """About page"""
    
    st.title("ℹ️ About ADGM Corporate Agent")
    
    st.markdown("---")
    
    st.markdown("""
    ## Overview
    
    The ADGM Corporate Agent is an AI-powered tool designed to help corporate service providers 
    and legal professionals ensure compliance with ADGM (Abu Dhabi Global Market) regulations.
    
    ## Features
    
    - **Document Analysis**: Automatically analyze corporate documents for compliance issues
    - **Process Detection**: Identify the type of corporate process from uploaded documents
    - **Checklist Verification**: Compare documents against ADGM requirements checklists
    - **Red Flag Detection**: Identify potential compliance issues and regulatory violations
    - **Document Comments**: Generate annotated versions of documents with highlighted issues
    - **Comprehensive Reporting**: Generate detailed compliance reports with citations
    
    ## Technology Stack
    
    - **Backend**: Python 3.11, Streamlit
    - **AI/ML**: OpenAI GPT-4, Sentence Transformers, BGE Reranker
    - **Vector Database**: ChromaDB
    - **Document Processing**: python-docx, BeautifulSoup, PyPDF2
    
    ## Regulatory Coverage
    
    The system covers various ADGM processes including:
    - Company Incorporation
    - Employment Contracts
    - Post-Registration Changes
    - Annual Filings
    - And more...
    
    ## Support
    
    For technical support or questions about ADGM compliance, please refer to the 
    official ADGM documentation or contact your legal advisor.
    """)

if __name__ == "__main__":
    main()
