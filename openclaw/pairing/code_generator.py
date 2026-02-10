"""Pairing code generation matching TypeScript openclaw/src/pairing"""
import secrets

# Alphabet excluding ambiguous characters (0, O, 1, I)
PAIRING_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
MAX_GENERATION_ATTEMPTS = 500


def generate_pairing_code(existing_codes: set[str] | None = None) -> str:
    """
    Generate unique 8-character pairing code
    
    Uses cryptographically secure randomness.
    Excludes ambiguous characters: 0, O, 1, I
    
    Args:
        existing_codes: Set of existing codes to avoid duplicates
        
    Returns:
        8-character pairing code
        
    Raises:
        RuntimeError: If cannot generate unique code after max attempts
    """
    existing = existing_codes or set()
    
    for attempt in range(MAX_GENERATION_ATTEMPTS):
        # Generate random code
        code = "".join(
            secrets.choice(PAIRING_CODE_ALPHABET)
            for _ in range(CODE_LENGTH)
        )
        
        # Check uniqueness
        if code not in existing:
            return code
    
    raise RuntimeError(
        f"Failed to generate unique pairing code after {MAX_GENERATION_ATTEMPTS} attempts"
    )


def validate_pairing_code(code: str) -> bool:
    """
    Validate pairing code format
    
    Args:
        code: Code to validate
        
    Returns:
        True if valid
    """
    if not code:
        return False
    
    if len(code) != CODE_LENGTH:
        return False
    
    # Check all characters are in alphabet
    return all(c in PAIRING_CODE_ALPHABET for c in code.upper())


def normalize_pairing_code(code: str) -> str:
    """
    Normalize pairing code (uppercase)
    
    Args:
        code: Code to normalize
        
    Returns:
        Normalized code
    """
    return code.upper()
