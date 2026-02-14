"""
Enhanced Document Ingestion Pipeline - Professional RAG Upgrade
Author: GreenValue AI Team (Enhanced by Senior RAG Developer)
Purpose: Table-aware document processing with financial data preservation.
"""

import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Table, Text, Title

from .config import RAGConfig
from .store import GreenValueDocumentStore

logger = logging.getLogger("greenvalue-rag")


class TableAwareChunker:
    """
    Advanced chunker that preserves financial tables and construction data.
    Specifically designed for PropTech documents with ROI calculations.
    """
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.child_chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Financial table patterns for PropTech
        self.financial_patterns = [
            r'cost.*table|table.*cost',
            r'roi.*calculation|return.*investment',
            r'energy.*saving|efficiency.*cost',
            r'renovation.*budget|retrofit.*cost',
            r'payback.*period|break.*even',
            r'u-value|r-value|thermal.*performance',
            r'kwh.*year|energy.*consumption',
            r'carbon.*emission|co2.*reduction'
        ]
    
    def detect_table_content(self, text: str) -> bool:
        """Detect if text contains tabular financial/construction data."""
        # Check for table indicators
        table_indicators = [
            '|',  # Markdown table pipes
            '\t',  # Tab-separated values
            '€', '$', '£',  # Currency symbols
            'kWh', 'W/m²K',  # Energy units
            'ROI', 'NPV', 'IRR',  # Financial metrics
        ]
        
        # Count table-like patterns
        indicator_count = sum(1 for indicator in table_indicators if indicator in text)
        
        # Check for financial patterns
        financial_match = any(
            re.search(pattern, text.lower()) 
            for pattern in self.financial_patterns
        )
        
        # Detect structured data (multiple lines with similar patterns)
        lines = text.split('\n')
        structured_lines = sum(
            1 for line in lines 
            if '|' in line or '\t' in line or any(curr in line for curr in ['€', '$', '£'])
        )
        
        return (
            indicator_count >= 2 or 
            financial_match or 
            structured_lines >= 3
        )
    
    def preserve_table_as_markdown(self, text: str) -> str:
        """Convert detected tables to clean Markdown format."""
        lines = text.split('\n')
        markdown_lines = []
        
        for line in lines:
            # Clean and format table rows
            if '|' in line:
                # Already markdown table - clean it
                cells = [cell.strip() for cell in line.split('|')]
                clean_line = '| ' + ' | '.join(cells) + ' |'
                markdown_lines.append(clean_line)
            elif '\t' in line:
                # Tab-separated - convert to markdown
                cells = [cell.strip() for cell in line.split('\t')]
                markdown_line = '| ' + ' | '.join(cells) + ' |'
                markdown_lines.append(markdown_line)
            else:
                markdown_lines.append(line)
        
        return '\n'.join(markdown_lines)
    
    def chunk_with_table_preservation(self, text: str, metadata: Dict) -> List[Document]:
        """Chunk text while preserving financial tables intact."""
        # Split into logical sections
        sections = re.split(r'\n\s*\n', text)
        chunks = []
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # Check if section contains table data
            if self.detect_table_content(section):
                # Preserve entire table as single chunk
                table_markdown = self.preserve_table_as_markdown(section)
                
                # Add table metadata
                table_metadata = metadata.copy()
                table_metadata.update({
                    'chunk_type': 'table',
                    'contains_financial_data': True,
                    'section_index': i
                })
                
                chunks.append(Document(
                    page_content=table_markdown,
                    metadata=table_metadata
                ))
                
                logger.debug(f"Preserved table chunk: {len(table_markdown)} chars")
            
            else:
                # Regular text chunking
                text_chunks = self.text_splitter.split_text(section)
                
                for j, chunk_text in enumerate(text_chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        'chunk_type': 'text',
                        'section_index': i,
                        'chunk_index': j
                    })
                    
                    chunks.append(Document(
                        page_content=chunk_text,
                        metadata=chunk_metadata
                    ))
        
        return chunks


class EnhancedDocumentIngestionPipeline:
    """
    Professional document ingestion with table-aware processing.
    Optimized for PropTech financial documents and construction data.
    """
    
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        store: Optional[GreenValueDocumentStore] = None
    ):
        self.config = config or RAGConfig()
        self.store = store
        self.chunker = TableAwareChunker(self.config)
        
        # PropTech document categories
        self.proptech_categories = {
            'valuation': ['ivs', 'appraisal', 'valuation', 'market'],
            'energy': ['energy', 'efficiency', 'thermal', 'insulation', 'u-value'],
            'finance': ['roi', 'cost', 'investment', 'budget', 'payback'],
            'retrofit': ['renovation', 'retrofit', 'upgrade', 'improvement'],
            'sustainability': ['green', 'sustainable', 'carbon', 'emission', 'eco'],
            'legal': ['regulation', 'compliance', 'standard', 'code', 'law']
        }
    
    def classify_document_category(self, text: str, filename: str) -> str:
        """Classify document into PropTech categories."""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        category_scores = {}
        
        for category, keywords in self.proptech_categories.items():
            score = 0
            for keyword in keywords:
                score += text_lower.count(keyword) * 2  # Text content weight
                score += filename_lower.count(keyword) * 5  # Filename weight
            
            category_scores[category] = score
        
        # Return category with highest score, default to 'real_estate'
        best_category = max(category_scores, key=category_scores.get)
        return best_category if category_scores[best_category] > 0 else 'real_estate'
    
    def extract_financial_metadata(self, text: str) -> Dict:
        """Extract financial and energy efficiency metadata."""
        metadata = {}
        
        # Currency detection
        currencies = ['€', '$', '£', 'USD', 'EUR', 'GBP']
        found_currencies = [curr for curr in currencies if curr in text]
        if found_currencies:
            metadata['currencies'] = found_currencies
        
        # Energy efficiency indicators
        energy_patterns = {
            'u_values': r'U-value[s]?\s*[:\-]?\s*([\d.,]+)',
            'r_values': r'R-value[s]?\s*[:\-]?\s*([\d.,]+)',
            'energy_consumption': r'([\d.,]+)\s*kWh',
            'co2_emissions': r'([\d.,]+)\s*(?:kg\s*)?CO2'
        }
        
        for key, pattern in energy_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                metadata[key] = matches
        
        # ROI indicators
        roi_patterns = [
            'payback period', 'return on investment', 'roi', 'npv', 'irr'
        ]
        
        found_roi = [pattern for pattern in roi_patterns if pattern in text.lower()]
        if found_roi:
            metadata['contains_roi_analysis'] = True
            metadata['roi_indicators'] = found_roi
        
        return metadata
    
    def process_pdf_with_tables(self, file_path: str) -> Tuple[List[Document], List[Document]]:
        """Process PDF with enhanced table extraction."""
        logger.info(f"📄 Processing PDF: {Path(file_path).name}")
        
        try:
            # Use Unstructured API for table extraction
            elements = partition_pdf(
                filename=file_path,
                strategy="hi_res",
                extract_images_in_pdf=False,
                infer_table_structure=True,
                model_name="yolox"
            )
            
            # Separate tables and text
            tables = [elem for elem in elements if isinstance(elem, Table)]
            texts = [elem for elem in elements if isinstance(elem, (Text, Title))]
            
            logger.info(f"  → Extracted {len(tables)} tables, {len(texts)} text elements")
            
            # Process text elements
            full_text = '\n\n'.join([elem.text for elem in texts])
            
            # Document metadata
            base_metadata = {
                'source_file': Path(file_path).name,
                'file_path': str(file_path),
                'category': self.classify_document_category(full_text, Path(file_path).name),
                'has_tables': len(tables) > 0,
                'table_count': len(tables)
            }
            
            # Add financial metadata
            financial_meta = self.extract_financial_metadata(full_text)
            base_metadata.update(financial_meta)
            
            # Create parent document
            parent_id = str(uuid.uuid4())
            parent_doc = Document(
                page_content=full_text,
                metadata={**base_metadata, 'parent_id': parent_id, 'doc_type': 'parent'}
            )
            
            # Process tables as separate high-priority chunks
            table_chunks = []
            for i, table in enumerate(tables):
                table_metadata = base_metadata.copy()
                table_metadata.update({
                    'parent_id': parent_id,
                    'doc_type': 'child',
                    'chunk_type': 'table',
                    'table_index': i,
                    'contains_financial_data': True,
                    'priority': 'high'  # Tables get priority in retrieval
                })
                
                # Convert table to markdown
                table_markdown = f"## Table {i+1}\n\n{table.text}"
                
                table_chunks.append(Document(
                    page_content=table_markdown,
                    metadata=table_metadata
                ))
            
            # Chunk text content with table awareness
            text_chunks = self.chunker.chunk_with_table_preservation(full_text, {
                **base_metadata,
                'parent_id': parent_id,
                'doc_type': 'child'
            })
            
            # Combine all child chunks
            all_child_chunks = table_chunks + text_chunks
            
            logger.info(f"  ✅ Created {len(all_child_chunks)} child chunks ({len(table_chunks)} tables)")
            
            return [parent_doc], all_child_chunks
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return [], []
    
    def ingest_file(self, file_path: str) -> Dict:
        """Ingest a single file with table-aware processing."""
        if not self.store:
            logger.error("Document store not initialized")
            return {"success": False, "error": "Store not initialized"}
        
        try:
            # Process PDF with table extraction
            parent_docs, child_docs = self.process_pdf_with_tables(file_path)
            
            if not parent_docs or not child_docs:
                return {"success": False, "error": "No content extracted"}
            
            # Store parent documents
            parent_count = self.store.add_documents(
                parent_docs, 
                collection=self.config.parent_collection
            )
            
            # Store child documents
            child_count = self.store.add_documents(
                child_docs,
                collection=self.config.child_collection
            )
            
            result = {
                "success": True,
                "file": Path(file_path).name,
                "parent_docs": parent_count,
                "child_docs": child_count,
                "tables_extracted": sum(1 for doc in child_docs if doc.metadata.get('chunk_type') == 'table'),
                "category": parent_docs[0].metadata.get('category'),
                "contains_financial_data": any(doc.metadata.get('contains_financial_data') for doc in child_docs)
            }
            
            logger.info(f"✅ Ingested: {result}")
            return result
            
        except Exception as e:
            logger.error(f"File ingestion failed: {e}")
            return {"success": False, "error": str(e)}
    
    def ingest_directory(
        self,
        directory: str = "/app/data/books",
        force_recreate: bool = False
    ) -> Dict:
        """Ingest all PDFs in directory with table-aware processing."""
        if not self.store:
            logger.error("Document store not initialized")
            return {"success": False, "error": "Store not initialized"}
        
        # Setup collections
        if not self.store.setup_collections(force_recreate=force_recreate):
            return {"success": False, "error": "Failed to setup collections"}
        
        pdf_files = list(Path(directory).glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {directory}")
            return {"success": False, "error": "No PDF files found"}
        
        logger.info(f"🚀 Processing {len(pdf_files)} PDF files...")
        
        results = []
        total_tables = 0
        
        for pdf_file in pdf_files:
            result = self.ingest_file(str(pdf_file))
            results.append(result)
            
            if result.get("success"):
                total_tables += result.get("tables_extracted", 0)
        
        successful = [r for r in results if r.get("success")]
        
        summary = {
            "success": True,
            "total_files": len(pdf_files),
            "successful": len(successful),
            "failed": len(pdf_files) - len(successful),
            "total_tables_preserved": total_tables,
            "collections": self.store.get_collection_stats(),
            "results": results
        }
        
        logger.info(f"🎯 Ingestion complete: {summary}")
        return summary
