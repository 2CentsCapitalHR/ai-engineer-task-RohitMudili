# ADGM Corporate Agent

An AI-powered corporate document analysis and compliance checking tool for ADGM (Abu Dhabi Global Market) regulations.

## 🏢 Overview

The ADGM Corporate Agent is designed to help corporate service providers and legal professionals ensure compliance with ADGM regulations. It automatically analyzes corporate documents, detects compliance issues, and generates comprehensive reports with citations to regulatory sources.

## ✨ Features

- **Document Analysis**: Automatically analyze corporate documents for compliance issues
- **Process Detection**: Identify the type of corporate process from uploaded documents
- **Checklist Verification**: Compare documents against ADGM requirements checklists
- **Red Flag Detection**: Identify potential compliance issues and regulatory violations
- **Document Comments**: Generate annotated versions of documents with highlighted issues
- **Comprehensive Reporting**: Generate detailed compliance reports with citations
- **RAG-powered**: Uses ChromaDB and advanced embeddings for regulatory knowledge retrieval

## 🛠️ Technology Stack

- **Backend**: Python 3.11, Streamlit
- **AI/ML**: OpenAI GPT-4, Sentence Transformers, BGE Reranker
- **Vector Database**: ChromaDB
- **Document Processing**: python-docx, BeautifulSoup, PyPDF2
- **Data Validation**: Pydantic

## 📋 Prerequisites

- Python 3.11 or higher
- OpenAI API key (for advanced LLM features)
- Internet connection (for fetching regulatory documents)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd 2cents
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your OpenAI API key
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## 🏃‍♂️ Quick Start

1. **Initialize the document database**
   ```bash
   python -m core.ingest refresh
   ```

2. **Launch the Streamlit application**
   ```bash
   streamlit run app/streamlit_app.py
   ```

3. **Open your browser** and navigate to `http://localhost:8501`

## 📖 Usage Guide

### Document Analysis

1. **Upload Documents**: Use the file uploader to select one or more .docx files
2. **Analyze**: Click "Analyze Documents" to start the analysis
3. **Review Results**: View the analysis results in organized tabs:
   - **Analysis Results**: Basic process and entity type detection
   - **Checklist Verification**: Compliance requirements analysis
   - **Red Flag Analysis**: Issues found with severity levels
   - **Detailed Report**: Comprehensive analysis with regulatory context

### Database Management

- **Refresh Database**: Update the regulatory document database
- **View Statistics**: See document counts and categories
- **Clear Database**: Remove all documents (use with caution)

### Export Results

- **JSON Report**: Download the full analysis report in JSON format
- **Summary Report**: Download a condensed summary
- **Commented Documents**: Generate annotated versions of your documents

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python -m pytest tests/

# Run specific test files
python -m pytest tests/test_detection.py
python -m pytest tests/test_checklist.py
python -m pytest tests/test_redflags.py

# Run with coverage
python -m pytest tests/ --cov=core --cov-report=html
```

## 📁 Project Structure

```
2cents/
├── app/
│   └── streamlit_app.py          # Main Streamlit UI
├── core/
│   ├── ingest.py                 # Document ingestion and ChromaDB setup
│   ├── retrieval.py              # RAG query and retrieval
│   ├── analyzer.py               # Document parsing and analysis
│   ├── checklist.py              # Checklist processing
│   ├── commenting.py             # Document annotation
│   ├── report.py                 # Report generation
│   └── utils.py                  # Utility functions
├── config/
│   └── settings.yml              # Configuration settings
├── docs/
│   ├── PROJECT_BRIEF.md          # Project overview
│   ├── ACCEPTANCE_CRITERIA.md    # Acceptance criteria
│   └── output_schema.json        # JSON output schema
├── examples/
│   └── input/                    # Example documents
├── ingest/
│   └── sources.yml               # Regulatory document sources
├── rules/
│   ├── checklists/               # Process-specific checklists
│   │   ├── incorporation_private_ltd_non_financial.yml
│   │   └── redflags/             # Red flag rules
│   │       └── base.yml
├── tests/                        # Unit tests
│   ├── test_detection.py
│   ├── test_checklist.py
│   └── test_redflags.py
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## ⚙️ Configuration

### Settings (`config/settings.yml`)

```yaml
rag:
  top_k: 8                    # Number of documents to retrieve
  rerank_k: 6                 # Number of documents to rerank
  min_score: 0.35             # Minimum similarity score

commenting:
  mode: "inline"              # Commenting mode (inline/aspose)

output:
  json_schema_path: "docs/output_schema.json"
```

### Sources (`ingest/sources.yml`)

Configure regulatory document sources:

```yaml
sources:
  - url: "https://www.adgm.com/registration-authority/registration-and-incorporation"
    type: html
    tags: ["incorporation", "ra", "guidance"]

options:
  chunk_size: 1000
  chunk_overlap: 120
  download_pdfs: true
  normalize_html: true
```

## 🔧 CLI Commands

### Document Ingestion

```bash
# Refresh the document database
python -m core.ingest refresh

# Refresh with custom sources
python -m core.ingest refresh --sources custom_sources.yml

# Refresh with custom ChromaDB path
python -m core.ingest refresh --chroma-path custom_chroma_db
```

## 📊 Output Schema

The system generates JSON reports matching the schema in `docs/output_schema.json`:

```json
{
  "process": "Company Incorporation",
  "entity_type": "Private Company Limited by Shares (Non-Financial)",
  "documents_uploaded": 4,
  "required_documents": 5,
  "missing_document": "Register of Members and Directors",
  "issues_found": [
    {
      "document": "Articles of Association",
      "section": "Clause 3.1",
      "issue": "Jurisdiction clause does not specify ADGM",
      "severity": "High",
      "suggestion": "Update jurisdiction to ADGM Courts."
    }
  ],
  "compliance_score": 0.8,
  "compliance_status": "Mostly Compliant"
}
```

## 🚨 Red Flag Detection

The system detects various compliance issues:

- **High Severity**:
  - Jurisdiction mismatches (non-ADGM courts)
  - Missing mandatory registers
  - Share capital in guarantee companies

- **Medium Severity**:
  - Missing signatures or execution formalities
  - Incomplete structural elements

- **Low Severity**:
  - Template placeholders
  - Lorem ipsum text

## 📋 Supported Processes

- **Company Incorporation**: Private companies, branches, guarantee companies
- **Employment**: Employment contracts, ER 2024 compliance
- **Post Registration**: Articles amendments, shareholder resolutions
- **Annual Filings**: Annual accounts, returns, statements

## 🔍 Regulatory Coverage

The system covers ADGM regulations including:

- Companies Regulations 2020
- Employment Regulations 2024
- Registration Authority guidance
- Policy statements and circulars
- Rulebook provisions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For technical support or questions about ADGM compliance:

- **Technical Issues**: Create an issue in the repository
- **ADGM Compliance**: Refer to official ADGM documentation or contact your legal advisor
- **Documentation**: Check the `docs/` directory for detailed specifications

## 🔄 Updates

To update the system:

1. Pull the latest changes: `git pull origin main`
2. Update dependencies: `pip install -r requirements.txt --upgrade`
3. Refresh the database: `python -m core.ingest refresh`
4. Restart the application: `streamlit run app/streamlit_app.py`

## 📈 Performance

- **Document Processing**: ~2-5 seconds per document
- **Analysis Pipeline**: ~10-30 seconds for typical incorporation package
- **Database Size**: ~50-100MB for full regulatory corpus
- **Memory Usage**: ~1-2GB RAM during analysis

## 🔒 Security

- No document content is stored permanently
- All processing is done locally (except OpenAI API calls)
- Temporary files are cleaned up automatically
- API keys are stored in environment variables

## 🎯 Roadmap

- [ ] Support for PDF documents
- [ ] Integration with Aspose for advanced commenting
- [ ] Multi-language support (Arabic)
- [ ] Real-time regulatory updates
- [ ] API endpoints for integration
- [ ] Mobile application
- [ ] Advanced AI models (Claude, local models)

---

**Disclaimer**: This tool is designed to assist with compliance checking but should not replace professional legal advice. Always consult with qualified legal professionals for critical compliance decisions.
