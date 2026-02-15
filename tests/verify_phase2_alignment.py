"""
Verification script for Phase 2 architecture alignment
"""
import sys
from pathlib import Path


def test_session_guards():
    """Verify SessionToolResultGuard implementation"""
    print("Testing Session Guards...")
    
    try:
        from openclaw.agents.session_guards import SessionToolResultGuard
        
        guard = SessionToolResultGuard()
        print("  ✅ SessionToolResultGuard imported successfully")
        
        # Check methods exist
        assert hasattr(guard, 'validate_message_order'), "Missing validate_message_order method"
        assert hasattr(guard, 'insert_tool_result'), "Missing insert_tool_result method"
        assert hasattr(guard, 'ensure_tool_results_after_assistant'), "Missing ensure_tool_results_after_assistant"
        assert hasattr(guard, 'check_provider_specific_rules'), "Missing check_provider_specific_rules"
        print("  ✅ All required methods present")
        
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_tool_execution_events():
    """Verify tool execution event support"""
    print("\nTesting Tool Execution Events...")
    
    try:
        from openclaw.events import EventType
        
        # Check for new event types
        assert hasattr(EventType, 'TOOL_EXECUTION_START'), "Missing TOOL_EXECUTION_START"
        assert hasattr(EventType, 'TOOL_EXECUTION_UPDATE'), "Missing TOOL_EXECUTION_UPDATE"
        assert hasattr(EventType, 'TOOL_EXECUTION_END'), "Missing TOOL_EXECUTION_END"
        print("  ✅ Tool execution event types defined")
        
        # Check runtime emits these events
        runtime_file = Path(__file__).parent.parent / "openclaw" / "agents" / "runtime.py"
        content = runtime_file.read_text()
        
        if "EventType.TOOL_EXECUTION_START" in content:
            print("  ✅ Runtime emits TOOL_EXECUTION_START")
        else:
            print("  ⚠️  Runtime may not emit TOOL_EXECUTION_START")
        
        if "EventType.TOOL_EXECUTION_END" in content:
            print("  ✅ Runtime emits TOOL_EXECUTION_END")
        else:
            print("  ⚠️  Runtime may not emit TOOL_EXECUTION_END")
        
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_steering_followup():
    """Verify steering and follow-up mechanism"""
    print("\nTesting Steering/Follow-up Mechanism...")
    
    try:
        runtime_file = Path(__file__).parent.parent / "openclaw" / "agents" / "runtime.py"
        content = runtime_file.read_text()
        
        # Check for parameter support
        if "get_steering_messages" in content:
            print("  ✅ get_steering_messages parameter found")
        else:
            print("  ❌ get_steering_messages parameter NOT found")
            return False
        
        if "get_followup_messages" in content:
            print("  ✅ get_followup_messages parameter found")
        else:
            print("  ❌ get_followup_messages parameter NOT found")
            return False
        
        # Check for steering logic
        if "steering = await get_steering_messages()" in content:
            print("  ✅ Steering message handling implemented")
        else:
            print("  ⚠️  Steering message handling may not be complete")
        
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_custom_message_types():
    """Verify custom message types"""
    print("\nTesting Custom Message Types...")
    
    try:
        from openclaw.agents.types import (
            BashExecutionMessage,
            CustomMessage,
            AgentMessage,
        )
        
        print("  ✅ BashExecutionMessage imported")
        print("  ✅ CustomMessage imported")
        
        # Check AgentMessage union includes new types
        # This is a bit tricky to verify at runtime, so we check the source
        types_file = Path(__file__).parent.parent / "openclaw" / "agents" / "types.py"
        content = types_file.read_text()
        
        if "BashExecutionMessage" in content and "class BashExecutionMessage" in content:
            print("  ✅ BashExecutionMessage defined")
        
        if "CustomMessage" in content and "class CustomMessage" in content:
            print("  ✅ CustomMessage defined")
        
        if "AgentMessage =" in content and "BashExecutionMessage" in content:
            print("  ✅ AgentMessage union includes BashExecutionMessage")
        
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_session_compaction():
    """Verify session compaction implementation"""
    print("\nTesting Session Compaction...")
    
    try:
        from openclaw.agents.session_compaction import (
            SessionCompactor,
            CompactionSummary,
            get_default_compactor,
        )
        
        print("  ✅ SessionCompactor imported")
        print("  ✅ CompactionSummary imported")
        print("  ✅ get_default_compactor imported")
        
        # Create compactor instance
        compactor = SessionCompactor()
        
        # Check methods
        assert hasattr(compactor, 'should_compact'), "Missing should_compact method"
        assert hasattr(compactor, 'compact'), "Missing compact method"
        assert hasattr(compactor, 'get_compaction_stats'), "Missing get_compaction_stats"
        print("  ✅ All required methods present")
        
        # Test basic functionality
        stats = compactor.get_compaction_stats([])
        assert isinstance(stats, dict), "get_compaction_stats should return dict"
        print("  ✅ get_compaction_stats works")
        
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_imports():
    """Test that all new modules import correctly"""
    print("\nTesting Module Imports...")
    
    try:
        import openclaw.agents.session_guards
        import openclaw.agents.session_compaction
        import openclaw.agents.types
        import openclaw.agents.runtime
        print("  ✅ All modules import successfully")
        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 Architecture Alignment Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Module Imports", test_imports()))
    results.append(("Session Guards", test_session_guards()))
    results.append(("Tool Execution Events", test_tool_execution_events()))
    results.append(("Steering/Follow-up", test_steering_followup()))
    results.append(("Custom Message Types", test_custom_message_types()))
    results.append(("Session Compaction", test_session_compaction()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All Phase 2 features verified successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ Some features failed verification")
        print("=" * 60)
        sys.exit(1)
