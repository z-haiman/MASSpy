# -*- coding: utf-8 -*-
"""TODO Module Docstrings."""
from __future__ import absolute_import

import math
from collections import OrderedDict
from collections.abc import Hashable, Iterable
from warnings import warn

from cycler import Cycler

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.axes import Axes

import numpy as np

from six import integer_types, iteritems, iterkeys, itervalues, string_types

from mass.analysis import linear
from mass.util.util import ensure_iterable

_ZERO_TOL = 1e-8
_FONTSIZES = [
    'xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large']
_LEGEND_LOCS = [
    "best", "upper right", "upper left", "lower left", "lower right", "right",
    "center left", "center right", "lower center", "upper center", "center",
    "left outside", "right outside", "lower outside", "upper outside"]

_custom_default_options = {"plot": {}, "tiled": {}}


def plot_simulation(solution, observable=None, time=None, ax=None, legend=None,
                    **kwargs):
    """Create a plot of the time profile for the given Solution object.

    Accepted ``kwargs`` are passed on to various matplotlib methods.
    Default ``kwargs`` values can be viewed via get_defaults("plot").
    See set_defaults() for a full description of the possible ``kwargs``.

    Parameters
    ----------
    solution: mass.Solution
        The mass.Solution object containing the solutions to be plotted.
    observable: str, iterable of str, optional
        A string or an iterable of strings corresponding to items to display in
        the given 'solution'. Objects can also be provided as long as their ids
        exist as keys in the given 'solution'. If None provided then all items
        in the given 'solution' are displayed.
    time: iterable, optional
        Either an iterable of two values containing the initial and final time
        points, or an iterable of values to treat as time points for the
        solutions. If None provided, the time points used in creating the
        Solution object will be used (accessed via solution.t).
    ax: matplotlib.axes.Axes, optional
        A matplotlib.pyplot.axes instance to plot the data on. If None,
        the current axis is used (accessed via plt.gca()).
    legend: tuple of length 3, str, iterable of str, optional
        If a tuple of length 3 provided, it should be of the following format:
        (list of labels, str for legend loc, str for legend fontsize), allowing
        for full control over the displayed legend.
        If providing a string, can be a single label (when plotting one line),
        the legend location, or the fontsize for the legend.
        If an iterable of strings are provided, they are assumed to be line
        labels unless they correspond to a legend location or legend fontsize.
        If legend is not None but no labels provided, default labels
        representing the keys in the solution object will be used.
        Accepted locations are standard matplotlib legend locations plus
        {"left outside", "right outside", "lower outside", "upper outside"}
        Accepted fontsize values are standard matplotlib legend fontsizes.
        Examples:
            Only legend labels: legend=["A", "B", "C"]
            Only legend properties: legend=("best", "medium")
            Labels and properties: legend=(["A", "B", "C"], "best", "medium")
    **kwargs

    Returns
    -------
    ax: matplotlib.axes.Axes
        A reference to the matplotlib.axes.Axes object used for plotting.

    See Also
    --------
    get_defaults: Default values for options
    set_defaults: Descriptions of accepted kwargs and input formats.

    """
    # Copy the solution object and validate the time input
    solution, time = _fmt_solution_and_time_input(solution, time)
    # Get observable solutions
    observable_solutions = _set_plot_observables(solution, time, observable)
    # Get current axis if none provided, otherwise check its type
    if ax is None:
        ax = plt.gca()
    if not isinstance(ax, Axes):
        raise TypeError("ax must be a matplotlib.axes Axes object.")

    # Update plot options with provided kwargs
    options = _update_kwargs("plot", **kwargs)
    # Set the plotting function.
    plot_function = _set_plot_function(ax, options["plot_function"])

    # Use the property cycler for the axis if provided
    if options["prop_cycle"] is not None:
        ax.set_prop_cycle(options["prop_cycle"])

    # Use the plotting function to plot the observable data.
    default_labels = []
    for label, sol in iteritems(observable_solutions):
        plot_function(time, sol, label=label)
        default_labels += [label]
    # Set axis options which include labels, limits, and gridlines.
    _set_axis_options(ax, options)
    # Set line colors and styles if no cycler provided.
    if options["prop_cycle"] is None:
        _set_line_properties(ax, options, len(default_labels))

    # Set the legend
    if legend is not None:
        # Filter out any leading underscores in default labels
        default_labels = [s if s[0] != "_" else s[1:] for s in default_labels]
        _set_axis_legend(ax, legend, default_labels, options)

    return ax


def plot_phase_portrait(solution, x, y, time=None, ax=None, legend=None,
                        time_poi=None, poi_labels=True, **kwargs):
    """Generate a plot of the time profile for the given Solution object.

    Accepted ``kwargs`` are passed on to various matplotlib methods.
    Default ``kwargs`` values can be viewed via get_defaults("plot").
    See set_defaults() for a full description of the possible ``kwargs``.

    Parameters
    ----------
    solution: mass.Solution
        The mass.Solution object containing the solutions to be plotted.
    x: str, iterable of str
        A string or an iterable of strings corresponding to items in
        the given 'solution' to plot as the x-axis. Objects can also be
        provided as long as their ids exist as keys in the given 'solution'.
    y: str, iterable of str
        A string or an iterable of strings corresponding to items in
        the given 'solution' to plot as the y-axis. Objects can also be
        provided as long as their ids exist as keys in the given 'solution'.
    time: iterable, optional
        Either an iterable of two values containing the initial and final time
        points, or an iterable of values to treat as time points for the
        solutions. If None provided, the time points used in creating the
        Solution object will be used (accessed via solution.t).
    ax: matplotlib.axes.Axes, optional
        A matplotlib.pyplot.axes instance to plot the data on. If None,
        the current axis is used (accessed via plt.gca()).
    legend: tuple of length 3, str, iterable of str, optional
        If a tuple of length 3 provided, it should be of the following format:
        (list of labels, str for legend loc, str for legend fontsize), allowing
        for full control over the displayed legend.
        If providing a string, can be a single label (when plotting one line),
        the legend location, or the fontsize for the legend.
        If an iterable of strings are provided, they are assumed to be line
        labels unless they correspond to a legend location or legend fontsize.
        If legend is not None but no labels provided, default labels
        representing the keys in the solution object will be used.
        Accepted locations are standard matplotlib legend locations plus
        {"left outside", "right outside", "lower outside", "upper outside"}
        Accepted fontsize values are standard matplotlib legend fontsizes.
        Examples:
            Only legend labels: legend=["A", "B", "C"]
            Only legend properties: legend=("best", "medium")
            Labels and properties: legend=(["A", "B", "C"], "best", "medium")
    time_poi: list, dict, optional
        Either an iterable of time "points of interest" (poi) to annotate, or
        a dict of time poi to annotate where keys are the time points and
        values are strings representing matplotlib recognized color for that
        time point. If None provided, only the initial and final time points
        are annotated, with default colors "red" and "blue" respectively.
    poi_labels: bool, optional
        If True, will label annotated time "points of interest" with their time
        values. Otherwise, time "points of interest" will not be labeled.
    **kwargs

    Returns
    -------
    ax: matplotlib.axes.Axes
        A reference to the matplotlib.axes.Axes object used for plotting.

    See Also
    --------
    get_defaults: Default values for options
    set_defaults: Descriptions of accepted kwargs and input formats.

    """
    # Copy the solution object and validate the time input
    solution, time = _fmt_solution_and_time_input(solution, time)
    # Get observable solutions
    x_sols = _set_plot_observables(solution, time, x)
    y_sols = _set_plot_observables(solution, time, y)
    # Get current axis if none provided, otherwise check its type
    if ax is None:
        ax = plt.gca()
    if not isinstance(ax, Axes):
        raise TypeError("ax must be a matplotlib.axes Axes object.")

    # Update plot options with provided kwargs
    options = _update_kwargs("plot", **kwargs)
    # Set the plotting function
    plot_function = _set_plot_function(ax, options["plot_function"])

    # Use the property cycler for the axis if provided
    if options["prop_cycle"] is not None:
        ax.set_prop_cycle(options["prop_cycle"])

    def find_poi_bounds(poi_bounds, key, sol):
        s_min, s_max = poi_bounds[key]
        if (s_min, s_max) == (None, None):
            s_min, s_max = (min(sol), max(sol))
        else:
            s_min, s_max = (min(s_min, min(sol)), max(s_max, max(sol)))
        poi_bounds[key] = s_min, s_max

    # Use the plotting function to plot the observable data
    default_labels = []
    poi_bounds = {"x": (None, None), "y": (None, None)}
    for x_label, x_sol in iteritems(x_sols):
        find_poi_bounds(poi_bounds, "x", x_sol)
        for y_label, y_sol in iteritems(y_sols):
            find_poi_bounds(poi_bounds, "y", y_sol)
            label = "{0} vs. {1}".format(x_label, y_label)
            plot_function(x_sol, y_sol, label=label)
            default_labels += [label]

    # Set axis options which include labels, limits, and gridlines.
    _set_axis_options(ax, options)
    # Set line colors and styles if no cycler provided.
    if options["prop_cycle"] is None:
        _set_line_properties(ax, options, len(default_labels))

    # Set the legend
    if legend is not None:
        _set_axis_legend(ax, legend, default_labels, options)

    endpoints = [time[0], time[-1]]
    _annotate_time_points_of_interest(ax, options["plot_function"], solution,
                                      x, y, time_poi, endpoints, poi_labels,
                                      poi_bounds)

    return ax


def plot_tiled_phase_portrait(solution, observable=None, time=None, ax=None,
                              time_poi=None, poi_labels=True,
                              display_data=None, empty_tiles="upper",
                              **kwargs):
    """Generate a tiled phase portrait for items in a given Solution object.

    Accepted ``kwargs`` are passed on to various matplotlib methods.
    Default ``kwargs`` values can be viewed via get_defaults("tiled").
    See set_defaults() for a full description of the possible ``kwargs``.

    Parameters
    ----------
    solution: mass.Solution
        The mass.Solution object containing the solutions to be plotted.
    observable: str, iterable of str, optional
        A string or an iterable of strings corresponding to items in the given
        'solution' to plot against each other in the tiled phase portrait.
        Objects can also be provided as long as their ids exist as keys in the
        given 'solution'. If None provided then all items in the given
        'solution' are displayed.
    time: iterable, optional
        Either an iterable of two values containing the initial and final time
        points, or an iterable of values to treat as time points for the
        solutions. If None provided, the time points used in creating the
        Solution object will be used (accessed via solution.t).
    ax: matplotlib.axes.Axes, optional
        A matplotlib.pyplot.axes instance to plot the data on. If None,
        the current axis is used (accessed via plt.gca()).
    time_poi: list, dict, optional
        Either an iterable of time "points of interest" (poi) to annotate, or
        a dict of time poi to annotate where keys are the time points and
        values are strings representing matplotlib recognized color for that
        time point. If None provided, only the initial and final time points
        are annotated, with default colors "red" and "blue" respectively.
    poi_labels: bool, optional
        If True, will make a legend for annotated time "points of interest".
        Otherwise, time "points of interest" will not be labeled.
    display_data: array_like, shape (N, N), optional
        Additional data to display on the tiled phase portrait. Must matrix of
        shape (N, N) where N = number of observables. The value at [i, j] of
        the data must correspond to a empty tile at the [i, j] position of the
        tiled phase portrait. All other values are ignored.".
    empty_tiles: str, optional
        A string representing whether to place empty tiles on the lower left
        triangular section (i > j), the upper right triangular section
        (i < j). Plot tiles are placed opposite of data tiles. Accepted
        values are {"lower", "upper"}. If None provided then phase portraits
        are placed on all tiles. Default is 'upper'.
    **kwargs

    Returns
    -------
    ax: matplotlib.axes.Axes
        A reference to the matplotlib.axes.Axes object used for plotting.

    See Also
    --------
    get_defaults: Default values for options
    set_defaults: Descriptions of accepted kwargs and input formats.

    """
    solution, time = _fmt_solution_and_time_input(solution, time)
    observable_solutions = _set_plot_observables(solution, time, observable)
    N = len(observable_solutions)

    # Get current axis if none provided, otherwise check its type
    if ax is None:
        ax = plt.gca()
    if not isinstance(ax, Axes):
        raise TypeError("ax must be a matplotlib.axes Axes object.")

    options = _update_kwargs("tiled", **kwargs)
    display_data, empty_tiles = _fmt_empty_tiles(display_data, empty_tiles, N)

    fontsize = options["fontsize"]
    # Create N x N subplots where N is the number of observable solutions
    ax.axis("off")
    s = (1 / N)
    for i, x in enumerate(observable_solutions):
        for j, y in enumerate(observable_solutions):
            subax = ax.inset_axes(bounds=[i * s, 1 - s * (j + 1), s, s])
            plot_args = [solution, x, y, time, subax, time_poi]
            data_args = [i, j, display_data, empty_tiles]
            subax.set_xmargin(0.15)
            subax.set_ymargin(0.15)
            subax.set_xticks([])
            subax.set_yticks([])
            if j == N - 1:
                subax.set_xlabel(x, fontdict={"size": fontsize})
            if i == 0:
                subax.set_ylabel(y, fontdict={"size": fontsize})
            _place_tile(i, j, options, plot_args, data_args)

    if poi_labels:
        endpoints = [round(time[i], int(abs(math.log10(_ZERO_TOL))))
                     for i in [0, -1]]
        time_poi, poi_color = _validate_time_poi_input(time_poi, endpoints)
        points = [mpl.lines.Line2D([], [], label="t={0}".format(t), color=c,
                                   marker="o", linestyle=" ")
                  for t, c in zip(time_poi, poi_color)]
        ax.legend(handles=points, loc="center left", bbox_to_anchor=(1.0, .5))

    if options["title"] is not None:
        ax.set_title(options["title"][0],
                     fontdict=options["title"][1])
    return ax


def make_display_data(N, to_display, display_format="{}",
                      empty_tiles="upper"):
    """Make a matrix recognized by 'plot_tiled_phase_portrait'.

    Items from the 'to_display' list are displayed on empty tiles starting from
    the upper leftmost tile and moving across and down tiles until reaching the
    lower rightmost tile. A tile can be skipped by providing an empty list or
    an empty string for that tile.

    Parameters
    ----------
    N: int
        The dimensions of the returned matrix. Should be equal to the number of
        observable solutions for the relevant tiled phase portrait.
    to_display: list
        The values to display on the tiles without plots.
    display_format: str, optional
        THe desired string format for the provided values. All items in the
        provided in 'to_display' must be able to adhere to this format.
    empty_tiles: str, optional
        Either 'upper' or 'lower' to indicate whether to format the matrix for
        empty upper tiles or empty lower tiles. Should correspond to the
        'empty_tiles' kwarg provided to the 'plot_tiled_phase_portrait'
        function.

    Returns
    -------
    display_data: numpy.ndarray
        A numpy array containing the values from 'to_display' formatted for the
        'display_data' argument in the 'plot_tiled_phase_portrait' function.

    Notes
    -----
    This function is a simple helper function with the purpose of is to create
    the formatted matrix that the 'display_data' argument can recognize for
    displaying additional data on tiles without plots for the
    'plot_tiled_phase_portrait' function.

    """
    compare_dict = {"lower": np.greater, "upper": np.less}
    if empty_tiles in compare_dict:
        compare = compare_dict[empty_tiles]
    else:
        raise ValueError("'empty_tiles' must be one of the following: "
                         "{'lower', 'upper'}")

    if to_display is None:
        to_display = []
    to_display = ensure_iterable(to_display)

    c = 0
    display_data = np.zeros((N, N), dtype=object)
    for i in range(N):
        for j in range(N):
            display_data[i, j] = ""
            try:
                if compare([i], [j]) and c < len(to_display):
                    if to_display[c]:
                        if not isinstance(to_display[c], string_types) \
                           and hasattr(to_display[c], '__iter__'):
                            display_data[i, j] = str(display_format
                                                     .format(*to_display[c]))
                        else:
                            display_data[i, j] = str(display_format
                                                     .format(to_display[c]))
                    c += 1
            except (ValueError, IndexError):
                raise ValueError("Could not format 'to_display' values to the "
                                 "'display_format'.")
    return display_data


def get_default_colors(n_items, start=0):
    """Return a list of the colors for a given number of items.

    This function is primarily for internal use.

    Parameters
    ----------
    n_items: int
        Number of items that need a color.
    start: int
        The index of where to start the cmap.

    Returns
    -------
    list:
        A list of of (n_items - start) colors.

    """
    for parameter, value in zip(["n_items", "start"], [n_items, start]):
        if not isinstance(value, integer_types):
            raise TypeError(parameter + " must be an integer.")

    values = np.linspace(0, 1, 20)
    if n_items > 10 and n_items <= 20:
        cmap = cm.get_cmap("tab20")(values)
    elif n_items > 20 and n_items <= 60:
        cmap = np.vstack((cm.get_cmap("tab20")(values),
                          cm.get_cmap("tab20b")(values),
                          cm.get_cmap("tab20c")(values)))
    elif n_items > 60:
        cmap = cm.get_cmap("nipy_spectral")(np.linspace(0, 1, n_items))
    else:
        cmap = cm.get_cmap("tab10")(np.linspace(0, 1, 10))

    return list(cmap)[start:n_items]


def get_defaults(plot_type):
    """Get the default values for options of a plotting function.

    Parameters
    ----------
    plot_type: str
        The type of plotting function used. Accepted 'plot_type' values are
        {"plot", "tiled"}, with "plot" corresponding to the 'plot_simulation'
        and 'plot_phase_portrait' functions, and with "tiled" corresponding to
        the 'plot_tiled_phase_portrait' function.

    Returns
    -------
    options: dict
        A dict containing key:value pairs of the possible options and their
        default values for a given "plot_type".

    See Also
    --------
    set_defaults: Descriptions of accepted kwargs and input formats.

    """
    if plot_type not in {"plot", "tiled"}:
        raise ValueError("Unrecognized 'plot_type' value.")

    options = {
        "plot_function": "plot",
        "grid": None,
        "prop_cycle": None,
        "linecolor": None,
        "linestyle": None,
        "title": (None, {"size": "medium"}),
    }
    # Update dict for single plot specific options
    if _custom_default_options[plot_type]:
        options = _custom_default_options[plot_type]
    elif plot_type is "plot":
        options.update({
            "xlabel": (None, {"size": "medium"}),
            "ylabel": (None, {"size": "medium"}),
            "xlim": (None, None),
            "ylim": (None, None),
            "default_legend_loc": "best",
            "default_legend_fontsize": "medium",
            "default_legend_ncol": None,
        })
    # Update dict for tiled specific options
    elif plot_type is "tiled":
        options.update({
            "fontsize": "large",
            "diag_color": "black",
            "data_color": "lightgray",
            "none_color": "white",
        })
    else:
        pass

    return options


def set_defaults(plot_type, **kwargs):
    """Get the default values for options of a plotting function.

    Parameters
    ----------
    plot_type: str
        The type of plotting function used. Accepted 'plot_type' values are
        {"plot", "tiled"}, with "plot" corresponding to the 'plot_simulation'
        and 'plot_phase_portrait' functions, and with "tiled" corresponding to
        the 'plot_tiled_phase_portrait' function.
    kwargs:
        plot_function: str
            A string representing the plotting function to use.
            Accepted values are {"plot", "semilogx", "semilogy", "loglog"}.
                "plot" uses an linear x-axis and a linear y-axis
                "semilogx" uses an logarithmic x-axis and a linear y-axis
                "semilogy" uses an linear x-axis and a logarithmic y-axis
                "loglog" uses an logarithmic x-axis and a logarithmic y-axis
            Default value is "plot".
        grid: tuple, bool
            If providing a tuple, the expected format is ("which", "axis"),
            where the values for "which" and "axis" are passed to the
            corresponding argument passed to axes.grid. Accepted values include
            {"major", "minor", "both"} for "which" and {"x", "y, "both"} for
            "axis". If True is provided, gridlines are set with using default
            values for "which" and "axis", and gridlines are removed if False.
        prop_cycle: cylcer.Cyler
            Set a property cycler to control colors and other style properties
            for multiline plots. The property cycler is validated through the
            matplotlib.rcsetup.cycler function and set through the
            axes.set_prop_cycle function. Providing a property cycler will
            cause "linecolor" and "linestyle" kwargs to be ignored.
        linecolor: str, iterable of str, None
            A string or an iterable of strings representing matplotlib.colors
            to use as line colors. If a single string is provided, the color
            will be applied to all solutions to be plotted. If an iterable of
            strings is provided, it must be equal to the number of lines
            to be newly plotted. All colors are validated using the
            matplotlib.colors.is_color_like function. If None provided, will
            use colors obtained from the get_default_colors function.
            Will be ignored if a property cycler is provided via prop_cycle.
        linestyle: str, iterable of str, None
            A string or an iterable of strings representing matplotlib
            recognized linestyles. If a single string is provided, the
            linestyle will be applied to all solutions to be plotted. If an
            iterable of strings is provided, it must be equal to the number of
            lines to be newly plotted. If None provided, will use solid lines.
            Will be ignored if a property cycler is provided via prop_cycle.
        title: string, tuple
            Either a string to use as a title, or a tuple where the first value
            is the title as a string, and the second value is a dict of font
            options to pass to axes.set_title function. Keys must be one of the
            six matplotlib.font_manager font properties. When setting new
            defaults, the new value must be the tuple.
        xlabel: string, tuple
            Either a string to use as the x-axis label, or a tuple where the
            first value is the label as a string, and the second value is a
            dict of font options to pass to axes.set_xlabel function. Keys must
            be one of the six matplotlib.font_manager font properties. When
            setting new defaults, the new value must be the tuple.
            Only valid for plot_type="plot".
        ylabel: string, tuple
            Either a string to use as the y-axis label, or a tuple where the
            first value is the label as a string, and the second value is a
            dict of font options to pass to axes.set_ylabel function. Keys must
            be one of the six matplotlib.font_manager font properties. When
            setting new defaults, the new value must be the tuple.
            Only valid for plot_type="plot".
        xlim: tuple
            A tuple of integers or floats of form (xmin, xmax) specifying the
            limits of the x-axis. Args are passed to axes.set_xlim function.
            Only valid for plot_type="plot".
        ylim: tuple
            A tuple of integers or floats of form (ymin, ymax) specifying the
            limits of the y-axis. Args are passed to axes.set_ylim function.
            Only valid for plot_type="plot".
        default_legend_loc: str, float
            The default legend location if no location was provided to the
            legend arg of the plotting function. Ideally, this kwarg should not
            be used directly in the plotting function, but as a kwarg for
            setting a new default location for the set_defaults function.
            Accepted locations are standard matplotlib legend locations plus
            {"left outside", "right outside", "lower outside", "upper outside"}
            Only valid for plot_type="plot".
        default_legend_fontsize: str, float
            The default legend fontsize if no fontsize was provided to the
            legend arg of the plotting function. Ideally, this kwarg should not
            be used directly in the plotting function, but as a kwarg for
            setting a new default fontsize for the set_defaults function.
            Accepted fontsize values are standard matplotlib legend fontsizes.
            Only valid for plot_type="plot".
        legend_ncol: int, optional
            An int representing the number of columns for the legend. If
            None, then ncols=int(math.ceil(math.sqrt(n_items)/3)).
            Only valid for plot_type="plot".
        fontsize: str, float
            The size of the font for the common axis labels and titles.
            Accepted fontsize values are standard matplotlib legend fontsizes.
            Only valid for plot_type="tiled".
        diag_color: str
            A string representing the color to make the diagonal tiles in the
            tiled phase portrait. All colors are validated using the
            matplotlib.colors.is_color_like function.
            Only valid for plot_type="tiled".
        data_color: str
            A string representing the color to make the tiles displaying data
            in the tiled phase portrait. All colors are validated using the
            matplotlib.colors.is_color_like function.
            Only valid for plot_type="tiled".
        none_color: str
            A string representing the color to make the empty tiles in the
            tiled phase portrait. All colors are validated using the
            matplotlib.colors.is_color_like function.
            Only valid for plot_type="tiled".

    Returns
    -------
    dict:
        A dict containing key:value pairs of the possible options and their
        new default values for a given "plot_type".

    See Also
    --------
    get_defaults: Default values for options

    """
    if plot_type not in {"plot", "tiled"}:
        raise ValueError("Unrecognized 'plot_type' value.")

    if kwargs:
        options = _update_kwargs(plot_type, **kwargs)
        _custom_default_options[plot_type].update(options)
    else:
        _custom_default_options[plot_type] = {}

    return _custom_default_options[plot_type]


# Internal
def _fmt_solution_and_time_input(solution, time):
    """Copy the solution object and format the time input (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    # Copy the solution object to prevent modifications to the original
    solution = solution.copy()
    # Use time stored in Solution if None provided
    if time is None:
        time = solution.t
    # Create an array of time points to use if time bounds provided.
    elif len(time) == 2:
        time = _make_time_vector(solution, time)
    # Use the array of time points provided
    elif isinstance(time, Iterable) and not isinstance(time, string_types):
        time = np.array(sorted(time))
    # If time input is not recognized, then raise an error
    else:
        raise TypeError("Unrecognized 'time' input")
    return solution, time


def _set_plot_observables(solution, time, observable):
    """Set plot observables and return the solution values (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    # Return all items in the solution if no observables are provided.
    if observable is None:
        observable = solution.solutions

    # If a single observable is provided, make it iterable.
    if not hasattr(observable, '__iter__') or \
       isinstance(observable, string_types):
        observable = [observable]

    # Replace objects providfed in observable with their identifiers.
    observable = [getattr(x, "id", x) for x in observable]

    # Check to ensure specified observables are in the Solution object
    if not set(observable).issubset(set(iterkeys(solution))):
        raise ValueError("observable solutions must keys from the Solution")

    # Turn solutions into interpolating functions if the timepoints provided
    # are not identical to those used in the simulation.
    if not isinstance(time, np.ndarray):
        time = np.array(time)

    if not np.array_equal(solution.t, time):
        solution.interpolate = True

    observable = OrderedDict((x, solution[x])
                             if isinstance(solution[x], np.ndarray)
                             else (x, solution[x](time)) for x in observable)

    return observable


def _set_plot_function(ax, option):
    """Set the plotting function to be used (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    plotting_functions_dict = {"plot": ax.plot,
                               "semilogx": ax.semilogx,
                               "semilogy": ax.semilogy,
                               "loglog": ax.loglog}

    return plotting_functions_dict[option]


def _set_axis_options(ax, options):
    """Set axis labels, titles, limits, and gridlines (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    # Set the xlabel, ylabel, and the title if provided.
    for key, setter in zip(["xlabel", "ylabel", "title"],
                           [ax.set_xlabel, ax.set_ylabel, ax.set_title]):
        if options[key][0] is not None:
            setter(options[key][0], fontdict=options[key][1])

    # Set the xlim and the ylim if provided.
    for key, setter in zip(["xlim", "ylim"], [ax.set_xlim, ax.set_ylim]):
        if options[key] != (None, None):
            limits = list(options[key])
            if 0. in limits:
                plot_func = options["plot_function"]
                if key == "xlim" and plot_func in ["loglog", "semilogx"] \
                   or key == "ylim" and plot_func in ["loglog", "semilogy"]:
                    limits[limits.index(0.)] = _ZERO_TOL
            setter(tuple(limits))

    # Set the gridlines if provided.
    if options["grid"] is not None:
        if isinstance(options["grid"], bool):
            ax.grid(options["grid"])
        else:
            ax.grid(True, which=options["grid"][0], axis=options["grid"][1])


def _set_line_properties(ax, options, n_new):
    """Set line colors and styles (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    # Get the current lines on the plot.
    lines = _filter_lines(ax)
    # Get default values for linestyles and linecolors.
    default_dict = {
        "linecolor": get_default_colors(len(lines), start=len(lines) - n_new),
        "linestyle": ["-"] * n_new}

    for key in ["linecolor", "linestyle"]:
        # Set the property if given
        if options[key] is not None:
            to_apply = options[key].copy()
        # Skip linestyles if not given
        elif options[key] is None and key == "linestyle":
            continue
        else:
            to_apply = default_dict[key]

        # Apply to all newly plotted items if only one value provided.
        if len(to_apply) == 1 and n_new != 1:
            to_apply = to_apply * n_new
        # Use default values if the input does not match the number of newly
        # plotted lines.
        elif len(to_apply) != n_new:
            warn("Wrong number of {0}s provided, will use default {0}s "
                 "instead.".format(key))
            to_apply = default_dict[key]
        else:
            pass
        # Set from the last line to the first line to
        # preserve previously plotted lines.
        to_apply.reverse()
        for i, value in enumerate(to_apply):
            if key is "linestyle":
                lines[len(lines) - 1 - i].set_linestyle(value)
            else:
                lines[len(lines) - 1 - i].set_color(value)


def _set_axis_legend(ax, legend, default_labels, options):
    """Set axis legend and associated properties (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    # Initialize default values for fontsize, legend location
    font = options["default_legend_fontsize"]
    loc = options["default_legend_loc"]
    ncol = options["default_legend_ncol"]
    legend = [legend] if isinstance(legend, string_types) else legend
    legend = list(v if isinstance(v, string_types) else list(v)
                  for v in legend)
    # Parse through legend input if provided as a tuple.
    if len(legend) <= 3:
        while legend:
            brk = False
            font, brk = _get_legend_values(legend, _FONTSIZES, font, brk)
            loc, brk = _get_legend_values(legend, _LEGEND_LOCS, loc, brk)
            if legend and isinstance(legend[0], string_types):
                legend = [legend]
            items, brk = _get_legend_values(legend, [], default_labels, brk)
            if legend and not brk:
                if isinstance(legend[-1], string_types):
                    msg = ("Could not interpret legend parameter '{0}'"
                           .format(legend[-1]))
                else:
                    msg = ("'{0}' required != '{1}' provided"
                           .format(len(default_labels), len(legend[-1])))
                msg += ", will attempt to use default legend values instead."
                warn(msg)
                del legend[-1]
            if not legend:
                break
    # Set the legend if only labels are provided.
    elif (all(isinstance(entry, string_types) for entry in legend)
          and len(legend) == len(default_labels)):
        items = legend
    # Use default values if input could not be interpreted.
    else:
        warn("Could not interpret the legend input, will use the default "
             "entries and parameters instead.")
        items = default_labels
    # Get the legend properties
    property_dict = _get_legend_properties(loc, ncol, len(items))
    property_dict.update({"fontsize": font})

    # Apply new labels to the lines and make/update the legend.
    lines = _filter_lines(ax)
    for new_label, line in zip(items, lines[len(lines) - len(items):]):
        line.set_label(new_label)

    labels = [line.get_label() for line in lines]

    ax.legend(lines, labels, **property_dict)


def _validate_time_poi_input(time_poi, endpoints):
    """Validate time_poi input and return with poi colors (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    # Use endpoints if no time points of interest provided
    if time_poi is None:
        time_poi = endpoints
        poi_color = ["red", "blue"]
    # Seperate time points of interest and their corresponding colors
    elif isinstance(time_poi, dict):
        time_poi = OrderedDict((k, time_poi[k]) for k in sorted(time_poi))
        poi_color = list(itervalues(time_poi))
        time_poi = list(iterkeys(time_poi))
    else:
        time_poi = ensure_iterable(time_poi)
        poi_color = ["red"] * len(time_poi)
    return time_poi, poi_color


def _annotate_time_points_of_interest(ax, plot_function, solution, x, y,
                                      time_poi, endpoints, poi_labels,
                                      plot_bounds):
    """Annotate time "points of interest" for the given axis (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    # Set the plotting function
    plot_function = _set_plot_function(ax, plot_function)
    time_poi, poi_color = _validate_time_poi_input(time_poi, endpoints)

    x_pois = _set_plot_observables(solution, time_poi, x)
    y_pois = _set_plot_observables(solution, time_poi, y)

    def poi_in_bounds(bounds, coord):
        if bounds[0] <= coord and coord <= bounds[-1]:
            return True
        else:
            return False

    for i, [t, c] in enumerate(zip(time_poi, poi_color)):
        for x_poi in itervalues(x_pois):
            if not poi_in_bounds(plot_bounds["x"], x_poi[i]):
                continue
            for y_poi in itervalues(y_pois):
                if not poi_in_bounds(plot_bounds["y"], y_poi[i]):
                    continue
                xy = (x_poi[i], y_poi[i])
                label = "t={0}".format(t)

                plot_function(*xy, label=label, color=c,
                              marker="o", linestyle="")
                if poi_labels:
                    ax.annotate("    " + label, xy=xy, xycoords="data",
                                xytext=xy, textcoords='offset points')


def _place_tile(i, j, options, plot_args, data_args):
    """Generate and place tiles for a tiled phase portrait (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    solution, x, y, time, subax, time_poi = plot_args
    i, j, display_data, empty_tiles = data_args

    def _make_tile(condition, options, plot_args, data_args):
        solution, x, y, time, subax, time_poi = plot_args
        i, j = data_args[0:2]
        if condition:
            subax = plot_phase_portrait(solution, x, y, time, ax=subax,
                                        time_poi=time_poi,
                                        poi_labels=False)
        elif display_data is not None and not condition:
            if not str(display_data[j, i]):
                subax.set_facecolor(options["none_color"])
            else:
                subax.annotate(str(display_data[j, i]), xy=(0.5, 0.5),
                               xycoords="axes fraction", va="center",
                               ha="center", fontsize=options["fontsize"])
                subax.set_facecolor(options["data_color"])
        else:
            subax.set_facecolor(options["none_color"])

    if i == j:
        subax.set_facecolor(options["diag_color"])
    elif empty_tiles == "upper":
        _make_tile(i < j, options, plot_args, data_args)
    elif empty_tiles == "lower":
        _make_tile(i > j, options, plot_args, data_args)
    else:
        subax = plot_phase_portrait(solution, x, y, time, ax=subax,
                                    time_poi=time_poi,
                                    poi_labels=False)


def _update_kwargs(plot_type, **kwargs):
    """Validate kwargs and update their corresponding values (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    options = get_defaults(plot_type)
    # Return default options if no kwargs provided.
    if kwargs:
        update_functions_dict = {
            "plot_function": _update_plot_function,
            "xlabel": _update_labels,
            "ylabel": _update_labels,
            "title": _update_labels,
            "xlim": _update_limits,
            "ylim": _update_limits,
            "grid": _update_grid,
            "linecolor": _update_lines,
            "linestyle": _update_lines,
            "prop_cycle": _update_lines,
            "default_legend_loc": _update_legend_properties,
            "default_legend_fontsize": _update_legend_properties,
            "default_legend_ncol": _update_legend_properties,
            "fontsize": _update_tiles,
            "diag_color": _update_tiles,
            "data_color": _update_tiles,
            "none_color": _update_tiles,
        }
        # Iterate through kwargs and update options.
        for key, value in iteritems(kwargs):
            if key in update_functions_dict and key in options:
                update_functions_dict[key](options, key, value)
            else:
                warn("kwarg '" + str(key) + "' not recognized")
    return options


def _update_plot_function(options, key, value):
    """Validate the 'plot_function' kwarg (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    allowed_plotting_functions = {"loglog", "semilogx", "semilogy", "plot"}
    if value not in allowed_plotting_functions:
        raise ValueError(str(key) + "must be one of the following: "
                         + str(allowed_plotting_functions))
    options[key] = value


def _update_labels(options, key, value):
    """Validate kwargs for axis labels (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    # Check input types for option
    if not hasattr(value, '__iter__'):
        raise TypeError(str(key) + " must be an iterable")
    if isinstance(value, string_types):
        value = (value, options[key][1])
    if not isinstance(value[1], dict):
        raise TypeError("fontdict must be a dictionary")
    # Update options
    options[key] = value


def _update_limits(options, key, value):
    """Validate kwargs for axis limits (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    if not hasattr(value, '__iter__') or len(value) != 2:
        raise TypeError(str(key) + " must be an iterable of length 2")
    elif not all(isinstance(v, (float, integer_types))for v in value):
        raise TypeError("Limits must be ints or floats")
    elif value[0] > value[1]:
        warn("{0}min is greater than {0}max, attempting to swap values"
             .format(key[0]))
        value = (value[1], value[0])
    else:
        value = tuple(value)
    # Update options
    options[key] = value


def _update_grid(options, key, value):
    """Validate the 'grid' kwarg (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    which_args = ["major", "minor", "both"]
    axis_args = ["x", "y", "both"]

    if isinstance(value, string_types):
        if value in which_args:
            value = (value, "both")
        else:
            value = ("both", value)

    if isinstance(value, bool):
        pass
    elif len(value) == 2 and all(isinstance(v, string_types) for v in value):
        if value[0] not in which_args:
            raise ValueError("The first value must be one of the following: "
                             + str(which_args))
        if value[1] not in axis_args:
            raise ValueError("The second value must be one of the following: "
                             + str(axis_args))
    else:
        raise TypeError(str(key) + " must be string or a tuple of strings")

    options[key] = value


def _update_lines(options, key, value):
    """Validate kwargs for line properties (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    is_color_like = mpl.colors.is_color_like
    if isinstance(value, string_types):
        value = [value]

    if isinstance(value, Cycler):
        value = mpl.rcsetup.cycler(value)
    elif (not isinstance(value, Iterable)
          or not all(isinstance(v, string_types) for v in value)):
        raise TypeError(key + " must be a string or an iterable of strings.")
    elif key is "linecolor" and not all(is_color_like(v) for v in value):
        raise ValueError("Invalid colors found: "
                         + str([v for v in value if not is_color_like(v)]))
    else:
        pass
    options[key] = value


def _update_legend_properties(options, key, value):
    """Validate kwargs for legend properties (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    allowed_dict = {"default_legend_loc": _LEGEND_LOCS,
                    "default_legend_fontsize": _FONTSIZES}
    if not isinstance(value, (integer_types, float)):
        if key is "default_legend_ncol":
            raise TypeError(key + " must be a numerical value.")
        if value not in allowed_dict[key]:
            raise ValueError(key + " must be one of the following: "
                             + str(allowed_dict[key]))
    elif value < 0:
        raise ValueError(key + " must be a non negative value")
    elif key is "default_legend_loc" and value > 10:
        raise ValueError(key + " must be a value between 0 and 10, inclusive.")
    else:
        pass

    options[key] = value


def _get_legend_values(legend, allowable, default, success):
    """Help set legend location, fontsize, and entries (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    parameter = None
    if legend:
        item = legend[-1]
        if allowable:
            if ((isinstance(item, Hashable)
                 and (isinstance(item, (integer_types, float))
                      or item in allowable))):
                parameter = legend.pop(-1)
                success = True
        elif (not isinstance(item, Hashable) and len(item) == len(default)):
            parameter = legend.pop(-1)
            success = True
        else:
            parameter = default
    else:
        parameter = default
    if parameter is None:
        parameter = default
    return parameter, success


def _get_legend_properties(loc, ncol, n_items):
    """Help set legend location and number of columns (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    loc_anchor_dict = {"left outside": ("center right", (-0.15, 0.5)),
                       "right outside": ("center left", (1.05, 0.5)),
                       "lower outside": ("upper center", (0.5, -0.2)),
                       "upper outside": ("lower center", (0.5, 1.15))}
    if loc in loc_anchor_dict:
        loc, anchor = loc_anchor_dict[loc]
    else:
        anchor = None

    if ncol is None:
        ncol = int(math.ceil(math.sqrt(n_items) / 3))

    return {"loc": loc, "bbox_to_anchor": anchor, "ncol": ncol}


def _update_tiles(options, key, value):
    """Validate kwargs for tile color and fontsize (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    if "_color" in key and not mpl.colors.is_color_like(value):
        raise ValueError("Invalid color input: " + str(value))

    if key == "fontsize" and value not in _FONTSIZES \
       and (isinstance(value, (integer_types, float)) and value < 0):
        raise ValueError(key + " must be a non-negative value or one of the "
                         "following: " + str(_FONTSIZES))

    options[key] = value


def _fmt_empty_tiles(display_data, empty_tiles, N):
    """Validate the input for data to display (Helper function).

    Warnings
    --------
    This method is intended for internal use only.

    """
    if empty_tiles is not None and empty_tiles not in {"lower", "upper"}:
        raise ValueError("empty_tiles must be 'lower', 'upper', or None.")
    if display_data is not None:
        # Ensure data is a numpy array and of N x N dimensions
        if not isinstance(display_data, np.ndarray):
            display_data = np.array(display_data)
        if not np.array_equal(display_data.shape, (N, N)):
            raise ValueError("display_data must be an N x N matrix where N is "
                             "equal to the number of observable solutions.")

    return display_data, empty_tiles


def _filter_lines(ax, to_return="lines"):
    """Filter axis lines to seperate plotted lines from plotted time_pois.

    Warnings
    --------
    This method is intended for internal use only.

    """
    if to_return not in {"lines", "tpoi"}:
        raise ValueError("Unrecognized 'to_return' value")

    if to_return == "lines":
        return [l for l in ax.get_lines() if l.get_label()[:2] != "t="]
    else:
        return [l for l in ax.get_lines() if l.get_label()[:2] == "t="]


def _make_time_vector(solution, time):
    """Create a time array using the model timescales and given time bounds.

    Warnings
    --------
    This method is intended for internal use only.

    """
    J = linear.jacobian(solution.model)
    rank = linear.matrix_rank(J)
    timescales = np.real_if_close(-1 / np.sort(linear.eig(J))[:rank])

    min_ts = min([ts for ts in timescales if ts >= time[0]])
    max_ts = max([ts for ts in timescales if ts <= time[-1]])
    end = max(time[-1], max_ts)
    if time[0] == 0:
        start = min_ts / 100
        t_vec = np.concatenate([[0], np.geomspace(start, end,
                                                  solution.numpoints)])
    else:
        start = min(time[0], min_ts)
        t_vec = np.geomspace(start, end, solution.numpoints)

    return t_vec
