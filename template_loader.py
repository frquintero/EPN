"""YAML frontmatter loader for templates/prompts.md.

Parses YAML frontmatter sections and extracts role templates, LLM configurations,
and provider selection logic.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


@dataclass
class RoleTemplate:
    task: Optional[str] = None
    instructions: Optional[str] = None


class PromptsRepository:
    """Repository for role templates and LLM config with provider selection."""

    def __init__(self, path: Optional[str] = None) -> None:
        if yaml is None:
            raise ImportError("PyYAML is required for template loading. Install with: pip install PyYAML")

        self.root = os.path.dirname(os.path.abspath(__file__))
        self.path = path or os.path.join(self.root, "templates", "prompts.md")
        self._loaded = False
        self._exists = False
        self._templates: Dict[str, RoleTemplate] = {}
        self._llm_configs: Dict[str, Dict] = {}  # Multiple provider configs
        self._selected_provider: str = "groq"  # Default provider
        self._sha256: Optional[str] = None
        self._initial_query: Optional[str] = None
        self._initial_query_error: Optional[str] = None
        self._frontmatter: Dict = {}

    def _compute_sha256(self, data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def load(self) -> None:
        if self._loaded:
            return
        if not os.path.exists(self.path):
            # Nothing to load; remain empty, allow fallbacks
            self._exists = False
            self._loaded = True
            return

        with open(self.path, "r", encoding="utf-8") as f:
            content = f.read()

        self._exists = True
        self._sha256 = self._compute_sha256(content)

        # Parse YAML frontmatter
        frontmatter, _ = self._parse_frontmatter(content)
        if not frontmatter:
            # Fallback to old markdown parsing for backward compatibility
            self._load_markdown_fallback(content)
            return

        self._frontmatter = frontmatter
        self._load_from_frontmatter(frontmatter)
        self._loaded = True

    def _parse_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """Parse YAML frontmatter from content. Returns (frontmatter_dict, remaining_content)."""
        if not content.startswith('---'):
            return {}, content

        # Find the end of frontmatter
        lines = content.split('\n')
        end_idx = -1
        for i, line in enumerate(lines[1:], 1):  # Skip first ---
            if line.strip() == '---':
                end_idx = i
                break

        if end_idx == -1:
            return {}, content  # No closing ---

        frontmatter_text = '\n'.join(lines[1:end_idx])
        remaining_content = '\n'.join(lines[end_idx + 1:]) if end_idx + 1 < len(lines) else ''

        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
            return frontmatter, remaining_content
        except yaml.YAMLError:
            return {}, content  # Fallback on parse error

    def _load_from_frontmatter(self, frontmatter: Dict) -> None:
        """Load templates and configs from parsed YAML frontmatter."""
        # Load role templates
        for role_name, role_data in frontmatter.items():
            if role_name in ['LLM_CONFIGS', 'LLM_CONFIG', 'SELECTED_PROVIDER', 'RUN', 'version', 'format']:
                continue  # Skip special sections

            if isinstance(role_data, dict):
                task = role_data.get('task')
                instructions = role_data.get('instructions')
                if task or instructions:
                    self._templates[role_name] = RoleTemplate(task=task, instructions=instructions)

        # Load LLM configurations
        llm_configs = frontmatter.get('LLM_CONFIGS', {})
        if llm_configs:
            self._llm_configs = llm_configs
        else:
            # Fallback to single LLM_CONFIG for backward compatibility
            llm_config = frontmatter.get('LLM_CONFIG', {})
            if llm_config:
                self._llm_configs = {'groq': llm_config}

        # Load selected provider
        selected_provider = frontmatter.get('SELECTED_PROVIDER', 'groq')
        if selected_provider in self._llm_configs:
            self._selected_provider = selected_provider

        # Load initial query
        run_section = frontmatter.get('RUN', {})
        if isinstance(run_section, dict):
            query = run_section.get('query')
            if query:
                # Remove brackets if present
                if query.startswith('[') and query.endswith(']'):
                    query = query[1:-1].strip()
                if query:
                    self._initial_query = query

    def _load_markdown_fallback(self, content: str) -> None:
        """Fallback to old markdown parsing for backward compatibility."""
        # Split into sections by role header '## <ID>' (uppercase + underscores)
        # Keep LLM_CONFIG as a special section
        pattern = re.compile(r"^##\s+([A-Z0-9_]+)\s*$", re.MULTILINE)
        sections = list(pattern.finditer(content))
        for i, head in enumerate(sections):
            role_id = head.group(1).strip()
            start = head.end()
            end = sections[i + 1].start() if i + 1 < len(sections) else len(content)
            body = content[start:end]

            if role_id == "LLM_CONFIG":
                self._llm_configs = {'groq': self._parse_llm_overrides(body)}
                continue
            if role_id == "RUN":
                q, err = self._parse_initial_query(body)
                if err:
                    self._initial_query_error = err
                elif q is not None:
                    self._initial_query = q
                continue

            role_template = self._parse_role_template(body)
            self._templates[role_id] = role_template

    def _parse_subsection(self, body: str, title: str) -> Optional[str]:
        # Find '### {title}' and capture text until next '###' or end
        rx = re.compile(rf"^###\s+{re.escape(title)}\s*$", re.MULTILINE)
        m = rx.search(body)
        if not m:
            return None
        start = m.end()
        # Next subsection or end of section
        m2 = re.search(r"^###\s+", body[start:], re.MULTILINE)
        if m2:
            end = start + m2.start()
        else:
            end = len(body)
        text = body[start:end].strip()
        return text if text else None

    def _parse_role_template(self, body: str) -> RoleTemplate:
        task = self._parse_subsection(body, "Task")
        instructions = self._parse_subsection(body, "Instructions")
        # Limits subsections are ignored by code (templates are authoritative)
        return RoleTemplate(task=task, instructions=instructions)

    def _parse_llm_overrides(self, body: str) -> Dict[str, object]:
        # Accept simple YAML-like lines: key: value
        overrides: Dict[str, object] = {}
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = [part.strip() for part in line.split(":", 1)]
            # Cast basic types
            if key in {"temperature"}:
                try:
                    overrides[key] = float(value)
                    continue
                except ValueError:
                    pass
            if key in {"max_tokens"}:
                try:
                    overrides[key] = int(value)
                    continue
                except ValueError:
                    pass
            overrides[key] = value
        # Normalize response_format if provided as a simple token
        rf = overrides.get("response_format")
        if isinstance(rf, str):
            if rf.lower() == "json_object":
                overrides["response_format"] = {"type": "json_object"}
        # Only keep known keys used by llm_config
        allowed = {"provider", "model", "temperature", "max_tokens", "reasoning_effort", "response_format"}
        return {k: v for k, v in overrides.items() if k in allowed}

    def _parse_initial_query(self, body: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse initial query from RUN section.

        Rules:
        - If a non-empty value is provided, it must be bracketed: query: [ ... ]
        - If empty (e.g., "query:"), treat as no override (no error).
        - If non-empty and not bracketed, return an error.
        """
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' not in line:
                continue
            key, value = [part.strip() for part in line.split(':', 1)]
            if key.lower() == 'query':
                if not value:
                    return None, None
                # Must be [ ... ] on the same line
                if value.startswith('[') and value.endswith(']') and len(value) >= 2:
                    inner = value[1:-1].strip()
                    if inner:
                        return inner, None
                    # Empty brackets mean no override
                    return None, None
                return None, "RUN.query must be provided in brackets: query: [your text]"
        return None, None

    def get_template(self, role_id: str) -> Optional[RoleTemplate]:
        """Return template for the exact role id only (no fallback)."""
        self.load()
        return self._templates.get(role_id)

    def get_raw_template(self, role_id: str) -> Optional[RoleTemplate]:
        self.load()
        return self._templates.get(role_id)

    def get_llm_overrides(self) -> Dict[str, object]:
        """Return LLM config for the selected provider."""
        self.load()
        return dict(self._llm_configs.get(self._selected_provider, {}))

    def get_selected_provider(self) -> str:
        """Return the currently selected provider."""
        self.load()
        return self._selected_provider

    def get_available_providers(self) -> list[str]:
        """Return list of available providers."""
        self.load()
        return list(self._llm_configs.keys())

    def set_provider(self, provider: str) -> bool:
        """Set the active provider. Returns True if successful."""
        self.load()
        if provider in self._llm_configs:
            self._selected_provider = provider
            return True
        return False

    def get_sha256(self) -> Optional[str]:
        self.load()
        return self._sha256

    def get_initial_query(self) -> Optional[str]:
        self.load()
        if self._initial_query_error:
            raise ValueError(self._initial_query_error)
        return self._initial_query

    def has_templates(self) -> bool:
        self.load()
        return bool(self._exists)


# Singleton accessor
_repo: Optional[PromptsRepository] = None


def repo(path: Optional[str] = None) -> PromptsRepository:
    global _repo
    if _repo is None or (path is not None and _repo.path != path):
        _repo = PromptsRepository(path)
    return _repo
