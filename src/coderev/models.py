"""Core data models.

Every finding must carry a location (path + line) and a rule id — that is the
whole point of the product: no unlocatable opinions.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

SEVERITIES = ("suggestion", "warning", "blocker")
RISK_LEVELS = ("low", "medium", "high")
_RANK = {name: idx for idx, name in enumerate(SEVERITIES)}


@dataclass(frozen=True)
class Finding:
    path: str
    line_start: int
    title: str
    rule_id: str = "general"
    line_end: int | None = None
    severity: str = "suggestion"
    detail: str = ""
    suggestion: str = ""
    confidence: float = 0.0

    @property
    def key(self) -> tuple[str, int, str]:
        """Dedupe fingerprint: same file + line + rule is the same finding."""
        return (self.path, self.line_start, self.rule_id)

    @property
    def rank(self) -> int:
        return _RANK.get(self.severity, 0)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        missing = [key for key in ("path", "line_start", "title") if not data.get(key)]
        if missing:
            raise ValueError(f"finding 缺少字段: {', '.join(missing)}")

        severity = str(data.get("severity", "suggestion")).lower()
        if severity not in SEVERITIES:
            severity = "suggestion"

        confidence = float(data.get("confidence") or 0.0)
        confidence = min(max(confidence, 0.0), 1.0)

        line_end = data.get("line_end")
        return cls(
            path=str(data["path"]).lstrip("./"),
            line_start=int(data["line_start"]),
            line_end=int(line_end) if line_end else None,
            title=str(data["title"]).strip()[:120],
            rule_id=str(data.get("rule_id") or "general"),
            severity=severity,
            detail=str(data.get("detail") or "").strip(),
            suggestion=str(data.get("suggestion") or "").strip(),
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "severity": self.severity,
            "rule_id": self.rule_id,
            "title": self.title,
            "detail": self.detail,
            "suggestion": self.suggestion,
            "confidence": round(self.confidence, 3),
        }


@dataclass(frozen=True)
class TestGap:
    """A place that lacks tests — suggestion only, nothing is generated or run."""

    path: str
    symbol: str
    reason: str = ""
    cases: tuple[str, ...] = ()
    confidence: float = 0.0

    @property
    def key(self) -> tuple[str, str]:
        return (self.path, self.symbol)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestGap":
        missing = [key for key in ("path", "symbol") if not data.get(key)]
        if missing:
            raise ValueError(f"test_gap 缺少字段: {', '.join(missing)}")

        raw_cases = data.get("cases") or []
        if isinstance(raw_cases, str):
            raw_cases = [raw_cases]
        cases = tuple(str(case).strip() for case in raw_cases if str(case).strip())[:5]

        confidence = float(data.get("confidence") or 0.0)
        confidence = min(max(confidence, 0.0), 1.0)

        return cls(
            path=str(data["path"]).lstrip("./"),
            symbol=str(data["symbol"]).strip()[:80],
            reason=str(data.get("reason") or "").strip(),
            cases=cases,
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "symbol": self.symbol,
            "reason": self.reason,
            "cases": list(self.cases),
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ReviewResult:
    summary: str = ""
    risk_level: str = "low"
    findings: list[Finding] = field(default_factory=list)
    test_gaps: list[TestGap] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewResult":
        if not isinstance(data, dict):
            raise ValueError("模型输出必须是 JSON 对象")

        raw_findings = data.get("findings") or []
        if not isinstance(raw_findings, list):
            raise ValueError("findings 必须是数组")

        findings: list[Finding] = []
        for item in raw_findings:
            if not isinstance(item, dict):
                continue
            try:
                findings.append(Finding.from_dict(item))
            except (ValueError, TypeError):
                # 单条解析失败不应让整次审查失败
                continue

        raw_gaps = data.get("test_gaps") or []
        if not isinstance(raw_gaps, list):
            raw_gaps = []

        test_gaps: list[TestGap] = []
        for item in raw_gaps:
            if not isinstance(item, dict):
                continue
            try:
                test_gaps.append(TestGap.from_dict(item))
            except (ValueError, TypeError):
                continue

        risk = str(data.get("risk_level", "low")).lower()
        if risk not in RISK_LEVELS:
            risk = "low"

        return cls(
            summary=str(data.get("summary") or "").strip(),
            risk_level=risk,
            findings=findings,
            test_gaps=test_gaps,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "risk_level": self.risk_level,
            "findings": [f.to_dict() for f in self.sorted_findings()],
            "test_gaps": [g.to_dict() for g in self.test_gaps],
        }

    def sorted_findings(self) -> list[Finding]:
        """Highest severity first, then highest confidence."""
        return sorted(self.findings, key=lambda f: (-f.rank, -f.confidence))

    def without(self, findings: list[Finding]) -> "ReviewResult":
        keep = {finding.key for finding in findings}
        return replace(self, findings=[f for f in self.findings if f.key in keep])
