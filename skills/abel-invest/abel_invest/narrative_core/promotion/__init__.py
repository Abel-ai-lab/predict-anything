"""Public facade for Abel Invest strategy promotion."""

from __future__ import annotations

from .constants import *  # noqa: F403
from .models import (
    PromotionHostedPaperContractRequired,
    PromotionHostedPaperRewriteRequired,
    PromotionPackagedFile,
    PromotionResult,
)
from .orchestrator import (
    _collect_hosted_paper_dependency_scan,
    _trade_log_oracle_facts,
    _validate_agent_paper_signal_contract,
    _write_hosted_paper_contract_request,
    prepare_promotion,
)
from .packaging import (
    _report_packaged_files,
    _validate_packaged_research_evidence_sources,
)
from .paper.smoke import _paper_smoke_context, _run_edge_paper_run_one_smoke
from .paper.trace import PROMOTION_TAIL_TRACE_FILENAME
from .report import _report_paper_execution_profile
from .source_scan import (
    paper_signal_design_facts as _paper_signal_design_facts,
    source_temporal_dependency_facts as _source_temporal_dependency_facts,
)

__all__ = [
    "PromotionHostedPaperContractRequired",
    "PromotionHostedPaperRewriteRequired",
    "PromotionPackagedFile",
    "PromotionResult",
    "prepare_promotion",
    *[
        name
        for name in globals()
        if name.startswith("PROMOTION_") or name == "LOCAL_RUNTIME_STATE_DIR"
    ],
]
