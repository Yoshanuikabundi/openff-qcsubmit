"""
Components to expand stereochemistry and tautomeric states of molecules.
"""
from typing import List, Tuple, Union

from openforcefield.topology import Molecule
from openforcefield.utils.toolkits import OpenEyeToolkitWrapper, RDKitToolkitWrapper
from qcsubmit.datasets import ComponentResult

from .base_component import CustomWorkflowComponent, ToolkitValidator


class EnumerateTautomers(ToolkitValidator, CustomWorkflowComponent):
    """
    Enumerate the tautomers of a molecule using the backend toolkits through the OFFTK.

    Attributes:
        max_tautomers: int, default=20
            The maximum amount of tautomers to be made by the component per molecule.
        toolkit: str, default='openeye'
            The backend toolkit to be used by the OFFTK.

    Note:
        The provenance information and toolkit settings are handled by the
        [ToolkitValidator][qcsubmit.workflow_components.base_component.ToolkitValidator] mixin.
    """

    component_name = "EnumerateTautomers"
    component_description = "Enumerate the tautomers of a molecule if possible, if none are found return the input."
    component_fail_message = "The molecule tautomers could not be enumerated."

    # custom settings for the class
    max_tautomers: int = 20
    skip_unique_check: bool = False  # This component makes new molecules

    _processes = None

    def _apply(self, molecules: List[Molecule]) -> ComponentResult:
        """
        Enumerate tautomers of the input molecule if no tautomers are found only the input molecule is returned.

         Parameters:
            molecules: The list of molecules the component should be applied on.

        Returns:
            A [ComponentResult][qcsubmit.datasets.ComponentResult] instance containing information about the molecules
            that passed and were filtered by the component and details about the component which generated the result.
        """

        toolkit = self._toolkits[self.toolkit]()

        result = self._create_result(skip_unique_check=self.skip_unique_check)

        for molecule in molecules:
            try:
                tautomers = molecule.enumerate_tautomers(
                    max_states=self.max_tautomers, toolkit_registry=toolkit
                )

                if len(tautomers) == 0:
                    result.add_molecule(molecule)
                else:
                    for tautomer in tautomers:
                        result.add_molecule(tautomer)

            except Exception:
                result.filter_molecule(molecule)

        return result


class EnumerateStereoisomers(ToolkitValidator, CustomWorkflowComponent):
    """
    Enumerate the stereo centers and bonds of a molecule using the backend toolkits through the OFFTK.

    Attributes:
        undefined_only: bool, default=False
            If we should only enumerate undefined stereo centers and bonds or not.
        max_isomers: int, default=20
            The maximum amount of isomers to be generated by the component.
        rationalise: bool, default=True
            Try and generate a conformer for the molecule to rationalise it.
        include_input: bool, default=True
            If the input molecule should be included in the result or not.
        toolkit: str, default='openeye'
            The backend toolkit to be used by the OFFTK.

    Note:
        The provenance information and toolkit settings are handled by the
        [ToolkitValidator][qcsubmit.workflow_components.base_component.ToolkitValidator] mixin.
    """

    component_name = "EnumerateStereoisomers"
    component_description = (
        "Enumerate the stereo centers and bonds of the molecule if possible."
    )
    component_fail_message = (
        "The molecules stereo centers or bonds could not be enumerated"
    )

    undefined_only: bool = False
    max_isomers: int = 20
    rationalise: bool = True
    include_input: bool = False
    skip_unique_check: bool = False

    _processes = None

    cache: Union[OpenEyeToolkitWrapper, RDKitToolkitWrapper, None] = None

    def _apply_init(self, result: ComponentResult) -> None:

        self.cache = self._toolkits[self.toolkit]()

    def _apply_finalize(self, result: ComponentResult) -> None:

        self.cache = None

    def _apply(
        self, molecules: List[Molecule]
    ) -> Tuple[ComponentResult, List[Molecule]]:
        """
        Enumerate stereo centers and bonds of the input molecule if no isomers are found only the input molecule is
        returned.

        Parameters:
            molecules: The list of molecules the component should be applied on.

        Returns:
            A [ComponentResult][qcsubmit.datasets.ComponentResult] instance containing information about the molecules
            that passed and were filtered by the component and details about the component which generated the result.
        """

        toolkit = self.cache

        result = self._create_result(skip_unique_check=self.skip_unique_check)

        for molecule in molecules:
            try:
                isomers = molecule.enumerate_stereoisomers(
                    undefined_only=self.undefined_only,
                    max_isomers=self.max_isomers,
                    rationalise=self.rationalise,
                    toolkit_registry=toolkit,
                )

                if len(isomers) == 0 or self.include_input:
                    result.add_molecule(molecule)
                else:
                    for isomer in isomers:
                        result.add_molecule(isomer)

            except Exception:
                result.filter_molecule(molecule)

        return result


class EnumerateProtomers(ToolkitValidator, CustomWorkflowComponent):
    """
    Enumerate the formal charges of the input molecule using the backend toolkits through the OFFTK.

    Note:
        Only Openeye is supported so far.
    """

    component_name = "EnumerateProtomers"
    component_description = "Enumerate the protomers of the molecule if possible."
    component_fail_message = "The molecules formal charges could not be enumerated possibly due to a missing toolkit."

    # restrict the allowed toolkits for this module
    toolkit = "openeye"
    _toolkits = {"openeye": OpenEyeToolkitWrapper}

    max_states: int = 10

    cache: bool = False
    skip_unique_check: bool = True  # This component makes new molecules

    _processes = None

    def _apply_init(self, result: ComponentResult) -> None:

        from openforcefield.utils.toolkits import OpenEyeToolkitWrapper

        self.has_oe = OpenEyeToolkitWrapper.is_available()

    def _apply_finalize(self, result: ComponentResult) -> None:

        pass

    def _apply(self, molecules: List[Molecule]) -> ComponentResult:
        """
        Enumerate the formal charges of the molecule if possible if not only the input molecule is returned.

        Parameters:
            molecules: The list of molecules the component should be applied on.

        Returns:
            A [ComponentResult][qcsubmit.datasets.ComponentResult] instance containing information about the molecules
            that passed and were filtered by the component and details about the component which generated the result.

        Important:
            This is only possible using Openeye so far, if openeye is not available this step will fail.
        """

        result = self._create_result(skip_unique_check=self.skip_unique_check)

        has_oe = self.cache

        # must have openeye to use this feature
        if has_oe:

            for molecule in molecules:
                try:
                    protomers = molecule.enumerate_protomers(max_states=self.max_states)

                    if len(protomers) == 0:
                        result.add_molecule(molecule)

                    else:
                        for protomer in protomers:
                            result.add_molecule(protomer)

                except Exception:
                    result.filter_molecule(molecule)
        else:
            result.filtered = molecules

        return result
