'''
Created on 28 Dec 2017

@author: Alpha Renner

This class is a 2d plotter and provides functionality
for analysis of 2d neuron fields
To be extended!

Attributes:
    CM_JET (TYPE): Description
    CM_ONOFF (TYPE): Description
'''

################################################################################################
# Import required packages
import csv
import os
from brian2 import ms, us, defaultclock, second
import numpy as np
import shutil
#import matplotlib.animation as animation
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph.exporters  # looks redundant, but this is necessary for export
import sparse
from scipy import ndimage
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import subprocess
# pg.setConfigOption('background', 'w') # makes  background white
from pyqtgraph.colormap import ColorMap
CM_JET = ColorMap([0.0, 0.33, 0.66, 1.0],
                  [(0, 0, 255, 255), (0, 255, 255, 255),
                   (255, 255, 0, 255), (255, 10, 10, 255)], mode=2)

CM_ONOFF = ColorMap([0.0, 0.33, 0.66, 1.0],
                    [(0, 0, 0, 255), (0, 255, 0, 255),
                     (255, 0, 0, 255), (255, 255, 0, 255)], mode=2)


class DVSmonitor():

    """Summary

    Attributes:
        pol (TYPE): Description
        t (TYPE): Description
        xi (TYPE): Description
        yi (TYPE): Description
    """

    def __init__(self, xi, yi, t, pol):
        """Summary

        Args:
            xi (TYPE): Description
            yi (TYPE): Description
            t (TYPE): Description
            pol (TYPE): Description
        """
        self.t = t * us
        self.xi = xi
        self.yi = yi
        self.pol = pol


class Plotter2d(object):
    """
    TODO: Merge plotrange and mask?

    Attributes:
        cols (TYPE): Description
        dims (TYPE): Description
        mask (TYPE): Description
        plotrange (TYPE): Description
        pol (TYPE): Description
        rows (TYPE): Description
        shape (TYPE): Description
    """

    def __init__(self, monitor, dims, plotrange=None):
        """Summary

        Args:
            monitor (TYPE): Description
            dims (TYPE): Description
            plotrange (None, optional): Description
        """
        self.rows = dims[0]
        self.cols = dims[1]
        self.dims = dims

        self._t = monitor.t  # times of spikes
        self.shape = (dims[0], dims[1], len(monitor.t))

        self.monitor = monitor #mainly for debugging!

        #self.name = monitor.name
        try:  # that should work if the monitor is a Brian2 Spikemonitor
            self._i = monitor.i  # neuron index number of spike
            # print(self._i)
            self._xi, self._yi = np.unravel_index(self._i, (dims[0], dims[1]))
            self.pol = np.zeros_like(self._t)
            #assert(len(self._i) == len(self._t))
        except:  # that should work, if it is a DVSmonitor (it has xi and yi instead of y)
            self._xi = np.asarray(monitor.xi, dtype='int')
            self._yi = np.asarray(monitor.yi, dtype='int')
            self._i = np.ravel_multi_index((self._xi, self._yi), dims)  # neuron index number of spike
            self.pol = monitor.pol
            try:  # check, if _t has a unit (dvs raw data is given in us)
                self._t[0].dim
            except:
                self._t = self._t * us

        self.mask = slice(len(monitor.t))  # [True] * (len(monitor.t))
        if plotrange is None:
            self.plotrange = (0 * ms, np.max(self.t))
        else:
            self.plotrange = plotrange
            self.set_range(plotrange)

        # this might use a lot of memory, but saves computation (I usually keep dt and filtersize)
        self._filtered = {}

    @property
    def t(self):
        """Summary

        Returns:
            TYPE: Description
        """
        return self._t[self.mask]

    @property
    def t_(self):
        """
        unitless t in ms

        Returns:
            TYPE: Description
        """
        return self._t[self.mask] / ms

    @property
    def i(self):
        """Summary

        Returns:
            TYPE: Description
        """
        return self._i[self.mask]

    @property
    def xi(self):
        """Summary

        Returns:
            TYPE: Description
        """
        return self._xi[self.mask]

    @property
    def yi(self):
        """Summary

        Returns:
            TYPE: Description
        """
        return self._yi[self.mask]

    @property
    def plotlength(self):
        """Summary

        Returns:
            TYPE: Description
        """
        # if self.plotrange is not None:
        plotlength = self.plotrange[1] - self.plotrange[0]
        # else:
        #    plotlength = np.max(self.t)
        return plotlength

    def plotshape(self, dt):
        """Summary

        Args:
            dt (TYPE): Description

        Returns:
            TYPE: Description
        """
        plottimesteps = int(np.ceil(0.0001 + self.plotlength / dt))
        # print(plottimesteps)
        return (plottimesteps, self.dims[0], self.dims[1])

    def set_range(self, plotrange):
        '''
        set a range with unit that is applied for all computations with this monitor

        Args:
            plotrange (TYPE): Description
        '''
        if plotrange:
            self.plotrange = plotrange
            # TODO: Use slicing
            self.mask = np.where(self._t <= plotrange[1]) & (self._t >= plotrange[0])
        else:
            self.plotrange = (0 * ms, np.max(self._t))
            self.mask = slice(len(self._t))  # [True] * (len(self._t))

    def get_sparse3d(self, dt):
        """Using the package sparse (based of scipy sparse, but for 3d), the spiketimes
        are converted into a sparse matrix. This step is basically just for easy
        conversion into a dense matrix later, as you cannot do so many computations
        with the sparse representation.

        Args:
            dt (TYPE): Description

        Returns:
            TYPE: Description
        """
        # print(len(self.t))
        #print(np.max(self.t / dt))
        # print(self.plotshape(dt))
        sparse_spikemat = sparse.COO((np.ones(len(self.t)), (self.t / dt, self.xi, self.yi)),
                                     shape=self.plotshape(dt))
        return sparse_spikemat

    # Example:
    # sparse_test = sparse.COO((np.ones(5), (np.asarray([0,10,40,60,80]) / 10, [1,2,3,4,5], [5,4,3,2,1])),shape=(9,6,6))
    # print(sparse_test.todense())

    def get_dense3d(self, dt):
        """Transforms the sparse spike time representation in a dense representation,
        where every spike is given as a 1 in a 3d matrix (time + 2 spatial dimensions)
        The data is binned using dt. If there is more than one spike in a bin, the bin will
        not have the value 1, but the number of spikes.

        Args:
            dt (TYPE): Description

        Returns:
            TYPE: Description
        """
        sparse3d = self.get_sparse3d(dt)
        return sparse3d.todense()

    def get_filtered(self, dt, filtersize):
        """applies a rectangular filter (convolution) of length filtersize over time (dimension 0).
        It returns a 3d matrix with the firing rate.
        Spiketimes will be binned with a step size of dt.

        Args:
            dt (TYPE): the time step with which the spike times are binned
            filtersize (TYPE): length of the filter (in brian2 time units)
        Returns:
            TYPE: Description
        """
        dense3d = self.get_dense3d(dt)
        self._filtered[(dt / ms, filtersize / ms)] = ndimage.uniform_filter1d(
            dense3d, size=int(filtersize / dt), axis=0, mode='constant') * second / dt
        return self._filtered[(dt / ms, filtersize / ms)]
    #    import timeit
    #    timeit.timeit("ndimage.uniform_filter(dense3d, size=(0,0,10))",
    #                  setup = 'from scipy import ndimage',
    #                  globals={'dense3d':dense3d},number = 1)
    #    timeit.timeit("ndimage.uniform_filter1d(dense3d,size=10, axis = 2, mode='constant')",
    #                  setup = 'from scipy import ndimage',
    #                  globals={'dense3d':dense3d},number = 1)
    #    timeit.timeit("ndimage.convolve1d(dense3d, weights=np.ones(10), axis = 2)",
    #                  setup = 'from scipy import ndimage;import numpy as np',
    #                  globals={'dense3d':dense3d},number = 1)

    def plot3d_on_off(self, plot_dt=defaultclock.dt, filtersize=10 * ms, colormap=CM_ONOFF):
        """
        Args:
            plot_dt (TYPE, optional): Description
            filtersize (TYPE, optional): Description
            colormap (TYPE, optional): Description

        Returns:
            TYPE: Description
        """

        video_filtered0 = 0
        video_filtered1 = 0

        prev_mask = self.mask
        self.mask = np.where(self.pol == 0)[0]
        if len(self.t) > 0:
            try:
                video_filtered0 = self.get_filtered(plot_dt, filtersize)
            except MemoryError:
                print('the dt you have set would generate a too large matrix for you memory, trying 10*dt')
                video_filtered0 = self.get_filtered(plot_dt * 10, filtersize)
            video_filtered0[video_filtered0 > 0] = 1

        self.mask = np.where(self.pol == 1)[0]
        if len(self.t) > 0:
            try:
                video_filtered1 = self.get_filtered(plot_dt, filtersize)
            except MemoryError:
                print('the dt you have set would generate a too large matrix for you memory, trying 10*dt')
                video_filtered1 = self.get_filtered(plot_dt * 10, filtersize)
            video_filtered1[video_filtered1 > 0] = 2


        video_filtered = video_filtered0 + video_filtered1

        imv = pg.ImageView()
        imv.setImage(video_filtered, xvals=np.arange(
            0, video_filtered.shape[0] * (plot_dt / ms), plot_dt / ms))
        imv.ui.histogram.gradient.setColorMap(colormap)
        # imv.setPredefinedGradient("thermal")
        # imv.show()
        # imv.export("plot/plot_.png")

        self.mask = prev_mask
        return imv

    def plot3d(self, plot_dt=defaultclock.dt, filtersize=10 * ms, colormap=CM_JET):
        """
        Args:
            plot_dt (TYPE, optional): Description
            filtersize (TYPE, optional): Description
            colormap (TYPE, optional): Description

        Returns:
            TYPE: Description
        """
        try:
            video_filtered = self.get_filtered(plot_dt, filtersize)
        except MemoryError:
            print('the dt you have set would generate a too large matrix for you memory, trying 10*dt')
            video_filtered = self.get_filtered(plot_dt * 10, filtersize)

        imv = pg.ImageView()
        imv.setImage(video_filtered, xvals=np.arange(
            0, video_filtered.shape[0] * (plot_dt / ms), plot_dt / ms))
        imv.ui.histogram.gradient.setColorMap(colormap)
        # imv.setPredefinedGradient("thermal")
        # imv.show()
        # imv.export("plot/plot_.png")
        return imv

    def rate_histogram(self, filename, filtersize=50 * ms, plot_dt=defaultclock.dt * 100, num_bins=50):
        """Summary

        Args:
            filename (TYPE): Description
            filtersize (TYPE, optional): Description
            plot_dt (TYPE, optional): Description
            num_bins (int, optional): Description
        """
        video_filtered = self.get_filtered(plot_dt, filtersize)
        histrange = (0, np.max(video_filtered))
        num_bins = num_bins
        flat_rate_time = np.reshape(
            video_filtered, (video_filtered.shape[0], video_filtered.shape[1] * video_filtered.shape[2]))
        hist2d = np.zeros((len(flat_rate_time), num_bins))
        for t in range(len(flat_rate_time)):
            # ,density = True)
            hist = np.histogram(
                flat_rate_time[t], bins=num_bins, range=histrange)
            hist2d[t] = np.log10(hist[0])

        hist2d[hist2d == -np.inf] = 0

        hist2d = np.flip(hist2d, 1)
        densetimes = np.arange(
            self.plotrange[0] / ms, self.plotrange[1] / ms, plot_dt / ms)
        pddf_rate = pd.DataFrame(data=hist2d.T,    # values
                                 # 1st column as index
                                 index=np.flip(
                                     np.round(hist[1][0:(len(hist[1]) - 1)], 0), 0),
                                 columns=densetimes / 1000)

        plt.figure()
        sns_fig = sns.heatmap(pddf_rate, cmap='jet', vmax=None).get_figure()
        plt.xlabel('time in s')
        plt.ylabel('firing rate in Hz')
        # plt.show()
        sns_fig.savefig(str(filename) + '_ratehistogram' + '.png')
        # plt.figure()
        # plt.imshow(hist2d.T/np.max(hist2d))#, vmax = 0.1)
        plt.close()

    def ifr_histogram(self, filename, num_bins=50):
        """Summary

        Args:
            filename (TYPE): Description
            num_bins (int, optional): Description
        """
        from scipy.interpolate import interp1d
        dt = 5 * ms
        densetimes = np.arange(
            self.plotrange[0] / ms, self.plotrange[1] / ms, dt / ms)
        denseisis = np.zeros((len(densetimes), self.cols * self.rows))
        for i in range(self.cols * self.rows):
            inds = np.where(i == self.i)[0]
            isitimes = self.t_[inds]
            if len(isitimes) > 2:
                interpf = interp1d(isitimes[1:], np.diff(
                    isitimes), kind='linear', bounds_error=False, fill_value=0.0)
                denseisis[:, i] = interpf(densetimes)
            else:
                denseisis[:, i] = 0  # np.nan
#        imv = pg.ImageView()
#        imv.setImage(np.reshape(1/(denseisis/1000),(denseisis.shape[0],self.cols,self.rows)))
#        imv.setPredefinedGradient("thermal")
#        imv.show()

        denseifrs = 1 / (denseisis / 1000)
        denseifrs[denseifrs == np.inf] = 0
        histrangeifr = (0, np.max(denseifrs))
        histrangeisi = (0, np.max(denseisis))
        histrangeisi = (0, 200)
        num_bins = num_bins
        hist2disi = np.zeros((len(denseisis), num_bins))
        hist2difr = np.zeros((len(denseifrs), num_bins))
        for t in range(len(denseisis)):
            # ,density = True)
            histisi = np.histogram(
                denseisis[t], bins=num_bins, range=histrangeisi)
            hist2disi[t] = histisi[0]
            # ,density = True)
            histifr = np.histogram(
                denseifrs[t], bins=num_bins, range=histrangeifr)
            hist2difr[t] = np.log10(histifr[0])

        hist2disi = np.flip(hist2disi, 1)
        hist2difr = np.flip(hist2difr, 1)

        hist2difr[hist2difr == -np.inf] = 0
        hist2difr[hist2difr == np.nan] = 0

        # Make pandas df with colnames and rownames for nicer plotting with sns
        pddf_ifr = pd.DataFrame(data=hist2difr.T,    # values
                                # 1st column as index
                                index=np.flip(
                                    np.round(histifr[1][0:(len(histifr[1]) - 1)], 0), 0),
                                columns=densetimes / 1000)

        plt.figure()
        sns_fig = sns.heatmap(pddf_ifr, cmap='jet', vmax=None,
                              cbar_kws={'label': 'log(n)'}).get_figure()
        #sns_fig = sns.heatmap(hist2difr.T,cmap = 'jet',xticklabels=densetimes,yticklabels=np.flip(np.round(histifr[1][0:(len(histifr[1])-1)],0),0),vmax=None).get_figure()
        plt.xlabel('time in s')
        plt.ylabel('ifr in Hz')
        if filename is None:
            plt.show()
        else:
            sns_fig.savefig(str(filename) + '_ifrhistogram' + '.png')
            plt.close()

#        plt.figure()
#        sns_fig = sns.heatmap(hist2disi.T,yticklabels=np.flip(np.round(histisi[1][0:(len(histisi[1])-1)],0),0),vmax=100).get_figure()
#        plt.xlabel('timestep')
#        plt.ylabel('isi in ms')
#        #plt.show()
#        sns_fig.savefig(str(filename) + '_ratehistogram'+ '.png')
#        #plt.figure()
        # plt.imshow(hist2d.T/np.max(hist2d))#, vmax = 0.1)

    def savez(self, filename):
        """
        saves the object in a sparse way.
        only i,t, rows and cols are saved to an npz

        Args:
            filename (TYPE): Description
        """
        np.savez_compressed(str(filename) + ".npz", self.i,
                            self.t, self.dims)

    @classmethod
    def loadz(cls, filename):
        """
        loads a file that has previously been saved with savez and returns a
        SpikeMonitor2d object

        usage:
            spikemonObject = SpikeMonitor2d.loadz(myfilename)
            #e.g.
            spikemonObject.plot3d()

        Args:
            filename (TYPE): Description

        Returns:
            TYPE: Description
        """
        def mon():
            """Summary

            Returns:
                TYPE: Description
            """
            return 0
        try:
            with np.load(str(filename)) as loaded_npz:
                i, t, dims = [loaded_npz[arr] for arr in loaded_npz]
            mon.t = t * second
            mon.i = i
            return cls(mon, dims)
        except:
            with np.load(str(filename)) as loaded_npz:
                i, t, rows, cols = [loaded_npz[arr] for arr in loaded_npz]
            mon.t = t * second
            mon.i = i
            return cls(mon, (rows, cols))

    @classmethod
    def loaddvs(cls, eventsfile, dims = None):
        """
        loads a dvs numpy (events file) from aedat2numpy and returns a
        SpikeMonitor2d object, you can also directly pass an events array

        usage:
            spikemonObject = SpikeMonitor2d.loadz(myfilename)
            #e.g.
            spikemonObject.plot3d()

        Args:
            eventsfile (TYPE): Description

        Returns:
            TYPE: Description
        """
        if type(eventsfile) == str:
            events = np.load(eventsfile)
        else:
            events = eventsfile
        mon = DVSmonitor(*list(events))
        if dims is None:
            dims = (int(1 + np.max(mon.xi)), int(np.max(1 + mon.yi)))
        return cls(mon, dims)

    def savecsv(self, filename):
        """
        not tested

        Args:
            filename (TYPE): Description
        """
        with open(str(filename) + '.csv', 'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(self.t / second)
            csvwriter.writerow(self.i)

    def plot_panes(self, num_panes=None, timestep=None, filtersize=50 * ms, num_rows=2, filename=None):
        """
        Args:
            num_panes (None, optional): Description
            timestep (None, optional): Description
            filtersize (TYPE, optional): Description
            num_rows (int, optional): Description
            filename (None, optional): Description

        Returns:
            TYPE: Description
        """
        if num_panes is None and timestep is None:
            print('please specify either num_panes or timestep')
            return
        if num_panes is not None and timestep is not None:
            print('please specify either num_panes or timestep, not both!')
            return
        if num_panes is not None:
            timestep = self.plotlength / num_panes

        dt = filtersize / 10  # this is a choice we have to make
        num_steps = int(timestep / dt)
        video_filtered = self.get_filtered(dt, filtersize)

        gw_paneplot = pg.GraphicsWindow(title="pane plot")
        f = int(num_panes / num_rows)
        width = 1920
        gw_paneplot.resize(width, width / f * num_rows)

        vb = dict()
        imItems = dict()
        for i in range(num_panes):
            picture = video_filtered[i * num_steps]
            imItems[i] = pg.ImageItem(cm.jet(picture / np.max(video_filtered)))
            # imItems[i].setTitle(title=str(i*timestep)) #not possible for images
            vb[i] = gw_paneplot.addViewBox()
            vb[i].addItem(imItems[i])
            if np.mod(i + 1, np.round(num_panes / num_rows)) == 0:
                gw_paneplot.nextRow()

        # gw_paneplot.ui.histogram.gradient.setColorMap(CM_JET)
        # gw_paneplot.show()
        QtGui.QApplication.processEvents()  # without this, only the first plot is exported
        exp_img = pg.exporters.ImageExporter(gw_paneplot.scene())
        if filename is None:
            gw_paneplot.show()
        elif filename.endswith('.png'):
            exp_img.export(filename)
        elif filename.endswith('.svg'):
            exp = pg.exporters.SVGExporter(gw_paneplot.scene())
            exp.export(filename + '.svg')
        else:
            exp_img.export(filename + '_panes.png')

        return gw_paneplot

    def generate_gif(self, filename, tempfolder=os.path.expanduser('~'), filtersize=100 * ms, plot_dt=200 * defaultclock.dt):
        """
        This only works on linux at the moment
        On wiondows it could be done with ffmpeg somehow like that (names need to be adjusted):
        ffmpeg -f image2 -i image_%03d.jpg -vf scale=500x500 gifout.gif

        Args:
            filename (TYPE): Description
            tempfolder (TYPE, optional): Description
            filtersize (TYPE, optional): Description
            plot_dt (TYPE, optional): Description
        """
        gif_temp_dir = os.path.join(tempfolder, "gif_temp")
        pgImage = self.plot3d(plot_dt=plot_dt, filtersize=filtersize)
        if not os.path.exists(gif_temp_dir):
            os.makedirs(gif_temp_dir)
        pgImage.export(os.path.join(gif_temp_dir, "gif.png"))
        linux_command = "cd " + \
            str(gif_temp_dir) + ";" + \
            " convert -delay 1 -loop 0 *.png " + os.path.abspath(filename)
        if not filename.endswith('.gif'):
            linux_command = linux_command + ".gif"
        result = subprocess.check_output(linux_command, shell=True)
        print(result)
        # os.system(linux_command)
        shutil.rmtree(gif_temp_dir)
