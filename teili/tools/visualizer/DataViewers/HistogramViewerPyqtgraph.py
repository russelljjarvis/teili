import numpy as np
import warnings
try:
    import pyqtgraph as pg
    from PyQt5 import QtGui
except BaseException:
    warnings.warn("No method using pyqtgraph can be used as pyqtgraph or PyQt5"
                  "can't be imported.")

from teili.tools.visualizer.DataViewers.HistogramViewer import HistogramViewer
from teili.tools.visualizer.DataViewers.DataViewerUtilsPyqtgraph import DataViewerUtilsPyqtgraph

class HistogramViewerPyqtgraph(HistogramViewer):
    """ Class to plot histogram with pyqtgraph backend """

    def __init__(self, MyPlotSettings, mainfig=None, subfig=None, QtApp=None):
        """ Setup HistogramViewer by initializing main figure and subfigure.
            If any of them is set to None, it will be created internally.

        Args:
            MyPlotSettings (PlotSettings object): instance of class
                PlotSettings holding basic plot settings (e.g. fontsize, ...)
            mainfig (pyqtgraph window object): pyqtgraph main window
                (pg.GraphicsWindow())
            subfig (pyqtgraph subplot): pyqtgraph subplot of mainfig which will
                hold the histogram
            QtApp (pyqtgraph application): pyqtgraph application to run plots
                (QtGui.QApplication([]))
        """

        self.MyPlotSettings = MyPlotSettings

        # QtApp
        self.QtApp = QtApp
        if not self.QtApp:
            self.QtApp = QtGui.QApplication([])

        # figure
        self.mainfig = mainfig
        if not self.mainfig:
            if subfig:
                pass  # TODO: !1
                # self.mainfig = subfig.figure get pyqt win
            else:
                self.mainfig = pg.GraphicsWindow()

        # subplot
        self.subfig = subfig
        if not self.subfig:
            self.subfig = self.mainfig.addPlot(row=1, column=1)

        pg.setConfigOptions(antialias=True)

        self.set_DataViewerUtils()

    def set_DataViewerUtils(self):
        """ Set which DataViewerUtils class should be considered"""
        self.DVUtils = DataViewerUtilsPyqtgraph(QtApp=self.QtApp, mainfig=self.mainfig)

    def create_plot(
            self,
            data,
            subgroup_labels=None,
            bins=None,
            orientation='vertical',
            title='histogram',
            xlabel='bins',
            ylabel='count'):
        """ Function to generate histogram for groups of event sets (spike times, neuron ids) with pyqtgraph
        Args:
            data (list of lists): list of lists of neuron ids of events (e.g. [[3,4,5,2],[9,7,7 8]]
            subgroup_labels (list of str): list of labels for the different subgroups (e.g. ['exc', 'inh'])
            bins (array, list): array with edges of bins in histogram
            orientation (str): orientation of histogram (vertical or horizontal)
            title (str): title of plot
            xlabel (str): label of x-axis
            ylabel (str): label for y-axis
            """

        if bins is None:
            max_per_dataset = []
            for x in data:
                if np.size(x) > 0:  # to avoid error by finding max of emtpy dataset
                    max_per_dataset.append(np.nanmax(x))
                else:
                    max_per_dataset.append(0)
            bins = range(int(max(max_per_dataset))+2)  # +2 to always have at least 1 bin

        # check if num colors ok
        assert len(
            self.MyPlotSettings.colors) >= len(data), 'You have {} subgroups but only {} colors in your MyPlotSettings.colors'.format(
            len(data), len(
                self.MyPlotSettings.colors))

        if subgroup_labels is not None:
            self.subfig.addLegend()

        # histogram
        for subgroup_nr, (subgroup, color) in enumerate(
                zip(data, self.MyPlotSettings.colors)):

            if (np.isnan(subgroup)).any():
                subgroup = subgroup[~np.isnan(subgroup)]
                warnings.warn("One of your subgroup contains NAN entries. They are removed and not shown in the histogram")

            y, x = np.histogram(subgroup, bins=bins)
            color = np.asarray(pg.colorTuple(pg.mkColor(color)))

            if orientation == 'horizontal':
                barchart = pg.BarGraphItem(
                    x0=y * 0, y0=x[:-1], height=1.0, width=y, pen=None, brush=color)
            else:
                barchart = pg.BarGraphItem(
                    x0=x[:-1], y0=0, height=y, width=1.0, pen=None, brush=color)

            if subgroup_labels is not None:
                style = pg.PlotDataItem(pen=color)
                self.subfig.legend.addItem(style, subgroup_labels[subgroup_nr])
            self.subfig.addItem(barchart)

        if subgroup_labels is not None:
            legendStyle = {
                'color': '#FFF', 'size': str(
                    self.MyPlotSettings.fontsize_legend) + 'pt'}
            for item in self.subfig.legend.items:
                for single_item in item:
                    if isinstance(single_item,
                                  pg.graphicsItems.LabelItem.LabelItem):
                        single_item.setText(single_item.text, **legendStyle)

        self._set_title_and_labels(title=title, xlabel=xlabel, ylabel=ylabel)

    def _set_title_and_labels(self, title, xlabel, ylabel):
        """ Set title and label of x- and y-axis in plot
        Args:
            title (str): title of plot
            xlabel (str): label for x-axis
            ylabel (str): label for y-axis
        """
        if title is not None:
            titleStyle = {
                'color': '#FFF', 'size': str(
                    self.MyPlotSettings.fontsize_title) + 'pt'}
            self.subfig.setTitle(title, **titleStyle)

        labelStyle = {'color': '#FFF',
                      'font-size': str(self.MyPlotSettings.fontsize_axis_labels) + 'pt'}
        if xlabel is not None:
            self.subfig.setLabel('bottom', xlabel, **labelStyle)
        if ylabel is not None:
            self.subfig.setLabel('left', ylabel, **labelStyle)
        self.subfig.getAxis('bottom').tickFont = QtGui.QFont(
            'arial', self.MyPlotSettings.fontsize_axis_labels)
        self.subfig.getAxis('left').tickFont = QtGui.QFont(
            'arial', self.MyPlotSettings.fontsize_axis_labels)
