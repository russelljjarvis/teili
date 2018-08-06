import numpy as np

try:
    from teili.tools.visualizer.DataModels import EventsModel, StateVariablesModel
    from teili.tools.visualizer.DataControllers import DataController
    from teili.tools.visualizer.DataViewers import HistogramViewerMatplotlib
    from teili.tools.visualizer.DataViewers import HistogramViewerPyqtgraph
except BaseException:
    from teili.teili.tools.visualizer.DataModels.DataModel import EventsModel, StateVariablesModel
    from teili.teili.tools.visualizer.DataControllers.DataController import DataController
    from teili.teili.tools.visualizer.DataViewers.HistogramViewerMatplotlib import HistogramViewerMatplotlib
    from teili.teili.tools.visualizer.DataViewers.HistogramViewerPyqtgraph import HistogramViewerPyqtgraph


class HistogramController(DataController):
    """ Class to plot histograms with different backends and from different DataModels"""

    def __init__(
            self,
            MyPlotSettings,
            DataModel_to_attr,
            subgroup_labels=None,
            bins=None,
            orientation='vertical',
            title='histogram',
            xlabel='bins',
            ylabel='count',
            backend='matplotlib',
            mainfig=None,
            subfig=None,
            QtApp=None,
            show_immediately=True):
        """ Setup Histogram Controller and create histogram plot
        Args:
            MyPlotSettings (PlotSettings object): instance of class PlotSettings holding basic plot settings (e.g. fontsize, ...)
            DataModel_to_attr (dict): dict ::class DataModel::  attr_of_DataModel_to_consider
                                                (data model can also be a brian state monitor or spike monitor)
            subgroup_labels (list of str): list of labels for the different subgroups (e.g. ['exc', 'inh'])
            bins (array, list): array with edges of bins in histogram
            orientation (str): orientation of histogram (vertical or horizontal)
            title (str): title of plot
            xlabel (str): label of x-axis
            ylabel (str): label for y-axis
            backend (str): 'matplotlib' or 'pyqtgraph', defines which backend should be used for plotting
            mainfig (figure object): figure which holds the subfig (subplots) (plt.figure or  pg.GraphicsWindow())
            subfig (subplot): subplot of mainfig which will hold the histogram
            QtApp (pyqtgraph application): pyqtgraph application to run plots ( QtGui.QApplication([]) ),
                                            only required if backend is pyqtgraph
            show_immediately (bool): if True: plot is shown immediately after it has been created
        """
        self.subgroup_labels = subgroup_labels
        self.bins = bins
        self.orientation = orientation
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel

        if backend == 'matplotlib':
            self.my_histogram = HistogramViewerMatplotlib(
                MyPlotSettings, mainfig=mainfig, subfig=subfig)
        elif backend == 'pyqtgraph':
            self.my_histogram = HistogramViewerPyqtgraph(
                MyPlotSettings, mainfig=mainfig, subfig=subfig, QtApp=QtApp)
        else:
            raise Exception(
                'You asked for the backend "{}" which is not supported'.format(backend))

        self._get_data(DataModel_to_attr)
        self.create_histogram()
        if show_immediately:
            self.show_histogram()

    def _get_data(self, DataModel_to_attr):
        """ get data from DataModel_to_attr. Reformat it as list (self.data) of attributes considered"""

        self.data = []
        for data_model, attr_to_consider in DataModel_to_attr.items():
            self.data.append(
                np.asarray(
                    getattr(
                        data_model,
                        attr_to_consider)).flatten())

    def create_histogram(self):
        """ Function to create histogram in subfigure with data from DataModel_to_attr with subgroups  defined above"""

        self.my_histogram.create_histogram(
            data=self.data,
            subgroup_labels=self.subgroup_labels,
            bins=self.bins,
            orientation=self.orientation,
            title=self.title,
            xlabel=self.xlabel,
            ylabel=self.ylabel)

    def show_histogram(self):
        """ show plot """

        self.my_histogram.show_histogram()

    def save_histogram(self, path_to_save, figure_size):
        """ Save figure to path_to_save with size figure_size
        Args:
            path_to_save (str): path to location where to save figure incl filename
            figure_size (2-tuple): tuple of width and height of figure to save
        """

        self.my_histogram.save_histogram(path_to_save, figure_size)
