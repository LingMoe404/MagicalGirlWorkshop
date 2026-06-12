import re
from dataclasses import dataclass
from enum import Enum


class SearchResultMode(Enum):
    SUCCESS = "success"
    QUALITY_FALLBACK = "quality_fallback"


@dataclass(frozen=True)
class CrfCandidate:
    crf: int
    vmaf: float
    encoded_percent: float


@dataclass(frozen=True)
class SearchResult:
    mode: SearchResultMode
    crf: int
    vmaf: float
    encoded_percent: float


_SUMMARY_PATTERN = re.compile(
    r"\bcrf\s+(?P<crf>\d+)\s+VMAF\s+(?P<vmaf>[\d.]+)"
    r"\s+predicted video stream size.+?"
    r"\((?P<percent>[\d.]+)%\)",
    re.IGNORECASE,
)
_SUCCESS_PATTERN = re.compile(
    r"\bcrf\s+(?P<crf>\d+)\s+successful\b",
    re.IGNORECASE,
)


class AbAv1ResultParser:
    def __init__(self):
        self._candidates = {}
        self._successful_crf = None
        self._no_suitable_crf = False
        self._other_terminal_error = False

    @property
    def candidates(self):
        return tuple(self._candidates.values())

    def feed(self, line):
        summary_match = _SUMMARY_PATTERN.search(line)
        if summary_match:
            candidate = CrfCandidate(
                crf=int(summary_match.group("crf")),
                vmaf=float(summary_match.group("vmaf")),
                encoded_percent=float(summary_match.group("percent")),
            )
            if self._candidates.get(candidate.crf) == candidate:
                return None
            self._candidates[candidate.crf] = candidate
            return candidate

        success_match = _SUCCESS_PATTERN.search(line)
        if success_match:
            self._successful_crf = int(success_match.group("crf"))

        normalized = line.strip().casefold()
        if "failed to find a suitable crf" in normalized:
            self._no_suitable_crf = True
        elif normalized.startswith("error:"):
            self._other_terminal_error = True

        return None

    def finish(self, return_code, target_vmaf):
        if return_code == 0 and self._successful_crf is not None:
            candidate = self._candidates.get(self._successful_crf)
            if candidate is None:
                return None
            return SearchResult(
                mode=SearchResultMode.SUCCESS,
                crf=candidate.crf,
                vmaf=candidate.vmaf,
                encoded_percent=candidate.encoded_percent,
            )

        if (
            return_code != 0
            and self._no_suitable_crf
            and not self._other_terminal_error
        ):
            qualifying = [
                candidate
                for candidate in self._candidates.values()
                if candidate.vmaf >= target_vmaf
            ]
            if not qualifying:
                return None
            candidate = max(qualifying, key=lambda item: item.crf)
            return SearchResult(
                mode=SearchResultMode.QUALITY_FALLBACK,
                crf=candidate.crf,
                vmaf=candidate.vmaf,
                encoded_percent=candidate.encoded_percent,
            )

        return None
