from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Union, Dict, Any


class AgentAdapter(ABC):
	"""
	Adapter contract for invoking an AI agent with a text prompt.

	Implementations should talk to local models or remote HTTP services and
	return either a plain string or a dict with an "output" field.
	"""

	@abstractmethod
	def invoke(self, prompt: str) -> Union[str, Dict[str, Any]]:
		"""Invoke the agent with a single text prompt."""
		raise NotImplementedError


class MediaAnalyzerAdapter(ABC):
	"""
	Adapter contract for media/file analysis pipelines.

	Implementations analyze a given file and return a structured dict, e.g.
	{"toxicity": str, "suggestions": list[str], "report": str, "pdf_path": str, ...}
	"""

	@abstractmethod
	def analyze_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
		"""Analyze a local file of a given type (e.g., text|audio|video)."""
		raise NotImplementedError

