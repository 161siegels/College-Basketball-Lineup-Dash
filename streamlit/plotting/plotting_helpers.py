import seaborn as sns
from seaborn.distributions import _freedman_diaconis_bins

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc
from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import HoverTool
from math import pi
import numpy as np
from typing import *
import altair as alt
import pandas as pd

def create_ncaa_half_court(ax=None, three_line='mens', court_color='#dfbb85',
                           lw=3, lines_color='black', lines_alpha=0.5,
                           paint_fill='blue', paint_alpha=0.4,
                           inner_arc=False):
    """
    Version 2020.2.19

    Creates NCAA Basketball Half Court
    Dimensions are in feet (Court is 97x50 ft)
    Created by: Rob Mulla / https://github.com/RobMulla

    * Note that this function uses "feet" as the unit of measure.
    * NCAA Data is provided on a x range: 0, 100 and y-range 0 to 100
    * To plot X/Y positions first convert to feet like this:
    ```
    Events['X_'] = (Events['X'] * (94/100))
    Events['Y_'] = (Events['Y'] * (50/100))
    ```
    ax: matplotlib axes if None gets current axes using `plt.gca`

    three_line: 'mens', 'womens' or 'both' defines 3 point line plotted
    court_color : (hex) Color of the court
    lw : line width
    lines_color : Color of the lines
    lines_alpha : transparency of lines
    paint_fill : Color inside the paint
    paint_alpha : transparency of the "paint"
    inner_arc : paint the dotted inner arc
    """
    if ax is None:
        ax = plt.gca()

    # Create Pathes for Court Lines
    center_circle = Circle((50 / 2, 94 / 2), 6,
                           linewidth=lw, color=lines_color, lw=lw,
                           fill=False, alpha=lines_alpha)
    hoop = Circle((50 / 2, 5.25), 1.5 / 2,
                  linewidth=lw, color=lines_color, lw=lw,
                  fill=False, alpha=lines_alpha)

    # Paint - 18 Feet 10 inches which converts to 18.833333 feet - gross!
    paint = Rectangle(((50 / 2) - 6, 0), 12, 18.833333,
                      fill=paint_fill, alpha=paint_alpha,
                      lw=lw, edgecolor=None)

    paint_boarder = Rectangle(((50 / 2) - 6, 0), 12, 18.833333,
                              fill=False, alpha=lines_alpha,
                              lw=lw, edgecolor=lines_color)

    arc = Arc((50 / 2, 18.833333), 12, 12, theta1=-
    0, theta2=180, color=lines_color, lw=lw,
              alpha=lines_alpha)

    block1 = Rectangle(((50 / 2) - 6 - 0.666, 7), 0.666, 1,
                       fill=True, alpha=lines_alpha,
                       lw=0, edgecolor=lines_color,
                       facecolor=lines_color)
    block2 = Rectangle(((50 / 2) + 6, 7), 0.666, 1,
                       fill=True, alpha=lines_alpha,
                       lw=0, edgecolor=lines_color,
                       facecolor=lines_color)
    ax.add_patch(block1)
    ax.add_patch(block2)

    l1 = Rectangle(((50 / 2) - 6 - 0.666, 11), 0.666, 0.166,
                   fill=True, alpha=lines_alpha,
                   lw=0, edgecolor=lines_color,
                   facecolor=lines_color)
    l2 = Rectangle(((50 / 2) - 6 - 0.666, 14), 0.666, 0.166,
                   fill=True, alpha=lines_alpha,
                   lw=0, edgecolor=lines_color,
                   facecolor=lines_color)
    l3 = Rectangle(((50 / 2) - 6 - 0.666, 17), 0.666, 0.166,
                   fill=True, alpha=lines_alpha,
                   lw=0, edgecolor=lines_color,
                   facecolor=lines_color)
    ax.add_patch(l1)
    ax.add_patch(l2)
    ax.add_patch(l3)
    l4 = Rectangle(((50 / 2) + 6, 11), 0.666, 0.166,
                   fill=True, alpha=lines_alpha,
                   lw=0, edgecolor=lines_color,
                   facecolor=lines_color)
    l5 = Rectangle(((50 / 2) + 6, 14), 0.666, 0.166,
                   fill=True, alpha=lines_alpha,
                   lw=0, edgecolor=lines_color,
                   facecolor=lines_color)
    l6 = Rectangle(((50 / 2) + 6, 17), 0.666, 0.166,
                   fill=True, alpha=lines_alpha,
                   lw=0, edgecolor=lines_color,
                   facecolor=lines_color)
    ax.add_patch(l4)
    ax.add_patch(l5)
    ax.add_patch(l6)

    # 3 Point Line
    if (three_line == 'mens') | (three_line == 'both'):
        # 22' 1.75" distance to center of hoop
        three_pt = Arc((50 / 2, 6.25), 44.291, 44.291, theta1=12,
                       theta2=168, color=lines_color, lw=lw,
                       alpha=lines_alpha)

        # 4.25 feet max to sideline for mens
        ax.plot((3.34, 3.34), (0, 11.20),
                color=lines_color, lw=lw, alpha=lines_alpha)
        ax.plot((50 - 3.34, 50 - 3.34), (0, 11.20),
                color=lines_color, lw=lw, alpha=lines_alpha)
        ax.add_patch(three_pt)

    if (three_line == 'womens') | (three_line == 'both'):
        # womens 3
        three_pt_w = Arc((50 / 2, 6.25), 20.75 * 2, 20.75 * 2, theta1=5,
                         theta2=175, color=lines_color, lw=lw, alpha=lines_alpha)
        # 4.25 inches max to sideline for mens
        ax.plot((4.25, 4.25), (0, 8), color=lines_color,
                lw=lw, alpha=lines_alpha)
        ax.plot((50 - 4.25, 50 - 4.25), (0, 8.1),
                color=lines_color, lw=lw, alpha=lines_alpha)

        ax.add_patch(three_pt_w)

    # Add Patches
    ax.add_patch(paint)
    ax.add_patch(paint_boarder)
    ax.add_patch(center_circle)
    ax.add_patch(hoop)
    ax.add_patch(arc)

    if inner_arc:
        inner_arc = Arc((50 / 2, 18.833333), 12, 12, theta1=180,
                        theta2=0, color=lines_color, lw=lw,
                        alpha=lines_alpha, ls='--')
        ax.add_patch(inner_arc)

    # Restricted Area Marker
    restricted_area = Arc((50 / 2, 6.25), 8, 8, theta1=0,
                          theta2=180, color=lines_color, lw=lw,
                          alpha=lines_alpha)
    ax.add_patch(restricted_area)

    # Backboard
    ax.plot(((50 / 2) - 3, (50 / 2) + 3), (4, 4),
            color=lines_color, lw=lw * 1.5, alpha=lines_alpha)
    ax.plot((50 / 2, 50 / 2), (4.3, 4), color=lines_color,
            lw=lw, alpha=lines_alpha)

    # Half Court Line
    ax.axhline(94 / 2, color=lines_color, lw=lw, alpha=lines_alpha)

    # Plot Limit
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 94 / 2 + 2)
    ax.set_facecolor(court_color)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    return ax


def bokeh_draw_court_two(figure, line_color='black', line_width=3, lines_alpha=0.5,
                         paint_color='#0343DF', paint_alpha=0.4, court_color='#dfbb85',):
    """Returns a figure with the basketball court lines drawn onto it
    This function draws a court based on the x and y-axis values that the NBA
    stats API provides for the shot chart data.  For example the center of the
    hoop is located at the (0,0) coordinate.  Twenty-two feet from the left of
    the center of the hoop in is represented by the (-220,0) coordinates.
    So one foot equals +/-10 units on the x and y-axis.
    Parameters
    ----------
    figure : Bokeh figure object
        The Axes object to plot the court onto.
    line_color : str, optional
        The color of the court lines. Can be a a Hex value.
    line_width : float, optional
        The linewidth the of the court lines in pixels.
    Returns
    -------
    figure : Figure
        The Figure object with the court on it.
    """

    figure.circle(x=50 / 2, y=94 / 2, radius=3, line_alpha=lines_alpha,
                  line_color=line_color, line_width=line_width,
                  fill_color=None)

    # hoop
    figure.circle(x=50/2, y=5.25, radius=0.75, line_alpha=lines_alpha,
                  line_color=line_color, line_width=line_width,
                  fill_color=None)
    # paint
    figure.rect(50/2,18.833333/2,12,18.833333, fill_alpha=paint_alpha, fill_color=paint_color,
                line_color=None, line_alpha=0)
    figure.rect(50 / 2, 18.833333 / 2, 12, 18.833333, fill_alpha=0, fill_color=None,
                line_color=line_color, line_alpha=lines_alpha, line_width=line_width)

    # arc
    figure.arc(50/2, 18.8333333, 6, start_angle=0, end_angle=pi, line_color=line_color,
               line_alpha=lines_alpha, line_width=line_width)

    # block
    figure.rect( ((50/2)-6-0.666)+0.333, 7.5, 0.666, 1, line_color=line_color, fill_color=line_color, fill_alpha=lines_alpha,
                line_alpha=lines_alpha, line_width=0)
    figure.rect((50/2)+6+0.333, 7.5, 0.666, 1, line_color=line_color, fill_color=line_color, fill_alpha=lines_alpha,
                line_alpha=lines_alpha, line_width=0)

    figure.rect((50 / 2) - 6 - 0.666+0.333, 11+0.166/2, 0.666, 0.166,
                   line_color=line_color, fill_color=line_color, fill_alpha=lines_alpha,
                line_alpha=lines_alpha, line_width=0)
    figure.rect((50 / 2) - 6 - 0.666+0.333, 14+0.166/2, 0.666, 0.166,
                line_color=line_color, fill_color=line_color, fill_alpha=lines_alpha,
                line_alpha=lines_alpha, line_width=0)
    figure.rect((50 / 2) - 6 - 0.666+0.333, 17+0.166/2, 0.666, 0.166,
                line_color=line_color, fill_color=line_color, fill_alpha=lines_alpha,
                line_alpha=lines_alpha, line_width=0)
    figure.rect((50 / 2) + 6+0.333, 11+0.166/2, 0.666, 0.166,
                line_color=line_color, fill_color=line_color, fill_alpha=lines_alpha,
                line_alpha=lines_alpha, line_width=0)
    figure.rect((50 / 2) + 6+0.333, 14+0.166/2, 0.666, 0.166,
                line_color=line_color, fill_color=line_color, fill_alpha=lines_alpha,
                line_alpha=lines_alpha, line_width=0)
    figure.rect((50 / 2) + 6+0.333, 17+0.166/2, 0.666, 0.166,
                line_color=line_color, fill_color=line_color, fill_alpha=lines_alpha,
                line_alpha=lines_alpha, line_width=0)

    figure.arc(50 / 2, 6.25, (22+1.75/12), start_angle=12*pi/180,
                   end_angle=168*pi/180, line_color=line_color,
               line_width=line_width, line_alpha=lines_alpha)

    figure.line(x=3.34, y=np.arange(0, 11.2+0.1,0.1), line_color=line_color,
                line_width=line_width, line_alpha=lines_alpha)
    figure.line(x=50-3.34, y=np.arange(0, 11.2+0.1,0.1), line_color=line_color,
                line_width=line_width, line_alpha=lines_alpha)

    # Restricted Area Marker
    figure.arc(50/2, 5.25, 4, 0, pi, line_color=line_color, line_width=line_width, line_alpha=lines_alpha)

    # Backboard
    figure.line(np.arange(50/2-3, 50/2+3+0.1,0.1), 4, line_width=line_width*1.5, line_color=line_color, line_alpha=lines_alpha)
    figure.line(50/2, np.arange(4,4.3+0.01,0.01), line_width=line_width, line_color=line_color, line_alpha=lines_alpha)

    # Half Court Line
    figure.line(np.arange(0,50,0.1), 94 / 2, line_width=line_width, line_color=line_color,line_alpha=lines_alpha)

    figure.background_fill_color=court_color

    return figure


def shot_chart(data, kind="scatter", title="", color="b", cmap=None,
               xlim=(-250, 250), ylim=(422.5, -47.5),
               court_color="gray", court_lw=2, outer_lines=False,
               flip_court=False, kde_shade=True, gridsize=None, ax=None,
               despine=False, **kwargs):
    """
    Returns an Axes object with player shots plotted.
    Parameters
    ----------
    x, y : strings or vector
        The x and y coordinates of the shots taken. They can be passed in as
        vectors (such as a pandas Series) or as columns from the pandas
        DataFrame passed into ``data``.
    data : DataFrame, optional
        DataFrame containing shots where ``x`` and ``y`` represent the
        shot location coordinates.
    kind : { "scatter", "kde", "hex" }, optional
        The kind of shot chart to create.
    title : str, optional
        The title for the plot.
    color : matplotlib color, optional
        Color used to plot the shots
    cmap : matplotlib Colormap object or name, optional
        Colormap for the range of data values. If one isn't provided, the
        colormap is derived from the valuue passed to ``color``. Used for KDE
        and Hexbin plots.
    {x, y}lim : two-tuples, optional
        The axis limits of the plot.
    court_color : matplotlib color, optional
        The color of the court lines.
    court_lw : float, optional
        The linewidth the of the court lines.
    outer_lines : boolean, optional
        If ``True`` the out of bound lines are drawn in as a matplotlib
        Rectangle.
    flip_court : boolean, optional
        If ``True`` orients the hoop towards the bottom of the plot.  Default
        is ``False``, which orients the court where the hoop is towards the top
        of the plot.
    kde_shade : boolean, optional
        Default is ``True``, which shades in the KDE contours.
    gridsize : int, optional
        Number of hexagons in the x-direction.  The default is calculated using
        the Freedman-Diaconis method.
    ax : Axes, optional
        The Axes object to plot the court onto.
    despine : boolean, optional
        If ``True``, removes the spines.
    kwargs : key, value pairs
        Keyword arguments for matplotlib Collection properties or seaborn plots.
    Returns
    -------
     ax : Axes
        The Axes object with the shot chart plotted on it.
    """
    data = data.loc[~data["ESPN_Shot_X"].isna()]
    if len(data) ==0:
        return None
    else:
        x = data['ESPN_Shot_X']+25
        y = data['ESPN_Shot_Y']+4.75

    color = 'b' if color is None else color

    if ax is None:
        fig, ax = plt.subplots()

    if cmap is None:
        cmap = sns.light_palette(color, as_cmap=True)

    if not flip_court:
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
    else:
        ax.set_xlim(xlim[::-1])
        ax.set_ylim(ylim[::-1])

    # ax.get_xaxis().set_visible(False)
    # ax.get_yaxis().set_visible(False)
    ax.set_title(title, fontsize=18)

    create_ncaa_half_court(ax)
    #draw_court(ax, color=court_color, lw=court_lw, outer_lines=outer_lines)

    if kind == "scatter":
        made_shots = (data['EventResult'] == 'made').values
        ax.scatter(x[made_shots], y[made_shots], edgecolors=color, facecolors=color, **kwargs)
        ax.scatter(x[~made_shots], y[~made_shots], edgecolors=color, facecolors='none', **kwargs)

    elif kind == "kde":
        sns.kdeplot(x, y, shade=kde_shade, cmap=cmap, ax=ax, **kwargs)
        ax.set_xlabel('')
        ax.set_ylabel('')

    elif kind == "hex":
        if gridsize is None:
            # Get the number of bins for hexbin using Freedman-Diaconis rule
            # This is idea was taken from seaborn, which got the calculation
            # from http://stats.stackexchange.com/questions/798/
            x_bin = _freedman_diaconis_bins(x)
            y_bin = _freedman_diaconis_bins(y)
            gridsize = int(np.mean([x_bin, y_bin]))

        ax.hexbin(x, y, gridsize=gridsize, cmap=cmap, **kwargs)

    else:
        raise ValueError("kind must be 'scatter', 'kde', or 'hex'.")

    # Set the spines to match the rest of court lines, makes outer_lines
    # somewhate unnecessary
    for spine in ax.spines:
        ax.spines[spine].set_lw(court_lw)
        ax.spines[spine].set_color(court_color)

    if despine:
        ax.spines["top"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

    return fig

def bokeh_shot_chart(data, fill_color="#1f77b4",
                     scatter_size=10, court_line_color='black', court_line_width=3,
                     hover_tool=True, **kwargs):

    # TODO: Settings for hover tooltip
    """
    Returns a figure with both FGA and basketball court lines drawn onto it.
    This function expects data to be a ColumnDataSource with the x and y values
    named "LOC_X" and "LOC_Y".  Otherwise specify x and y.
    Parameters
    ----------
    data : DataFrame
        The DataFrame that contains the shot chart data.
    x, y : str, optional
        The x and y coordinates of the shots taken.
    fill_color : str, optional
        The fill color of the shots. Can be a a Hex value.
    scatter_size : int, optional
        The size of the dots for the scatter plot.
    fill_alpha : float, optional
        Alpha value for the shots. Must be a floating point value between 0
        (transparent) to 1 (opaque).
    line_alpha : float, optiona
        Alpha value for the outer lines of the plotted shots. Must be a
        floating point value between 0 (transparent) to 1 (opaque).
    court_line_color : str, optional
        The color of the court lines. Can be a a Hex value.
    court_line_width : float, optional
        The linewidth the of the court lines in pixels.
    hover_tool : boolean, optional
        If ``True``, creates hover tooltip for the plot.
    tooltips : List of tuples, optional
        Provides the information for the the hover tooltip.
    Returns
    -------
    fig : Figure
        The Figure object with the shot chart plotted on it.
    """
    data = data.loc[~data["ESPN_Shot_X"].isna()]
    if len(data) ==0:
        return figure()
    else:
        x = data['ESPN_Shot_X'] + 25
        y = data['ESPN_Shot_Y'] + 4.75
        data['x_adj'] = x
        data['y_adj'] = y
        x= 'x_adj'
        y='y_adj'
    made_shots = (data['EventResult'] == 'made')
    source_made = ColumnDataSource(data.loc[made_shots])
    source_missed = ColumnDataSource(data.loc[~made_shots])

    fig = figure(width=700, height=658, x_range=[0, 50],
                 y_range=[0, 47.5], min_border=0, x_axis_type=None,
                 y_axis_type=None, outline_line_color="black", **kwargs)

    fig.scatter(x, y, source=source_missed, size=scatter_size, fill_color=None,
                line_color=fill_color)
    fig.scatter(x, y, source=source_made, size=scatter_size, fill_color=fill_color,
                line_color=fill_color)

    bokeh_draw_court_two(fig, line_color=court_line_color,
                     line_width=court_line_width)

    if hover_tool:
        hover = HoverTool( tooltips=[('Date', '@DateString'),
                                     ('HomeTeam', '@Home'),
                                     ('AwayTeam', '@Away'),
                                     ('Half', '@Half'),
                                     ('GameClock', '@GameClock'),
                                     ('EventDescription', '@EventDescription'),
                                     ('ShotDistance', '@ShotDistance'),
                                     ('ESPN_Shot_X', '@ESPN_Shot_X'),
                                     ('ESPN_Shot_Y', '@ESPN_Shot_Y'),])
        fig.add_tools(hover)

    return fig