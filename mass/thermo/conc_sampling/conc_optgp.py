# -*- coding: utf-8 -*-
"""Provides concentration sampling through an OptGP sampler.

Based on sampling implementations in :mod:`cobra.sampling.optgp`

"""
from multiprocessing import Pool

from cobra.sampling.hr_sampler import shared_np_array

import numpy as np

import pandas as pd

from mass.core.mass_configuration import MassConfiguration
from mass.thermo.conc_sampling.conc_hr_sampler import ConcHRSampler, step

MASSCONFIGURATION = MassConfiguration()


def mp_init(obj):
    """Initialize the multiprocessing pool."""
    global sampler
    sampler = obj


# Has to be outside the class to be usable with multiprocessing
def _sample_chain(args):
    """Sample a single chain for OptGPSampler.

    ``center`` and ``n_samples`` are updated locally and forgotten afterwards.

    Warnings
    --------
    This method is intended for internal use only.

    """
    n, idx = args
    center = sampler.center
    np.random.seed((sampler._seed + idx) % np.iinfo(np.int32).max)
    pi = np.random.randint(sampler.n_warmup)

    prev = sampler.warmup[pi, ]
    prev = step(sampler, center, prev - center, 0.95)

    n_samples = max(sampler.n_samples, 1)
    samples = np.zeros((n, center.shape[0]))

    for i in range(1, sampler.thinning * n + 1):
        pi = np.random.randint(sampler.n_warmup)
        delta = sampler.warmup[pi, ] - center

        prev = step(sampler, prev, delta)

        if sampler.problem.homogeneous and (
                n_samples * sampler.thinning % sampler.nproj == 0):
            prev = sampler._reproject(prev)
            center = sampler._reproject(center)

        if i % sampler.thinning == 0:
            samples[i // sampler.thinning - 1, ] = prev

        center = ((n_samples * center) / (n_samples + 1) +
                  prev / (n_samples + 1))
        n_samples += 1

    return (sampler.retries, samples)


class ConcOptGPSampler(ConcHRSampler):
    """A parallel optimized sampler.

    A parallel sampler with fast convergence and parallel execution
    :cite:`MHM14`.

    Notes
    -----
    The sampler is very similar to artificial centering where each process
    samples its own chain. The implementation used here is the similar
    as in the Python :mod:`cobra` package.

    Initial points are chosen randomly from the warmup points followed by a
    linear transformation that pulls the points a little bit towards the
    center of the sampling space.

    If the number of processes used is larger than the one requested,
    number of samples is adjusted to the smallest multiple of the number of
    processes larger than the requested sample number. For instance, if you
    have 3 processes and request 8 samples you will receive 9.

    Memory usage is roughly in the order of::

        (number included reactions + number included metabolites)^2

    due to the required nullspace matrices and warmup points. So large
    models easily take up a few GB of RAM. However, most of the large matrices
    are kept in shared memory. So the RAM usage is independent of the number
    of processes.

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
        of lower samplimg. If ``None`` then the value is determined via the
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

    def __init__(self, concentration_solver, processes=None, thinning=100,
                 nproj=None, seed=None):
        """Initialize a new ConcOptGPSampler."""
        super(ConcOptGPSampler, self).__init__(concentration_solver, thinning,
                                               nproj=nproj, seed=seed)
        self.generate_cva_warmup()

        if processes is None:
            self.processes = MASSCONFIGURATION.processes
        else:
            self.processes = processes

        # This maps our saved center into shared memory,
        # meaning they are synchronized across processes
        self.center = shared_np_array(
            (len(concentration_solver.variables), ), self.warmup.mean(axis=0))

    def sample(self, n, concs=True):
        """Generate a set of samples.

        This is the basic sampling function for all hit-and-run samplers.

        Notes
        -----
        Performance of this function linearly depends on the number
        of metabolites in your model and the thinning factor.

        If the number of processes is larger than one, computation is split
        across as the CPUs of your machine. This may shorten computation time.

        However, there is also overhead in setting up parallel computation so
        it is recommended to calculate large numbers of samples at once
        (``n`` > 1000).

        Parameters
        ----------
        n : int
            The number of samples that are generated at once.
        concs : boolean
            Whether to return concentrations or the internal solver variables.
            If ``False`` will return a variable for each metabolite and
            reaction Keq as well as all additional variables that may have
            been defined in the model.

        Returns
        -------
        numpy.matrix
            A matrix with ``n`` rows, each containing a concentration sample.

        """
        if self.processes > 1:
            n_process = np.ceil(n / self.processes).astype(int)
            n = n_process * self.processes

            # The cast to list is weird but not doing it gives recursion
            # limit errors, something weird going on with multiprocessing
            args = list(zip(
                [n_process] * self.processes, range(self.processes)))

            # No with statement or starmap here since Python 2.x
            # does not support it :(
            mp = Pool(self.processes, initializer=mp_init, initargs=(self,))
            results = mp.map(_sample_chain, args, chunksize=1)
            mp.close()
            mp.join()

            chains = np.vstack([r[1] for r in results])
            self.retries += sum(r[0] for r in results)
        else:
            mp_init(self)
            results = _sample_chain((n, 0))
            chains = results[1]

        # Update the global center
        self.center = (self.n_samples * self.center +
                       np.atleast_2d(chains).sum(0)) / (self.n_samples + n)
        self.n_samples += n

        names = [v.name for v in self.concentration_solver.variables]
        df = pd.DataFrame(chains, columns=names)
        # Map from logspace back to linspace
        df = df.apply(np.exp)

        if concs:
            df = df.loc[:, self.concentration_solver.included_metabolites]

        return df

    # Models can be large so don't pass them around during multiprocessing
    def __getstate__(self):
        """Return the object for serialization.
        
        Warnings
        --------
        This method is intended for internal use only.

        """
        d = dict(self.__dict__)
        del d['model']
        return d


__all__ = ("ConcOptGPSampler",)
