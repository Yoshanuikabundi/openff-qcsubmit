"""
Components to expand stereochemistry and tautomeric states of molecules.
"""
from typing import List

from openff.toolkit.topology import Molecule
from openff.toolkit.utils.toolkits import OpenEyeToolkitWrapper
from pydantic import Field
from typing_extensions import Literal

from openff.qcsubmit.common_structures import ComponentProperties
from openff.qcsubmit.datasets import ComponentResult
from openff.qcsubmit.utils import check_missing_stereo
from openff.qcsubmit.workflow_components.base_component import (
    CustomWorkflowComponent,
    ToolkitValidator,
)


class EnumerateTautomers(ToolkitValidator, CustomWorkflowComponent):
    """
    Enumerate the tautomers of a molecule using the backend toolkits through the OFFTK.
    """

    type: Literal["EnumerateTautomers"] = "EnumerateTautomers"
    # custom settings for the class
    max_tautomers: int = Field(
        20, description="The maximum number of tautomers that should be generated."
    )

    @classmethod
    def description(cls) -> str:
        return "Enumerate the tautomers of a molecule if possible, returning the input plus any new molecules."

    @classmethod
    def fail_reason(cls) -> str:
        return "The molecule tautomers could not be enumerated."

    @classmethod
    def properties(cls) -> ComponentProperties:
        return ComponentProperties(process_parallel=True, produces_duplicates=True)

    def _apply_init(self, result: ComponentResult) -> None:
        """
        Here we load up the toolkit backend into the _cache.
        """
        self._cache["toolkit"] = self._toolkits[self.toolkit]()

    def _apply(self, molecules: List[Molecule]) -> ComponentResult:
        """
        Enumerate tautomers of the input molecule.

        The input molecules tautomers are enumerated using the desired backend toolkit and are returned along with the input molecule.

         Parameters:
            molecules: The list of molecules the component should be applied on.

        Returns:
            A [ComponentResult][qcsubmit.datasets.ComponentResult] instance containing information about the molecules
            that passed and were filtered by the component and details about the component which generated the result.
        """

        toolkit = self._cache["toolkit"]

        result = self._create_result()

        for molecule in molecules:
            try:
                tautomers = molecule.enumerate_tautomers(
                    max_states=self.max_tautomers, toolkit_registry=toolkit
                )
                for tautomer in tautomers:
                    result.add_molecule(tautomer)
                # add the input molecule
                result.add_molecule(molecule=molecule)

            except Exception:
                result.filter_molecule(molecule)

        return result


class EnumerateStereoisomers(ToolkitValidator, CustomWorkflowComponent):
    """
    Enumerate the stereo centers and bonds of a molecule using the backend toolkits through the OFFTK, only well defined
    molecules are returned by this component, this is check via a OFFTK round trip.
    """

    type: Literal["EnumerateStereoisomers"] = "EnumerateStereoisomers"
    undefined_only: bool = Field(
        False,
        description="If we should only enumerate parts of the molecule with undefined stereochemistry or all stereochemistry.",
    )
    max_isomers: int = Field(
        20, description="The maximum number of stereoisomers to be generated."
    )
    rationalise: bool = Field(
        True,
        description="If we should check that the resulting molecules are physically possible by attempting to generate conformers for them.",
    )

    @classmethod
    def description(cls) -> str:
        return "Enumerate the stereo centers and bonds of the molecule, returing the input molecule if valid and any new molecules."

    @classmethod
    def fail_reason(cls) -> str:
        return "The molecules stereo centers or bonds could not be enumerated."

    @classmethod
    def properties(cls) -> ComponentProperties:
        return ComponentProperties(process_parallel=True, produces_duplicates=True)

    def _apply_init(self, result: ComponentResult) -> None:

        self._cache["toolkit"] = self._toolkits[self.toolkit]()

    def _apply(self, molecules: List[Molecule]) -> ComponentResult:
        """
        Enumerate stereo centers and bonds of the input molecule

        Parameters:
            molecules: The list of molecules the component should be applied on.

        Returns:
            A [ComponentResult][qcsubmit.datasets.ComponentResult] instance containing information about the molecules
            that passed and were filtered by the component and details about the component which generated the result.
        """

        toolkit = self._cache["toolkit"]

        result = self._create_result()

        for molecule in molecules:
            try:
                isomers = molecule.enumerate_stereoisomers(
                    undefined_only=self.undefined_only,
                    max_isomers=self.max_isomers,
                    rationalise=self.rationalise,
                    toolkit_registry=toolkit,
                )

                # now check that each molecule is well defined
                for isomer in isomers:
                    if not check_missing_stereo(isomer):
                        result.add_molecule(isomer)

                # now check the input
                # rationalise if needed
                if self.rationalise:
                    molecule.generate_conformers(n_conformers=1)
                if not check_missing_stereo(molecule):
                    result.add_molecule(molecule)

            except Exception:
                result.filter_molecule(molecule)

        return result


class EnumerateProtomers(ToolkitValidator, CustomWorkflowComponent):
    """
    Enumerate the formal charges of the input molecule using the backend toolkits through the OFFTK.

    Important:
        Only Openeye is supported so far.
    """

    type: Literal["EnumerateProtomers"] = "EnumerateProtomers"
    # restrict the allowed toolkits for this module
    toolkit = "openeye"
    _toolkits = {"openeye": OpenEyeToolkitWrapper}

    max_states: int = Field(
        10, description="The maximum number of states that should be generated."
    )

    @classmethod
    def description(cls) -> str:
        return "Enumerate the protomers of the molecule, returning the input molecule and any new molecules."

    @classmethod
    def fail_reason(cls) -> str:
        return "The molecules formal charges could not be enumerated possibly due to a missing toolkit."

    @classmethod
    def properties(cls) -> ComponentProperties:
        return ComponentProperties(process_parallel=True, produces_duplicates=True)

    def _apply_init(self, result: ComponentResult) -> None:

        self._cache["toolkit"] = self._toolkits[self.toolkit]()

    def _apply(self, molecules: List[Molecule]) -> ComponentResult:
        """
        Enumerate the formal charges of the molecule.

        Parameters:
            molecules: The list of molecules the component should be applied on.

        Returns:
            A [ComponentResult][qcsubmit.datasets.ComponentResult] instance containing information about the molecules
            that passed and were filtered by the component and details about the component which generated the result.

        Important:
            This is only possible using Openeye so far, if openeye is not available this step will fail.
        """

        result = self._create_result()

        has_oe = self._cache["toolkit"]

        # must have openeye to use this feature
        if has_oe:

            for molecule in molecules:
                try:
                    protomers = molecule.enumerate_protomers(max_states=self.max_states)

                    for protomer in protomers:
                        result.add_molecule(protomer)
                    result.add_molecule(molecule)

                except Exception:
                    result.filter_molecule(molecule)

            return result

        else:
            for molecule in molecules:
                result.filter_molecule(molecule)

            return result
