from pydantic import BaseModel, Field
from typing import List, Optional

class AttackPayload(BaseModel):
    attack_type: str = Field(..., description="Le type d'attaque (ex: DAN, Prompt Injection)")
    payload: str = Field(..., description="Le prompt malveillant généré")
    expected_behavior: str = Field(..., description="Ce qu'on s'attend à voir si l'attaque réussit")

class AttackResult(BaseModel):
    attack_type: str
    payload: str
    target_response: str
    is_vulnerable: bool
    vulnerability_score: int = Field(default=0, ge=0, le=10)
    details: str

class SecurityReport(BaseModel):
    target_name: str
    total_attacks: int
    successful_attacks: int
    overall_security_score: int
    findings: List[AttackResult]
