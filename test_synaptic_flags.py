#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 14 10:40:10 2019

@author: matteo
"""

"""
This file provides an example of how to use neuron and synapse models which are present
on neurmorphic chips in the context of synaptic plasticity based on precise timing of spikes.
We use a standard STDP protocal with a exponentioally decaying window.

"""
from pyqtgraph.Qt import QtGui
import pyqtgraph as pg
import pyqtgraph.exporters
import numpy as np
import os


from brian2 import us, ms, pA, nA, prefs,\
        SpikeMonitor, StateMonitor,\
        SpikeGeneratorGroup

from teili.core.groups import Neurons, Connections
from teili import TeiliNetwork
from teili.models.neuron_models import DPI
from teili.models.synapse_models import DPISyn, DPIstdp
from teili.stimuli.testbench import STDP_Testbench


prefs.codegen.target = "numpy"
Net = TeiliNetwork()

from teili.models.builder.neuron_equation_builder import NeuronEquationBuilder
from teili.models.builder.synapse_equation_builder import SynapseEquationBuilder
from teili.models.parameters.dpi_neuron_param import parameters as neuron_model_param


my_neuron = NeuronEquationBuilder.import_eq('teili/models/equations/DPI', num_inputs=2)



my_syn_model = SynapseEquationBuilder.import_eq(
    'teili/models/equations/DPISyn')

test_neuron1 = Neurons(N=2, equation_builder=my_neuron(num_inputs=2),
                                             name="testNeuron")
test_neuron2 = Neurons(N=2, equation_builder=my_neuron(num_inputs=2),
                                             name="testNeuron1")



input_timestamps = np.asarray([1, 3, 4, 5, 6, 7, 8, 9]) * ms
input_indices = np.asarray([0, 0, 0, 0, 0, 0, 0, 0])
input_spikegenerator = SpikeGeneratorGroup(1, indices=input_indices,
                                           times=input_timestamps, name='gtestInp')


input_synapse = Connections(input_spikegenerator, test_neuron1,
                            equation_builder=my_syn_model(),
                            name="input_synapse")

test_synapse = Connections(test_neuron1, test_neuron2, equation_builder=my_syn_model)

input_synapse.connect(True)

test_synapse.connect(True)

spikemon_input = SpikeMonitor(input_spikegenerator, name='spikemon_input')
spikemon_test_neuron1 = SpikeMonitor(
        test_neuron1, name='spikemon_test_neurons1')
spikemon_test_neuron2 = SpikeMonitor(
        test_neuron2, name='spikemon_test_neurons2')

statemon_input_synapse = StateMonitor(
        input_synapse, variables='Ie_syn', record=True, name='statemon_input_synapse')

statemon_test_synapse = StateMonitor(
        test_synapse, variables='Ie_syn', record=True, name='statemon_test_synapse')

Net.add(input_spikegenerator, test_neuron1, test_neuron2,
        input_synapse, test_synapse,
        spikemon_input, spikemon_test_neuron1, spikemon_test_neuron2,
         statemon_test_synapse, statemon_input_synapse)

# Example of how to set parameters, saved as a dictionary
test_neuron1.set_params(neuron_model_param)
test_neuron2.set_params(neuron_model_param)

# Example of how to set a single parameter
test_neuron1.refP = 1 * ms
test_neuron2.refP = 1 * ms

input_synapse.weight = 5000
test_synapse.weight = 8000
test_neuron1.Iconst = 10 * nA


input_synapse.beta = 1
test_synapse.beta = 1

duration = 20
Net.run(duration * ms)


app = QtGui.QApplication.instance()
if app is None:
        app = QtGui.QApplication(sys.argv)
else:
        print('QApplication instance already exists: %s' % str(app))

pg.setConfigOptions(antialias=True)

labelStyle = {'color': '#FFF', 'font-size': '12pt'}
win = pg.GraphicsWindow()
win.resize(2100, 1200)
win.setWindowTitle('Simple Spiking Neural Network')

p1 = win.addPlot(title="Input spike generator")
p2 = win.addPlot(title="Input synapses")
win.nextRow()
p3 = win.addPlot(title='Intermediate test neurons 1')
p4 = win.addPlot(title="Test synapses")
win.nextRow()
p5 = win.addPlot(title="Rasterplot of output test neurons 2")
p6 = win.addPlot(title="Output test neurons 2")

colors = [(255, 0, 0), (89, 198, 118), (0, 0, 255), (247, 0, 255),
                    (0, 0, 0), (255, 128, 0), (120, 120, 120), (0, 171, 255)]


p1.setXRange(0, duration, padding=0)
p2.setXRange(0, duration, padding=0)
p3.setXRange(0, duration, padding=0)
p4.setXRange(0, duration, padding=0)
p5.setXRange(0, duration, padding=0)
p6.setXRange(0, duration, padding=0)

# Spike generator
p1.plot(x=np.asarray(spikemon_input.t / ms), y=np.asarray(spikemon_input.i),
                pen=None, symbol='o', symbolPen=None,
                symbolSize=7, symbolBrush=(255, 255, 255))

# Input synapses
for i, data in enumerate(np.asarray(statemon_input_synapse.Ie_syn)):
        name = 'Syn_{}'.format(i)
        p2.plot(x=np.asarray(statemon_input_synapse.t / ms), y=data,
                        pen=pg.mkPen(colors[3], width=2), name=name)

# Output synapses
for i, data in enumerate(np.asarray(statemon_test_synapse.Ie_syn)):
        name = 'Syn_{}'.format(i)
        p4.plot(x=np.asarray(statemon_test_synapse.t / ms), y=data,
                        pen=pg.mkPen(colors[1], width=2), name=name)

p5.plot(x=np.asarray(spikemon_test_neuron2.t / ms), y=np.asarray(spikemon_test_neuron2.i),
                pen=None, symbol='o', symbolPen=None,
                symbolSize=7, symbolBrush=(255, 0, 0))

p1.setLabel('left', "Neuron ID", **labelStyle)
p1.setLabel('bottom', "Time (ms)", **labelStyle)
p2.setLabel('left', "EPSC", units='A', **labelStyle)
p2.setLabel('bottom', "Time (ms)", **labelStyle)

p4.setLabel('left', "EPSC", units="A", **labelStyle)
p4.setLabel('bottom', "Time (ms)", **labelStyle)

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


app.exec()



