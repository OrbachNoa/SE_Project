from __future__ import annotations

from typing import Iterable, List, Optional

from .InputValidator import IInputValidator
from .ValidationResult import ValidationResult


class ValidatorPipeline:
    """Executes a sequence of registered validators and aggregates their results."""

    def __init__(self, validators: Optional[Iterable[IInputValidator]] = None) -> None:
        """Initializes the pipeline optionally with a predefined list of validators."""
        self._validators: List[IInputValidator] = list(validators) if validators else []

    def add(self, validator: IInputValidator) -> None:
        """Registers a new validator to the end of the pipeline."""
        self._validators.append(validator)

    def validate(self, data: List[str], fail_fast: bool = False) -> ValidationResult:
        """Runs registered validators against the input data and optionally stops at the first error if fail_fast is True."""
        
        # Create a central result object to aggregate all validation errors
        aggregated = ValidationResult()
        # Iterate over all registered validators in the pipeline
        for validator in self._validators:
            # Run the current validator on the data and get its partial result
            partial = validator.validate_as_result(data)
            # Merge any found errors into our central result object
            aggregated.merge(partial)
            # If fail_fast is enabled and an error was already found
            if fail_fast and not aggregated.is_valid:
                # Stop the loop to prevent running subsequent validators
                break

        # Return the final result, which is valid only if no errors were found
        return aggregated