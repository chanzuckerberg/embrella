"""
Legacy workflow views and templates.

This package contains deprecated code using old patterns:
- Django server-side template rendering
- Old agent-based job submission (not processor-based)

DO NOT copy these patterns for new code. Use modern APIs instead:
- workflow/views/execution_api.py - Modern processor-based execution
- workflow/processors/ - Processor system
"""
