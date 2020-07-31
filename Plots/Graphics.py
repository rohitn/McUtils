"""
Provides Graphics base classes that can be extended upon
"""


import platform
# import matplotlib.figure
# import matplotlib.axes
from .Properties import GraphicsPropertyManager, GraphicsPropertyManager3D
from .Styling import Styled, ThemeManager
from .Backends import Backends

__all__ = ["GraphicsBase", "Graphics", "Graphics3D", "GraphicsGrid"]


class GraphicsException(Exception):
    pass

########################################################################################################################
#
#                                               GraphicsBase
#
from abc import *

class GraphicsBase(metaclass=ABCMeta):
    """
    The base class for all things Graphics
    Defines the common parts of the interface with some calling into matplotlib
    """
    opt_keys = {
        'axes_labels',
        'plot_label',
        'plot_range',
        'plot_legend',
        'ticks',
        'scale',
        'image_size',
        'event_handlers',
        'animated',
        'background',
        'epilog'
        'prolog',
        'aspect_ratio',
        'padding'
    }
    def _get_def_opt(self, key, val):
        if val is None:
            try:
                v = object.__getattribute__(self, '_'+key) # we overloaded getattr
            except AttributeError:
                try:
                    v = object.__getattribute__(self._prop_manager, '_' + key)  # we overloaded getattr
                except AttributeError:
                    v = None
            if v is None and key in self.default_style:
                v = self.default_style[key]
            return v
        else:
            return val

    def __init__(self,
                 *args,
                 figure = None,
                 tighten = False,
                 axes = None,
                 subplot_kw = None,
                 parent = None,
                 image_size = None,
                 padding = None,
                 aspect_ratio = None,
                 non_interactive = None,
                 mpl_backend = None,
                 theme=None,
                 prop_manager = GraphicsPropertyManager,
                 theme_manager = ThemeManager,
                 **opts
                 ):
        """
        :param args:
        :type args:
        :param figure:
        :type figure: matplotlib.figure.Figure | None
        :param axes:
        :type axes: matplotlib.axes.Axes | None
        :param subplot_kw:
        :type subplot_kw: dict | None
        :param parent:
        :type parent: GraphicsBase | None
        :param opts:
        :type opts:
        """

        if subplot_kw is None:
            subplot_kw = {}

        self.non_interactive = non_interactive
        # if mpl_backend is None and platform.system() == "Darwin":
        #     mpl_backend = "TkAgg"
        self.mpl_backend = mpl_backend
        aspect_ratio = self._get_def_opt('aspect_ratio', aspect_ratio)
        image_size = self._get_def_opt('image_size', image_size)
        padding = self._get_def_opt('padding', padding)
        if image_size is not None and 'figsize' not in subplot_kw:
            try:
                w, h = image_size
            except TypeError:
                w = image_size
                asp = aspect_ratio
                if asp is None or isinstance(asp, str):
                    asp = 4.8/6.4
                h = w * asp
            if padding is not None:
                pw, ph = padding
                try:
                    pwx, pwy = pw
                except (TypeError, ValueError):
                    pwx = pwy = pw
                try:
                    phx, phy = ph
                except (TypeError, ValueError):
                    phx = phy = ph
                w += pwx + pwy
                h += phx + phy
                image_size = (w, h)
            subplot_kw['figsize'] = (w/72., h/72.)

        theme = self._get_def_opt('theme', theme)
        if theme is not None:
            if isinstance(theme, (str, dict)):
                theme = [theme]
            with theme_manager(*theme):
                self.figure, self.axes = self._init_suplots(figure, axes, *args, **subplot_kw)
        else:
            self.figure, self.axes = self._init_suplots(figure, axes, *args, **subplot_kw)
        self._prop_manager = prop_manager(self, self.figure, self.axes)
        self.set_options(padding=padding, aspect_ratio=aspect_ratio, image_size=image_size, **opts)

        self.event_handler = None
        self._shown = False
        self.parent = parent
        self.animator = None
        self.tighten = tighten

    @staticmethod
    def _subplot_init(*args, mpl_backend=None, **kw):
        if mpl_backend is not None:
            import matplotlib as mpl
            mpl.use(mpl_backend)
        import matplotlib.pyplot as plt

        return plt.subplots(*args, **kw)

    def _init_suplots(self, figure, axes, *args, **kw):
        """Initializes the subplots for the Graphics object

        :param figure:
        :type figure:
        :param axes:
        :type axes:
        :param args:
        :type args:
        :param kw:
        :type kw:
        :return: figure, axes
        :rtype: matplotlib.figure.Figure, matplotlib.axes.Axes
        """

        if figure is None:
            figure, axes = self._subplot_init(*args, mpl_backend=self.mpl_backend, **kw)
            # yes axes is overwritten intentionally for now -- not sure how to "reparent" an Axes object
        elif isinstance(figure, GraphicsBase):
            axes = figure.axes # type: matplotlib.axes.Axes
            figure = figure.figure # type: matplotlib.figure.Figure

        if axes is None:
            axes = figure.add_subplot(1, 1, 1) # type: matplotlib.axes.Axes

        return figure, axes

    @property
    def event_handlers(self):
        from .Interactive import EventHandler
        h = self.event_handler  # type: EventHandler
        if h is not None:
            h = h.data
        return h

    @property
    def animated(self):
        return self._animated

    def bind_events(self, *handlers, **events):
        from .Interactive import EventHandler

        if len(handlers) > 0 and isinstance(handlers[0], dict):
            handlers = handlers[0]
        elif len(handlers) == 0 or (len(handlers) > 0 and handlers[0] is not None):
            handlers = dict(handlers)
        if isinstance(handlers, dict):
            handlers = dict(handlers, **events)
            if self.event_handler is None:
                self.event_handler = EventHandler(self, **handlers)
            else:
                self.event_handler.bind(**handlers)

    def create_animation(self, *args, **opts):
        from .Interactive import Animator

        if len(args) > 0 and args[0] is not None:
            if self.animator is not None:
                self.animator.stop()
            self.animator = Animator(self, *args, **opts)

    def set_options(self,
                    event_handlers=None,
                    animated=None,
                    prolog=None,
                    epilog=None,
                    **opts
                    ):
        """Sets options for the plot
        :param event_handlers:
        :param animated:
        :param opts:
        :type opts:
        :return:
        :rtype:
        """
        self.bind_events(event_handlers)
        self._animated = animated
        self.create_animation(animated)

        self._prolog = prolog
        if self._prolog is not None:
            self.prolog = prolog

        self._epilog = epilog
        if self._epilog is not None:
            self.epilog = epilog

    @property
    def prolog(self):
        return self._prolog
    @prolog.setter
    def prolog(self, p):
        # might want to clear the elements in the prolog?
        self._prolog = p

    @property
    def epilog(self):
        return self._epilog
    @epilog.setter
    def epilog(self, e):
        # might want to clear the elements in the epilog?
        self._epilog = e

    def __getattr__(self, item):
        reraise_error = None
        axes = object.__getattribute__(self, 'axes')
        try:
            meth = getattr(axes, item)
        except AttributeError as e:
            if 'Axes' not in e.args[0]:
                reraise_error = e
            else:
                try:
                    meth = getattr(self.figure, item)
                except AttributeError as e:
                    if 'Figure' not in e.args[0]:
                        reraise_error = e
                    else:
                        reraise_error = AttributeError("'{}' object has no attribute '{}'".format(
                            type(self).__name__,
                            item
                        ))
        if reraise_error is not None:
            raise reraise_error

        return meth

    def copy_axes(self):
        """Copies the axes object

        :return:
        :rtype: matplotlib.axes.Axes
        """
        raise GraphicsException("{}.{} this hack doesn't work anymore".format(
                                type(self).__name__,
                                "copy_axes"
                                ))

        import pickle, io

        buf = io.BytesIO()
        pickle.dump(self.axes, buf)
        buf.seek(0)
        return pickle.load(buf)

    def refresh(self):
        """Refreshes the axes

        :return:
        :rtype:
        """

        self.axes = self.copy_axes()
        self.figure = self.axes.figure

        return self

    @property
    def opts(self):
        opt_dict = {}
        for k in self.opt_keys:
            if k in self.__dict__:
                opt_dict[k] = getattr(self, k)
            elif "_"+k in self.__dict__:
                opt_dict[k] = getattr(self, "_" + k)
        return opt_dict

    def copy(self):
        """Creates a copy of the object with new axes and a new figure

        :return:
        :rtype:
        """
        return type(self)(**self.opts)

    def prep_show(self):
        self.set_options(**self.opts)  # matplotlib is dumb so it makes sense to just reset these again...
        if self.epilog is not None:
            self._epilog_graphics = [e.plot(self.axes) for e in self.epilog]
        if self.prolog is not None:
            self._prolog_graphics = [p.plot(self.axes) for p in self.prolog]
        if self.tighten:
            self.figure.tight_layout()
        self._shown = True
    def show(self, reshow = True):
        from .VTKInterface import VTKWindow

        if isinstance(self.figure, VTKWindow):
            self.figure.show()
        else:
            import matplotlib.pyplot as plt

            if self.non_interactive:
                plt.ioff()
            elif self.non_interactive is False:
                plt.ion()

            if reshow or not self._shown:
                self.prep_show()
                plt.show()
            else:
                self._shown = False
                self.refresh().show()
                # raise GraphicsException("{}.show can only be called once per object".format(type(self).__name__))

    def clear(self):
        ax = self.axes  # type: matplotlib.axes.Axes
        all_things = ax.artists + ax.patches
        for a in all_things:
            a.remove()

    def _repr_html_(self):
        # hacky, but hopefully enough to make it work?
        return self.figure._repr_html_()

    def savefig(self, where, format='png', **kw):
        if 'facecolor' not in kw:
            kw['facecolor'] = self.background# -_- stupid MPL
        return self.figure.savefig(where,
                    format=format,
                    **kw
                    )
    def to_png(self):
        import io
        buf = io.BytesIO()
        fig = self.figure
        fig.savefig(buf,
                    format='png',
                    facecolor = self.background #-_- stupid MPL
                    )
        buf.seek(0)
        return buf

    def _repr_png_(self):
        # currently assumes a matplotlib backend...
        return self.to_png().read()

########################################################################################################################
#
#                                               Graphics
#
class Graphics(GraphicsBase):
    """
    A mini wrapper to matplotlib.pyplot to create a unified interface I know how to work with
    """
    default_style = dict(
        theme='mccoy',
        frame=((True, False), (True, False)),
        aspect_ratio=1,
        image_size=300,
        padding = ((30, 10), (30, 10))
    )

    def set_options(self,
                    axes_labels=None,
                    plot_label=None,
                    plot_range=None,
                    plot_legend=None,
                    frame=None,
                    ticks=None,
                    scale=None,
                    padding=None,
                    ticks_style=None,
                    image_size=None,
                    aspect_ratio=None,
                    background=None,
                    colorbar=None,
                    prolog=None,
                    epilog=None,
                    **parent_opts
                    ):

        super().set_options(**parent_opts)

        opts = (
            ('plot_label', plot_label),
            ('plot_legend', plot_legend),
            ('axes_labels', axes_labels),
            ('frame', frame),
            ('plot_range', plot_range),
            ('ticks', ticks),
            ('ticks_style', ticks_style),
            ('scale', scale),
            ('aspect_ratio', aspect_ratio),
            ('image_size', image_size),
            ('padding', padding),
            ('background', background),
            ('colorbar', colorbar)
        )
        for oname, oval in opts:
            oval = self._get_def_opt(oname, oval)
            if oval is not None:
                setattr(self, oname, oval)
    # attaching custom property setters
    @property
    def plot_label(self):
        return self._prop_manager.plot_label
    @plot_label.setter
    def plot_label(self, value):
        self._prop_manager.plot_label = value

    @property
    def plot_legend(self):
        return self._prop_manager.plot_legend
    @plot_legend.setter
    def plot_legend(self, value):
        self._prop_manager.plot_legend = value

    @property
    def axes_labels(self):
        return self._prop_manager.axes_labels
    @axes_labels.setter
    def axes_labels(self, value):
        self._prop_manager.axes_labels = value

    @property
    def frame(self):
        return self._prop_manager.frame
    @frame.setter
    def frame(self, value):
        self._prop_manager.frame = value

    @property
    def plot_range(self):
        return self._prop_manager.plot_range
    @plot_range.setter
    def plot_range(self, value):
        self._prop_manager.plot_range = value

    @property
    def ticks(self):
        return self._prop_manager.ticks
    @ticks.setter
    def ticks(self, value):
        self._prop_manager.ticks = value

    @property
    def ticks_style(self):
        return self._prop_manager.ticks_style
    @ticks_style.setter
    def ticks_style(self, value):
        self._prop_manager.ticks_style = value

    @property
    def scale(self):
        return self._prop_manager.ticks
    @scale.setter
    def scale(self, value):
        self._prop_manager.scale = value

    @property
    def aspect_ratio(self):
        return self._prop_manager.aspect_ratio
    @aspect_ratio.setter
    def aspect_ratio(self, value):
        self._prop_manager.aspect_ratio = value

    @property
    def image_size(self):
        return self._prop_manager.image_size
    @image_size.setter
    def image_size(self, value):
        self._prop_manager.image_size = value

    @property
    def padding(self):
        return self._prop_manager.padding
    @padding.setter
    def padding(self, value):
        self._prop_manager.padding = value

    @property
    def background(self):
        return self._prop_manager.background
    @background.setter
    def background(self, value):
        self._prop_manager.background = value

    @property
    def colorbar(self):
        return self._prop_manager.colorbar
    @colorbar.setter
    def colorbar(self, value):
        self._prop_manager.colorbar = value
    def add_colorbar(self, graphics=None, norm=None, cmap=None, **kw):
        fig = self.figure  # type: matplotlib.figure.Figure
        ax = self.axes  # type: matplotlib.axes.Axes
        if graphics is None:
            import matplotlib.cm as cm
            graphics = cm.ScalarMappable(norm=norm, cmap=cmap)
        fig.colorbar(graphics, **kw)

########################################################################################################################
#
#                                               Graphics3D
#
class Graphics3D(Graphics):
    """A mini wrapper to matplotlib.pyplot to create a unified interface I know how to work with"""
    def __init__(self, *args,
                 figure=None,
                 axes=None,
                 subplot_kw=None,
                 event_handlers=None,
                 animate=None,
                 axes_labels=None,
                 plot_label=None,
                 plot_range=None,
                 plot_legend=None,
                 ticks=None,
                 scale=None,
                 ticks_style=None,
                 image_size=None,
                 background=None,
                 backend=Backends.MPL,
                 **kwargs
                 ):

        self._backend = backend
        super().__init__(
            *args,
            figure=figure,
            axes=axes,
            subplot_kw=subplot_kw,
            axes_labels=axes_labels,
            plot_label=plot_label,
            plot_range=plot_range,
            plot_legend=plot_legend,
            ticks=ticks,
            scale=scale,
            ticks_style=ticks_style,
            image_size=image_size,
            event_handlers=event_handlers,
            animate=animate,
            prop_manager=GraphicsPropertyManager3D,
            **kwargs
        )

    @staticmethod
    def _subplot_init(*args, backend = Backends.MPL, mpl_backend=None, **kw):
        if backend == Backends.VTK:
            from .VTKInterface import VTKWindow
            window = VTKWindow()
            return window, window
        else:
            from mpl_toolkits.mplot3d import Axes3D
            if mpl_backend is not None:
                import matplotlib as mpl
                mpl.use(mpl_backend)
            import matplotlib.pyplot as plt

            subplot_kw = {"projection": '3d'}
            if 'subplot_kw' in kw:
                subplot_kw = dict(subplot_kw, **kw['subplot_kw'])
                del kw['subplot_kw']
            return plt.subplots(*args, subplot_kw=subplot_kw, **kw)

    def _init_suplots(self, figure, axes, *args, **kw):
        """matplotlib subplot instantiation

        :param figure:
        :type figure:
        :param axes:
        :type axes:
        :param args:
        :type args:
        :param kw:
        :type kw:
        :return:
        :rtype:
        """

        if figure is None:
            figure, axes = self._subplot_init(*args, backend = self._backend, mpl_backend=self.mpl_backend, **kw)
        elif isinstance(figure, GraphicsBase):
            axes = figure.axes
            figure = figure.figure

        if axes is None:
            if self._backend == Backends.MPL:
                axes = figure
            else:
                axes = figure.add_subplot(1, 1, 1, projection='3d')

        return figure, axes

    @property
    def plot_label(self):
        return self._prop_manager.plot_label
    @plot_label.setter
    def plot_label(self, value):
        self._prop_manager.plot_label = value

    @property
    def plot_legend(self):
        return self._prop_manager.plot_legend
    @plot_legend.setter
    def plot_legend(self, value):
        self._prop_manager.plot_legend = value

    @property
    def axes_labels(self):
        return self._prop_manager.axes_labels
    @axes_labels.setter
    def axes_labels(self, value):
        self._prop_manager.axes_labels = value

    @property
    def frame(self):
        return self._prop_manager.frame
    @frame.setter
    def frame(self, value):
        self._prop_manager.frame = value

    @property
    def plot_range(self):
        return self._prop_manager.plot_range
    @plot_range.setter
    def plot_range(self, value):
        self._prop_manager.plot_range = value

    @property
    def ticks(self):
        return self._prop_manager.ticks
    @ticks.setter
    def ticks(self, value):
        self._prop_manager.ticks = value

    @property
    def ticks_style(self):
        return self._prop_manager.ticks_style
    @ticks_style.setter
    def ticks_style(self, value):
        self._prop_manager.ticks_style = value

    @property
    def scale(self):
        return self._prop_manager.ticks
    @scale.setter
    def scale(self, value):
        self._prop_manager.scale = value

    @property
    def aspect_ratio(self):
        return self._prop_manager.aspect_ratio
    @aspect_ratio.setter
    def aspect_ratio(self, value):
        self._prop_manager.aspect_ratio = value

    @property
    def image_size(self):
        return self._prop_manager.image_size
    @image_size.setter
    def image_size(self, value):
        self._prop_manager.image_size = value

    @property
    def padding(self):
        return self._prop_manager.padding
    @padding.setter
    def padding(self, value):
        self._prop_manager.padding = value

    @property
    def background(self):
        return self._prop_manager.background
    @background.setter
    def background(self, value):
        self._prop_manager.background = value

    @property
    def colorbar(self):
        return self._prop_manager.colorbar
    @colorbar.setter
    def colorbar(self, value):
        self._prop_manager.colorbar = value

    # set plot ranges
    @property
    def ticks(self):
        return self._ticks

    @property
    def aspect_ratio(self):
        return self._aspect_ratio
    @aspect_ratio.setter
    def aspect_ratio(self, ar):
        pass
        # if isinstance(ar, (float, int)):
        #     a, b = self.plot_range
        #     cur_ar = (b[1] - b[0]) / (a[1] - a[0])
        #     targ_ar = ar / cur_ar
        #     self.axes.set_aspect(targ_ar)
        # elif isinstance(ar, str):
        #     self.axes.set_aspect(ar)
        # else:
        #     self.axes.set_aspect(ar[0], **ar[1])

########################################################################################################################
#
#                                               GraphicsGrid
#
class GraphicsGrid(GraphicsBase):
    default_style = dict(
        spacings=(.2, .2),
        padding=((30, 10), (30, 10))
    )
    def __init__(self,
                 *args,
                 nrows=2, ncols=2,
                 graphics_class=Graphics,
                 figure=None,
                 axes=None,
                 subplot_kw=None,
                 _subplot_init=None,
                 mpl_backend = None,
                 tighten = False,
                 **opts
                 ):

        # if mpl_backend is None and platform.system() == "Darwin":
        #     mpl_backend = "TkAgg"
        self.mpl_backend = mpl_backend
        super().__init__(
            figure=figure, axes=axes,
            graphics_class=graphics_class
        )
        self.figure, self.axes = self._init_suplots(
            nrows, ncols,
            figure, axes,
            graphics_class,
            *args,
            subplot_kw=subplot_kw,
            _subplot_init=graphics_class._subplot_init if _subplot_init is None else _subplot_init,
            mpl_backend = mpl_backend,
            **opts
        )
        self.shape = (nrows, ncols)
        self._colorbar_axis = None # necessary hack for only GraphicsGrid
        self.tighten = tighten

    def _get_def_opt(self, key, val):
        if val is None:
            try:
                v = object.__getattribute__(self, '_'+key) # we overloaded getattr
            except AttributeError:
                if key in self.default_style:
                    v = self.default_style[key]
                else:
                    v = None
            return v
        else:
            return val
    def set_options(self,
                    image_size = None,
                    colorbar = None,
                    spacings = None,
                    padding = None,
                    tight = None,
                    **ignored
                    ):

        self._image_size = self._get_def_opt('image_size', image_size)
        if self._image_size is not None:
            self.image_size = self._image_size

        self._colorbar = colorbar
        if colorbar is not None:
            self.colorbar = colorbar

        self._spacings = self._get_def_opt('spacings', spacings)
        if self._spacings is not None:
            self.spacings = self._spacings

        self._padding = self._get_def_opt('padding', padding)
        if self._padding is not None:
            self.padding = self._padding

    def _init_suplots(self,
                      nrows, ncols, figure, axes, graphics_class, *args,
                      subplot_kw=None, _subplot_init=None,
                      fig_kw=None, mpl_backend = None,
                      **kw
                      ):
        """Initializes the subplots for the Graphics object

        :param figure:
        :type figure:
        :param axes:
        :type axes:
        :param args:
        :type args:
        :param kw:
        :type kw:
        :return: figure, axes
        :rtype: matplotlib.figure.Figure, matplotlib.axes.Axes
        """
        import matplotlib.figure, matplotlib.axes
        if mpl_backend is not None:
            import matplotlib
            matplotlib.use(mpl_backend)

        if figure is None:
            if subplot_kw is None:
                subplot_kw = {}
            if fig_kw is None:
                fig_kw = {}
            if 'figsize' not in fig_kw:
                w = nrows * 300
                h = ncols * 300
                fig_kw['figsize'] = (w/72., h/72.) #(4*ncols, 4*nrows)
            figure, axes = _subplot_init(*args, nrows = nrows, ncols=ncols, subplot_kw=subplot_kw, **fig_kw)

            if isinstance(axes, matplotlib.axes.Axes):
                axes = [[axes]]
            elif isinstance(axes[0], matplotlib.axes.Axes):
                if ncols == 1:
                    axes = [[ax] for ax in axes]
                else:
                    axes = [axes]

            # if 'image_size' not in kw:
            #     kw['image_size'] = (300, 300)
            for i in range(nrows):
                for j in range(ncols):
                    axes[i][j] = graphics_class(figure=figure, axes=axes[i][j], **kw)
        elif isinstance(figure, GraphicsGrid):
            axes = figure.axes  # type: matplotlib.axes.Axes
            figure = figure.figure  # type: matplotlib.figure.Figure

        if axes is None:
            axes = [
                graphics_class(
                    figure.add_subplot(nrows, ncols, i),
                    **kw
                ) for i in range(nrows * ncols)
            ]

        return figure, axes

    def __iter__(self):
        import itertools as ip
        return ip.chain(*self.axes)
    def __getitem__(self, item):
        try:
            i, j = item
        except ValueError:
            return self.axes[item]
        else:
            return self.axes[i][j]

    def __setitem__(self, item, val):
        try:
            i, j = item
        except ValueError:
            self.axes[item] = val
        else:
            self.axes[i][j] = val

    # set size
    def calc_image_size(self):
        w=0; h=0
        for f in self:
            wh = f.image_size
            if wh is not None:
                w += wh[0]
                h += wh[1]
        return w, h
    @property
    def image_size(self):
        if self._image_size is None:
            self._image_size = self.calc_image_size()
        return self._image_size

    @property
    def colorbar(self):
        return self._colorbar
    @colorbar.setter
    def colorbar(self, c):
        self._colorbar = c
        if self._colorbar is True:
            self.add_colorbar()
        elif isinstance(self._colorbar, dict):
            self.add_colorbar(**self.colorbar)

    def add_colorbar(self, graphics=None, norm=None, cmap=None, **kw):
        fig = self.figure  # type: matplotlib.figure.Figure
        ax = self.axes  # type: matplotlib.axes.Axes
        if graphics is None:
            import matplotlib.cm as cm
            graphics = cm.ScalarMappable(norm=norm, cmap=cmap)
        if 'cax' not in kw:
            if self._colorbar_axis is None:
                self.padding_right = .1
                self._colorbar_axis = fig.add_axes([0.93, 0.15, 0.02, 0.7])
            kw['cax'] = self._colorbar_axis

        fig.colorbar(graphics, **kw)

    def prep_show(self):
        self.image_size = self.image_size
        self.spacings = self.spacings
        self.padding = self.padding
        if self.tighten:
            self.figure.tight_layout()

    def show(self):
        for f in self:
            if isinstance(f, GraphicsBase):
                f.prep_show()
        self.prep_show()
        f.show()
