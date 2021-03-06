import numpy as np
from scipy.stats import norm

from brian2 import Hz, mA, ms, mV, prefs, SpikeMonitor, StateMonitor, defaultclock,\
    ExplicitStateUpdater, SpikeGeneratorGroup, TimedArray, PoissonGroup,\
    PopulationRateMonitor

from teili.core.groups import Neurons, Connections
from teili import TeiliNetwork
from teili.stimuli.testbench import SequenceTestbench
from teili.tools.group_tools import add_group_activity_proxy
from teili.models.builder.synapse_equation_builder import SynapseEquationBuilder
from teili.models.builder.neuron_equation_builder import NeuronEquationBuilder

static_synapse_model = SynapseEquationBuilder(base_unit='quantized',
    plasticity='non_plastic')
neuron_model = NeuronEquationBuilder(base_unit='quantized',
    position='spatial')

import sys
import pickle
import os
from datetime import datetime

#############
# Load models
path = os.path.expanduser('/Users/Pablo/git/teili/')
model_path = os.path.join(path, "teili", "models", "equations", "")
adp_synapse_model = SynapseEquationBuilder.import_eq(
        model_path + 'StochInhStdp.py')

# Initialize simulation preferences
prefs.codegen.target = "numpy"
defaultclock.dt = 1 * ms
stochastic_decay = ExplicitStateUpdater('''x_new = f(x,t)''')
net = TeiliNetwork()

# Initialize input sequence
poisson_spikes = PoissonGroup(100, rates=50*Hz)

#################
# Building network
# cells
num_exc = 100
num_inh = 25
exc_cells = Neurons(num_exc,
                    equation_builder=neuron_model(num_inputs=3),
                    method=stochastic_decay,
                    name='exc_cells',
                    verbose=True)
inh_cells = Neurons(num_inh,
                    equation_builder=neuron_model(num_inputs=3),
                    method=stochastic_decay,
                    name='inh_cells',
                    verbose=True)
# Register proxy arrays
dummy_unit = 1*mV
exc_cells.variables.add_array('activity_proxy', 
                               size=exc_cells.N,
                               dimensions=dummy_unit.dim)
exc_cells.variables.add_array('normalized_activity_proxy', 
                               size=exc_cells.N)

# Connections
feedforward_exc = Connections(poisson_spikes, exc_cells,
                              equation_builder=static_synapse_model(),
                              method=stochastic_decay,
                              name='feedforward_exc')
feedforward_inh = Connections(poisson_spikes, inh_cells,
                              equation_builder=static_synapse_model(),
                              method=stochastic_decay,
                              name='feedforward_inh')
exc_inh_conn = Connections(exc_cells, inh_cells,
                           equation_builder=static_synapse_model(),
                           method=stochastic_decay,
                           name='exc_inh_conn')
inh_exc_conn = Connections(inh_cells, exc_cells,
                           equation_builder=adp_synapse_model,
                           method=stochastic_decay,
                           name='inh_exc_conn')
exc_exc_conn = Connections(exc_cells, exc_cells,
                           equation_builder=static_synapse_model(),
                           method=stochastic_decay,
                           name='exc_exc_conn')
inh_inh_conn = Connections(inh_cells, inh_cells,
                           equation_builder=static_synapse_model(),
                           method=stochastic_decay,
                           name='inh_inh_conn')
feedforward_exc.connect()
feedforward_inh.connect()
exc_inh_conn.connect()
inh_exc_conn.connect()
exc_exc_conn.connect()
inh_inh_conn.connect(p=.1)

# Time constants
feedforward_exc.tausyn = 5*ms
feedforward_inh.tausyn = 5*ms
inh_exc_conn.tausyn = 10*ms
exc_inh_conn.tausyn = 5*ms
exc_exc_conn.tausyn = 5*ms
inh_inh_conn.tausyn = 10*ms
exc_cells.tau = 19*ms
inh_cells.tau = 10*ms

exc_cells.Vm = 3*mV
exc_cells.I_min = -16*mA
exc_cells.I_max = 15*mA
inh_cells.Vm = 3*mV
inh_cells.I_min = -16*mA
inh_cells.I_max = 15*mA

inh_exc_conn.weight = -1
inh_exc_conn.w_plast = 1
inh_exc_conn.w_max = 15
inh_exc_conn.A_max = 15
inh_exc_conn.taupre = 20*ms
inh_exc_conn.taupost = 20*ms
inh_exc_conn.rand_num_bits_syn = 4
inh_exc_conn.stdp_thres = 3
inh_inh_conn.weight = -1
feedforward_exc.weight = 4
feedforward_inh.weight = 4
exc_inh_conn.weight = 1
exc_exc_conn.weight = 1

# Add proxy activity group
activity_proxy_group = [exc_cells]
add_group_activity_proxy(activity_proxy_group,
                         buffer_size=300,
                         decay=150)
variance_th = 13
inh_exc_conn.variance_th = np.random.uniform(
        low=variance_th - 0.1,
        high=variance_th + 0.1,
        size=len(inh_exc_conn))

##################
# Setting up monitors
spikemon_exc_neurons = SpikeMonitor(exc_cells, name='spikemon_exc_neurons')
spikemon_inh_neurons = SpikeMonitor(inh_cells, name='spikemon_inh_neurons')
spikemon_seq_neurons = SpikeMonitor(poisson_spikes, name='spikemon_seq_neurons')
statemon_ffe_conns = StateMonitor(feedforward_exc, variables=['I_syn'], record=True,
                                  name='statemon_ffe_conns')
statemon_ee_conns = StateMonitor(exc_exc_conn, variables=['I_syn'], record=True,
                                  name='statemon_ee_conns')
statemon_ie_conns = StateMonitor(inh_exc_conn, variables=['I_syn'], record=True,
                                  name='statemon_ie_conns')
statemon_inh_conns = StateMonitor(inh_exc_conn, variables=['w_plast', 'normalized_activity_proxy'], record=True,
                                  name='statemon_inh_conns')
statemon_inh_cells = StateMonitor(inh_cells, variables=['Vm'], record=True,
                                  name='statemon_inh_cells')
statemon_exc_cells = StateMonitor(exc_cells, variables=['Vm', 'normalized_activity_proxy'], record=True,
                                  name='statemon_exc_cells')
statemon_pop_rate_e = PopulationRateMonitor(exc_cells)

net = TeiliNetwork()
net.add(poisson_spikes, exc_cells, inh_cells, inh_exc_conn, feedforward_exc,
        spikemon_exc_neurons, spikemon_inh_neurons, exc_inh_conn, 
        spikemon_seq_neurons, statemon_ffe_conns, statemon_inh_conns,
        statemon_ie_conns, statemon_inh_cells, inh_inh_conn,
        statemon_ee_conns, exc_exc_conn, statemon_exc_cells,
        statemon_pop_rate_e, feedforward_inh)

net.run(10000*ms, report='stdout', report_period=100*ms)
variance_th = 2
inh_exc_conn.variance_th = np.random.uniform(
        low=variance_th - 0.1,
        high=variance_th + 0.1,
        size=len(inh_exc_conn))
net.run(10000*ms, report='stdout', report_period=100*ms)

# Plots
from brian2 import *
figure()
_ = hist(inh_exc_conn.w_plast, bins=20)
xlabel('Inh. weight')
ylabel('Count')
title('Distribution of inhibitory weights')

figure()
y = np.mean(statemon_exc_cells.normalized_activity_proxy, axis=0)
stdd=np.std(statemon_exc_cells.normalized_activity_proxy, axis=0)
plot(statemon_inh_conns.t/ms, y)
ylabel('normalized activity mean value')
xlabel('time (ms)')
ylim([-0.05, 1.05])
fill_between(statemon_inh_conns.t/ms, y-stdd, y+stdd, facecolor='lightblue')
annotate(f"""Shown for the sake of comparison with ADP
           variance threshold: 14 for first 10s, 2 afterwards""", xy = (0, 0.1))

figure()
plot(statemon_exc_cells.normalized_activity_proxy.T)
xlabel('time (ms)')
ylabel('normalized activity value')
title('Normalized activity of all neurons')

figure()
plot(np.array(statemon_pop_rate_e.t/ms), np.array(statemon_pop_rate_e.smooth_rate(width=60*ms)/Hz))
xlabel('time (ms)')
ylabel('Mean firing rate (Hz)')
title('Effect of inhibitory weights on firing pattern of excitatory neurons')

tot_e_curr = np.sum(statemon_ffe_conns.I_syn, axis=0) + np.sum(statemon_ee_conns.I_syn, axis=0)
tot_i_curr = np.sum(statemon_ie_conns.I_syn, axis=0)
figure()
plot(statemon_ffe_conns.t/ms, tot_e_curr/amp, color='r', label='summed exc. currents')
plot(statemon_inh_conns.t/ms, -tot_i_curr/amp, color='b', label='summed inh. current')
plot(statemon_inh_conns.t/ms, (tot_e_curr - tot_i_curr)/amp, color='k', label='net. current')
ylabel('Current [amp]')
xlabel('time [ms]')
title('EI balance')
legend()

figure()
plot(spikemon_exc_neurons.t/ms, spikemon_exc_neurons.i, '.')
title('Exc. neurons')
figure()
plot(spikemon_inh_neurons.t/ms, spikemon_inh_neurons.i, '.')
title('Inh. neurons')
figure()
plot(spikemon_seq_neurons.t/ms, spikemon_seq_neurons.i, '.')
title('Input spikes')

# TODO vectorize by working with flattened array
#win_slidings = []
#win_size = 30
## Get indices to make calculations over a sliding window
#for y in range(np.shape(statemon_exc_cells.Vm)[1]):
#    win_slidings.append([])
#    for x in range(win_size):
#            win_slidings[-1].append(x+y)
#
# Adjust last win_size-1 intervals which are outside array dimensions
#trim_win = [val[:-(i+1)] for i, val in enumerate(win_slidings[-win_size+1:])]
#win_slidings[-win_size+1:] = trim_win
#
#mean_exc_rate = []
#mean_inh_rate = []
#for i in win_slidings:
#    mean_exc_rate.append(np.mean(statemon_exc_cells.Vm[:,i]))
#    mean_inh_rate.append(np.mean(statemon_inh_cells.Vm[:,i]))
#
#figure()
#plot(mean_exc_rate)
#title('Mean of 100 excitatory neurons')
#xlabel('time(ms)')
#ylabel('V')
#
#figure()
#plot(mean_inh_rate)
#title('Mean of 25 inhibitory neurons')
#xlabel('time(ms)')
#ylabel('V')

show()
np.savez('adp.npz', proxy=statemon_exc_cells.normalized_activity_proxy.T,
         e_curr=tot_e_curr/amp, i_curr=tot_i_curr/amp)
