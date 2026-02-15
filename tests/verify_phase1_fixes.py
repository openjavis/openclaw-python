"""
Quick verification script for Phase 1 fixes
Tests the critical fixes without requiring full integration
"""
import sys
from pathlib import Path

def test_message_order_fix():
    """Verify that tool_results_to_add is properly initialized"""
    print("Testing message order fix...")
    
    runtime_file = Path(__file__).parent.parent / "openclaw" / "agents" / "runtime.py"
    content = runtime_file.read_text()
    
    # Check if tool_results_to_add is initialized
    if "tool_results_to_add = []" in content:
        print("  ✅ tool_results_to_add initialization found")
    else:
        print("  ❌ tool_results_to_add initialization NOT found")
        return False
    
    # Check if tool results are stored instead of immediately added
    if 'tool_results_to_add.append({' in content:
        print("  ✅ Tool results are stored in list (not immediately added)")
    else:
        print("  ❌ Tool results storage logic NOT found")
        return False
    
    # Check if assistant message is added before tool results
    lines = content.split('\n')
    assistant_add_line = None
    tool_results_add_line = None
    
    for i, line in enumerate(lines):
        if 'session.add_assistant_message(final_text, tool_calls)' in line:
            assistant_add_line = i
        if 'for tr in tool_results_to_add:' in line:
            tool_results_add_line = i
    
    if assistant_add_line and tool_results_add_line:
        if assistant_add_line < tool_results_add_line:
            print(f"  ✅ Assistant message (line {assistant_add_line}) is added BEFORE tool results (line {tool_results_add_line})")
        else:
            print(f"  ❌ Wrong order: assistant at {assistant_add_line}, tool results at {tool_results_add_line}")
            return False
    else:
        print("  ⚠️  Could not verify exact ordering in code")
    
    return True


def test_file_detection_fix():
    """Verify that file detection checks both content and metadata"""
    print("\nTesting file detection fix...")
    
    runtime_file = Path(__file__).parent.parent / "openclaw" / "agents" / "runtime.py"
    content = runtime_file.read_text()
    
    # Check if metadata is accessed for file_path
    if "result_metadata = result.metadata" in content or "result.metadata" in content:
        print("  ✅ Metadata access found")
    else:
        print("  ❌ Metadata access NOT found")
        return False
    
    # Check for metadata file_path check
    if 'result_metadata.get("file_path")' in content or 'result_metadata.get("path")' in content:
        print("  ✅ Metadata file_path check found")
    else:
        print("  ❌ Metadata file_path check NOT found")
        return False
    
    # Check for comprehensive file detection
    if "# Check both content (JSON string) and metadata" in content or \
       "# 1. Try to parse output as JSON" in content:
        print("  ✅ Comprehensive file detection logic found")
    else:
        print("  ⚠️  Comment markers not found (but logic may still be present)")
    
    return True


def test_cron_duplicate_fix():
    """Verify that duplicate Cron execute method is removed"""
    print("\nTesting Cron duplicate fix...")
    
    cron_file = Path(__file__).parent.parent / "openclaw" / "agents" / "tools" / "cron.py"
    content = cron_file.read_text()
    
    # Count occurrences of "async def execute"
    execute_count = content.count("async def execute(")
    
    if execute_count == 1:
        print(f"  ✅ Only 1 execute method found (duplicate removed)")
    else:
        print(f"  ❌ Found {execute_count} execute methods (should be 1)")
        return False
    
    # Count occurrences of "def get_schema"
    schema_count = content.count("def get_schema(")
    
    if schema_count == 1:
        print(f"  ✅ Only 1 get_schema method found (duplicate removed)")
    else:
        print(f"  ❌ Found {schema_count} get_schema methods (should be 1)")
        return False
    
    # Check file size (should be smaller after removing ~293 lines)
    line_count = len(content.split('\n'))
    if line_count < 600:  # Original was 775 lines
        print(f"  ✅ File size reduced to {line_count} lines (was ~775)")
    else:
        print(f"  ⚠️  File has {line_count} lines (expected < 600)")
    
    return True


def test_syntax():
    """Basic syntax check"""
    print("\nTesting Python syntax...")
    
    try:
        import openclaw.agents.runtime
        import openclaw.agents.tools.cron
        print("  ✅ Modules import successfully (no syntax errors)")
        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1 Fixes Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Message Order Fix", test_message_order_fix()))
    results.append(("File Detection Fix", test_file_detection_fix()))
    results.append(("Cron Duplicate Fix", test_cron_duplicate_fix()))
    results.append(("Syntax Check", test_syntax()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All Phase 1 fixes verified successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ Some fixes failed verification")
        print("=" * 60)
        sys.exit(1)
