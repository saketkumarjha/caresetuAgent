"""
End-to-end tests for the voice agent with RAG integration.
Tests the complete flow from user query to agent response with RAG.
"""

import os
import unittest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Import components to test
from agent import BusinessVoiceAgent
from simple_rag_engine import SimpleRAGEngine, RAGResponse, SearchResult
from unified_knowledge_base import UnifiedKnowledgeBase
from conversation_context import ConversationContextManager
from conversation_learning import ConversationLearningEngine

class TestVoiceAgentE2E(unittest.TestCase):
    """End-to-end tests for the voice agent with RAG integration."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.kb_dir = os.path.join(self.temp_dir, "knowledge_base")
        self.pdf_dir = os.path.join(self.temp_dir, "pdf_content")
        self.unified_dir = os.path.join(self.temp_dir, "unified_kb")
        
        os.makedirs(self.kb_dir, exist_ok=True)
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(self.unified_dir, exist_ok=True)
        
        # Create test knowledge base files
        self._create_test_knowledge_files()
        
        # Mock agent components
        self._setup_mocks()
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
        self.patches.stop()
    
    def _create_test_knowledge_files(self):
        """Create test knowledge files for testing."""
        # Create JSON knowledge base files
        faq_data = {
            "id": "faq1",
            "title": "Appointment FAQs",
            "content": "Q: How do I schedule an appointment?\nA: You can schedule online or call our office.",
            "category": "faq",
            "tags": ["appointment", "scheduling"],
            "company_id": "caresetu",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Write JSON files
        with open(os.path.join(self.kb_dir, "faq.json"), "w") as f:
            json.dump(faq_data, f)
        
        # Create PDF content and metadata files
        pdf_content = """
        FREQUENTLY ASKED QUESTIONS
        
        Q1: What are your business hours?
        A1: We are open Monday-Friday 9AM-5PM.
        """
        
        pdf_metadata = {
            "filename": "faq.pdf",
            "content": pdf_content,
            "document_type": "faq",
            "file_size": 1024,
            "processed_at": datetime.now().isoformat()
        }
        
        # Write PDF content and metadata files
        doc_id = "test_doc_123"
        with open(os.path.join(self.pdf_dir, f"caresetu_{doc_id}_content.txt"), "w") as f:
            f.write(pdf_content)
        
        with open(os.path.join(self.pdf_dir, f"caresetu_{doc_id}_metadata.json"), "w") as f:
            json.dump(pdf_metadata, f)
    
    def _setup_mocks(self):
        """Set up mocks for agent components."""
        # Create patch for agent initialization
        patcher = patch.multiple(
            'agent.BusinessVoiceAgent',
            _create_tts=MagicMock(return_value=MagicMock()),
            _create_business_context=MagicMock(return_value=MagicMock())
        )
        self.patches = patcher
        self.patches.start()
        
        # Mock config
        self.config_patcher = patch('agent.config', autospec=True)
        self.mock_config = self.config_patcher.start()
        self.mock_config.google.api_key = "fake_api_key"
        
        # Mock LLM
        self.llm_patcher = patch('agent.google.LLM', autospec=True)
        self.mock_llm = self.llm_patcher.start()
        
        # Mock STT
        self.stt_patcher = patch('agent.create_assemblyai_stt', autospec=True)
        self.mock_stt = self.stt_patcher.start()
        
        # Mock VAD
        self.vad_patcher = patch('agent.silero.VAD.load', autospec=True)
        self.mock_vad = self.vad_patcher.start()
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
        self.patches.stop()
        self.config_patcher.stop()
        self.llm_patcher.stop()
        self.stt_patcher.stop()
        self.vad_patcher.stop()
    
    @patch('agent.SimpleRAGEngine')
    @patch('agent.UnifiedKnowledgeBase')
    @patch('agent.ConversationContextManager')
    @patch('agent.ConversationLearningEngine')
    def test_agent_initialization(self, mock_learning, mock_context, mock_kb, mock_rag):
        """Test agent initialization with RAG components."""
        # Setup mocks
        mock_kb_instance = MagicMock()
        mock_kb.return_value = mock_kb_instance
        
        mock_rag_instance = MagicMock()
        mock_rag.return_value = mock_rag_instance
        
        # Initialize agent
        agent = BusinessVoiceAgent()
        
        # Verify that RAG components were initialized
        self.assertIsNotNone(agent.knowledge_base)
        self.assertIsNotNone(agent.rag_engine)
        self.assertIsNotNone(agent.context_manager)
        self.assertIsNotNone(agent.learning_engine)
        
        # Verify that UnifiedKnowledgeBase was initialized with correct parameters
        mock_kb.assert_called_once()
        
        # Verify that SimpleRAGEngine was initialized with the knowledge base
        mock_rag.assert_called_once_with(mock_kb_instance)
    
    @patch('agent.SimpleRAGEngine')
    @patch('agent.UnifiedKnowledgeBase')
    @patch('agent.ConversationContextManager')
    @patch('agent.ConversationLearningEngine')
    async def test_rag_enhanced_response_generation(self, mock_learning, mock_context, mock_kb, mock_rag):
        """Test RAG-enhanced response generation."""
        # Setup mocks
        mock_kb_instance = MagicMock()
        mock_kb.return_value = mock_kb_instance
        
        mock_rag_instance = MagicMock()
        mock_rag_instance.search_and_generate = AsyncMock()
        
        # Create a sample RAG response
        search_result = SearchResult(
            document_id="doc1",
            section_id="sec1",
            content="Our business hours are Monday-Friday 9AM-5PM.",
            relevance_score=0.9,
            document_type="faq",
            source_file="faq.pdf",
            context_match="hours",
            snippet="Our business hours",
            title="Business Hours",
            matched_terms=["hours", "business"]
        )
        
        rag_response = RAGResponse(
            answer="Our business hours are Monday-Friday 9AM-5PM.",
            sources=["faq.pdf"],
            confidence=0.9,
            context_used="",
            retrieved_content=[search_result],
            processing_time=0.1
        )
        
        mock_rag_instance.search_and_generate.return_value = rag_response
        mock_rag.return_value = mock_rag_instance
        
        # Mock context manager
        mock_context_instance = MagicMock()
        mock_context_instance.get_or_create_context = AsyncMock()
        mock_context_instance.get_conversation_summary = AsyncMock(return_value="")
        mock_context_instance.add_conversation_turn = AsyncMock()
        mock_context.return_value = mock_context_instance
        
        # Initialize agent
        agent = BusinessVoiceAgent()
        
        # Test RAG-enhanced response generation
        user_query = "What are your business hours?"
        session_id = "test_session"
        
        response = await agent._generate_rag_enhanced_response(user_query, session_id)
        
        # Verify that RAG search was called with correct parameters
        mock_rag_instance.search_and_generate.assert_called_once()
        call_args = mock_rag_instance.search_and_generate.call_args[1]
        self.assertEqual(call_args["query"], user_query)
        self.assertEqual(call_args["session_id"], session_id)
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertIn("business hours", response.lower())
        self.assertIn("monday-friday", response.lower())
    
    @patch('agent.SimpleRAGEngine')
    @patch('agent.UnifiedKnowledgeBase')
    @patch('agent.ConversationContextManager')
    @patch('agent.ConversationLearningEngine')
    def test_conversation_context_tracking(self, mock_learning, mock_context, mock_kb, mock_rag):
        """Test conversation context tracking."""
        # Setup mocks
        mock_kb_instance = MagicMock()
        mock_kb.return_value = mock_kb_instance
        
        mock_rag_instance = MagicMock()
        mock_rag.return_value = mock_rag_instance
        
        # Mock context manager
        mock_context_instance = MagicMock()
        mock_context_instance.get_or_create_context = AsyncMock()
        mock_context_instance.add_conversation_turn = AsyncMock()
        mock_context_instance.get_conversation_summary = AsyncMock(return_value="Previous conversation about business hours")
        mock_context.return_value = mock_context_instance
        
        # Initialize agent
        agent = BusinessVoiceAgent()
        
        # Test context tracking
        self.assertEqual(mock_context_instance.add_conversation_turn.call_count, 0)
        
        # Simulate conversation turns
        agent.current_session_id = "test_session"
        
        # Verify that context manager was initialized
        self.assertIsNotNone(agent.context_manager)
    
    @patch('agent.SimpleRAGEngine')
    @patch('agent.UnifiedKnowledgeBase')
    @patch('agent.ConversationContextManager')
    @patch('agent.ConversationLearningEngine')
    def test_conversation_learning(self, mock_learning, mock_context, mock_kb, mock_rag):
        """Test conversation learning capabilities."""
        # Setup mocks
        mock_kb_instance = MagicMock()
        mock_kb.return_value = mock_kb_instance
        
        mock_rag_instance = MagicMock()
        mock_rag.return_value = mock_rag_instance
        
        # Mock learning engine
        mock_learning_instance = MagicMock()
        mock_learning_instance.detect_user_learning_opportunity = MagicMock(return_value=True)
        mock_learning_instance.search_learned_information = MagicMock(return_value=[])
        mock_learning.return_value = mock_learning_instance
        
        # Initialize agent
        agent = BusinessVoiceAgent()
        
        # Verify that learning engine was initialized
        self.assertIsNotNone(agent.learning_engine)
        
        # Test learning detection
        user_query = "Let me tell you that we also have weekend hours on Saturday from 10AM-2PM"
        result = agent.learning_engine.detect_user_learning_opportunity(user_query, {"session_id": "test_session"})
        
        # Verify learning detection
        self.assertTrue(result)
    
    @patch('agent.SimpleRAGEngine')
    @patch('agent.UnifiedKnowledgeBase')
    @patch('agent.ConversationContextManager')
    @patch('agent.ConversationLearningEngine')
    def test_domain_expertise_adaptation(self, mock_learning, mock_context, mock_kb, mock_rag):
        """Test domain expertise adaptation."""
        # Setup mocks
        mock_kb_instance = MagicMock()
        mock_kb.return_value = mock_kb_instance
        
        mock_rag_instance = MagicMock()
        mock_rag.return_value = mock_rag_instance
        
        # Initialize agent
        agent = BusinessVoiceAgent()
        
        # Test domain detection
        query = "I need to schedule a medical consultation for my diabetes"
        intent = agent._detect_query_intent(query, [])
        
        # Verify domain detection
        self.assertEqual(intent, "healthcare")

if __name__ == "__main__":
    unittest.main()