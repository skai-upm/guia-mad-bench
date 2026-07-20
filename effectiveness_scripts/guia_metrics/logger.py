from __future__ import annotations

from datetime import datetime
from pathlib import Path
import traceback
from typing import Optional


class ExtendedReportLogger:
    """Append-only logger for metric execution details.

    The paper states that concise CSV files should contain metric values,
    while detailed errors should be moved to an extended report.
    """

    def __init__(self, report_path: str | Path):
        self.report_path = Path(report_path)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, metric: str, message: str, pred_file: Optional[str] = None,
            gold_file: Optional[str] = None, exception: Optional[BaseException] = None) -> None:
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        lines = [
            "=" * 90,
            f"[{timestamp}] metric={metric}",
        ]
        if pred_file:
            lines.append(f"pred_file={pred_file}")
        if gold_file:
            lines.append(f"gold_file={gold_file}")
        lines.append(message)
        if exception is not None:
            lines.append("Exception traceback:")
            lines.append("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
        with self.report_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")
