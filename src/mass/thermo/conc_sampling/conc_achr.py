# -*- coding: utf-8 -*-
"""Provides concentration sampling through an ACHR sampler.

Based on sampling implementations in :mod:`cobra.sampling.achr`

"""
import numpy as np

import pandas as pd

from mass.thermo.conc_sampling.conc_hr_sampler import ConcHRSampler, step


class ConcACHRSampler(ConcHRSampler):
    """Artificial Centering Hit-and-Run sampler for concentration sampling.

    A sampler with low memory footprint and good convergence :cite:`KS98`.

    Notes
    -----
    ACHR generates samples by choosing new directions from the sampling space's
    center and the warmup points. The implementation used here is the similar
    as in the Python :mod:`cobra` package.

    This implementation uses only the initial warmup points to generate new
    directions and not any other previous iterates. This usually gives better
    mixing since the startup points are chosen to span the space in a wide
    manner. This also makes the generated sampling chain quasi-markovian since
    the center converges rapidly.

    Memory usage is roughly in the order of::

        (number included reactions + number included metabolites)^2

    due to the required nullspace matrices and warmup points. So large
    models easily take up a few GB of RAM.

    Parameters
    ----------
    concentration_solver : ConcSolver
        The :class:`.ConcSolver` to use in generating samples.
    thinning : int
        The thinning factor for the generated sampling chain as a positive
        ``int`` > 0. A thinning factor of 10 means samples are returned every
        10 steps.
    nproj : int or None
        A positive ``int`` > 0 indicating how often to reporject the sampling
        point into the feasibility space. Avoids numerical issues at the cost
        of lower sampling. If ``None`` then the value is determined via the
        following::

            nproj = int(min(len(self.concentration_solver.variables)**3, 1e6))

        Default is ``None``
    seed : int or None
        A positive ``int`` > 0 indiciating random number seed that should be
        used. If ``None`` provided, the current time stamp is used.

        Default is ``None``.

    Attributes
    ----------
    concentration_solver : ConcSolver
        The :class:`.ConcSolver` used to generate samples.
    feasibility_tol : float
        The tolerance used for checking equalities feasibility.
    bounds_tol : float
        The tolerance used for checking bounds feasibility.
    thinning : int
        The currently used thinning factor.
    n_samples : int
        The total number of samples that have been generated by this
        sampler instance.
    retries : int
        The overall of sampling retries the sampler has observed. Larger
        values indicate numerical instabilities.
    problem : collections.namedtuple
        A :class:`~collections.namedtuple` whose attributes define the entire
        sampling problem in matrix form. See docstring of
        :class:`~cobra.sampling.hr_sampler.Problem` for more information.
    warmup : numpy.matrix
        A matrix of with as many columns as variables in the model of the
        :class:`.ConcSolver` and more than 3 rows containing a warmup
        sample in each row. ``None`` if no warmup points have been generated
        yet.
    nproj : int
        How often to reproject the sampling point into the feasibility space.

    """

    def __init__(self, concentration_solver, thinning=100, nproj=None, seed=None):
        """Initialize a new ConcACHRSampler."""
        super(ConcACHRSampler, self).__init__(
            concentration_solver, thinning, nproj=nproj, seed=seed
        )
        self.generate_cva_warmup()
        self.prev = self.center = self.warmup.mean(axis=0)
        np.random.seed(self.seed)

    def sample(self, n, concs=True):
        """Generate a set of samples.

        This is the basic sampling function for all hit-and-run samplers.

        Notes
        -----
        Performance of this function linearly depends on the number
        of variables in the model of the :class:`.ConcSolver`
        and the thinning factor.

        Parameters
        ----------
        n : int
            The number of samples that are generated at once.
        concs : bool
            Whether to return concentrations or the internal solver variables.
            If ``False`` will return a variable for each metabolite and
            reaction equilibrium constant as well as all additional variables
            that may have been defined in the model of the
            :class:`.ConcSolver`.

        Returns
        -------
        numpy.matrix
            A matrix with ``n`` rows, each containing a concentration sample.

        """
        samples = np.zeros((n, self.warmup.shape[1]))

        for i in range(1, self.thinning * n + 1):
            self.__single_iteration()

            if i % self.thinning == 0:
                samples[
                    i // self.thinning - 1,
                ] = self.prev

        names = [v.name for v in self.concentration_solver.variables]
        df = pd.DataFrame(samples, columns=names)
        # Map from logspace back to linspace
        df = df.apply(np.exp)

        if concs:
            df = df.loc[:, self.concentration_solver.included_metabolites]

        return df

    def __single_iteration(self):
        """Perform a single iteration of sampling.

        Warnings
        --------
        This method is intended for internal use only.

        """
        pi = np.random.randint(self.n_warmup)

        # Mix in the original warmup points to not get stuck
        delta = (
            self.warmup[
                pi,
            ]
            - self.center
        )
        self.prev = step(self, self.prev, delta)

        self.center = (self.n_samples * self.center) / (
            self.n_samples + 1
        ) + self.prev / (self.n_samples + 1)
        self.n_samples += 1


__all__ = ("ConcACHRSampler",)
