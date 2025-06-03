"""
test_advanced_memory_system_pytest.py - Comprehensive tests for the advanced memory system

Tests all components:
- Three-tier memory types (KT/ŚT/DT - Short/Mid/Long-term)
- Memory analysis and importance scoring
- Memory search and retrieval
- Memory promotion mechanisms
- Background maintenance tasks
- Memory analytics
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, date, time
from dataclasses import asdict

# Import the system under test
from advanced_memory_system import (
    MemoryType,
    ContextType,
    AnalyticsAction,
    MemoryEntry,
    MemorySearchResult,
    MemoryAnalyzer,
    MemorySearchEngine,
    MemoryManager,
    get_memory_manager,
    add_memory_advanced,
    search_memories_advanced,
    IMPORTANCE_THRESHOLDS,
    EMOTIONAL_KEYWORDS,
    PERSONAL_INDICATORS,
)

from database_models import (
    ShortTermMemory,
    MidTermMemory,
    LongTermMemory,
    MemoryAnalytics,
)


class TestMemoryEntry:
    """Test MemoryEntry data class and conversions"""
    
    def test_memory_entry_creation(self):
        """Test creating a MemoryEntry with all fields"""
        entry = MemoryEntry(
            content="Test content",
            user="test_user",
            memory_type=MemoryType.SHORT_TERM,
            context_type=ContextType.CONVERSATION,
            importance_score=0.75,
            context_tags="tag1,tag2"
        )
        
        assert entry.content == "Test content"
        assert entry.user == "test_user"
        assert entry.memory_type == MemoryType.SHORT_TERM
        assert entry.context_type == ContextType.CONVERSATION
        assert entry.importance_score == 0.75
        assert entry.context_tags == "tag1,tag2"
        assert isinstance(entry.created_at, datetime)
    
    def test_memory_entry_from_short_term(self):
        """Test converting ShortTermMemory to MemoryEntry"""
        st_memory = ShortTermMemory(
            id=1,
            content="Short term content",
            user="user1",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=15),
            last_accessed=datetime.now(),
            importance_score=0.6,
            context_tags="tag1,tag2"
        )
        
        entry = MemoryEntry.from_short_term(st_memory)
        
        assert entry.content == "Short term content"
        assert entry.user == "user1"
        assert entry.memory_type == MemoryType.SHORT_TERM
        assert entry.importance_score == 0.6
        assert entry.context_tags == "tag1,tag2"
    
    def test_memory_entry_from_mid_term(self):
        """Test converting MidTermMemory to MemoryEntry"""
        mt_memory = MidTermMemory(
            id=2,
            content="Mid term content",
            user="user2",
            importance_score=0.7,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
            context_type="task",
            access_count=3
        )
        
        entry = MemoryEntry.from_mid_term(mt_memory)
        
        assert entry.content == "Mid term content"
        assert entry.user == "user2"
        assert entry.memory_type == MemoryType.MID_TERM
        assert entry.context_type == ContextType.TASK
        assert entry.access_count == 3
    
    def test_memory_entry_from_long_term(self):
        """Test converting LongTermMemory to MemoryEntry"""
        lt_memory = LongTermMemory(
            id=3,
            content="Long term content",
            user="user3",
            created_at=datetime.now(),
            importance_score=0.9,
            is_important=True,
            memory_type="personal",
            context_tags="important,milestone",
            access_count=10
        )
        
        entry = MemoryEntry.from_long_term(lt_memory)
        
        assert entry.content == "Long term content"
        assert entry.user == "user3"
        assert entry.memory_type == MemoryType.LONG_TERM
        assert entry.importance_score == 0.9
        assert entry.is_important == True
        assert entry.context_tags == "important,milestone"
        assert entry.access_count == 10


class TestMemoryAnalyzer:
    """Test MemoryAnalyzer importance scoring"""
    
    @pytest.fixture
    def analyzer(self):
        return MemoryAnalyzer()
    
    def test_analyze_importance_basic(self, analyzer):
        """Test basic importance analysis"""
        content = "This is a simple test message"
        result = analyzer.analyze_importance(content, "test_user")
        score = result.new_score
        
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_analyze_importance_emotional_content(self, analyzer):
        """Test that emotional content gets higher scores"""
        emotional_content = "I am so excited and happy about this amazing achievement!"
        neutral_content = "The weather today is partly cloudy."        
        emotional_result = analyzer.analyze_importance(emotional_content, "test_user")
        neutral_result = analyzer.analyze_importance(neutral_content, "test_user")
        
        emotional_score = emotional_result.new_score
        neutral_score = neutral_result.new_score
        
        assert emotional_score > neutral_score
    
    def test_analyze_importance_personal_indicators(self, analyzer):
        """Test that personal content gets higher scores"""
        personal_content = "My birthday is tomorrow and I need to remember this."
        impersonal_content = "The system status is operational."
        
        personal_result = analyzer.analyze_importance(personal_content, "test_user")
        impersonal_result = analyzer.analyze_importance(impersonal_content, "test_user")
        
        personal_score = personal_result.new_score
        impersonal_score = impersonal_result.new_score
        
        assert personal_score > impersonal_score
    
    def test_analyze_importance_length_factor(self, analyzer):
        """Test that longer content can get higher scores"""
        short_content = "OK"
        long_content = "This is a detailed explanation of an important process that involves multiple steps and considerations that need to be remembered for future reference and implementation."
        
        short_result = analyzer.analyze_importance(short_content, "test_user")
        long_result = analyzer.analyze_importance(long_content, "test_user")
        
        short_score = short_result.new_score
        long_score = long_result.new_score
        assert long_score >= short_score
    
    def test_analyze_importance_keywords(self, analyzer):
        """Test that important keywords increase score"""
        keyword_content = "Remember this important deadline for the project!"
        normal_content = "Just a regular conversation message."
        
        keyword_result = analyzer.analyze_importance(keyword_content, "test_user")
        normal_result = analyzer.analyze_importance(normal_content, "test_user")
        
        keyword_score = keyword_result.new_score
        normal_score = normal_result.new_score
        
        assert keyword_score > normal_score
    
    def test_analyze_importance_with_context(self, analyzer):
        """Test importance analysis with context type"""
        content = "User preferences updated"
        
        task_result = analyzer.analyze_importance(content, "test_user", {"context_type": ContextType.TASK})
        conversation_result = analyzer.analyze_importance(content, "test_user", {"context_type": ContextType.CONVERSATION})
        personal_result = analyzer.analyze_importance(content, "test_user", {"context_type": ContextType.PERSONAL})
        
        task_score = task_result.new_score
        conversation_score = conversation_result.new_score
        personal_score = personal_result.new_score
          # Personal preferences should be considered more important
        assert personal_score >= task_score
        assert personal_score >= conversation_score
    
    def test_analyze_importance_caching(self, analyzer):
        """Test that analysis results are cached"""
        content = "Test content for caching"
          # First analysis
        result1 = analyzer.analyze_importance(content, "test_user")
        score1 = result1.new_score
        
        # Second analysis should use cache
        result2 = analyzer.analyze_importance(content, "test_user")
        score2 = result2.new_score
        
        assert score1 == score2
        # Note: Caching may be based on content+user combination


class TestMemorySearchEngine:
    """Test MemorySearchEngine functionality"""
    
    @pytest.fixture
    def search_engine(self):
        return MemorySearchEngine()
    
    @pytest.fixture
    def sample_memories(self):
        """Create sample memories for testing"""
        return [
            MemoryEntry(
                content="Python is a programming language",
                user="user1",
                memory_type=MemoryType.LONG_TERM,
                context_tags=["programming", "python"]
            ),
            MemoryEntry(
                content="I love eating pizza on weekends",
                user="user1", 
                memory_type=MemoryType.MID_TERM,
                context_tags=["food", "preferences"]
            ),
            MemoryEntry(
                content="Meeting scheduled for tomorrow at 2 PM",
                user="user1",
                memory_type=MemoryType.SHORT_TERM,
                context_tags=["schedule", "meeting"]
            ),
            MemoryEntry(
                content="My favorite programming language is Python",
                user="user1",
                memory_type=MemoryType.LONG_TERM,
                context_tags=["programming", "python", "preferences"]
            )
        ]
    
    def test_search_memories_exact_match(self, search_engine, sample_memories):
        """Test searching for exact matches"""
        results = search_engine.search_memories(sample_memories, "Python", limit=10)
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result.content}")
        
        # Should find 2 Python-related memories
        assert len(results) == 2  
        # All results should contain "python" (case insensitive)
        assert all("python" in result.content.lower() for result in results)
    
    def test_search_memories_fuzzy_match(self, search_engine, sample_memories):
        """Test fuzzy matching"""
        results = search_engine.search_memories(sample_memories, "programming", limit=10)
        
        assert len(results) >= 2  # Should find programming-related memories
    
    def test_search_memories_by_context_tags(self, search_engine, sample_memories):
        """Test searching by context tags"""
        results = search_engine.search_memories(sample_memories, "food", limit=10)
        
        assert len(results) >= 1
        assert any("pizza" in result.content.lower() for result in results)
    
    def test_search_memories_by_memory_type(self, search_engine, sample_memories):
        """Test filtering by memory type"""
        results = search_engine.search_memories(
            sample_memories, 
            "test", 
            memory_type=MemoryType.SHORT_TERM,
            limit=10
        )
        
        assert all(result.memory_type == MemoryType.SHORT_TERM for result in results)
    
    def test_search_memories_by_user(self, search_engine, sample_memories):
        """Test filtering by user"""
        # Add a memory for different user
        sample_memories.append(
            MemoryEntry(
                content="Different user content",
                user="user2",
                memory_type=MemoryType.LONG_TERM
            )
        )
        
        results = search_engine.search_memories(
            sample_memories,
            "content",
            user="user1",
            limit=10
        )        
        assert all(result.user == "user1" for result in results)
    
    def test_search_memories_limit(self, search_engine, sample_memories):
        """Test result limiting"""
        results = search_engine.search_memories(sample_memories, "user", limit=2)
        
        assert len(results) <= 2
    
    def test_search_memories_relevance_scoring(self, search_engine, sample_memories):
        """Test that results are ordered by relevance"""
        results = search_engine.search_memories(sample_memories, "Python programming", limit=10)
        
        # Results should be ordered by relevance (highest first)
        for i in range(len(results) - 1):
            # Each result should have relevance >= next result
            current_relevance = search_engine._calculate_relevance("Python programming", results[i].content)
            next_relevance = search_engine._calculate_relevance("Python programming", results[i + 1].content)
            assert current_relevance >= next_relevance


class TestMemoryManager:
    """Test MemoryManager functionality"""
    
    @pytest.fixture
    def memory_manager(self):
        return MemoryManager()    
    @patch('advanced_memory_system.add_short_term_memory')
    @patch('advanced_memory_system.add_memory_analytics_entry')
    def test_add_memory_short_term(self, mock_analytics, mock_add_st, memory_manager):
        """Test adding short-term memory"""
        mock_add_st.return_value = 1
        
        result = memory_manager.add_memory(
            content="Test short term memory",
            user="test_user",
            memory_type=MemoryType.SHORT_TERM
        )
        
        assert isinstance(result, MemoryEntry)
        mock_add_st.assert_called_once()
        mock_analytics.assert_called_once()
    
    @patch('advanced_memory_system.add_mid_term_memory')
    @patch('advanced_memory_system.add_memory_analytics_entry')
    def test_add_memory_mid_term(self, mock_analytics, mock_add_mt, memory_manager):
        """Test adding mid-term memory"""
        mock_add_mt.return_value = 2
        
        # Use context dict to pass context type information
        context = {"context_type": ContextType.TASK}
        result = memory_manager.add_memory(
            content="Test mid term memory",
            user="test_user",
            memory_type=MemoryType.MID_TERM,
            context=context
        )
        
        assert isinstance(result, MemoryEntry)
        mock_add_mt.assert_called_once()
        mock_analytics.assert_called_once()    
    @patch('advanced_memory_system.add_long_term_memory_enhanced')
    @patch('advanced_memory_system.add_memory_analytics_entry')
    def test_add_memory_long_term(self, mock_analytics, mock_add_lt, memory_manager):
        """Test adding long-term memory"""
        mock_add_lt.return_value = 3
        
        result = memory_manager.add_memory(
            content="Test long term memory",
            user="test_user",
            memory_type=MemoryType.LONG_TERM
        )
        
        assert isinstance(result, MemoryEntry)
        mock_add_lt.assert_called_once()
        mock_analytics.assert_called_once()    
    @patch('advanced_memory_system.get_short_term_memories')
    @patch('advanced_memory_system.get_mid_term_memories')
    @patch('advanced_memory_system.get_long_term_memories_enhanced')
    def test_search_memories_all_types(self, mock_get_lt, mock_get_mt, mock_get_st, memory_manager):
        """Test searching across all memory types"""
        # Mock database responses
        now = datetime.now()
        mock_get_st.return_value = [
            ShortTermMemory(
                id=1, 
                content="Short term test", 
                user="user1", 
                importance_score=0.5,
                created_at=now,
                expires_at=now + timedelta(hours=1),
                last_accessed=now,
                context_tags="test"
            )
        ]
        mock_get_mt.return_value = [
            MidTermMemory(
                id=2, 
                content="Mid term test", 
                user="user1", 
                importance_score=0.6,
                created_at=now,
                expires_at=now + timedelta(days=1),
                context_type=ContextType.CONVERSATION.value,
                access_count=1,
                context_tags="test"
            )
        ]
        mock_get_lt.return_value = [
            LongTermMemory(
                id=3, 
                content="Long term test", 
                user="user1", 
                importance_score=0.8,
                created_at=now,
                is_important=True,
                memory_type="general",
                context_tags="test",
                access_count=1
            )        ]
        results = memory_manager.search_memories("test", user="user1", limit=10)
        
        assert isinstance(results, MemorySearchResult)
        assert len(results.memories) >= 1  # At least one result should be found
        assert results.total_count >= 1
      
    @patch('advanced_memory_system.get_short_term_memories')
    @patch('advanced_memory_system.add_mid_term_memory')
    @patch('advanced_memory_system.delete_expired_short_term_memories')
    def test_promote_memories_short_to_mid(self, mock_delete, mock_add_mt, mock_get_st, memory_manager):
        """Test promoting memories from short-term to mid-term"""
        # Mock important short-term memory
        now = datetime.now()
        important_memory = ShortTermMemory(
            id=1,
            content="Very important information that should be remembered",
            user="user1",
            importance_score=0.85,  # Above threshold
            created_at=now - timedelta(minutes=10),
            expires_at=now + timedelta(minutes=5),
            last_accessed=now,
            context_tags="important"
        )
        
        mock_get_st.return_value = [important_memory]
        mock_add_mt.return_value = 2
        
        promoted_results = memory_manager.promote_memories()
        
        assert isinstance(promoted_results, dict)
        assert promoted_results['short_to_mid'] >= 0
        mock_add_mt.assert_called()
      
    @patch('advanced_memory_system.get_mid_term_memories')
    @patch('advanced_memory_system.add_long_term_memory_enhanced')
    @patch('advanced_memory_system.delete_expired_mid_term_memories')
    def test_promote_memories_mid_to_long(self, mock_delete, mock_add_lt, mock_get_mt, memory_manager):
        """Test promoting memories from mid-term to long-term"""
        # Mock important mid-term memory
        now = datetime.now()
        important_memory = MidTermMemory(
            id=2,
            content="Very important daily information",
            user="user1",
            importance_score=0.7,
            created_at=now - timedelta(hours=12),
            expires_at=now + timedelta(days=1),
            context_type=ContextType.PERSONAL.value,  # Use PERSONAL instead of USER_PREFERENCE
            access_count=5,  # Frequently accessed
            context_tags="important"
        )
        
        mock_get_mt.return_value = [important_memory]
        mock_add_lt.return_value = 3
          # Mock analyzer to return high importance
        with patch.object(memory_manager.analyzer, 'analyze_importance') as mock_analyze:
            mock_analyze.return_value = MagicMock(new_score=0.9)
            promoted_results = memory_manager.promote_memories()
        
        assert isinstance(promoted_results, dict)
        assert promoted_results['mid_to_long'] >= 0
        mock_add_lt.assert_called()


class TestBackgroundTasks:
    """Test background maintenance tasks"""
    
    @pytest.mark.asyncio
    @patch('advanced_memory_system.get_memory_manager')
    async def test_memory_maintenance_loop(self, mock_get_manager):
        """Test memory maintenance background task"""
        from advanced_memory_system import memory_maintenance_loop
        
        mock_manager = Mock()
        mock_manager.promote_memories.return_value = 2
        mock_manager.cleanup_expired_memories.return_value = 3
        mock_get_manager.return_value = mock_manager
        
        # Run one iteration with short interval
        task = asyncio.create_task(memory_maintenance_loop(interval_minutes=0.01))
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify maintenance was called
        assert mock_manager.promote_memories.called
        assert mock_manager.cleanup_expired_memories.called
    
    @pytest.mark.asyncio
    @patch('advanced_memory_system.get_memory_manager')
    async def test_analytics_cleanup_loop(self, mock_get_manager):
        """Test analytics cleanup background task"""
        from advanced_memory_system import analytics_cleanup_loop
        
        mock_manager = Mock()
        mock_manager.cleanup_old_analytics.return_value = 10
        mock_get_manager.return_value = mock_manager
        
        # Run one iteration with short interval
        task = asyncio.create_task(analytics_cleanup_loop(interval_hours=0.001))
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify cleanup was called
        assert mock_manager.cleanup_old_analytics.called


class TestIntegrationFunctions:
    """Test main integration functions"""
    
    @patch('advanced_memory_system.get_memory_manager')
    def test_add_memory_advanced(self, mock_get_manager):
        """Test add_memory_advanced function"""
        mock_manager = Mock()
        mock_manager.add_memory.return_value = 123
        mock_get_manager.return_value = mock_manager
        
        result = add_memory_advanced(
            content="Test memory",
            user="test_user",
            memory_type=MemoryType.SHORT_TERM
        )
        
        assert result == 123
        mock_manager.add_memory.assert_called_once()
    
    @patch('advanced_memory_system.get_memory_manager')
    def test_search_memories_advanced(self, mock_get_manager):
        """Test search_memories_advanced function"""
        mock_manager = Mock()
        mock_results = [
            MemoryEntry(content="Test result", user="user1", memory_type=MemoryType.LONG_TERM)
        ]
        mock_manager.search_memories.return_value = mock_results
        mock_get_manager.return_value = mock_manager
        
        results = search_memories_advanced(
            query="test",
            user="user1",
            limit=10
        )
        
        assert len(results) == 1
        assert results[0].content == "Test result"
        mock_manager.search_memories.assert_called_once()


class TestConfigurationAndConstants:
    """Test configuration values and constants"""
    
    def test_importance_thresholds(self):
        """Test that importance thresholds are properly configured"""
        assert 'short_to_mid' in IMPORTANCE_THRESHOLDS
        assert 'mid_to_long' in IMPORTANCE_THRESHOLDS
        assert 'direct_long_term' in IMPORTANCE_THRESHOLDS
        
        assert 0.0 <= IMPORTANCE_THRESHOLDS['short_to_mid'] <= 1.0
        assert 0.0 <= IMPORTANCE_THRESHOLDS['mid_to_long'] <= 1.0
        assert 0.0 <= IMPORTANCE_THRESHOLDS['direct_long_term'] <= 1.0
    
    def test_emotional_keywords(self):
        """Test that emotional keywords are defined"""
        assert len(EMOTIONAL_KEYWORDS) > 0
        assert isinstance(EMOTIONAL_KEYWORDS, dict)
        assert all(isinstance(category, str) for category in EMOTIONAL_KEYWORDS.keys())
        assert all(isinstance(keywords, list) for keywords in EMOTIONAL_KEYWORDS.values())
    
    def test_personal_indicators(self):
        """Test that personal indicators are defined"""
        assert len(PERSONAL_INDICATORS) > 0
        assert isinstance(PERSONAL_INDICATORS, list)
        assert all(isinstance(indicator, str) for indicator in PERSONAL_INDICATORS)
    
    def test_memory_type_enum(self):
        """Test MemoryType enum values"""
        assert MemoryType.SHORT_TERM.value == "short_term"
        assert MemoryType.MID_TERM.value == "mid_term" 
        assert MemoryType.LONG_TERM.value == "long_term"
    
    def test_context_type_enum(self):
        """Test ContextType enum values"""
        assert ContextType.CONVERSATION.value == "conversation"
        assert ContextType.TASK.value == "task"
        assert ContextType.USER_PREFERENCE.value == "user_preference"
        assert ContextType.SYSTEM_EVENT.value == "system_event"
    
    def test_analytics_action_enum(self):
        """Test AnalyticsAction enum values"""
        assert AnalyticsAction.ADD.value == "add"
        assert AnalyticsAction.SEARCH.value == "search"
        assert AnalyticsAction.PROMOTE.value == "promote"
        assert AnalyticsAction.DELETE.value == "delete"


# Performance and edge case tests
class TestPerformanceAndEdgeCases:
    """Test performance and edge cases"""
    
    @pytest.fixture
    def analyzer(self):
        return MemoryAnalyzer()
    
    def test_empty_content_analysis(self, analyzer):
        """Test analysis of empty content"""
        result = analyzer.analyze_importance("", "test_user")
        score = result.new_score
        assert score == 0.0
    
    def test_very_long_content_analysis(self, analyzer):
        """Test analysis of very long content"""
        long_content = "This is a test. " * 1000  # Very long content
        result = analyzer.analyze_importance(long_content, "test_user")
        score = result.new_score
        
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_special_characters_analysis(self, analyzer):
        """Test analysis of content with special characters"""
        special_content = "Test with émojis 🎉 and spëcial çharacters!"
        result = analyzer.analyze_importance(special_content, "test_user")
        score = result.new_score
        
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_search_performance_large_dataset(self):
        """Test search performance with large dataset"""
        search_engine = MemorySearchEngine()
        
        # Create large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append(
                MemoryEntry(
                    content=f"Memory entry number {i} with various content",
                    user="user1",
                    memory_type=MemoryType.LONG_TERM,
                    context_tags=[f"tag{i % 10}"]
                )
            )
        
        # Test search performance
        import time
        start_time = time.time()
        results = search_engine.search_memories(large_dataset, "content", limit=10)
        end_time = time.time()
        
        # Should complete within reasonable time (1 second)
        assert end_time - start_time < 1.0
        assert len(results) <= 10
    
    def test_memory_manager_concurrent_access(self):
        """Test memory manager with concurrent access simulation"""
        manager = MemoryManager()
        
        # Simulate multiple concurrent operations
        with patch('advanced_memory_system.add_short_term_memory') as mock_add:
            mock_add.return_value = 1
            
            results = []
            for i in range(10):
                result = manager.add_memory(
                    content=f"Concurrent memory {i}",
                    user="user1",
                    memory_type=MemoryType.SHORT_TERM
                )
                results.append(result)
            
            # All operations should succeed
            assert all(r == 1 for r in results)
            assert mock_add.call_count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
