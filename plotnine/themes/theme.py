from __future__ import annotations

import typing
from copy import copy, deepcopy
from functools import cached_property
from typing import overload

from ..exceptions import PlotnineError
from ..options import get_option, set_option
from .themeable import Themeables, themeable

if typing.TYPE_CHECKING:
    from typing import Any, Type

    from typing_extensions import Self

    from plotnine import ggplot
    from plotnine.typing import Axes, Figure

# All complete themes are initiated with these rcparams. They
# can be overridden.
default_rcparams = {
    "axes.axisbelow": "True",
    "font.sans-serif": [
        "Helvetica",
        "DejaVu Sans",  # MPL ships with this one
        "Avant Garde",
        "Computer Modern Sans serif",
        "Arial",
    ],
    "font.serif": [
        "Times",
        "Palatino",
        "New Century Schoolbook",
        "Bookman",
        "Computer Modern Roman",
        "Times New Roman",
    ],
    "lines.antialiased": "True",
    "patch.antialiased": "True",
    "timezone": "UTC",
}


class theme:
    """
    Base class for themes

    In general, only complete themes should subclass this class.

    Parameters
    ----------
    complete : bool
        Themes that are complete will override any existing themes.
        themes that are not complete (ie. partial) will add to or
        override specific elements of the current theme. e.g:

        ```python
        theme_gray() + theme_xkcd()
        ```

        will be completely determined by [](`~plotnine.themes.theme_xkcd`),
        but:

        ```python
        theme_gray() + theme(axis_text_x=element_text(angle=45))
        ```

        will only modify the x-axis text.
    kwargs: dict
        kwargs are :ref:`themeables <themeables>`. The themeables are
        elements that are subclasses of `themeable`. Many themeables
        are defined using theme elements i.e

        - [](`~plotnine.themes.element_line`)
        - [](`~plotnine.themes.element_rect`)
        - [](`~plotnine.themes.element_text`)

        These simply bind together all the aspects of a themeable
        that can be themed. See [](`~plotnine.themes.themeable.themeable`).

    Notes
    -----
    When subclassing, make sure to call :python:`theme.__init__`.
    After which you can customise :python:`self._rcParams` within
    the `__init__` method of the new theme. The `rcParams`
    should not be modified after that.
    """

    complete: bool

    # This is set when the figure is created,
    # it is useful at legend drawing time and
    # when applying the theme.
    plot: ggplot
    figure: Figure
    axs: list[Axes]

    # Dictionary to collect matplotlib objects that will
    # be targeted for theming by the themeables
    # It is initialised in the plot context and removed at
    # the end of it.
    _targets: dict[str, Any]

    def __init__(
        self,
        complete=False,
        # Generate themeables keyword parameters with
        #
        #     from plotnine.themes.themeable import themeable
        #     for name in themeable.registry():
        #         print(f'{name}=None,')
        axis_title_x=None,
        axis_title_y=None,
        axis_title=None,
        legend_title=None,
        legend_text_legend=None,
        legend_text_colorbar=None,
        legend_text=None,
        plot_title=None,
        plot_subtitle=None,
        plot_caption=None,
        strip_text_x=None,
        strip_text_y=None,
        strip_text=None,
        title=None,
        axis_text_x=None,
        axis_text_y=None,
        axis_text=None,
        text=None,
        axis_line_x=None,
        axis_line_y=None,
        axis_line=None,
        axis_ticks_minor_x=None,
        axis_ticks_minor_y=None,
        axis_ticks_major_x=None,
        axis_ticks_major_y=None,
        axis_ticks_major=None,
        axis_ticks_minor=None,
        axis_ticks_x=None,
        axis_ticks_y=None,
        axis_ticks=None,
        legend_ticks=None,
        panel_grid_major_x=None,
        panel_grid_major_y=None,
        panel_grid_minor_x=None,
        panel_grid_minor_y=None,
        panel_grid_major=None,
        panel_grid_minor=None,
        panel_grid=None,
        line=None,
        legend_key=None,
        legend_frame=None,
        legend_background=None,
        legend_box_background=None,
        panel_background=None,
        panel_border=None,
        plot_background=None,
        strip_background_x=None,
        strip_background_y=None,
        strip_background=None,
        rect=None,
        axis_ticks_length_major_x=None,
        axis_ticks_length_major_y=None,
        axis_ticks_length_major=None,
        axis_ticks_length_minor_x=None,
        axis_ticks_length_minor_y=None,
        axis_ticks_length_minor=None,
        axis_ticks_length=None,
        axis_ticks_pad_major_x=None,
        axis_ticks_pad_major_y=None,
        axis_ticks_pad_major=None,
        axis_ticks_pad_minor_x=None,
        axis_ticks_pad_minor_y=None,
        axis_ticks_pad_minor=None,
        axis_ticks_pad=None,
        axis_ticks_direction_x=None,
        axis_ticks_direction_y=None,
        axis_ticks_direction=None,
        panel_spacing_x=None,
        panel_spacing_y=None,
        panel_spacing=None,
        plot_margin_left=None,
        plot_margin_right=None,
        plot_margin_top=None,
        plot_margin_bottom=None,
        plot_margin=None,
        panel_ontop=None,
        aspect_ratio=None,
        dpi=None,
        figure_size=None,
        legend_box=None,
        legend_box_margin=None,
        legend_box_just=None,
        legend_direction=None,
        legend_key_width=None,
        legend_key_height=None,
        legend_key_size=None,
        legend_ticks_length=None,
        legend_margin=None,
        legend_box_spacing=None,
        legend_spacing=None,
        legend_position=None,
        legend_title_position=None,
        legend_text_position=None,
        legend_key_spacing_x=None,
        legend_key_spacing_y=None,
        legend_key_spacing=None,
        strip_align_x=None,
        strip_align_y=None,
        strip_align=None,
        subplots_adjust=None,
        **kwargs,
    ):
        self.themeables = Themeables()
        self.complete = complete
        self._is_setup = False

        if complete:
            self._rcParams = deepcopy(default_rcparams)
        else:
            self._rcParams = {}

        # Themeables
        official_themeables = themeable.registry()
        locals_args = dict(locals())
        it = (
            (name, element)
            for name, element in locals_args.items()
            if element is not None and name in official_themeables
        )
        new = themeable.from_class_name

        for name, element in it:
            self.themeables[name] = new(name, element)

        # Unofficial themeables (for extensions)
        for name, element in kwargs.items():
            self.themeables[name] = new(name, element)

    def __eq__(self, other: object) -> bool:
        """
        Test if themes are equal

        Mostly for testing purposes
        """
        return other is self or (
            isinstance(other, type(self))
            and other.themeables == self.themeables
            and other.rcParams == self.rcParams
        )

    @cached_property
    def T(self):
        """
        Convenient access to the themeables
        """
        return self.themeables

    @property
    def getp(self):
        return self.themeables.getp

    def P(self, name: str, key="value"):
        """
        Convenient access into the properties of the themeables

        Parameters
        ----------
        name :
            Themeable name
        key :
            Property name to lookup

        Returns
        -------
        :
            Value of themeable property
        """
        return self.themeables.property(name, key)

    def apply(self):
        """
        Apply this theme, then apply additional modifications in order.

        This method will be called once after plot has completed.
        Subclasses that override this method should make sure that the
        base class method is called.
        """
        self._add_default_themeable_properties()

        for th in self.themeables.values():
            th.apply(self)

    def setup(self, plot: ggplot):
        """
        Setup theme for applying

        This method will be called when the figure and axes have been created
        but before any plotting or other artists have been added to the
        figure. This method gives the theme and the elements references to
        the figure and/or axes.

        It also initialises where the artists to be themed will be stored.
        """
        from .elements.element_base import element_base

        self.plot = plot
        self.figure = plot.figure
        self.axs = plot.axs
        self._targets = {}

        for name, th in self.themeables.items():
            if isinstance(th.theme_element, element_base):
                th.theme_element.setup(self, name)

        self._is_setup = True

    def _add_default_themeable_properties(self):
        """
        Add default themeable properties that depend depend on the plot

        Some properties may be left unset (None) and their final values are
        best worked out dynamically after the plot has been built, but
        before the themeables are applied.

        This is where the theme is modified to add those values.
        """
        smart_title_and_subtitle_ha(self)

    @property
    def rcParams(self):
        """
        Return rcParams dict for this theme.

        Notes
        -----
        Subclasses should not need to override this method method as long as
        self._rcParams is constructed properly.

        rcParams are used during plotting. Sometimes the same theme can be
        achieved by setting rcParams before plotting or a apply
        after plotting. The choice of how to implement it is is a matter of
        convenience in that case.

        There are certain things can only be themed after plotting. There
        may not be an rcParam to control the theme or the act of plotting
        may cause an entity to come into existence before it can be themed.

        """
        try:
            rcParams = deepcopy(self._rcParams)
        except NotImplementedError:
            # deepcopy raises an error for objects that are drived from or
            # composed of matplotlib.transform.TransformNode.
            # Not desirable, but probably requires upstream fix.
            # In particular, XKCD uses matplotlib.patheffects.withStrok
            rcParams = copy(self._rcParams)

        for th in self.themeables.values():
            rcParams.update(th.rcParams)
        return rcParams

    def add_theme(self, other: theme) -> theme:
        """
        Add themes together

        Subclasses should not override this method.

        This will be called when adding two instances of class 'theme'
        together.
        A complete theme will annihilate any previous themes. Partial themes
        can be added together and can be added to a complete theme.
        """
        if self._is_setup:
            other.setup(self.plot)

        if other.complete:
            return other

        self.themeables.update(deepcopy(other.themeables))
        return self

    def __add__(self, other: theme) -> theme:
        """
        Add other theme to this theme
        """
        if not isinstance(other, theme):
            msg = f"Adding theme failed. {other} is not a theme"
            raise PlotnineError(msg)
        self = deepcopy(self)
        return self.add_theme(other)

    @overload
    def __radd__(self, other: theme) -> theme:
        ...

    @overload
    def __radd__(self, other: ggplot) -> ggplot:
        ...

    def __radd__(self, other: theme | ggplot) -> theme | ggplot:
        """
        Add theme to ggplot object or to another theme

        This will be called in one of two ways:

        ```python
        ggplot() + theme()
        theme1() + theme2()
        ```

        In both cases, `self` is the [](`~plotnine.themes.theme`)
        on the right hand side.

        Subclasses should not override this method.
        """
        # ggplot() + theme, get theme
        # if hasattr(other, 'theme'):
        if not isinstance(other, theme):
            if self.complete:
                other.theme = self
            else:
                # If no theme has been added yet,
                # we modify the default theme
                other.theme = other.theme or theme_get()
                other.theme = other.theme.add_theme(self)
            return other
        # theme1 + theme2
        else:
            if self.complete:
                # e.g. other + theme_gray()
                return self
            else:
                # e.g. other + theme(...)
                return other.add_theme(self)

    def __iadd__(self, other: theme) -> Self:
        """
        Add theme to theme
        """
        self.add_theme(other)
        return self

    def __deepcopy__(self, memo: dict) -> theme:
        """
        Deep copy without copying the figure
        """
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        old = self.__dict__
        new = result.__dict__

        shallow = {"plot", "figure", "axs"}
        for key, item in old.items():
            if key in shallow:
                new[key] = item
                memo[id(new[key])] = new[key]
            else:
                new[key] = deepcopy(item, memo)

        return result

    def to_retina(self) -> theme:
        """
        Return a retina-sized version of this theme

        The result is a theme that has double the dpi.
        """
        dpi = self.themeables.property("dpi")
        return self + theme(dpi=dpi * 2)


def theme_get() -> theme:
    """
    Return the default theme

    The default theme is the one set (using [](`~plotnine.themes.theme_set`))
    by the user. If none has been set, then [](`~plotnine.themes.theme_gray`)
    is the default.
    """
    from .theme_gray import theme_gray

    _theme = get_option("current_theme")
    if isinstance(_theme, type):
        _theme = _theme()
    return _theme or theme_gray()


def theme_set(new: theme | Type[theme]) -> theme:
    """
    Change the current(default) theme

    Parameters
    ----------
    new : theme
        New default theme

    Returns
    -------
    out : theme
        Previous theme
    """
    if not isinstance(new, theme) and not issubclass(new, theme):
        raise PlotnineError("Expecting object to be a theme")

    out: theme = get_option("current_theme")
    set_option("current_theme", new)
    return out


def theme_update(**kwargs: themeable):
    """
    Modify elements of the current theme

    Parameters
    ----------
    kwargs : dict
        Theme elements
    """
    assert "complete" not in kwargs
    theme_set(theme_get() + theme(**kwargs))  # pyright: ignore


def smart_title_and_subtitle_ha(plot_theme: theme):
    """
    Smartly add the horizontal alignment for the title and subtitle
    """
    from .elements import element_text

    thm = plot_theme.themeables
    has_title = "plot_title" in plot_theme._targets
    has_subtitle = "plot_subtitle" in plot_theme._targets

    title_ha = plot_theme.getp(("plot_title", "ha"))
    subtitle_ha = plot_theme.getp(("plot_subtitle", "ha"))
    default_title_ha, default_subtitle_ha = "center", "left"
    kwargs = {}

    if not title_ha:
        if has_subtitle and not subtitle_ha:
            title_ha = default_subtitle_ha
        else:
            title_ha = default_title_ha
        kwargs["plot_title"] = element_text(ha=title_ha)

    if not subtitle_ha:
        subtitle_ha = default_subtitle_ha
        kwargs["plot_subtitle"] = element_text(ha=subtitle_ha)

    if kwargs:
        plot_theme += theme(**kwargs)
