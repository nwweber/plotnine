"""
Provide theamables, the elements of plot can be style with theme()

From the ggplot2 documentation the axis.title inherits from text.
What this means is that axis.title and text have the same elements
that may be themed, but the scope of what they apply to is different.
The scope of text covers all text in the plot, axis.title applies
only to the axis.title. In matplotlib terms this means that a theme
that covers text also has to cover axis.title.
"""
from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING
from warnings import warn

import numpy as np

from .._utils import to_rgba
from .._utils.registry import RegistryHierarchyMeta
from ..exceptions import PlotnineError, deprecated_themeable_name
from .elements import element_blank
from .elements.element_base import element_base

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Sequence, Type

    from matplotlib.patches import Patch, Rectangle
    from matplotlib.text import Text

    from plotnine.typing import Axes, Figure, Theme


class themeable(metaclass=RegistryHierarchyMeta):
    """
    Abstract class of things that can be themed.

    Every subclass of themeable is stored in a dict at
    :python:`themeable.register` with the name of the subclass as
    the key.

    It is the base of a class hierarchy that uses inheritance in a
    non-traditional manner. In the textbook use of class inheritance,
    superclasses are general and subclasses are specializations. In some
    since the hierarchy used here is the opposite in that superclasses
    are more specific than subclasses.

    It is probably better to think if this hierarchy of leveraging
    Python's multiple inheritance to implement composition. For example
    the `axis_title` themeable is *composed of* the `x_axis_title` and the
    `y_axis_title`. We are just using multiple inheritance to specify
    this composition.

    When implementing a new themeable based on the ggplot2 documentation,
    it is important to keep this in mind and reverse the order of the
    "inherits from" in the documentation.

    For example, to implement,

    - `axis_title_x` - `x` axis label (element_text;
      inherits from `axis_title`)
    - `axis_title_y` - `y` axis label (element_text;
      inherits from `axis_title`)


    You would have this implementation:


    ```python
    class axis_title_x(themeable):
        ...

    class axis_title_y(themeable):
        ...

    class axis_title(axis_title_x, axis_title_y):
        ...
    ```

    If the superclasses fully implement the subclass, the body of the
    subclass should be "pass". Python(__mro__) will do the right thing.

    When a method does require implementation, call `super()`{.py}
    then add the themeable's implementation to the axes.

    Notes
    -----
    A user should never create instances of class
    [](`~plotnine.themes.themeable.Themeable`) or subclasses of it.
    """

    _omit: list[str] = []
    """
    Properties to ignore during the apply stage.

    These properties may have been used when creating the artists and
    applying them would create a conflict or an error.
    """

    def __init__(self, theme_element: element_base | str | float):
        self.theme_element = theme_element
        if isinstance(theme_element, element_base):
            self._properties: dict[str, Any] = theme_element.properties
        else:
            # The specific themeable takes this value and
            # does stuff with rcParams or sets something
            # on some object attached to the axes/figure
            self._properties = {"value": theme_element}

    @staticmethod
    def from_class_name(name: str, theme_element: Any) -> themeable:
        """
        Create a themeable by name

        Parameters
        ----------
        name : str
            Class name
        theme_element : element object
            An element of the type required by the theme.
            For lines, text and rects it should be one of:
            [](`~plotnine.themes.element_line`),
            [](`~plotnine.themes.element_rect`),
            [](`~plotnine.themes.element_text`) or
            [](`~plotnine.themes.element_blank`)

        Returns
        -------
        out : plotnine.themes.themeable.themeable
        """
        msg = f"There no themeable element called: {name}"
        try:
            klass: Type[themeable] = themeable._registry[name]
        except KeyError as e:
            raise PlotnineError(msg) from e

        if not issubclass(klass, themeable):
            raise PlotnineError(msg)

        return klass(theme_element)

    @classmethod
    def registry(cls) -> Mapping[str, Any]:
        return themeable._registry

    def is_blank(self) -> bool:
        """
        Return True if theme_element is made of element_blank
        """
        return isinstance(self.theme_element, element_blank)

    def merge(self, other: themeable):
        """
        Merge properties of other into self

        Raises
        ------
        ValueError
            If any of the properties are blank
        """
        if self.is_blank() or other.is_blank():
            raise ValueError("Cannot merge if there is a blank.")
        else:
            self._properties.update(other._properties)

    def __eq__(self, other: object) -> bool:
        "Mostly for unittesting."
        return other is self or (
            isinstance(other, type(self))
            and self._properties == other._properties
        )

    @property
    def rcParams(self) -> dict[str, Any]:
        """
        Return themeables rcparams to an rcparam dict before plotting.

        Returns
        -------
        dict
            Dictionary of legal matplotlib parameters.

        This method should always call super(...).rcParams and
        update the dictionary that it returns with its own value, and
        return that dictionary.

        This method is called before plotting. It tends to be more
        useful for general themeables. Very specific themeables
        often cannot be be themed until they are created as a
        result of the plotting process.
        """
        return {}

    @property
    def properties(self):
        """
        Return only the properties that can be applied
        """
        d = self._properties.copy()
        for key in self._omit:
            with suppress(KeyError):
                del d[key]
        return d

    def apply(self, theme: Theme):
        """
        Called by the theme to apply the themeable

        Subclasses should not have to override this method
        """
        blanks = (self.blank_figure, self.blank_ax)
        applys = (self.apply_figure, self.apply_ax)
        do_figure, do_ax = blanks if self.is_blank() else applys

        do_figure(theme.figure, theme._targets)
        for ax in theme.axs:
            do_ax(ax)

    def apply_ax(self, ax: Axes):
        """
        Called after a chart has been plotted.

        Subclasses can override this method to customize the plot
        according to the theme.

        This method should be implemented as `super().apply_ax()`{.py}
        followed by extracting the portion of the axes specific to this
        themeable then applying the properties.


        Parameters
        ----------
        ax : matplotlib.axes.Axes
        """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        """
        Apply theme to the figure
        """

    def blank_ax(self, ax: Axes):
        """
        Blank out theme elements
        """

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        """
        Blank out elements on the figure
        """


class Themeables(dict[str, themeable]):
    """
    Collection of themeables

    The key is the name of the class.
    """

    def update(self, other: Themeables, **kwargs):  # type: ignore
        """
        Update themeables with those from `other`

        This method takes care of inserting the `themeable`
        into the underlying dictionary. Before doing the
        insertion, any existing themeables that will be
        affected by a new from `other` will either be merged
        or removed. This makes sure that a general themeable
        of type :class:`text` can be added to override an
        existing specific one of type :class:`axis_text_x`.
        """
        for new in other.values():
            new_key = new.__class__.__name__

            # 1st in the mro is self, the
            # last 2 are (themeable, object)
            for child in new.__class__.mro()[1:-2]:
                child_key = child.__name__
                try:
                    self[child_key].merge(new)
                except KeyError:
                    pass
                except ValueError:
                    # Blank child is will be overridden
                    del self[child_key]
            try:
                self[new_key].merge(new)
            except (KeyError, ValueError):
                # Themeable type is new or
                # could not merge blank element.
                self[new_key] = new

    @property
    def _dict(self):
        """
        Themeables in reverse based on the inheritance hierarchy.

        Themeables should be applied or merged in order from general
        to specific. i.e.
            - apply :class:`axis_line` before :class:`axis_line_x`
            - merge :class:`axis_line_x` into :class:`axis_line`
        """
        hierarchy = themeable._hierarchy
        result: dict[str, themeable] = {}
        for lst in hierarchy.values():
            for name in reversed(lst):
                if name in self and name not in result:
                    result[name] = self[name]
        return result

    def items(self):
        """
        List of (name, themeable) in reverse based on the inheritance.
        """
        return self._dict.items()

    def values(self):
        """
        List of themeables in reverse based on the inheritance hierarchy.
        """
        return self._dict.values()

    def getp(self, key: str | tuple[str, str], default: Any = None) -> Any:
        """
        Get the value a specific themeable(s) property

        Themeables store theming attribute values in the
        :attr:`Themeable.properties` :class:`dict`. The goal
        of this method is to look a value from that dictionary,
        and fallback along the inheritance heirarchy of themeables.

        Parameters
        ----------
        key :
            Themeable and property name to lookup. If a `str`,
            the name is assumed to be "value".

        default :
            Value to return if lookup fails
        Returns
        -------
        out : object
            Value

        Raises
        ------
        KeyError
            If key is in not in any of themeables
        """
        if isinstance(key, str):
            key = (key, "value")

        name, prop = key
        hlist = themeable._hierarchy[name]
        scalar = key == "value"
        for th in hlist:
            with suppress(KeyError):
                value = self[th]._properties[prop]
                if not scalar or value is not None:
                    return value

        return default

    def property(self, name: str, key: str = "value") -> Any:
        """
        Get the value a specific themeable(s) property

        Themeables store theming attribute values in the
        :attr:`Themeable.properties` :class:`dict`. The goal
        of this method is to look a value from that dictionary,
        and fallback along the inheritance heirarchy of themeables.

        Parameters
        ----------
        name : str
            Themeable name
        key : str
            Property name to lookup

        Returns
        -------
        out : object
            Value

        Raises
        ------
        KeyError
            If key is in not in any of themeables
        """
        default = object()
        res = self.getp((name, key), default)
        if res is default:
            hlist = themeable._hierarchy[name]
            msg = f"'{key}' is not in the properties of {hlist}"
            raise KeyError(msg)
        return res

    def is_blank(self, name: str) -> bool:
        """
        Return True if the themeable *name* is blank

        If the *name* is not in the list of themeables then
        the lookup falls back to inheritance hierarchy.
        If none of the themeables are in the hierarchy are
        present, `False` is returned.

        Parameters
        ----------
        names : str
            Themeable, in order of most specific to most
            general.
        """
        for th in themeable._hierarchy[name]:
            if element := self.get(th):
                return element.is_blank()

        return False


def _blankout_rect(rect: Patch):
    """
    Make rect invisible
    """
    # set_visible(False) does not clear the attributes
    rect.set_edgecolor("None")
    rect.set_facecolor("None")
    rect.set_linewidth(0)


class text_themeable(themeable):
    """
    Base class for all element_text themeables
    """

    _omit = ["margin"]


class texts_themeable(themeable):
    """
    Base class for themeables that modify lists of Text

    Where possible, setting the properties with a sequence
    of values.

    e.g.

        theme(axis_text_x=element_text(color=("red", "green", "blue")))

    The number of values in the sequence must match the number of
    text objects in the figure.
    """

    _omit = ["margin"]

    def set(self, texts: Sequence[Text]):
        props = self.properties

        n = len(texts)
        sequence_props = {}
        for name, value in props.items():
            if (
                isinstance(value, (list, tuple, np.ndarray))
                and len(value) == n
            ):
                sequence_props[name] = value

        for key in sequence_props:
            del props[key]

        for t in texts:
            t.set(**props)

        for name, values in sequence_props.items():
            for t, value in zip(texts, values):
                t.set(**{name: value})


# element_text themeables


class axis_title_x(text_themeable):
    """
    x axis label

    Parameters
    ----------
    theme_element : element_text
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if text := targets.get("axis_title_x"):
            text.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if text := targets.get("axis_title_x"):
            text.set_visible(False)


class axis_title_y(text_themeable):
    """
    y axis label

    Parameters
    ----------
    theme_element : element_text
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if text := targets.get("axis_title_y"):
            text.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if text := targets.get("axis_title_y"):
            text.set_visible(False)


class axis_title(axis_title_x, axis_title_y):
    """
    Axis labels

    Parameters
    ----------
    theme_element : element_text
    """


class legend_title(themeable):
    """
    Legend title

    Parameters
    ----------
    theme_element : element_text
    """

    _omit = ["margin", "ha", "va"]

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if text := targets.get("legend_title"):
            text.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if text := targets.get("legend_title"):
            text.set_visible(False)


class legend_text_legend(texts_themeable):
    """
    Legend text for the common legend

    Parameters
    ----------
    theme_element : element_text

    Notes
    -----
    Horizontal alignment `ha` has no effect when the text is to the
    left or to the right. Likewise vertical alignment `va` has no
    effect when the text at the top or the bottom.
    """

    _omit = ["margin", "ha", "va"]

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if texts := targets.get("legend_text_legend"):
            self.set(texts)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if texts := targets.get("legend_text_legend"):
            for text in texts:
                text.set_visible(False)


class legend_text_colorbar(texts_themeable):
    """
    Colorbar text

    Parameters
    ----------
    theme_element : element_text

    Notes
    -----
    Horizontal alignment `ha` has no effect when the text is to the
    left or to the right. Likewise vertical alignment `va` has no
    effect when the text at the top or the bottom.
    """

    _omit = ["margin", "ha", "va"]

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if texts := targets.get("legend_text_colorbar"):
            self.set(texts)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if texts := targets.get("legend_text_colorbar"):
            for text in texts:
                text.set_visible(False)


legend_text_colourbar = legend_text_colorbar


class legend_text(legend_text_legend, legend_text_colorbar):
    """
    Legend text

    Parameters
    ----------
    theme_element : element_text
    """


class plot_title(text_themeable):
    """
    Plot title

    Parameters
    ----------
    theme_element : element_text

    Notes
    -----
    The default horizontal alignment for the title is center. However the
    title will be left aligned if and only if there is a subtitle and its
    horizontal alignment has not been set (so it defaults to the left).

    The defaults ensure that, short titles are not awkwardly left-aligned,
    and that a title and a subtitle will not be awkwardly mis-aligned in
    the center or with different alignments.
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if text := targets.get("plot_title"):
            text.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if text := targets.get("plot_title"):
            text.set_visible(False)


class plot_subtitle(text_themeable):
    """
    Plot subtitle

    Parameters
    ----------
    theme_element : element_text

    Notes
    -----
    The default horizontal alignment for the subtitle is left. And when
    it is present, by default it drags the title to the left. The subtitle
    drags the title to the left only if none of the two has their horizontal
    alignment are set.
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if text := targets.get("plot_subtitle"):
            text.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if text := targets.get("plot_subtitle"):
            text.set_visible(False)


class plot_caption(text_themeable):
    """
    Plot caption

    Parameters
    ----------
    theme_element : element_text
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if text := targets.get("plot_caption"):
            text.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if text := targets.get("plot_caption"):
            text.set_visible(False)


class strip_text_x(texts_themeable):
    """
    Facet labels along the horizontal axis

    Parameters
    ----------
    theme_element : element_text
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if texts := targets.get("strip_text_x"):
            self.set(texts)

        if rects := targets.get("strip_background_x"):
            for rect in rects:
                rect.set_visible(True)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if texts := targets.get("strip_text_x"):
            for text in texts:
                text.set_visible(False)

        if rects := targets.get("strip_background_x"):
            for rect in rects:
                rect.set_visible(False)


class strip_text_y(texts_themeable):
    """
    Facet labels along the vertical axis

    Parameters
    ----------
    theme_element : element_text
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if texts := targets.get("strip_text_y"):
            self.set(texts)

        if rects := targets.get("strip_background_y"):
            for rect in rects:
                rect.set_visible(True)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if texts := targets.get("strip_text_y"):
            for text in texts:
                text.set_visible(False)

        if rects := targets.get("strip_background_y"):
            for rect in rects:
                rect.set_visible(False)


class strip_text(strip_text_x, strip_text_y):
    """
    Facet labels along both axes

    Parameters
    ----------
    theme_element : element_text
    """


class title(axis_title, legend_title, plot_title, plot_subtitle, plot_caption):
    """
    All titles on the plot

    Parameters
    ----------
    theme_element : element_text
    """


class axis_text_x(texts_themeable):
    """
    x-axis tick labels

    Parameters
    ----------
    theme_element : element_text
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        self.set(ax.get_xticklabels())

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.xaxis.set_tick_params(
            which="both", labelbottom=False, labeltop=False
        )


class axis_text_y(texts_themeable):
    """
    y-axis tick labels

    Parameters
    ----------
    theme_element : element_text
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        self.set(ax.get_yticklabels())

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.yaxis.set_tick_params(
            which="both", labelleft=False, labelright=False
        )


class axis_text(axis_text_x, axis_text_y):
    """
    Axis tick labels

    Parameters
    ----------
    theme_element : element_text
    """


class text(axis_text, legend_text, strip_text, title):
    """
    All text elements in the plot

    Parameters
    ----------
    theme_element : element_text
    """

    @property
    def rcParams(self) -> dict[str, Any]:
        rcParams = super().rcParams

        family = self.properties.get("family")

        style = self.properties.get("style")
        weight = self.properties.get("weight")
        size = self.properties.get("size")
        color = self.properties.get("color")

        if family:
            rcParams["font.family"] = family
        if style:
            rcParams["font.style"] = style
        if weight:
            rcParams["font.weight"] = weight
        if size:
            rcParams["font.size"] = size
            rcParams["xtick.labelsize"] = size
            rcParams["ytick.labelsize"] = size
            rcParams["legend.fontsize"] = size
        if color:
            rcParams["text.color"] = color

        return rcParams


# element_line themeables


class axis_line_x(themeable):
    """
    x-axis line

    Parameters
    ----------
    theme_element : element_line
    """

    position = "bottom"
    _omit = ["solid_capstyle"]

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.spines["top"].set_visible(False)
        ax.spines["bottom"].set(**self.properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.spines["top"].set_visible(False)
        ax.spines["bottom"].set_visible(False)


class axis_line_y(themeable):
    """
    y-axis line

    Parameters
    ----------
    theme_element : element_line
    """

    position = "left"
    _omit = ["solid_capstyle"]

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set(**self.properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.spines["left"].set_visible(False)
        ax.spines["right"].set_visible(False)


class axis_line(axis_line_x, axis_line_y):
    """
    x & y axis lines

    Parameters
    ----------
    theme_element : element_line
    """


class axis_ticks_minor_x(themeable):
    """
    x-axis tick lines

    Parameters
    ----------
    theme_element : element_line
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        # The ggplot._draw_breaks_and_labels uses set_tick_params to
        # turn off the ticks that will not show. That sets the location
        # key (e.g. params["bottom"]) to False. It also sets the artist
        # to invisible. Theming should not change those artists to visible,
        # so we return early.
        params = ax.xaxis.get_tick_params(which="minor")
        if not params.get("left", False):
            return

        # We have to use both
        #    1. Axis.set_tick_params()
        #    2. Tick.tick1line.set()
        # We split the properties so that set_tick_params keeps
        # record of the properties it cares about so that it does
        # not undo them. GH703
        # https://github.com/matplotlib/matplotlib/issues/26008
        tick_params = {}
        properties = self.properties
        with suppress(KeyError):
            tick_params["width"] = properties.pop("linewidth")
        with suppress(KeyError):
            tick_params["color"] = properties.pop("color")

        if tick_params:
            ax.xaxis.set_tick_params(which="minor", **tick_params)

        for tick in ax.xaxis.get_minor_ticks():
            tick.tick1line.set(**properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        for tick in ax.xaxis.get_minor_ticks():
            tick.tick1line.set_visible(False)


class axis_ticks_minor_y(themeable):
    """
    y-axis minor tick lines

    Parameters
    ----------
    theme_element : element_line
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        params = ax.yaxis.get_tick_params(which="minor")
        if not params.get("left", False):
            return

        tick_params = {}
        properties = self.properties
        with suppress(KeyError):
            tick_params["width"] = properties.pop("linewidth")
        with suppress(KeyError):
            tick_params["color"] = properties.pop("color")

        if tick_params:
            ax.yaxis.set_tick_params(which="minor", **tick_params)

        for tick in ax.yaxis.get_minor_ticks():
            tick.tick1line.set(**properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        for tick in ax.yaxis.get_minor_ticks():
            tick.tick1line.set_visible(False)


class axis_ticks_major_x(themeable):
    """
    x-axis major tick lines

    Parameters
    ----------
    theme_element : element_line
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        params = ax.xaxis.get_tick_params(which="major")
        if not params.get("left", False):
            return

        tick_params = {}
        properties = self.properties
        with suppress(KeyError):
            tick_params["width"] = properties.pop("linewidth")
        with suppress(KeyError):
            tick_params["color"] = properties.pop("color")

        if tick_params:
            ax.xaxis.set_tick_params(which="major", **tick_params)

        for tick in ax.xaxis.get_major_ticks():
            tick.tick1line.set(**properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        for tick in ax.xaxis.get_major_ticks():
            tick.tick1line.set_visible(False)


class axis_ticks_major_y(themeable):
    """
    y-axis major tick lines

    Parameters
    ----------
    theme_element : element_line
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        params = ax.yaxis.get_tick_params(which="major")
        if not params.get("left", False):
            return

        tick_params = {}
        properties = self.properties
        with suppress(KeyError):
            tick_params["width"] = properties.pop("linewidth")
        with suppress(KeyError):
            tick_params["color"] = properties.pop("color")

        if tick_params:
            ax.yaxis.set_tick_params(which="major", **tick_params)

        for tick in ax.yaxis.get_major_ticks():
            tick.tick1line.set(**properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        for tick in ax.yaxis.get_major_ticks():
            tick.tick1line.set_visible(False)


class axis_ticks_major(axis_ticks_major_x, axis_ticks_major_y):
    """
    x & y axis major tick lines

    Parameters
    ----------
    theme_element : element_line
    """


class axis_ticks_minor(axis_ticks_minor_x, axis_ticks_minor_y):
    """
    x & y axis minor tick lines

    Parameters
    ----------
    theme_element : element_line
    """


class axis_ticks_x(axis_ticks_major_x, axis_ticks_minor_x):
    """
    x major and minor axis tick lines

    Parameters
    ----------
    theme_element : element_line
    """


class axis_ticks_y(axis_ticks_major_y, axis_ticks_minor_y):
    """
    y major and minor axis tick lines

    Parameters
    ----------
    theme_element : element_line
    """


class axis_ticks(axis_ticks_major, axis_ticks_minor):
    """
    x & y major and minor axis tick lines

    Parameters
    ----------
    theme_element : element_line
    """


class legend_ticks(themeable):
    """
    The ticks on a legend

    Parameters
    ----------
    theme_element : element_line
    """

    _omit = ["solid_capstyle"]

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if coll := targets.get("legend_ticks"):
            coll.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if coll := targets.get("legend_ticks"):
            coll.set_visible(False)


class panel_grid_major_x(themeable):
    """
    Vertical major grid lines

    Parameters
    ----------
    theme_element : element_line
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.xaxis.grid(which="major", **self.properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.grid(False, which="major", axis="x")


class panel_grid_major_y(themeable):
    """
    Horizontal major grid lines

    Parameters
    ----------
    theme_element : element_line
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.yaxis.grid(which="major", **self.properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.grid(False, which="major", axis="y")


class panel_grid_minor_x(themeable):
    """
    Vertical minor grid lines

    Parameters
    ----------
    theme_element : element_line
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.xaxis.grid(which="minor", **self.properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.grid(False, which="minor", axis="x")


class panel_grid_minor_y(themeable):
    """
    Horizontal minor grid lines

    Parameters
    ----------
    theme_element : element_line
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.yaxis.grid(which="minor", **self.properties)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.grid(False, which="minor", axis="y")


class panel_grid_major(panel_grid_major_x, panel_grid_major_y):
    """
    Major grid lines

    Parameters
    ----------
    theme_element : element_line
    """


class panel_grid_minor(panel_grid_minor_x, panel_grid_minor_y):
    """
    Minor grid lines

    Parameters
    ----------
    theme_element : element_line
    """


class panel_grid(panel_grid_major, panel_grid_minor):
    """
    Grid lines

    Parameters
    ----------
    theme_element : element_line
    """


class line(axis_line, axis_ticks, panel_grid, legend_ticks):
    """
    All line elements

    Parameters
    ----------
    theme_element : element_line
    """

    @property
    def rcParams(self) -> dict[str, Any]:
        rcParams = super().rcParams
        color = self.properties.get("color")
        linewidth = self.properties.get("linewidth")
        linestyle = self.properties.get("linestyle")
        d = {}

        if color:
            d["axes.edgecolor"] = color
            d["xtick.color"] = color
            d["ytick.color"] = color
            d["grid.color"] = color
        if linewidth:
            d["axes.linewidth"] = linewidth
            d["xtick.major.width"] = linewidth
            d["xtick.minor.width"] = linewidth
            d["ytick.major.width"] = linewidth
            d["ytick.minor.width"] = linewidth
            d["grid.linewidth"] = linewidth
        if linestyle:
            d["grid.linestyle"] = linestyle

        rcParams.update(d)
        return rcParams


# element_rect themeables


class legend_key(themeable):
    """
    Legend key background

    Parameters
    ----------
    theme_element : element_rect
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        properties = self.properties
        # list[DrawingArea]
        if das := targets.get("legend_key"):
            for da in das:
                da.patch.set(**properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        # list[DrawingArea]
        if das := targets.get("legend_key"):
            for da in das:
                _blankout_rect(da.patch)


class legend_frame(themeable):
    """
    Frame around colorbar

    Parameters
    ----------
    theme_element : element_rect
    """

    _omit = ["facecolor"]

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if rect := targets.get("legend_frame"):
            rect.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if rect := targets.get("legend_frame"):
            _blankout_rect(rect)


class legend_background(themeable):
    """
    Legend background

    Parameters
    ----------
    theme_element : element_rect
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        # anchored offset box
        if aob := targets.get("legend_background"):
            properties = self.properties
            aob.patch.set(**properties)
            if properties:
                aob._drawFrame = True
                # some small sensible padding
                if not aob.pad:
                    aob.pad = 0.2

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if aob := targets.get("legend_background"):
            _blankout_rect(aob.patch)


class legend_box_background(themeable):
    """
    Legend box background

    Parameters
    ----------
    theme_element : element_rect

    Notes
    -----
    Not Implemented. We would have to place the outermost
    VPacker/HPacker boxes that hold the individual legends
    onto an object that has a patch.
    """


class panel_background(themeable):
    """
    Panel background

    Parameters
    ----------
    theme_element : element_rect
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        d = self.properties
        if "facecolor" in d and "alpha" in d:
            d["facecolor"] = to_rgba(d["facecolor"], d["alpha"])
            del d["alpha"]
        ax.patch.set(**d)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        _blankout_rect(ax.patch)


class panel_border(themeable):
    """
    Panel border

    Parameters
    ----------
    theme_element : element_rect
    """

    _omit = ["facecolor"]

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        d = self.properties
        # Be lenient if using element_line
        with suppress(KeyError):
            d["edgecolor"] = d.pop("color")

        if "edgecolor" in d and "alpha" in d:
            d["edgecolor"] = to_rgba(d["edgecolor"], d["alpha"])
            del d["alpha"]

        ax.patch.set(**d)

    def blank_ax(self, ax: Axes):
        super().blank_ax(ax)
        ax.patch.set_linewidth(0)


class plot_background(themeable):
    """
    Plot background

    Parameters
    ----------
    theme_element : element_rect
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        figure.patch.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        _blankout_rect(figure.patch)


class strip_background_x(themeable):
    """
    Horizontal facet label background

    Parameters
    ----------
    theme_element : element_rect
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        if bboxes := targets.get("strip_background_x"):
            for bbox in bboxes:
                bbox.set(**self.properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if rects := targets.get("strip_background_x"):
            for rect in rects:
                _blankout_rect(rect)


class strip_background_y(themeable):
    """
    Vertical facet label background

    Parameters
    ----------
    theme_element : element_rect
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        super().apply_figure(figure, targets)
        properties = self.properties
        if bboxes := targets.get("strip_background_y"):
            for bbox in bboxes:
                bbox.set(**properties)

    def blank_figure(self, figure: Figure, targets: dict[str, Any]):
        super().blank_figure(figure, targets)
        if rects := targets.get("strip_background_y"):
            for rect in rects:
                _blankout_rect(rect)


class strip_background(strip_background_x, strip_background_y):
    """
    Facet label background

    Parameters
    ----------
    theme_element : element_rect
    """


class rect(
    legend_key,
    legend_frame,
    legend_background,
    panel_background,
    panel_border,
    plot_background,
    strip_background,
):
    """
    All rectangle elements

    Parameters
    ----------
    theme_element : element_rect
    """


# value base themeables


class axis_ticks_length_major_x(themeable):
    """
    x-axis major-tick length

    Parameters
    ----------
    theme_element : float
        Value in points.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        try:
            t = ax.xaxis.get_major_ticks()[0]
        except IndexError:
            val = 0
        else:
            val = self.properties["value"] if t.tick1line.get_visible() else 0

        ax.xaxis.set_tick_params(which="major", size=val)


class axis_ticks_length_major_y(themeable):
    """
    y-axis major-tick length

    Parameters
    ----------
    theme_element : float
        Value in points.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        try:
            t = ax.yaxis.get_major_ticks()[0]
        except IndexError:
            val = 0
        else:
            val = self.properties["value"] if t.tick1line.get_visible() else 0

        ax.yaxis.set_tick_params(which="major", size=val)


class axis_ticks_length_major(
    axis_ticks_length_major_x, axis_ticks_length_major_y
):
    """
    Axis major-tick length

    Parameters
    ----------
    theme_element : float
        Value in points.
    """


class axis_ticks_length_minor_x(themeable):
    """
    x-axis minor-tick length

    Parameters
    ----------
    theme_element : float
        Value in points.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.xaxis.set_tick_params(
            which="minor", length=self.properties["value"]
        )


class axis_ticks_length_minor_y(themeable):
    """
    x-axis minor-tick length

    Parameters
    ----------
    theme_element : float
        Value in points.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.yaxis.set_tick_params(
            which="minor", length=self.properties["value"]
        )


class axis_ticks_length_minor(
    axis_ticks_length_minor_x, axis_ticks_length_minor_y
):
    """
    Axis minor-tick length

    Parameters
    ----------
    theme_element : float
        Value in points.
    """


class axis_ticks_length(axis_ticks_length_major, axis_ticks_length_minor):
    """
    Axis tick length

    Parameters
    ----------
    theme_element : float
        Value in points.
    """


class axis_ticks_pad_major_x(themeable):
    """
    x-axis major-tick padding

    Parameters
    ----------
    theme_element : float
        Value in points.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        val = self.properties["value"]

        for t in ax.xaxis.get_major_ticks():
            _val = val if t.tick1line.get_visible() else 0
            t.set_pad(_val)


class axis_ticks_pad_major_y(themeable):
    """
    y-axis major-tick padding

    Parameters
    ----------
    theme_element : float
        Value in points.

    Note
    ----
    Padding is not applied when the :class:`axis_ticks_major_y` are
    blank, but it does apply when the :class:`axis_ticks_length_major_y`
    is zero.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        val = self.properties["value"]

        for t in ax.yaxis.get_major_ticks():
            _val = val if t.tick1line.get_visible() else 0
            t.set_pad(_val)


class axis_ticks_pad_major(axis_ticks_pad_major_x, axis_ticks_pad_major_y):
    """
    Axis major-tick padding

    Parameters
    ----------
    theme_element : float
        Value in points.

    Note
    ----
    Padding is not applied when the :class:`axis_ticks_major` are
    blank, but it does apply when the :class:`axis_ticks_length_major`
    is zero.
    """


class axis_ticks_pad_minor_x(themeable):
    """
    x-axis minor-tick padding

    Parameters
    ----------
    theme_element : float

    Note
    ----
    Padding is not applied when the :class:`axis_ticks_minor_x` are
    blank, but it does apply when the :class:`axis_ticks_length_minor_x`
    is zero.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        val = self.properties["value"]

        for t in ax.xaxis.get_minor_ticks():
            _val = val if t.tick1line.get_visible() else 0
            t.set_pad(_val)


class axis_ticks_pad_minor_y(themeable):
    """
    y-axis minor-tick padding

    Parameters
    ----------
    theme_element : float

    Note
    ----
    Padding is not applied when the :class:`axis_ticks_minor_y` are
    blank, but it does apply when the :class:`axis_ticks_length_minor_y`
    is zero.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        val = self.properties["value"]

        for t in ax.yaxis.get_minor_ticks():
            _val = val if t.tick1line.get_visible() else 0
            t.set_pad(_val)


class axis_ticks_pad_minor(axis_ticks_pad_minor_x, axis_ticks_pad_minor_y):
    """
    Axis minor-tick padding

    Parameters
    ----------
    theme_element : float

    Note
    ----
    Padding is not applied when the :class:`axis_ticks_minor` are
    blank, but it does apply when the :class:`axis_ticks_length_minor`
    is zero.
    """


class axis_ticks_pad(axis_ticks_pad_major, axis_ticks_pad_minor):
    """
    Axis tick padding

    Parameters
    ----------
    theme_element : float
        Value in points.

    Note
    ----
    Padding is not applied when the :class:`axis_ticks` are blank,
    but it does apply when the :class:`axis_ticks_length` is zero.
    """


class axis_ticks_direction_x(themeable):
    """
    x-axis tick direction

    Parameters
    ----------
    theme_element : Literal["in", "out", "inout"]
        `in` for ticks inside the panel.
        `out` for ticks outside the panel.
        `inout` for ticks inside and outside the panel.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.xaxis.set_tick_params(
            which="major", tickdir=self.properties["value"]
        )


class axis_ticks_direction_y(themeable):
    """
    y-axis tick direction

    Parameters
    ----------
    theme_element : Literal["in", "out", "inout"]
        `in` for ticks inside the panel.
        `out` for ticks outside the panel.
        `inout` for ticks inside and outside the panel.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.yaxis.set_tick_params(
            which="major", tickdir=self.properties["value"]
        )


class axis_ticks_direction(axis_ticks_direction_x, axis_ticks_direction_y):
    """
    axis tick direction

    Parameters
    ----------
    theme_element : Literal["in", "out", "inout"]
        `in` for ticks inside the panel.
        `out` for ticks outside the panel.
        `inout` for ticks inside and outside the panel.
    """


class panel_spacing_x(themeable):
    """
    Horizontal spacing between the facet panels

    Parameters
    ----------
    theme_element : float
        Size as a fraction of the figure width.
    """


class panel_spacing_y(themeable):
    """
    Vertical spacing between the facet panels

    Parameters
    ----------
    theme_element : float
        Size as a fraction of the figure width.

    Notes
    -----
    It is deliberate to have the vertical spacing be a fraction of
    the width. That means that when :class:`panel_spacing_x` is the
    equal :class:`panel_spacing_x`, the spaces in both directions
    will be equal.
    """


class panel_spacing(panel_spacing_x, panel_spacing_y):
    """
    Spacing between the facet panels

    Parameters
    ----------
    theme_element : float
        Size as a fraction of the figure's dimension.
    """


# TODO: Distinct margins in all four directions
class plot_margin_left(themeable):
    """
    Plot Margin on the left

    Parameters
    ----------
    theme_element : float
        Must be in the [0, 1] range. It is specified
        as a fraction of the figure width and figure
        height.
    """


class plot_margin_right(themeable):
    """
    Plot Margin on the right

    Parameters
    ----------
    theme_element : float
        Must be in the [0, 1] range. It is specified
        as a fraction of the figure width and figure
        height.
    """


class plot_margin_top(themeable):
    """
    Plot Margin at the top

    Parameters
    ----------
    theme_element : float
        Must be in the [0, 1] range. It is specified
        as a fraction of the figure width and figure
        height.
    """


class plot_margin_bottom(themeable):
    """
    Plot Margin at the bottom

    Parameters
    ----------
    theme_element : float
        Must be in the [0, 1] range. It is specified
        as a fraction of the figure width and figure
        height.
    """


class plot_margin(
    plot_margin_left, plot_margin_right, plot_margin_top, plot_margin_bottom
):
    """
    Plot Margin

    Parameters
    ----------
    theme_element : float
        Must be in the [0, 1] range. It is specified
        as a fraction of the figure width and figure
        height.
    """


class panel_ontop(themeable):
    """
    Place panel background & gridlines over/under the data layers

    Parameters
    ----------
    theme_element : bool
        Default is False.
    """

    def apply_ax(self, ax: Axes):
        super().apply_ax(ax)
        ax.set_axisbelow(not self.properties["value"])


class aspect_ratio(themeable):
    """
    Aspect ratio of the panel(s)

    Parameters
    ----------
    theme_element : float
        `panel_height / panel_width`

    Notes
    -----
    For a fixed relationship between the `x` and `y` scales,
    use [](`~plotnine.coords.coord_fixed`).
    """


class dpi(themeable):
    """
    DPI with which to draw/save the figure

    Parameters
    ----------
    theme_element : int
    """

    # fig.set_dpi does not work
    # https://github.com/matplotlib/matplotlib/issues/24644

    @property
    def rcParams(self) -> dict[str, Any]:
        rcParams = super().rcParams
        rcParams["figure.dpi"] = self.properties["value"]
        return rcParams


class figure_size(themeable):
    """
    Figure size in inches

    Parameters
    ----------
    theme_element : tuple
        (width, height) in inches
    """

    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        figure.set_size_inches(self.properties["value"])


class legend_box(themeable):
    """
    How to box up multiple legends

    Parameters
    ----------
    theme_element : Literal["vertical", "horizontal"]
        Whether to stack up the legends vertically or
        horizontally.
    """


class legend_box_margin(themeable):
    """
    Padding between the legends and the box

    Parameters
    ----------
    theme_element : int
        Value in points.
    """


class legend_box_just(themeable):
    """
    Justification of legend boxes

    Parameters
    ----------
    theme_element : "left", "right", "center", "top", "bottom", "baseline", \
                    default=None
        If `None`, the value that will apply depends on :class:`legend_box`.
    """


class legend_direction(themeable):
    """
    Layout items in the legend

    Parameters
    ----------
    theme_element : Literal["vertical", "horizontal"]
        Vertically or horizontally
    """


class legend_key_width(themeable):
    """
    Legend key background width

    Parameters
    ----------
    theme_element : float
        Value in points
    """


class legend_key_height(themeable):
    """
    Legend key background height

    Parameters
    ----------
    theme_element : float
        Value in points.
    """


class legend_key_size(legend_key_width, legend_key_height):
    """
    Legend key background width and height

    Parameters
    ----------
    theme_element : float
        Value in points.
    """


class legend_ticks_length(themeable):
    """
    Length of ticks in the legend

    Parameters
    ----------
    theme_element : float
        A good value should be in the range `[0, 0.5]`.
    """


class legend_margin(themeable):
    """
    Padding between the legend and the inner box

    Parameters
    ----------
    theme_element : float
        Value in points
    """


class legend_box_spacing(themeable):
    """
    Spacing between the legend and the plotting area

    Parameters
    ----------
    theme_element : float
        Value in points.
    """


class legend_spacing(themeable):
    """
    Spacing between two adjacent legends

    Parameters
    ----------
    theme_element : float
        Value in points.
    """


class legend_position(themeable):
    """
    Location of legend

    Parameters
    ----------
    theme_element : "right" | "left" | "top" | "bottom" | "none" | tuple
        If `none`, no legend.
        If a tuple, 2-floats in the range `[0, 1]` for the location
        in screen coordinates.
    """


class legend_title_position(themeable):
    """
    Position of legend title

    Parameters
    ----------
    theme_element : None | "top" | "bottom" | "left" | "right"
        Position of the legend title. The default depends on the position
        of the legend.
    """


class legend_text_position(themeable):
    """
    Position of the legend text

    Alignment of legend title

    Parameters
    ----------
    theme_element : None | "top" | "bottom" | "left" | "right"
        Position of the legend key text. The default, depends on the
        position of the legend.
    """


class legend_key_spacing_x(themeable):
    """
    Horizontal spacing between two entries in a legend

    Parameters
    ----------
    theme_element : int
        Size in points
    """


class legend_key_spacing_y(themeable):
    """
    Vertical spacing between two entries in a legend

    Parameters
    ----------
    theme_element : int
        Size in points
    """


class legend_key_spacing(legend_key_spacing_x, legend_key_spacing_y):
    """
    Spacing between two entries in a legend

    Parameters
    ----------
    theme_element : int
        Size in points
    """


class strip_align_x(themeable):
    """
    Vertical alignment of the strip & its background w.r.t the panel border

    Parameters
    ----------
    theme_element : float
        Value as a proportion of the strip size. A good value
        should be the range `[-1, 0.5]`. A negative value
        puts the strip inside the axes. A positive value creates
        a margin between the strip and the axes. `0` puts the
        strip on top of the panels.
    """


class strip_align_y(themeable):
    """
    Horizontal alignment of the strip & its background w.r.t the panel border

    Parameters
    ----------
    theme_element : float
        Value as a proportion of the strip size. A good value
        should be the range `[-1, 0.5]`. A negative value
        puts the strip inside the axes. A positive value creates
        a margin between the strip and the axes. `0` puts the
        strip exactly beside the panels.
    """


class strip_align(strip_align_x, strip_align_y):
    """
    Alignment of the strip & its background w.r.t the panel border

    Parameters
    ----------
    theme_element : float
        Value as a proportion of the strip text size. A good value
        should be the range `[-1, 0.5]`. A negative value
        puts the strip inside the axes and a positive value
        creates a space between the strip and the axes.
    """


# Deprecated


class subplots_adjust(themeable):
    def apply_figure(self, figure: Figure, targets: dict[str, Any]):
        warn(
            "You no longer need to use subplots_adjust to make space for "
            "the legend or text around the panels. This paramater will be "
            "removed in a future version. You can still use 'plot_margin' "
            "'panel_spacing' for your other spacing needs.",
            FutureWarning,
        )


@deprecated_themeable_name
class legend_entry_spacing(legend_key_spacing):
    pass


@deprecated_themeable_name
class legend_entry_spacing_x(legend_key_spacing_x):
    pass


@deprecated_themeable_name
class legend_entry_spacing_y(legend_key_spacing_y):
    pass


class legend_title_align(themeable):
    def __init__(self):
        msg = (
            "Themeable 'legend_title_align' is deprecated. Use the "
            "horizontal and vertical alignment parameters ha & va "
            "of 'element_text' with 'lenged_title'."
        )
        warn(msg, FutureWarning, stacklevel=1)
