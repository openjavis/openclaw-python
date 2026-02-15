"""
Pairing code generation (aligned with TypeScript pairing-store.ts)

Generates 8-character pairing codes using a safe alphabet.
"""
import secrets
import string

# Safe alphabet excluding confusable characters: I, O, 0, 1
# Matches TypeScript: "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PAIRING_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PAIRING_CODE_LENGTH = 8


def generate_pairing_code(length: int = PAIRING_CODE_LENGTH) -> str:
    """
    Generate a secure pairing code
    
    Uses cryptographically secure random generator with
    a safe alphabet (no I, O, 0, 1 to avoid confusion).
    
    Args:
        length: Code length (default: 8)
        
    Returns:
        Pairing code (e.g., "A7JKPC29")
    """
    return "".join(
        secrets.choice(PAIRING_CODE_ALPHABET)
        for _ in range(length)
    )


def validate_pairing_code(code: str) -> bool:
    """
    Validate pairing code format
    
    Args:
        code: Code to validate
        
    Returns:
        True if valid
    """
    if not code or len(code) != PAIRING_CODE_LENGTH:
        return False
    
    return all(c in PAIRING_CODE_ALPHABET for c in code)
