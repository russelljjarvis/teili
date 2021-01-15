"""
This code implements a sequence learning using and Excitatory-Inhibitory 
network with STDP.
"""
import numpy as np
from scipy.stats import gamma
from scipy.signal import savgol_filter

from brian2 import ms, mV, Hz, prefs, SpikeMonitor, StateMonitor, defaultclock,\
    ExplicitStateUpdater, SpikeGeneratorGroup, TimedArray, PopulationRateMonitor

from teili.core.groups import Neurons, Connections
from teili import TeiliNetwork
from teili.models.neuron_models import StochasticLIF as neuron_model
from teili.models.synapse_models import StochasticSyn_decay_stoch_stdp as stdp_synapse_model
from teili.models.synapse_models import StochasticSyn_decay as static_synapse_model
from teili.stimuli.testbench import SequenceTestbench
from teili.tools.add_run_reg import add_lfsr
from teili.tools.group_tools import add_group_activity_proxy
from teili.models.builder.synapse_equation_builder import SynapseEquationBuilder

import sys
import json
import os
from datetime import datetime

# Load ADP synapse
path = os.path.expanduser("/home/pablo/teili_gl/teili")
model_path = os.path.join(path, "teili", "models", "equations", "")
adp_synapse_model = SynapseEquationBuilder.import_eq(
        model_path + 'StochSynAdp.py')

# process inputs
seq_dur = 150
learn_factor = 4
ei_p = 0.80
ie_p = 0.70
ee_p = 0.50#FIXME 0.30
ei_w = 2

# Defines if recurrent connections are included
if sys.argv[1] == 'no_rec':
    simple = True
elif sys.argv[1] == 'rec':
    simple = False
else:
    print('Provide correct argument')
    sys.exit(0)

# Initialize simulation preferences
prefs.codegen.target = "numpy"
defaultclock.dt = 1 * ms
stochastic_decay = ExplicitStateUpdater('''x_new = f(x,t)''')

# Initialize input sequence
num_items = 3
num_channels = 144
sub_sequence_duration = seq_dur
noise_prob = .001
item_rate = 25#FIXME 20
spike_times, spike_indices = [], []
sequence_repetitions = 150
sequence_duration = sequence_repetitions*sub_sequence_duration*ms
for i in range(sequence_repetitions):
    sequence = SequenceTestbench(num_channels, num_items, sub_sequence_duration,
                                 noise_prob, item_rate)
    tmp_i, tmp_t = sequence.stimuli()
    spike_indices.extend(tmp_i)
    tmp_t = [(x/ms+i*sub_sequence_duration) for x in tmp_t]
    spike_times.extend(tmp_t)
spike_indices = np.array(spike_indices)
spike_times = np.array(spike_times) * ms
# Save them for comparison
spk_i, spk_t = spike_indices, spike_times

# Reproduce activity in a neuron group (necessary for STDP compatibility)
spike_times = [spike_times[np.where(spike_indices==i)[0]] for i in range(num_channels)]
converted_input = (np.zeros((num_channels, int(sequence_duration/defaultclock.dt))) - 1)*ms
for ind, val in enumerate(spike_times):
    converted_input[ind, np.around(val/defaultclock.dt).astype(int)] = val
converted_input = np.transpose(converted_input)
converted_input = TimedArray(converted_input, dt=defaultclock.dt)
seq_cells = Neurons(num_channels, model='tspike=converted_input(t, i): second',
        threshold='t==tspike', refractory='tspike < 0*ms')
seq_cells.namespace.update({'converted_input':converted_input})

# Create neuron groups
num_exc = 81
num_inh = 20
exc_cells = Neurons(num_exc,
                    equation_builder=neuron_model(num_inputs=3),
                    method=stochastic_decay,
                    name='exc_cells',
                    verbose=True)
# Register proxy arrays
dummy_unit = 1*mV
exc_cells.variables.add_array('activity_proxy', 
                               size=exc_cells.N,
                               dimensions=dummy_unit.dim)

exc_cells.variables.add_array('normalized_activity_proxy', 
                               size=exc_cells.N)

inh_cells = Neurons(num_inh,
                    equation_builder=neuron_model(num_inputs=2),
                    method=stochastic_decay,
                    name='inh_cells',
                    verbose=True)

# Create synapses
exc_exc_conn = Connections(exc_cells, exc_cells,
                           equation_builder=static_synapse_model() if simple else stdp_synapse_model(),
                           method=stochastic_decay,
                           name='exc_exc_conn')
exc_inh_conn = Connections(exc_cells, inh_cells,
                           equation_builder=static_synapse_model(),
                           method=stochastic_decay,
                           name='exc_inh_conn')
inh_exc_conn = Connections(inh_cells, exc_cells,
                           equation_builder=adp_synapse_model,#FIXME
                           #equation_builder=static_synapse_model(),
                           method=stochastic_decay,
                           name='inh_exc_conn')
feedforward_exc = Connections(seq_cells, exc_cells,
                              equation_builder=stdp_synapse_model(),
                              method=stochastic_decay,
                              name='feedforward_exc')
feedforward_inh = Connections(seq_cells, inh_cells,
                              equation_builder=static_synapse_model(),
                              method=stochastic_decay,
                              name='feedforward_inh')

# Connect synapses
feedforward_exc.connect()#, p=.2) # FIXME
feedforward_inh.connect()#, p=.2)
exc_exc_conn.connect('i!=j', p=ee_p)
exc_inh_conn.connect(p=ei_p)
inh_exc_conn.connect(p=ie_p)

# Setting parameters
seed = 12
exc_cells.Vm = 3*mV
exc_cells.lfsr_num_bits = 9
inh_cells.Vm = 3*mV
feedforward_exc.A_gain = learn_factor
inh_exc_conn.weight = 1# FIXME
inh_exc_conn.variance_th = 0.50
mean_ie_w = 2
for i in range(num_inh):
    weight_length = np.shape(inh_exc_conn.weight[i,:])
    sampled_weights = gamma.rvs(a=mean_ie_w, loc=1, size=weight_length).astype(int)
    sampled_weights = -np.clip(sampled_weights, 0, 15)
    inh_exc_conn.w_plast[i,:] = sampled_weights#FIXME .weight
exc_exc_conn.weight = 0 if simple else 1
mean_ee_w = 2
#exc_exc_conn.taupre = 10*ms FIXME
#exc_exc_conn.taupost = 10*ms
for i in range(num_exc):
    if not simple:
        weight_length = np.shape(exc_exc_conn.w_plast[i,:])
        exc_exc_conn.w_plast[i,:] = gamma.rvs(a=mean_ee_w, size=weight_length).astype(int)
    weight_length = np.shape(exc_inh_conn.weight[i,:])
    sampled_weights = gamma.rvs(a=ei_w, loc=1, size=weight_length).astype(int)
    sampled_weights = np.clip(sampled_weights, 0, 15)
    exc_inh_conn.weight[i,:] = sampled_weights
feedforward_exc.weight = 1
mean_ffe_w = 2
mean_ffi_w = 1
for i in range(num_channels):
    weight_length = np.shape(feedforward_exc.w_plast[i,:])
    feedforward_exc.w_plast[i,:] = gamma.rvs(a=mean_ffe_w, size=weight_length).astype(int)
    weight_length = np.shape(feedforward_inh.weight[i,:])
    feedforward_inh.weight[i,:] = gamma.rvs(a=mean_ffi_w, loc=1, size=weight_length).astype(int)
#a=1.3
#x = np.linspace(gamma.ppf(0.01, a, loc=1),gamma.ppf(0.99, a, loc=1), 100)
#plt.plot(x, gamma.pdf(x, a,loc=1),'r-', lw=5, alpha=0.6, label='gamma pdf')
#plt.show()
add_lfsr(exc_cells, seed, defaultclock.dt)
add_lfsr(inh_cells, seed, defaultclock.dt)
add_lfsr(exc_exc_conn, seed, defaultclock.dt)
add_lfsr(exc_inh_conn, seed, defaultclock.dt)
add_lfsr(inh_exc_conn, seed, defaultclock.dt)
add_lfsr(feedforward_exc, seed, defaultclock.dt)
add_lfsr(feedforward_inh, seed, defaultclock.dt)

# Add proxy activity group
activity_proxy_group = [exc_cells]
add_group_activity_proxy(activity_proxy_group,
                         buffer_size=200,
                         decay=150)
inh_exc_conn.variance_th = np.random.uniform(
        low=inh_exc_conn.variance_th - 0.1,
        high=inh_exc_conn.variance_th + 0.1,
        size=len(inh_exc_conn))

# Setting up monitors
spikemon_exc_neurons = SpikeMonitor(exc_cells, name='spikemon_exc_neurons')
spikemon_inh_neurons = SpikeMonitor(inh_cells, name='spikemon_inh_neurons')
spikemon_seq_neurons = SpikeMonitor(seq_cells, name='spikemon_seq_neurons')
statemon_exc_cells = StateMonitor(exc_cells, variables=['Vm'], record=True,
                                  name='statemon_exc_cells')
statemon_inh_cells = StateMonitor(inh_cells, variables=['Vm'], record=True,
                                  name='statemon_inh_cells')
if not simple:
    statemon_rec_conns = StateMonitor(exc_exc_conn, variables=['w_plast'], record=True,
                                      name='statemon_rec_conns')
statemon_inh_conns = StateMonitor(inh_exc_conn, variables=['w_plast', 'delta_w'], record=True,
                                  name='statemon_inh_conns')
statemon_ffe_conns = StateMonitor(feedforward_exc, variables=['w_plast'], record=True,
                                  name='statemon_ffe_conns')
statemon_pop_rate_e = PopulationRateMonitor(exc_cells)
statemon_pop_rate_i = PopulationRateMonitor(inh_cells)

net = TeiliNetwork()
if not simple:
    net.add(seq_cells, exc_cells, inh_cells, exc_exc_conn, exc_inh_conn, inh_exc_conn,
            feedforward_exc, feedforward_inh, statemon_exc_cells, statemon_inh_cells,
            statemon_rec_conns, spikemon_exc_neurons, spikemon_inh_neurons,
            spikemon_seq_neurons, statemon_ffe_conns, statemon_pop_rate_e,
            statemon_pop_rate_i, statemon_inh_conns)
else:
    net.add(seq_cells, exc_cells, inh_cells, exc_exc_conn, exc_inh_conn, inh_exc_conn,
            feedforward_exc, feedforward_inh, statemon_exc_cells, statemon_inh_cells,
            spikemon_exc_neurons, spikemon_inh_neurons,
            spikemon_seq_neurons, statemon_ffe_conns, statemon_pop_rate_e,
            statemon_pop_rate_i, statemon_inh_conns)
net.run(sequence_duration + 0*ms, report='stdout', report_period=100*ms)

if not np.array_equal(spk_t, spikemon_seq_neurons.t):
    print('Proxy activity and generated input do not match.')
    sys.exit()

# Save targets of recurrent connections as python object
n_rows = num_exc
recurrent_ids = []
recurrent_weights = []
if not simple:
    for i in range(n_rows):
        recurrent_weights.append(list(exc_exc_conn.w_plast[i, :]))
        recurrent_ids.append(list(exc_exc_conn.j[i, :]))

tmp_spike_trains = spikemon_exc_neurons.spike_trains()
neuron_rate = {}
peak_instants = {}
interval = (sequence_duration/ms-sub_sequence_duration, sequence_duration/ms)
for key, val in tmp_spike_trains.items():
    selected_spikes = [x for x in val/ms if x>(sequence_duration/ms-sub_sequence_duration)]
    h, b = np.histogram(selected_spikes, range=interval)
    neuron_rate[key] = {'rate': savgol_filter(h, 9, 5), 't': b[:-1]}
    max_id = np.where(neuron_rate[key]['rate'] == max(neuron_rate[key]['rate']))[0]
    if neuron_rate[key]['rate'].any():
        peak_instants[key] = neuron_rate[key]['t'][max_id]
remove_keys = [key for key, val in peak_instants.items() if len(val)>1]
[peak_instants.pop(key) for key in remove_keys]
sorted_peaks = dict(sorted(peak_instants.items(), key=lambda x: x[1]))
permutation_ids = [x[0] for x in sorted_peaks.items()]
[permutation_ids.append(i) for i in range(num_exc) if not i in permutation_ids]
# Save data
date_time = datetime.now()
path = f"""{date_time.strftime('%Y.%m.%d')}_{date_time.hour}.{date_time.minute}/"""
os.mkdir(path)
np.savez(path+f'rasters.npz',
         input_t=np.array(spikemon_seq_neurons.t/ms), input_i=np.array(spikemon_seq_neurons.i),
         exc_spikes_t=np.array(spikemon_exc_neurons.t/ms), exc_spikes_i=np.array(spikemon_exc_neurons.i),
         inh_spikes_t=np.array(spikemon_inh_neurons.t/ms), inh_spikes_i=np.array(spikemon_inh_neurons.i),
        )
del spikemon_seq_neurons, spikemon_exc_neurons, spikemon_inh_neurons
np.savez(path+f'traces.npz',
         Vm_e=statemon_exc_cells.Vm, Vm_i=statemon_inh_cells.Vm,
         exc_rate_t=np.array(statemon_pop_rate_e.t/ms), exc_rate=np.array(statemon_pop_rate_e.smooth_rate(width=10*ms)/Hz),
         inh_rate_t=np.array(statemon_pop_rate_i.t/ms), inh_rate=np.array(statemon_pop_rate_i.smooth_rate(width=10*ms)/Hz),
        )
del statemon_pop_rate_i, statemon_pop_rate_e, statemon_exc_cells, statemon_inh_cells
np.savez(path+f'matrices.npz',
         rf=statemon_ffe_conns.w_plast,
         #am=statemon_rec_conns.w_plast, FIXME
         rec_ids=recurrent_ids, rec_w=recurrent_weights
        )

np.savez(path+f'permutation.npz',
         ids = permutation_ids
        )

Metadata = {'time_step': defaultclock.dt/ms,
            'num_symbols': num_items,
            'num_channels': num_channels,
            'sequence_duration': sub_sequence_duration,
            'input_noise': noise_prob,
            'input_rate': item_rate,
            'sequence_repetitions': sequence_repetitions,
            'num_exc': num_exc,
            'num_inh': num_inh,
            'e->i p': ei_p,
            'i->e p': ie_p,
            'e->e p': ee_p,
            'mean e->i w': ei_w,
            'mean i->e w': mean_ie_w,
            'mean e->e w': mean_ee_w,
            'learn_factor': learn_factor,
            'mean ffe w': mean_ffe_w,
            'mean ffi w': mean_ffi_w
        }
with open(path+'metadata.json', 'w') as f:
    json.dump(Metadata, f)