# -*- coding: utf-8 -*-
# @Author: mmilde
# @Date:   2017-25-08 13:43:10
# @Last Modified by:   Moritz Milde
# @Last Modified time: 2018-06-01 18:46:24
# -*- coding: utf-8 -*-

"""
This is a tutorial example used to learn the basics of the Brian2 INI library.
The emphasise is on neuron groups and non-plastic synapses.
"""

from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np

from brian2 import ms, mV, pA, nS, nA, pF, us, volt, second, Network, prefs,\
    SpikeMonitor, StateMonitor, figure, plot, show, xlabel, ylabel,\
    seed, xlim, ylim, subplot, network_operation, TimedArray,\
    defaultclock, SpikeGeneratorGroup, asarray, pamp, set_device, device

from teili.core.groups import Neurons, Connections
from teili import teiliNetwork
# from teili.models.neuron_models import DPI as neuron_model
# from teili.models.synapse_models import DPISyn as syn_model
# from teili.models.parameters.dpi_neuron_param import parameters as neuron_model_param
from teili.models.neuron_models import Izhikevich as neuron_model
from teili.models.synapse_models import DoubleExponential as syn_model
from teili.models.parameters.izhikevich_param import parameters as neuron_model_param

prefs.codegen.target = "numpy"
# defaultclock.dt = 10 * us

tsInp = asarray([1, 3, 4, 5, 6, 7, 8, 9]) * ms
indInp = asarray([0, 0, 0, 0, 0, 0, 0, 0])
gInpGroup = SpikeGeneratorGroup(1, indices=indInp,
                                times=tsInp, name='gtestInp')


Net = teiliNetwork()

testNeurons = Neurons(2, equation_builder=DPI(num_inputs=2), name="testNeuron")
# Example of how to set parameters, saved as a dictionary
testNeurons.set_params(neuron_model_param)
testNeurons.refP = 3 * ms

testNeurons2 = Neurons(2, equation_builder=neuron_model(num_inputs=2), name="testNeuron2")
testNeurons2.set_params(neuron_model_param)
testNeurons2.refP = 3 * ms


InpSyn = Connections(gInpGroup, testNeurons, equation_builder=DPISyn(), name="testSyn", verbose=False)
InpSyn.connect(True)

InpSyn.weight = 10
Syn = Connections(testNeurons, testNeurons2, equation_builder=DPISyn(), name="testSyn2")
Syn.connect(True)

# you can change all the parameters like this after creation of the neurongroup:
if 'Imem' in neuron_model().keywords['model']:
    InpSyn.weight = 10
    Syn.weight = 100

    # Example of how to set single parameters, rather than using an entire dictionary
    testNeurons.Iconst = 10 * nA
    # testNeurons2.Itau = 13 * pA
    # testNeurons2.Iath = 80 * pA
    # testNeurons2.Iagain = 20 * pA
    # testNeurons2.Ianorm = 8 * pA
elif 'Vm' in neuron_model().keywords['model']:
    InpSyn.weight = 1.5
    Syn.weight = 8.0
    # Example of how to set single parameters, rather than using an entire dictionary
    testNeurons.Iconst = 3 * nA

spikemonInp = SpikeMonitor(gInpGroup, name='spikemonInp')
spikemon = SpikeMonitor(testNeurons, name='spikemon')
spikemonOut = SpikeMonitor(testNeurons2, name='spikemonOut')
statemonInpSyn = StateMonitor(
    InpSyn, variables='Ie_syn', record=True, name='statemonInpSyn')
if 'Imem' in neuron_model().keywords['model']:
    statemonNeuOut = StateMonitor(testNeurons2,
                                  variables=['Imem'],
                                  record=0, name='statemonNeuOut')
    statemonNeuIn = StateMonitor(testNeurons, variables=[
                             "Iin", "Imem", "Iahp"], record=[0, 1], name='statemonNeu')
elif 'Vm' in neuron_model().keywords['model']:
    statemonNeuOut = StateMonitor(testNeurons2,
                                  variables=['Vm'],
                                  record=0, name='statemonNeuOut')
    statemonNeuIn = StateMonitor(testNeurons, variables=[
                             "Iin", "Vm", "Iadapt"], record=[0, 1], name='statemonNeu')

statemonSynOut = StateMonitor(
    Syn, variables='Ie_syn', record=True, name='statemonSynOut')

Net.add(gInpGroup, testNeurons, testNeurons2, InpSyn, Syn, spikemonInp, spikemon,
        spikemonOut, statemonNeuIn, statemonNeuOut, statemonSynOut, statemonInpSyn)

duration = 500
Net.run(duration * ms)

# Visualize simulation results
pg.setConfigOptions(antialias=True)

labelStyle = {'color': '#FFF', 'font-size': '12pt'}
win = pg.GraphicsWindow(title='teili Test Simulation')
win.resize(1900, 600)
win.setWindowTitle('Simple SNN')

p1 = win.addPlot(title="Spike generator")
p2 = win.addPlot(title="Input synapses")
win.nextRow()
p3 = win.addPlot(title='Intermediate neuron')
p4 = win.addPlot(title="Output synapses")
win.nextRow()
p5 = win.addPlot(title="Output spikes")
p6 = win.addPlot(title="Output membrane current")

colors = [(255, 0, 0), (89, 198, 118), (0, 0, 255), (247, 0, 255),
          (0, 0, 0), (255, 128, 0), (120, 120, 120), (0, 171, 255)]


p1.setXRange(0, duration, padding=0)
p2.setXRange(0, duration, padding=0)
p3.setXRange(0, duration, padding=0)
p4.setXRange(0, duration, padding=0)
p5.setXRange(0, duration, padding=0)
p6.setXRange(0, duration, padding=0)

# Spike generator
p1.plot(x=np.asarray(spikemonInp.t / ms), y=np.asarray(spikemonInp.i),
        pen=None, symbol='o', symbolPen=None,
        symbolSize=7, symbolBrush=(255, 255, 255))

# Input synapses
for i, data in enumerate(np.asarray(statemonInpSyn.Ie_syn)):
    name = 'Syn_{}'.format(i)
    p2.plot(x=np.asarray(statemonInpSyn.t / ms), y=data,
            pen=pg.mkPen(colors[3], width=2), name=name)

# Intermediate neurons
if hasattr(statemonNeuIn,'Imem'):
    for i, data in enumerate(np.asarray(statemonNeuIn.Imem)):
        p3.plot(x=np.asarray(statemonNeuIn.t / ms), y=data,
                pen=pg.mkPen(colors[6], width=2))
if hasattr(statemonNeuIn,'Vm'):
    for i, data in enumerate(np.asarray(statemonNeuIn.Vm)):
        p3.plot(x=np.asarray(statemonNeuIn.t / ms), y=data,
                pen=pg.mkPen(colors[6], width=2))

# Output synapses
for i, data in enumerate(np.asarray(statemonSynOut.Ie_syn)):
    name = 'Syn_{}'.format(i)
    p4.plot(x=np.asarray(statemonSynOut.t / ms), y=data,
            pen=pg.mkPen(colors[1], width=2), name=name)

if hasattr(statemonNeuOut,'Imem'):
    for data in np.asarray(statemonNeuOut.Imem):
        p6.plot(x=np.asarray(statemonNeuOut.t / ms), y=data,
                pen=pg.mkPen(colors[5], width=3))
if hasattr(statemonNeuOut,'Vm'):
    for data in np.asarray(statemonNeuOut.Vm):
        print(data)
        p6.plot(x=np.asarray(statemonNeuOut.t / ms), y=data,
                pen=pg.mkPen(colors[5], width=3))

p5.plot(x=np.asarray(spikemonOut.t / ms), y=np.asarray(spikemonOut.i),
        pen=None, symbol='o', symbolPen=None,
        symbolSize=7, symbolBrush=(255, 0, 0))

p1.setLabel('left', "Neuron ID", **labelStyle)
p1.setLabel('bottom', "Time (ms)", **labelStyle)
p2.setLabel('left', "Synaptic current", units='A', **labelStyle)
p2.setLabel('bottom', "Time (ms)", **labelStyle)
i_current_name = 'Imem' if 'Imem' in neuron_model().keywords['model'] else 'Vm'
p3.setLabel('left', "Membrane current %s"%i_current_name, units="A", **labelStyle)
p3.setLabel('bottom', "Time (ms)", **labelStyle)
p4.setLabel('left', "Synaptic current I_e", units="A", **labelStyle)
p4.setLabel('bottom', "Time (ms)", **labelStyle)
p6.setLabel('left', "Membrane current %s"%i_current_name, units="A", **labelStyle)
p6.setLabel('bottom', "Time (ms)", **labelStyle)
p5.setLabel('left', "Neuron ID", **labelStyle)
p5.setLabel('bottom', "Time (ms)", **labelStyle)

b = QtGui.QFont("Sans Serif", 10)
p1.getAxis('bottom').tickFont = b
p1.getAxis('left').tickFont = b
p2.getAxis('bottom').tickFont = b
p2.getAxis('left').tickFont = b
p3.getAxis('bottom').tickFont = b
p3.getAxis('left').tickFont = b
p4.getAxis('bottom').tickFont = b
p4.getAxis('left').tickFont = b
p5.getAxis('bottom').tickFont = b
p5.getAxis('left').tickFont = b
p6.getAxis('bottom').tickFont = b
p6.getAxis('left').tickFont = b


QtGui.QApplication.instance().exec_()
