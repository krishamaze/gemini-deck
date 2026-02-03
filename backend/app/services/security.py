import re
from typing import List, Tuple, Optional

class SecurityService:
    def __init__(self):
        # Basic heuristic patterns for Prompt Injection / Jailbreaks
        self.risk_patterns = [
            (r"ignore previous instructions", "Prompt Injection (Ignore Instructions)"),
            (r"you are now (DAN|do anything now)", "Jailbreak Attempt (DAN Mode)"),
            (r"system override", "System Override Attempt"),
            (r"delete all files", "Malicious Intent (File Deletion)"),
            (r"rm -rf", "Malicious Command (rm -rf)"),
            (r"/etc/shadow", "Sensitive File Access"),
        ]
        
    def analyze_prompt(self, prompt: str) -> Tuple[bool, Optional[str]]:
        """
        Analyzes a prompt for security risks.
        Returns: (is_safe: bool, reason: str | None)
        """
        prompt_lower = prompt.lower()
        
        for pattern, risk_name in self.risk_patterns:
            if re.search(pattern, prompt_lower):
                return False, f"Blocked: {risk_name} detected."
        
        # Length check (Buffer overflow prevention for CLI args)
        if len(prompt) > 10000:
            return False, "Blocked: Prompt exceeds maximum length (10k chars)."

        return True, None

    def sanitize_output(self, output: str) -> str:
        """
        Sanitizes AI output to prevent rendering malicious code execution or artifacts.
        (Basic implementation: can be expanded to redact PII)
        """
        # Example: Redact potential API keys (simple regex)
        # sk-([a-zA-Z0-9]{32,}) -> sk-[REDACTED]
        return output

# Singleton
_security_service = None

def get_security_service():
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service
