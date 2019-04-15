import unittest

from brian2 import us, ms, prefs, defaultclock, start_scope, SpikeGeneratorGroup, SpikeMonitor, StateMonitor
import numpy as np
import warnings

from teili.tools.visualizer.DataControllers import Histogram
from teili.tools.visualizer.DataViewers import PlotSettings
from teili.tools.visualizer.DataModels import EventsModel, StateVariablesModel
from teili.core.groups import Neurons, Connections
from teili import TeiliNetwork
from teili.models.neuron_models import DPI
from teili.models.synapse_models import DPISyn
from teili.models.parameters.dpi_neuron_param import parameters as neuron_model_param

try:
    import pyqtgraph as pg
    from PyQt5 import QtGui
    QtApp = QtGui.QApplication([])
    SKIP_PYQTGRAPH_RELATED_UNITTESTS = False
except BaseException:
    SKIP_PYQTGRAPH_RELATED_UNITTESTS = True

def run_brian_network():
    prefs.codegen.target = "numpy"
    defaultclock.dt = 10 * us

    start_scope()
    N_input, N_N1, N_N2 = 1, 5, 3
    duration_sim = 150

    Net = TeiliNetwork()
    # setup spike generator
    spikegen_spike_times = np.sort(
        np.random.choice(
            size=30,
            a=range(
                0,
                duration_sim,
                5),
            replace=False)) * ms
    spikegen_neuron_ids = np.zeros_like(spikegen_spike_times) / ms
    gInpGroup = SpikeGeneratorGroup(
        N_input,
        indices=spikegen_neuron_ids,
        times=spikegen_spike_times,
        name='gtestInp')
    # setup neurons
    testNeurons1 = Neurons(
        N_N1, equation_builder=DPI(
            num_inputs=2), name="testNeuron")
    testNeurons1.set_params(neuron_model_param)
    testNeurons2 = Neurons(
        N_N2, equation_builder=DPI(
            num_inputs=2), name="testNeuron2")
    testNeurons2.set_params(neuron_model_param)
    # setup connections
    InpSyn = Connections(
        gInpGroup,
        testNeurons1,
        equation_builder=DPISyn(),
        name="testSyn",
        verbose=False)
    InpSyn.connect(True)
    InpSyn.weight = '100 + rand() * 50'
    Syn = Connections(
        testNeurons1,
        testNeurons2,
        equation_builder=DPISyn(),
        name="testSyn2")
    Syn.connect(True)
    Syn.weight = '100+ rand() * 50'
    # spike monitors input and network
    spikemonN1 = SpikeMonitor(testNeurons1, name='spikemon')
    spikemonN2 = SpikeMonitor(testNeurons2, name='spikemonOut')
    # # state monitor neurons
    statemonN1 = StateMonitor(
        testNeurons1, variables=[
            "Iin", "Imem"], record=[
            0, 3], name='statemonNeu')
    statemonN2 = StateMonitor(
        testNeurons2,
        variables=['Iahp'],
        record=0,
        name='statemonNeuOut')

    Net.add(
        gInpGroup,
        testNeurons1,
        testNeurons2,
        InpSyn,
        Syn,
        spikemonN1,
        spikemonN2,
        statemonN1,
        statemonN2)
    Net.run(duration_sim * ms)
    print('Simulation run for {} ms'.format(duration_sim))
    return spikemonN1, spikemonN2, statemonN1, statemonN2


def get_plotsettings():
    MyPlotSettings = PlotSettings(
        fontsize_title=20,
        fontsize_legend=14,
        fontsize_axis_labels=14,
        marker_size=30,
        colors=[
            'r',
            'b',
            'g'])
    return MyPlotSettings


SHOW_PLOTS_IN_TESTS = False


class TestHistogram(unittest.TestCase):

    def test_getdata(self):

        spikemonN1, spikemonN2, statemonN1, statemonN2 = run_brian_network()

        # from DataModels & EventModels
        EM1 = EventsModel.from_brian_spike_monitor(spikemonN1)
        EM2 = EventsModel.from_brian_spike_monitor(spikemonN2)
        SVM = StateVariablesModel.from_brian_state_monitors(
            [statemonN1, statemonN2], skip_not_rec_neuron_ids=False)
        DataModel_to_attr = [(EM1, 'neuron_ids'), (EM2, 'neuron_ids'), (SVM, 'Imem')]

        HC = Histogram(
            MyPlotSettings=get_plotsettings(),
            DataModel_to_attr=DataModel_to_attr,
            show_immediately=SHOW_PLOTS_IN_TESTS)
        HC._get_data(DataModel_to_attr)
        self.assertEqual(len(HC.data), len(DataModel_to_attr))
        self.assertEqual(
            np.size(
                HC.data[0]), np.size(
                getattr(
                    spikemonN1, 'i')))

        # from brian state monitor and spike monitors
        DataModel_to_attr = [
            (spikemonN1, 'i'),
            (spikemonN2, 'i'),
            (statemonN1, 'Imem')]

        HC = Histogram(
            MyPlotSettings=get_plotsettings(),
            DataModel_to_attr=DataModel_to_attr,
            show_immediately=SHOW_PLOTS_IN_TESTS)
        HC._get_data(DataModel_to_attr)
        self.assertEqual(len(HC.data), len(DataModel_to_attr))
        self.assertEqual(
            np.size(
                HC.data[0]), np.size(
                getattr(
                    spikemonN1, 'i')))

    def test_createhistogram(self):
        # check backends
        spikemonN1, spikemonN2, statemonN1, statemonN2 = run_brian_network()

        EM1 = EventsModel.from_brian_spike_monitor(spikemonN1)
        EM2 = EventsModel.from_brian_spike_monitor(spikemonN2)
        SVM = StateVariablesModel.from_brian_state_monitors(
            [statemonN1, statemonN2], skip_not_rec_neuron_ids=False)
        DataModel_to_attr = [(EM1, 'neuron_ids'), (EM2, 'neuron_ids'), (SVM, 'Imem')]

        subgroup_labels = ['EM1', 'EM2', 'SVM']

        backend = 'matplotlib'
        HC = Histogram(
            MyPlotSettings=get_plotsettings(),
            DataModel_to_attr=DataModel_to_attr,
            subgroup_labels=subgroup_labels,
            bins=None,
            orientation='vertical',
            title='histogram',
            xlabel='bins',
            ylabel='count',
            backend=backend,
            mainfig=None,
            subfig=None,
            QtApp=None,
            show_immediately=SHOW_PLOTS_IN_TESTS)
        HC.create_plot()

        if not SKIP_PYQTGRAPH_RELATED_UNITTESTS:
            backend = 'pyqtgraph'
            HC = Histogram(
                MyPlotSettings=get_plotsettings(),
                DataModel_to_attr=DataModel_to_attr,
                subgroup_labels=subgroup_labels,
                bins=None,
                orientation='vertical',
                title='histogram',
                xlabel='bins',
                ylabel='count',
                backend=backend,
                mainfig=None,
                subfig=None,
                QtApp=QtApp,
                show_immediately=SHOW_PLOTS_IN_TESTS)
            HC.create_plot()
        else:
            warnings.warn("Skip part of unittest TestHistogram.test_createhistogram using pyqtgraph"
                                                       "as pyqtgraph could not be imported")


if __name__ == '__main__':
    unittest.main()
