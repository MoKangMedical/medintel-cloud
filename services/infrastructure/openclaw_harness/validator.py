"""Result Validator — verifies Harness output reliability and consistency.

Medical AI outputs must meet higher standards than general AI. The validator
ensures outputs are clinically sound, internally consistent, and appropriately
flagged for uncertainty.

Validation layers:
  1. Structural — output has required fields and correct types
  2. Consistency — internal logic doesn't contradict itself
  3. Domain — output adheres to medical domain standards
  4. Safety — no dangerous recommendations without proper warnings
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationSeverity(str, Enum):
    """Severity of a validation finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationFinding:
    """A single validation finding."""

    severity: ValidationSeverity = ValidationSeverity.INFO
    field: str = ""
    message: str = ""
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Result of validating a Harness output.

    Attributes:
        passed: Whether validation passed (no errors or criticals).
        score: Quality score from 0.0 (worst) to 1.0 (best).
        findings: List of individual validation findings.
        message: Summary message.
        metadata: Additional validation metadata.
    """

    passed: bool = True
    score: float = 1.0
    findings: list[ValidationFinding] = field(default_factory=list)
    message: str = "Validation passed"
    metadata: dict[str, Any] = field(default_factory=dict)


# Domain-specific required fields
DOMAIN_REQUIRED_FIELDS: dict[str, list[str]] = {
    "diagnosis": ["primary_diagnosis", "differential_list", "confidence"],
    "drug_discovery": ["target", "compounds", "admet_predictions"],
    "health_management": ["assessment", "plan", "follow_up_schedule"],
}

# Known dangerous medical patterns
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"no need for (further )?testing", "Recommendations to skip testing require review"),
    (r"definitely (not )?cancer", "Absolute cancer statements without biopsy are dangerous"),
    (r"stop all medications", "Stopping all medications without supervision is unsafe"),
    (r"guaranteed (cure|recovery)", "No medical outcome can be guaranteed"),
]


class ResultValidator:
    """Validates Harness outputs for clinical soundness and safety.

    Validation pipeline:
      1. Structural validation — required fields, types
      2. Consistency checks — no internal contradictions
      3. Domain rules — medical domain standards
      4. Safety screening — dangerous pattern detection

    Attributes:
        strict_mode: If True, warnings also cause validation failure.
    """

    def __init__(
        self,
        strict_mode: bool = False,
        domain_rules: dict[str, Any] | None = None,
    ) -> None:
        self.strict_mode = strict_mode
        self.domain_rules = domain_rules or {}

    def validate(
        self,
        output: Any,
        domain: str = "general",
    ) -> ValidationResult:
        """Run the full validation pipeline on a Harness output.

        Args:
            output: The output to validate (string, dict, or object).
            domain: The medical domain for domain-specific rules.

        Returns:
            ValidationResult with pass/fail status and findings.
        """
        findings: list[ValidationFinding] = []
        output_dict = self._normalize_output(output)

        findings.extend(self._validate_structure(output_dict, domain))
        findings.extend(self._validate_consistency(output_dict))
        findings.extend(self._validate_domain(output_dict, domain))
        findings.extend(self._validate_safety(output_dict))

        score = self._calculate_score(findings)
        passed = self._determine_pass(findings)

        error_count = sum(1 for f in findings if f.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for f in findings if f.severity == ValidationSeverity.WARNING)

        if passed:
            message = f"Validation passed (score: {score:.2f})"
        else:
            message = f"Validation failed — {error_count} error(s), {warning_count} warning(s)"

        return ValidationResult(
            passed=passed,
            score=score,
            findings=findings,
            message=message,
            metadata={
                "domain": domain,
                "strict_mode": self.strict_mode,
            },
        )

    def _normalize_output(self, output: Any) -> dict[str, Any]:
        if isinstance(output, dict):
            return output
        if isinstance(output, str):
            return {"raw_output": output}
        if hasattr(output, "__dict__"):
            return {k: v for k, v in output.__dict__.items() if not k.startswith("_")}
        if hasattr(output, "output"):
            return self._normalize_output(output.output)
        return {"raw_output": str(output)}

    def _validate_structure(
        self, output: dict[str, Any], domain: str
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if not output:
            findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                field="__root__",
                message="Output is empty",
            ))
            return findings

        required = DOMAIN_REQUIRED_FIELDS.get(domain, [])
        for field_name in required:
            if field_name not in output:
                findings.append(ValidationFinding(
                    severity=ValidationSeverity.ERROR,
                    field=field_name,
                    message=f"Missing required field: {field_name}",
                ))
        return findings

    def _validate_consistency(self, output: dict[str, Any]) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        confidence = output.get("confidence")
        if isinstance(confidence, (int, float)) and not 0.0 <= confidence <= 1.0:
            findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                field="confidence",
                message=f"Confidence {confidence} outside valid range [0, 1]",
            ))
        return findings

    def _validate_domain(
        self, output: dict[str, Any], domain: str
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if domain == "diagnosis":
            differential = output.get("differential_list", [])
            if isinstance(differential, list) and len(differential) < 2:
                findings.append(ValidationFinding(
                    severity=ValidationSeverity.WARNING,
                    field="differential_list",
                    message="Differential list has fewer than 2 alternatives",
                ))
        return findings

    def _validate_safety(self, output: dict[str, Any]) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        text = str(output).lower()
        for pattern, message in DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                findings.append(ValidationFinding(
                    severity=ValidationSeverity.CRITICAL,
                    field="__safety__",
                    message=f"Dangerous pattern detected: {message}",
                ))
        return findings

    def _calculate_score(self, findings: list[ValidationFinding]) -> float:
        if not findings:
            return 1.0
        penalties = {
            ValidationSeverity.INFO: 0.0,
            ValidationSeverity.WARNING: 0.1,
            ValidationSeverity.ERROR: 0.25,
            ValidationSeverity.CRITICAL: 0.5,
        }
        total = sum(penalties.get(f.severity, 0.0) for f in findings)
        return max(0.0, 1.0 - total)

    def _determine_pass(self, findings: list[ValidationFinding]) -> bool:
        if self.strict_mode:
            return not any(
                f.severity in (ValidationSeverity.WARNING, ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
                for f in findings
            )
        return not any(
            f.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for f in findings
        )
