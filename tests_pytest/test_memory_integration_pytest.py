"""
test_memory_integration_pytest.py - Integration tests for advanced memory system

Tests integration between memory_module.py and advanced_memory_system.py
Tests backward compatibility and fallback mechanisms
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Test imports for integration
import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.memory_module import (
    add_memory,
    retrieve_memories,
    delete_memory,
    ADVANCED_MEMORY_AVAILABLE,
    Memory,
    MemoryStats
)

# Import advanced system components for testing
if ADVANCED_MEMORY_AVAILABLE:
    from advanced_memory_system import (
        MemoryType,
        ContextType,
        MemoryEntry,
        get_memory_manager
    )


class TestMemoryModuleIntegration:
    """Test integration between old and new memory systems"""
    
    def test_advanced_memory_availability(self):
        """Test that advanced memory system is properly detected"""
        # This should be True if advanced_memory_system.py is available
        assert isinstance(ADVANCED_MEMORY_AVAILABLE, bool)
    
    @pytest.mark.skipif(not ADVANCED_MEMORY_AVAILABLE, reason="Advanced memory system not available")
    def test_memory_module_imports_advanced_system(self):
        """Test that memory module can import advanced components"""
        from modules.memory_module import MemoryType, ContextType
        
        assert MemoryType.SHORT_TERM == "short_term"
        assert MemoryType.MID_TERM == "mid_term"
        assert MemoryType.LONG_TERM == "long_term"
        
        assert ContextType.CONVERSATION == "conversation"
        assert ContextType.TASK == "task"
    
    @patch('modules.memory_module.add_memory_db')
    @patch('modules.memory_module.add_memory_analytics_entry')
    def test_add_memory_legacy_compatibility(self, mock_analytics, mock_add_db):
        """Test that legacy add_memory still works"""
        mock_add_db.return_value = 123
        
        result, success = add_memory("Test memory content", "test_user")
        
        assert success
        assert "Zapamiętałem" in result
        mock_add_db.assert_called_once()
    
    @patch('modules.memory_module.get_memories_db')
    def test_retrieve_memories_legacy_compatibility(self, mock_get_db):
        """Test that legacy retrieve_memories still works"""
        mock_get_db.return_value = [
            {'id': 1, 'content': 'Test memory', 'user': 'test_user'}
        ]
        
        result, success = retrieve_memories("test query", limit=10)
        
        assert success
        assert len(result) == 1
        assert isinstance(result[0], Memory)
        assert result[0].content == 'Test memory'
    
    @pytest.mark.skipif(not ADVANCED_MEMORY_AVAILABLE, reason="Advanced memory system not available")
    @patch('modules.memory_module.add_memory_advanced')
    def test_add_memory_with_advanced_features(self, mock_add_advanced):
        """Test adding memory with advanced features when available"""
        mock_add_advanced.return_value = 456
        
        # Test using the new advanced functionality
        from modules.memory_module import add_memory_with_context
        
        result, success = add_memory_with_context(
            content="Advanced memory content",
            user="test_user",
            memory_type=MemoryType.MID_TERM,
            context_type=ContextType.TASK
        )
        
        assert success
        mock_add_advanced.assert_called_once()
    
    @pytest.mark.skipif(not ADVANCED_MEMORY_AVAILABLE, reason="Advanced memory system not available")
    @patch('modules.memory_module.search_memories_advanced')
    def test_search_memories_with_advanced_features(self, mock_search_advanced):
        """Test searching memories with advanced features"""
        mock_search_advanced.return_value = [
            MemoryEntry(
                content="Advanced search result",
                user="test_user",
                memory_type=MemoryType.LONG_TERM,
                importance_score=0.85
            )
        ]
        
        from modules.memory_module import search_memories_with_context
        
        results, success = search_memories_with_context(
            query="test query",
            user="test_user",
            memory_type=MemoryType.LONG_TERM,
            limit=10
        )
        
        assert success
        assert len(results) == 1
        assert results[0]['importance_score'] == 0.85
        mock_search_advanced.assert_called_once()
    
    def test_memory_stats_legacy(self):
        """Test memory statistics with legacy system"""
        with patch('modules.memory_module.get_memories_db') as mock_get:
            mock_get.return_value = [
                {'id': 1, 'content': 'Memory 1', 'user': 'user1'},
                {'id': 2, 'content': 'Memory 2', 'user': 'user1'},
                {'id': 3, 'content': 'Memory 3', 'user': 'user2'}
            ]
            
            stats = MemoryStats.get_stats()
            
            assert stats.total_memories == 3
            assert stats.unique_users == 2
            assert stats.avg_memory_length > 0
    
    @pytest.mark.skipif(not ADVANCED_MEMORY_AVAILABLE, reason="Advanced memory system not available")
    def test_memory_stats_advanced(self):
        """Test memory statistics with advanced system"""
        with patch('modules.memory_module.get_memory_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_memory_statistics.return_value = {
                'total_memories': 100,
                'short_term_count': 20,
                'mid_term_count': 30,
                'long_term_count': 50,
                'unique_users': 5,
                'avg_importance_score': 0.65
            }
            mock_get_manager.return_value = mock_manager
            
            from modules.memory_module import get_advanced_memory_stats
            
            stats = get_advanced_memory_stats()
            
            assert stats['total_memories'] == 100
            assert stats['short_term_count'] == 20
            assert stats['mid_term_count'] == 30
            assert stats['long_term_count'] == 50
            assert stats['unique_users'] == 5
            assert stats['avg_importance_score'] == 0.65
    
    def test_error_handling_advanced_system_failure(self):
        """Test error handling when advanced system fails"""
        with patch('modules.memory_module.ADVANCED_MEMORY_AVAILABLE', False):
            # Should fall back to legacy system
            with patch('modules.memory_module.add_memory_db') as mock_add_legacy:
                mock_add_legacy.return_value = 789
                
                result, success = add_memory("Fallback test", "test_user")
                
                assert success
                mock_add_legacy.assert_called_once()


class TestMemoryModuleBackwardCompatibility:
    """Test backward compatibility with existing code"""
    
    @patch('modules.memory_module.add_memory_db')
    def test_old_function_signatures_still_work(self, mock_add_db):
        """Test that old function signatures still work"""
        mock_add_db.return_value = 999
        
        # Test with positional arguments (old style)
        result, success = add_memory("Old style memory", "old_user")
        assert success
        
        # Test with keyword arguments (old style)
        result, success = add_memory(content="Keyword memory", user="keyword_user")
        assert success
        
        # Test with None user (old behavior)
        result, success = add_memory("No user memory", None)
        assert success
    
    @patch('modules.memory_module.get_memories_db')
    def test_old_return_format_preserved(self, mock_get_db):
        """Test that old return formats are preserved"""
        mock_get_db.return_value = [
            {'id': 1, 'content': 'Legacy memory', 'user': 'legacy_user'}
        ]
        
        memories, success = retrieve_memories("legacy test")
        
        assert success
        assert isinstance(memories, list)
        assert len(memories) == 1
        assert isinstance(memories[0], Memory)
        assert hasattr(memories[0], 'id')
        assert hasattr(memories[0], 'content') 
        assert hasattr(memories[0], 'user')
    
    def test_memory_dataclass_compatibility(self):
        """Test that Memory dataclass works as expected"""
        memory = Memory(id=1, user="test", content="test content")
        
        assert memory.id == 1
        assert memory.user == "test"
        assert memory.content == "test content"
        
        # Test serialization compatibility
        memory_dict = memory.__dict__
        assert 'id' in memory_dict
        assert 'user' in memory_dict
        assert 'content' in memory_dict
    
    def test_memory_stats_dataclass_compatibility(self):
        """Test that MemoryStats dataclass works as expected"""
        with patch('modules.memory_module.get_memories_db') as mock_get:
            mock_get.return_value = [
                {'id': 1, 'content': 'Short memory', 'user': 'user1'},
                {'id': 2, 'content': 'Medium length memory content', 'user': 'user1'},
                {'id': 3, 'content': 'Very long memory content that goes on and on', 'user': 'user2'}
            ]
            
            stats = MemoryStats.get_stats()
            
            assert hasattr(stats, 'total_memories')
            assert hasattr(stats, 'unique_users')
            assert hasattr(stats, 'avg_memory_length')
            assert hasattr(stats, 'oldest_memory')
            assert hasattr(stats, 'newest_memory')
            
            assert isinstance(stats.total_memories, int)
            assert isinstance(stats.unique_users, int)
            assert isinstance(stats.avg_memory_length, float)


class TestMemoryModuleErrorHandling:
    """Test error handling in memory module"""
    
    def test_add_memory_validation(self):
        """Test input validation for add_memory"""
        # Test empty content
        result, success = add_memory("", "test_user")
        assert not success
        assert "Nie mogę zapisać pustej" in result
        
        # Test whitespace-only content
        result, success = add_memory("   ", "test_user")
        assert not success
        assert "Nie mogę zapisać pustej" in result
        
        # Test very short content
        result, success = add_memory("ab", "test_user")
        assert not success
        assert "zbyt krótkiej" in result
    
    @patch('modules.memory_module.add_memory_db')
    def test_add_memory_database_error(self, mock_add_db):
        """Test handling of database errors in add_memory"""
        mock_add_db.side_effect = Exception("Database error")
        
        result, success = add_memory("Valid content", "test_user")
        
        assert not success
        assert "błąd" in result.lower() or "error" in result.lower()
    
    @patch('modules.memory_module.get_memories_db')
    def test_retrieve_memories_database_error(self, mock_get_db):
        """Test handling of database errors in retrieve_memories"""
        mock_get_db.side_effect = Exception("Database error")
        
        result, success = retrieve_memories("test query")
        
        assert not success
        assert isinstance(result, str)  # Should return error message as string
    
    def test_retrieve_memories_validation(self):
        """Test input validation for retrieve_memories"""
        # Test with invalid limit
        with patch('modules.memory_module.get_memories_db') as mock_get:
            mock_get.return_value = []
            
            result, success = retrieve_memories("test", limit=0)
            assert success  # Should handle gracefully
            
            result, success = retrieve_memories("test", limit=-1)
            assert success  # Should handle gracefully
    
    @patch('modules.memory_module.delete_memory_db')
    def test_delete_memory_error_handling(self, mock_delete_db):
        """Test error handling in delete_memory"""
        mock_delete_db.side_effect = Exception("Database error")
        
        result, success = delete_memory(1)
        
        assert not success
        assert "błąd" in result.lower() or "error" in result.lower()
    
    def test_delete_memory_validation(self):
        """Test input validation for delete_memory"""
        # Test with invalid memory ID
        result, success = delete_memory(None)
        assert not success
        
        result, success = delete_memory(-1)
        assert not success


class TestMemoryModulePerformance:
    """Test performance aspects of memory module"""
    
    @patch('modules.memory_module.get_memories_db')
    def test_large_memory_retrieval(self, mock_get_db):
        """Test retrieving large number of memories"""
        # Create large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'id': i,
                'content': f'Memory content {i}',
                'user': f'user{i % 10}'
            })
        
        mock_get_db.return_value = large_dataset
        
        import time
        start_time = time.time()
        
        memories, success = retrieve_memories("test", limit=1000)
        
        end_time = time.time()
        
        assert success
        assert len(memories) == 1000
        # Should complete within reasonable time
        assert end_time - start_time < 1.0
    
    def test_memory_stats_performance(self):
        """Test performance of memory statistics calculation"""
        with patch('modules.memory_module.get_memories_db') as mock_get:
            # Create large dataset for stats calculation
            large_dataset = []
            for i in range(5000):
                large_dataset.append({
                    'id': i,
                    'content': f'Memory content number {i} with varying lengths',
                    'user': f'user{i % 100}'  # 100 different users
                })
            
            mock_get.return_value = large_dataset
            
            import time
            start_time = time.time()
            
            stats = MemoryStats.get_stats()
            
            end_time = time.time()
            
            assert stats.total_memories == 5000
            assert stats.unique_users == 100
            # Should complete within reasonable time
            assert end_time - start_time < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
