#!/usr/bin/env python3
"""Test script to verify Gemini message fixer"""

from openclaw.agents.gemini_message_fixer import fix_gemini_message_sequence

# Test case: tool message without preceding assistant
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello"},
    {"role": "tool", "name": "search_web", "tool_call_id": "call_123", "content": "Search results..."}
]

print("🧪 Testing Gemini Message Fixer")
print("=" * 60)
print("\n📥 Input messages:")
for i, msg in enumerate(messages):
    print(f"  [{i}] {msg.get('role')}: {msg.get('content', '')[:50]}...")

fixed = fix_gemini_message_sequence(messages)

print("\n📤 Fixed messages:")
for i, msg in enumerate(fixed):
    print(f"  [{i}] {msg.get('role')}: {msg.get('content', '')[:50]}...")
    if msg.get('tool_calls'):
        for tc in msg['tool_calls']:
            print(f"       → tool_call: name={tc.get('name')}, id={tc.get('id')}")

# Verify the fix
print("\n✅ Verification:")
for i, msg in enumerate(fixed):
    if msg.get('tool_calls'):
        for tc in msg['tool_calls']:
            if not tc.get('name'):
                print(f"❌ ERROR: tool_call at message {i} missing 'name' field!")
                exit(1)
            else:
                print(f"✓ tool_call at message {i} has name: {tc.get('name')}")

print("\n🎉 All tool_calls have required 'name' field!")
print("✅ Gemini API should accept these messages")
