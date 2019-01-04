# -*- coding: utf-8 -*-
"""TODO Module Docstrings."""
from __future__ import absolute_import

import re
from warnings import warn

from six import integer_types, string_types

from cobra.core.species import Species

from mass.util import expressions

# Precompiled regular expression for element parsing
ELEMENT_RE = re.compile("([A-Z][a-z]?)([0-9.]+[0-9.]?|(?=[A-Z])?)")


class MassMetabolite(Species):
    """Class for holding information regarding a metabolite.

    Parameters
    ----------
    id: str
        The identifier associated with the MassMetabolite.
    name: str, optional
        A human readable name for the metabolite.

    Attributes
    ----------
    formula: str, optional
        Chemical formula associated with the metabolite.
    charge: float, optional
        The charge number associated with the metabolite.
    compartment: str, optional
        The compartment where the metabolite is located.

    """

    def __init__(self, id=None, name="", formula=None, charge=None,
                 compartment=None):
        """Initialize the MassMetabolite Object."""
        # Check inputs to ensure they are they correct types.
        if not isinstance(id, string_types) and id is not None:
            raise TypeError("id must be a str")
        if not isinstance(name, string_types) and name is not None:
            raise TypeError("name must be a str")
        if not isinstance(formula, string_types) and formula is not None:
            raise TypeError("formula must be a str")
        if not isinstance(charge, (integer_types, float)) and \
           charge is not None:
            raise TypeError("charge must be an int or float")
        if not isinstance(compartment, string_types) and \
           compartment is not None:
            raise TypeError("compartment must be a str")

        Species.__init__(self, id, name)
        # Chemical formula and charge number of the metabolite
        self.formula = formula
        self.charge = charge
        # Compartment where the metabolite is located
        self.compartment = compartment
        # Inital concentration of the metabolite
        self._initial_condition = None
        # Gibbs energy of formation of the metabolite
        self._gibbs_formation_energy = None

        # For cobra compatibility
        self._constraint_sense = "E"
        self._bound = 0.

    # Public
    @property
    def elements(self):
        """Generate a dictionary of elements in the metabolite formula.

        Returns
        -------
        composition: dictionary
            A dictionary where the elements are the keys and their coefficients
            given as integers are the values.

        Notes
        -----
        Enzyme and macromolecule moieties can be recognized by enclosing them
            in brackets (e.g. [ENZYME]) when defining  the chemical formula.
            They are treated as one entity and therefore are counted once.

        """
        tmp_formula = self.formula
        if tmp_formula is None:
            return {}
        if "*" in tmp_formula:
            warn("invalid character '*' found in formula '{0}'"
                 .format(self.formula))
            tmp_formula = tmp_formula.replace("*", "")
        composition = {}
        if "[" in tmp_formula and "]" in tmp_formula:
            s = tmp_formula.index("[")
            e = tmp_formula.index("]") + 1
            moiety = tmp_formula[s:e][1:-1]
            composition[moiety] = 1
            tmp_formula = tmp_formula.replace(tmp_formula[s:e], "")

        for (element, count) in ELEMENT_RE.findall(tmp_formula):
            if count == "":
                count = 1
            else:
                try:
                    count = float(count)
                    if count == int(count):
                        count = int(count)
                    else:
                        warn("{0} is not an integer (in formula {1})"
                             .format(count, self.formula))
                except ValueError:
                    warn("failed to parse {0} (in formula {1})"
                         .format(count, self.formula))
                    return None
            if element in composition:
                composition[element] += count
            else:
                composition[element] = count

        return composition

    @property
    def initial_condition(self):
        """Return the initial condition of the metabolite.

        Warnings
        --------
        This method returns the initial condition stored inside the
            MassMetabolite. This initial condition does not necessarily return
            the initial condition stored inside the MassModel.
        """
        return getattr(self, "_initial_condition")

    @initial_condition.setter
    def initial_condition(self, value):
        """Set the initial condition of the metabolite.

        Warnings
        --------
        Initial conditions of metabolites cannot be negative.
        """
        if not isinstance(value, (integer_types, float)) and \
           value is not None:
            raise TypeError("Must be an int or float")
        elif value is None:
            pass
        elif value < 0.:
            raise ValueError("Must be a non-negative number")
        self._initial_condition = value

    # TODO Add in when thermodynamics are finished
    # @property
    # def gibbs_formation_energy(self):
    #     """Return the Gibbs formation energy of the metabolite."""
    #     return getattr(self, "_gibbs_formation_energy")
    #
    # @gibbs_formation_energy.setter
    # def gibbs_formation_energy(self, value):
    #     """Set the Gibbs formation energy for the metabolite."""
    #     if not isinstance(value, (integer_types, float)) and \
    #        value is not None:
    #         raise TypeError("Must be an int or float")
    #     self._gibbs_formation_energy = value

    @property
    def ordinary_differential_equation(self):
        """Return a sympy expression of the metabolite's associated ODE.

        Will return None if metabolite is not associated with a MassReaction.
        """
        return expressions.generate_ode(self)

    @property
    def formula_weight(self):
        """Calculate and return the formula weight of the metabolite.

        Does not consider any moeties enclosed in brackets.
        """
        try:
            return sum([count * ELEMENTS_AND_MOLECULAR_WEIGHTS[element]
                        for element, count in self.elements.items()])
        except KeyError as e:
            warn("The element {0} does not appear in the periodic table"
                 .format(e))

    # Shorthands
    @property
    def ic(self):
        """Shorthand getter for the initial condition."""
        return getattr(self, "_initial_condition")

    @ic.setter
    def ic(self, value):
        """Shorthand setter for the initial condition."""
        self.initial_condition = value

    # TODO Add in when thermodynamics are finished
    # @property
    # def gfe(self):
    #     """Shorthand getter for the Gibb's energy of formation."""
    #     return self.gibbs_formation_energy
    #
    # @gfe.setter
    # def gfe(self, value):
    #     """Shorthand setter for the Gibb's energy of formation."""
    #     self.gibbs_formation_energy = value

    @property
    def ode(self):
        """Shorthand getter for the metabolite's associated ODE."""
        return self.ordinary_differential_equation

    def remove_from_model(self, destructive=False):
        """Remove the metabolite's association from its MassModel.

        The change is reverted back upon when using the MassModel as a context.

        Parameters
        ----------
        destructive: bool, optional
            If False, the metabolite is removed from all associated reactions.
            If True, all associated reactions are remove from the MassModel.

        """
        return self._model.remove_metabolites(self, destructive)

    # Internal
    def _set_id_with_model(self, value):
        """Set the id of the MassMetabolite to the assoicated MassModel."""
        if value in self._model.metabolites:
            raise ValueError("The MassModel already contains a MassMetabolite"
                             " with the id:{0}".format(value))

    def _repr_html_(self):
        """HTML representation of the overview for the MassMetabolite."""
        return """
        <table>
            <tr>
                <td><strong>MassMetabolite identifier</strong></td>
                <td>{id}</td>
            </tr><tr>
                <td><strong>Name</strong></td>
                <td>{name}</td>
            </tr><tr>
                <td><strong>Memory address</strong></td>
                <td>{address}</td>
            </tr><tr>
                <td><strong>Formula</strong></td>
                <td>{formula}</td>
            </tr><tr>
                <td><strong>Compartment</strong></td>
                <td>{compartment}</td>
            </tr><tr>
                <td><strong>Initial Condition</strong></td>
                <td>{ic}</td>
            </tr><tr>
                <td><strong>Gibbs formation energy</strong></td>
                <td>{gibbs}</td>
            </tr><tr>
                <td><strong>In {n_reactions} reaction(s)</strong></td>
                <td>{reactions}</td>
            </tr>
        <table>""".format(id=self.id, name=self.name, formula=self.formula,
                          address='0x0%x' % id(self),
                          compartment=self.compartment,
                          ic=self._initial_condition,
                          gibbs=self._gibbs_formation_energy,
                          n_reactions=len(self.reactions),
                          reactions='. '.join(r.id for r in self.reactions))


ELEMENTS_AND_MOLECULAR_WEIGHTS = {
    'H': 1.007940,
    'He': 4.002602,
    'Li': 6.941000,
    'Be': 9.012182,
    'B': 10.811000,
    'C': 12.010700,
    'N': 14.006700,
    'O': 15.999400,
    'F': 18.998403,
    'Ne': 20.179700,
    'Na': 22.989770,
    'Mg': 24.305000,
    'Al': 26.981538,
    'Si': 28.085500,
    'P': 30.973761,
    'S': 32.065000,
    'Cl': 35.453000,
    'Ar': 39.948000,
    'K': 39.098300,
    'Ca': 40.078000,
    'Sc': 44.955910,
    'Ti': 47.867000,
    'V': 50.941500,
    'Cr': 51.996100,
    'Mn': 54.938049,
    'Fe': 55.845000,
    'Co': 58.933200,
    'Ni': 58.693400,
    'Cu': 63.546000,
    'Zn': 65.409000,
    'Ga': 69.723000,
    'Ge': 72.640000,
    'As': 74.921600,
    'Se': 78.960000,
    'Br': 79.904000,
    'Kr': 83.798000,
    'Rb': 85.467800,
    'Sr': 87.620000,
    'Y': 88.905850,
    'Zr': 91.224000,
    'Nb': 92.906380,
    'Mo': 95.940000,
    'Tc': 98.000000,
    'Ru': 101.070000,
    'Rh': 102.905500,
    'Pd': 106.420000,
    'Ag': 107.868200,
    'Cd': 112.411000,
    'In': 114.818000,
    'Sn': 118.710000,
    'Sb': 121.760000,
    'Te': 127.600000,
    'I': 126.904470,
    'Xe': 131.293000,
    'Cs': 132.905450,
    'Ba': 137.327000,
    'La': 138.905500,
    'Ce': 140.116000,
    'Pr': 140.907650,
    'Nd': 144.240000,
    'Pm': 145.000000,
    'Sm': 150.360000,
    'Eu': 151.964000,
    'Gd': 157.250000,
    'Tb': 158.925340,
    'Dy': 162.500000,
    'Ho': 164.930320,
    'Er': 167.259000,
    'Tm': 168.934210,
    'Yb': 173.040000,
    'Lu': 174.967000,
    'Hf': 178.490000,
    'Ta': 180.947900,
    'W': 183.840000,
    'Re': 186.207000,
    'Os': 190.230000,
    'Ir': 192.217000,
    'Pt': 195.078000,
    'Au': 196.966550,
    'Hg': 200.590000,
    'Tl': 204.383300,
    'Pb': 207.200000,
    'Bi': 208.980380,
    'Po': 209.000000,
    'At': 210.000000,
    'Rn': 222.000000,
    'Fr': 223.000000,
    'Ra': 226.000000,
    'Ac': 227.000000,
    'Th': 232.038100,
    'Pa': 231.035880,
    'U': 238.028910,
    'Np': 237.000000,
    'Pu': 244.000000,
    'Am': 243.000000,
    'Cm': 247.000000,
    'Bk': 247.000000,
    'Cf': 251.000000,
    'Es': 252.000000,
    'Fm': 257.000000,
    'Md': 258.000000,
    'No': 259.000000,
    'Lr': 262.000000,
    'Rf': 261.000000,
    'Db': 262.000000,
    'Sg': 266.000000,
    'Bh': 264.000000,
    'Hs': 277.000000,
    'Mt': 268.000000,
    'Ds': 281.000000,
    'Rg': 272.000000,
    'Cn': 285.000000,
    'Nh': 286.000000,
    'Fl': 289.000000,
    'Mc': 290.000000,
    'Lv': 293.000000,
    'Ts': 294.000000,
    'Og': 294.000000,
}
