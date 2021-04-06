"""
This code implements a sequence learning using and Excitatory-Inhibitory
network with STDP.
"""
import numpy as np
from scipy.stats import gamma, truncnorm
from scipy.signal import find_peaks

from brian2 import second, ms, mV, Hz, prefs, SpikeMonitor, StateMonitor,\
        defaultclock, ExplicitStateUpdater, SpikeGeneratorGroup,\
        PopulationRateMonitor, run

from SLIF_utils import random_integers

from teili.core.groups import Neurons, Connections
from teili import TeiliNetwork
from teili.models.neuron_models import QuantStochLIF as static_neuron_model
from teili.models.synapse_models import QuantStochSyn as static_synapse_model
from teili.models.synapse_models import QuantStochSynStdp as stdp_synapse_model
from teili.stimuli.testbench import SequenceTestbench, OCTA_Testbench
from teili.tools.add_run_reg import add_lfsr
from teili.tools.group_tools import add_group_activity_proxy,\
    add_group_params_re_init
from teili.models.builder.synapse_equation_builder import SynapseEquationBuilder
from teili.models.builder.neuron_equation_builder import NeuronEquationBuilder

from teili.tools.lfsr import create_lfsr
from teili.tools.misc import neuron_group_from_spikes
from SLIF_utils import neuron_rate,\
        rate_correlations, ensemble_convergence, permutation_from_rate

import sys
import pickle
import os
from datetime import datetime

#############
# Load models
path = os.path.expanduser("/home/pablo/git/teili")
model_path = os.path.join(path, "teili", "models", "equations", "")
adp_synapse_model = SynapseEquationBuilder.import_eq(
        model_path + 'StochSynAdp.py')
adapt_neuron_model = NeuronEquationBuilder(base_unit='quantized',
        intrinsic_excitability='threshold_adaptation',
        position='spatial')
reinit_synapse_model = SynapseEquationBuilder(base_unit='quantized',
        plasticity='quantized_stochastic_stdp',
        structural_plasticity='stochastic_counter')

#############
# Prepare parameters of the simulation
# Defines if recurrent connections are included
if sys.argv[1] == 'no_rec':
    simple = True
elif sys.argv[1] == 'rec':
    simple = False
else:
    print('Provide correct argument')
    sys.exit(0)
if sys.argv[2] == 'plastic_inh':
    i_plast = True
elif sys.argv[2] == 'static_inh':
    i_plast = False
else:
    print('Provide correct argument')
    sys.exit(0)

# Initialize simulation preferences
prefs.codegen.target = "numpy"
defaultclock.dt = 1 * ms
stochastic_decay = ExplicitStateUpdater('''x_new = f(x,t)''')

################################################
# Initialize input sequence
num_items = 3
item_duration = 50
item_superposition = 0
num_channels = 144
noise_prob = None#0.005
item_rate = 25
#sequence_repetitions = 700# 350
sequence_repetitions = 200

sequence = SequenceTestbench(num_channels, num_items, item_duration,
                             item_superposition, noise_prob, item_rate,
                             sequence_repetitions)
spike_indices, spike_times = sequence.stimuli()


# Adding incomplete sequence at the end of simulation
training_duration = np.max(spike_times)
sequence_duration = sequence.cycle_length * ms
incomplete_sequences = 3
include_symbols = [[2], [1], [0]]
test_duration = incomplete_sequences * sequence_duration
symbols = sequence.items
for incomp_seq in range(incomplete_sequences):
    for incl_symb in include_symbols[incomp_seq]:
        tmp_symb = [(x*ms + incomp_seq*sequence_duration + training_duration)
                        for x in symbols[incl_symb]['t']]
        spike_times = np.append(spike_times, tmp_symb)
        spike_indices = np.append(spike_indices, symbols[incl_symb]['i'])
# Get back unit that was remove by append operation
spike_times = spike_times*second

# Adding noise at the end of simulation
#incomplete_sequences = 5
#test_duration = incomplete_sequences*sequence_duration*ms
#noise_prob = 0.01
#noise_spikes = np.random.rand(num_channels, int(test_duration/ms))
#noise_indices = np.where(noise_spikes < noise_prob)[0]
#noise_times = np.where(noise_spikes < noise_prob)[1]
#spike_indices = np.concatenate((spike_indices, noise_indices))
#spike_times = np.concatenate((spike_times, noise_times+training_duration/ms))
"""
# Initialize rotating bar
testbench_stim = OCTA_Testbench()
num_channels = 100
num_items = None
noise_prob = None
item_rate = None
sequence_repetitions = 200
testbench_stim.rotating_bar(length=10, nrows=10,
                            direction='cw',
                            ts_offset=3, angle_step=10,
                            noise_probability=0.2,
                            repetitions=sequence_repetitions,
                            debug=False)
training_duration = np.max(testbench_stim.times)*ms
test_duration = 200*ms
spike_indices = testbench_stim.indices
spike_times = testbench_stim.times * ms
sequence_duration = 105*ms
"""

# Save them for comparison
spk_i, spk_t = np.array(spike_indices), np.around(spike_times/ms).astype(int)*ms

# Reproduce activity in a neuron group (necessary for STDP compatibility)
seq_cells = neuron_group_from_spikes(num_channels, defaultclock.dt,
    (training_duration+test_duration),
    spike_indices=np.array(spike_indices),
    spike_times=np.array(spike_times)*second)

#################
# Building network
num_exc = 48
num_inh = 12
#num_inh = 30
exc_cells = Neurons(num_exc,
                    equation_builder=adapt_neuron_model(num_inputs=3),
                    method=stochastic_decay,
                    name='exc_cells',
                    verbose=True)
# Register proxy arrays
if i_plast:
    dummy_unit = 1*mV
    exc_cells.variables.add_array('activity_proxy',
                                   size=exc_cells.N,
                                   dimensions=dummy_unit.dim)

    exc_cells.variables.add_array('normalized_activity_proxy',
                                   size=exc_cells.N)

inh_cells = Neurons(num_inh,
                    equation_builder=static_neuron_model(num_inputs=3),
                    method=stochastic_decay,
                    name='inh_cells',
                    verbose=True)

# Connections
ei_p = 0.50
ie_p = 0.70
ee_p = 0.60
#ee_p = 1.0

if not simple:
    exc_exc_conn = Connections(exc_cells, exc_cells,
                               equation_builder=stdp_synapse_model(),
                               method=stochastic_decay,
                               name='exc_exc_conn')
exc_inh_conn = Connections(exc_cells, inh_cells,
                           equation_builder=static_synapse_model(),
                           method=stochastic_decay,
                           name='exc_inh_conn')
if i_plast:
    inh_exc_conn = Connections(inh_cells, exc_cells,
                               equation_builder=adp_synapse_model,
                               method=stochastic_decay,
                               name='inh_exc_conn')
else:
    inh_exc_conn = Connections(inh_cells, exc_cells,
                               equation_builder=static_synapse_model(),
                               method=stochastic_decay,
                               name='inh_exc_conn')
inh_inh_conn = Connections(inh_cells, inh_cells,
                           equation_builder=static_synapse_model(),
                           method=stochastic_decay,
                           name='inh_inh_conn')
feedforward_exc = Connections(seq_cells, exc_cells,
                              equation_builder=reinit_synapse_model(),
                              method=stochastic_decay,
                              name='feedforward_exc')
feedforward_inh = Connections(seq_cells, inh_cells,
                              equation_builder=static_synapse_model(),
                              method=stochastic_decay,
                              name='feedforward_inh')

feedforward_exc.connect()
feedforward_inh.connect()
inh_inh_conn.connect(p=.1)
inh_exc_conn.connect(p=ie_p)
if not simple:
    exc_exc_conn.connect('i!=j', p=ee_p)
    exc_exc_conn.delay = np.random.randint(0, 15, size=np.shape(exc_exc_conn.j)[0]) * ms
exc_inh_conn.connect(p=ei_p)
exc_inh_conn.delay = np.random.randint(0, 15, size=np.shape(exc_inh_conn.j)[0]) * ms
#feedforward_exc.delay = np.random.randint(0, 15, size=np.shape(feedforward_exc.j)[0]) * ms
#feedforward_inh.delay = np.random.randint(0, 15, size=np.shape(feedforward_inh.j)[0]) * ms
inh_inh_conn.delay = np.random.randint(0, 15, size=np.shape(inh_inh_conn.j)[0]) * ms
#inh_exc_conn.delay = np.random.randint(0, 15, size=np.shape(inh_exc_conn.j)[0]) * ms

# Time constants
# Values similar to those in Klampfl&Maass(2013), Joglekar etal(2018), Vogels&Abbott(2009)
if not simple:
    exc_exc_conn.tausyn = 5*ms
    exc_exc_conn.taupre = 20*ms
    exc_exc_conn.taupost = 60*ms # 20 for rotating bar
    exc_exc_conn.stdp_thres = 1
exc_inh_conn.tausyn = 5*ms
inh_exc_conn.tausyn = 10*ms
inh_inh_conn.tausyn = 10*ms
feedforward_exc.tausyn = 5*ms
feedforward_exc.taupre = 20*ms
feedforward_exc.taupost = 60*ms # 20
feedforward_exc.stdp_thres = 1
feedforward_inh.tausyn = 5*ms
exc_cells.tau = 20*ms
inh_cells.tau = 10*ms

# LFSR lengths
if not simple:
    exc_exc_conn.rand_num_bits_Apre = 4
    exc_exc_conn.rand_num_bits_Apost = 4
feedforward_exc.rand_num_bits_Apre = 4
feedforward_exc.rand_num_bits_Apost = 4

exc_cells.Vm = 3*mV
inh_cells.Vm = 3*mV
learn_factor = 4
if i_plast:
    inh_exc_conn.inh_learning_rate = 0.01
#feedforward_exc.A_gain = learn_factor

# Weight initializations
ei_w = 3
mean_ie_w = 4
mean_ee_w = 1
mean_ffe_w = 3
mean_ffi_w = 1

inh_inh_conn.weight = -1
if i_plast:
    inh_exc_conn.weight = -1
    # 1 = no inhibition, 0 = maximum inhibition
    #var_th = .1
    var_th = 0.50
for neu in range(num_inh):
    weight_length = np.shape(inh_exc_conn.weight[neu,:])
    sampled_weights = gamma.rvs(a=mean_ie_w, loc=1, size=weight_length).astype(int)
    sampled_weights = np.clip(sampled_weights, 0, 15)
    #sampled_weights = truncnorm.rvs(-3, 4, loc=mean_ie_w, size=weight_length).astype(int)
    if i_plast:
        inh_exc_conn.w_plast[neu,:] = sampled_weights
    else:
        inh_exc_conn.weight[neu,:] = -sampled_weights
if not simple:
    exc_exc_conn.weight = 1
for neu in range(num_exc):
    if not simple:
        weight_length = np.shape(exc_exc_conn.w_plast[neu,:])
        exc_exc_conn.w_plast[neu,:] = gamma.rvs(a=mean_ee_w, size=weight_length).astype(int)
        #exc_exc_conn.w_plast[neu,:] = truncnorm.rvs(-1, 4, loc=mean_ee_w, size=weight_length).astype(int)
    weight_length = np.shape(exc_inh_conn.weight[neu,:])
    sampled_weights = gamma.rvs(a=ei_w, loc=1, size=weight_length).astype(int)
    sampled_weights = np.clip(sampled_weights, 0, 15)
    #sampled_weights = truncnorm.rvs(-2, 4, loc=ei_w, size=weight_length).astype(int)
    exc_inh_conn.weight[neu,:] = sampled_weights
feedforward_exc.weight = 1
num_inh_weight = np.shape(feedforward_inh.weight[neu,:])[0]
for ch in range(num_channels):
    wplast_length = np.shape(feedforward_exc.w_plast[ch,:])
    feedforward_exc.w_plast[ch,:] = np.clip(
            gamma.rvs(a=mean_ffe_w, size=wplast_length).astype(int),
            0,
            15)
    #feedforward_exc.w_plast[ch,:] = truncnorm.rvs(-3, 7, loc=mean_ffe_w, size=wplast_length).astype(int)
    feedforward_inh.weight[ch,:] = np.clip(
            gamma.rvs(a=mean_ffi_w, size=num_inh_weight).astype(int),
            0,
            15)
    #feedforward_inh.weight[ch,:] = truncnorm.rvs(-1, 7, loc=mean_ffi_w, size=num_inh_weight).astype(int)
# Set sparsity for ffe connections
for neu in range(num_exc):
    ffe_zero_w = np.random.choice(num_channels, int(num_channels*.3), replace=False)
    feedforward_exc.weight[ffe_zero_w,neu] = 0
    feedforward_exc.w_plast[ffe_zero_w,neu] = 0

# Set LFSRs for each group
#neu_groups = [exc_cells, inh_cells]
#if not simple:
#    syn_groups = [exc_exc_conn, exc_inh_conn, inh_exc_conn, feedforward_exc,
#                     feedforward_inh, inh_inh_conn]
#else:
#    syn_groups = [exc_inh_conn, inh_exc_conn, feedforward_exc,
#                     feedforward_inh, inh_inh_conn]
#ta = create_lfsr(neu_groups, syn_groups, defaultclock.dt)

if i_plast:
    # Add proxy activity group
    activity_proxy_group = [exc_cells]
    add_group_activity_proxy(activity_proxy_group,
                             buffer_size=400,
                             decay=150)
    inh_exc_conn.variance_th = np.random.uniform(
            low=var_th - 0.1,
            high=var_th + 0.1,
            size=len(inh_exc_conn))

# Adding mismatch
#mismatch_neuron_param = {
#    'tau': 0.05
#}
#mismatch_synap_param = {
#    'tausyn': 0.05
#}
#mismatch_plast_param = {
#    'taupre': 0.05,
#    'taupost': 0.05
#}
#
#exc_cells.add_mismatch(std_dict=mismatch_neuron_param, seed=10)
#inh_cells.add_mismatch(std_dict=mismatch_neuron_param, seed=10)
#exc_exc_conn.add_mismatch(std_dict=mismatch_synap_param, seed=11)
#exc_inh_conn.add_mismatch(std_dict=mismatch_synap_param, seed=11)
#inh_exc_conn.add_mismatch(std_dict=mismatch_synap_param, seed=11)
#feedforward_exc.add_mismatch(std_dict=mismatch_synap_param, seed=11)
#feedforward_inh.add_mismatch(std_dict=mismatch_synap_param, seed=11)
#exc_exc_conn.add_mismatch(std_dict=mismatch_plast_param, seed=11)
#feedforward_exc.add_mismatch(std_dict=mismatch_plast_param, seed=11)

###################
# Adding homeostatic mechanisms
re_init_dt = 15000*ms
add_group_params_re_init(groups=[feedforward_exc],
                         variable='w_plast',
                         re_init_variable='re_init_counter',
                         re_init_threshold=1,
                         re_init_dt=re_init_dt,
                         dist_param=3,
                         scale=1,
                         distribution='gamma',
                         clip_min=0,
                         clip_max=15,
                         variable_type='int',
                         reference='synapse_counter')
add_group_params_re_init(groups=[feedforward_exc],
                         variable='weight',
                         re_init_variable='re_init_counter',
                         re_init_threshold=1,
                         re_init_dt=re_init_dt,
                         distribution='deterministic',
                         const_value=1,
                         reference='synapse_counter')
add_group_params_re_init(groups=[feedforward_exc],
                         variable='tausyn',
                         re_init_variable='re_init_counter',
                         re_init_threshold=1,
                         re_init_dt=re_init_dt,
                         dist_param=5.5,
                         scale=1,
                         distribution='normal',
                         clip_min=4,
                         clip_max=7,
                         variable_type='int',
                         unit='ms',
                         reference='synapse_counter')

##################
# Setting up monitors
spikemon_exc_neurons = SpikeMonitor(exc_cells, name='spikemon_exc_neurons')
spikemon_inh_neurons = SpikeMonitor(inh_cells, name='spikemon_inh_neurons')
spikemon_seq_neurons = SpikeMonitor(seq_cells, name='spikemon_seq_neurons')
statemon_exc_cells = StateMonitor(exc_cells, variables=['Vm'], record=np.random.randint(0, num_exc),
                                  name='statemon_exc_cells')
if i_plast:
    statemon_proxy = StateMonitor(exc_cells, variables=['normalized_activity_proxy'], record=True,
                                      name='statemon_proxy')
statemon_inh_cells = StateMonitor(inh_cells, variables=['Vm'], record=np.random.randint(0, num_inh),
                                  name='statemon_inh_cells')
statemon_net_current = StateMonitor(exc_cells, variables=['Iin'], record=True,
                                  name='statemon_net_current')
if not simple:
    statemon_ee_conns = StateMonitor(exc_exc_conn, variables=['I_syn'], record=True,
                                     name='statemon_ee_conns')
statemon_ie_conns = StateMonitor(inh_exc_conn, variables=['I_syn'], record=True,
                                  name='statemon_ie_conns')
statemon_ffe_conns = StateMonitor(feedforward_exc, variables=['w_plast', 'I_syn'], record=True,
                                  name='statemon_ffe_conns')
statemon_pop_rate_e = PopulationRateMonitor(exc_cells)
statemon_pop_rate_i = PopulationRateMonitor(inh_cells)

net = TeiliNetwork()
if not simple:
    if i_plast:
        net.add(seq_cells, exc_cells, inh_cells, exc_exc_conn, exc_inh_conn, inh_exc_conn,
                feedforward_exc, statemon_exc_cells, statemon_inh_cells, feedforward_inh,
                spikemon_exc_neurons, spikemon_inh_neurons,
                spikemon_seq_neurons, statemon_ffe_conns, statemon_pop_rate_e,
                statemon_pop_rate_i, statemon_net_current, statemon_ie_conns,
                inh_inh_conn, statemon_proxy, statemon_ee_conns)
    else:
        net.add(seq_cells, exc_cells, inh_cells, exc_exc_conn, exc_inh_conn, inh_exc_conn,
                feedforward_exc, statemon_exc_cells, statemon_inh_cells, feedforward_inh,
                spikemon_exc_neurons, spikemon_inh_neurons,
                spikemon_seq_neurons, statemon_ffe_conns, statemon_pop_rate_e,
                statemon_pop_rate_i, statemon_net_current, statemon_ie_conns, inh_inh_conn,
                statemon_ee_conns)
else:
    net.add(seq_cells, exc_cells, inh_cells, exc_inh_conn, inh_exc_conn,
            feedforward_exc, statemon_exc_cells, statemon_inh_cells, feedforward_inh,
            spikemon_exc_neurons, spikemon_inh_neurons,
            spikemon_seq_neurons, statemon_ffe_conns, statemon_pop_rate_e,
            statemon_pop_rate_i, statemon_net_current, statemon_ie_conns, inh_inh_conn,
            statemon_proxy)

# Training
statemon_ffe_conns.active = True
net.run(training_duration, report='stdout', report_period=100*ms)

# Testing
#feedforward_inh.weight = 0
statemon_ffe_conns.active = True
net.run(test_duration, report='stdout', report_period=100*ms)

##########
# Evaluations
if not np.array_equal(spk_t, spikemon_seq_neurons.t):
    print('Proxy activity and generated input do not match.')
    from brian2 import *
    plot(spk_t, spk_i, 'k.')
    plot(spikemon_seq_neurons.t, spikemon_seq_neurons.i, 'r+')
    show()
    sys.exit()

last_sequence_t = (training_duration-sequence_duration)/ms
neu_rates = neuron_rate(spikemon_exc_neurons, kernel_len=200,
    kernel_var=10, kernel_min=0.001,
    interval=[0, int(training_duration/ms)])
    #rotating bar:
    #interval=[int(last_sequence_t), int(training_duration/ms)])
#foo = ensemble_convergence(seq_rates, neu_rates, [[0, 48], [48, 96], [96, 144]],
#                           sequence_duration, sequence_repetitions)
#
#corrs = rate_correlations(neu_rates, sequence_duration, sequence_repetitions)

############
# Saving results
# Save targets of recurrent connections as python object
n_rows = num_exc
recurrent_ids = []
recurrent_weights = []
if not simple:
    for row in range(n_rows):
        recurrent_weights.append(list(exc_exc_conn.w_plast[row, :]))
        recurrent_ids.append(list(exc_exc_conn.j[row, :]))

# Calculating permutation indices from firing rates
permutation_ids = permutation_from_rate(neu_rates, sequence_duration,
                                        defaultclock.dt)

# Save data
date_time = datetime.now()
path = f"""{date_time.strftime('%Y.%m.%d')}_{date_time.hour}.{date_time.minute}/"""
os.mkdir(path)
np.savez(path+f'rasters.npz',
         input_t=np.array(spikemon_seq_neurons.t/ms), input_i=np.array(spikemon_seq_neurons.i),
         exc_spikes_t=np.array(spikemon_exc_neurons.t/ms), exc_spikes_i=np.array(spikemon_exc_neurons.i),
         inh_spikes_t=np.array(spikemon_inh_neurons.t/ms), inh_spikes_i=np.array(spikemon_inh_neurons.i),
        )

np.savez(path+f'traces.npz',
         Vm_e=statemon_exc_cells.Vm, Vm_i=statemon_inh_cells.Vm,
         exc_rate_t=np.array(statemon_pop_rate_e.t/ms), exc_rate=np.array(statemon_pop_rate_e.smooth_rate(width=10*ms)/Hz),
         inh_rate_t=np.array(statemon_pop_rate_i.t/ms), inh_rate=np.array(statemon_pop_rate_i.smooth_rate(width=10*ms)/Hz),
        )

np.savez_compressed(path+f'matrices.npz',
         rf=statemon_ffe_conns.w_plast.astype(np.uint8),
         rec_ids=recurrent_ids, rec_w=recurrent_weights
        )

np.savez(path+f'permutation.npz',
         ids = permutation_ids
        )

Metadata = {'time_step': defaultclock.dt,
            'num_symbols': num_items,
            'num_channels': num_channels,
            'sequence_duration': sequence_duration,
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
            'mean ffi w': mean_ffi_w,
            'i_plast': i_plast,
            'simple': simple
        }
with open(path+'general.data', 'wb') as f:
    pickle.dump(Metadata, f)

Metadata = {'exc': exc_cells.get_params(),
            'inh': inh_cells.get_params()}
with open(path+'population.data', 'wb') as f:
    pickle.dump(Metadata, f)

Metadata = {'e->i': exc_inh_conn.get_params(),
            'i->e': inh_exc_conn.get_params(),
            'ffe': feedforward_exc.get_params(),
            'ffi': feedforward_inh.get_params()
            }
if not simple:
    Metadata['e->e'] = exc_exc_conn.get_params()
with open(path+'connections.data', 'wb') as f:
    pickle.dump(Metadata, f)

from brian2 import *
import pandas as pd
from scipy.signal import savgol_filter

if i_plast:
    figure()
    plot(statemon_proxy.normalized_activity_proxy.T)
    xlabel('time (ms)')
    ylabel('normalized activity value')
    title('Normalized activity of all neurons')

#_ = hist(corrs, bins=20)
#xlabel('Correlation values')
#ylabel('count')
#title('Correlations of average response to every sequence presentation (all neurons)')
#
#figure()
#neu=1
#y1 = pd.Series(foo[0,neu,:])
#y1=savgol_filter(y1.interpolate(), 31, 4)
#y2 = pd.Series(foo[1,neu,:])
#y2=savgol_filter(y2.interpolate(), 31, 4)
#y3 = pd.Series(foo[2,neu,:])
#y3=savgol_filter(y3.interpolate(), 31, 4)
#
#plot(y1, label='symbol 1')
#plot(y2, label='symbol 2')
#plot(y3, label='symbol 3')
#xlabel('# sequence presentation')
#ylabel('correlation value')
#legend()

win_len = 100
tot_e_curr = np.sum(statemon_ffe_conns.I_syn, axis=0)
if not simple:
    tot_e_curr += np.sum(statemon_ee_conns.I_syn, axis=0)
tot_i_curr = np.sum(statemon_ie_conns.I_syn, axis=0)
a=np.convolve(tot_e_curr, np.ones(win_len)/win_len, mode='valid')
b=np.convolve(tot_i_curr, np.ones(win_len)/win_len, mode='valid')
figure()
plot(a/amp, color='r', label='summed exc. currents')
plot(-b/amp, color='b', label='summed inh. current')
plot((a - b)/amp, color='k', label='net. current')
ylabel('Current [amp]')
xlabel('time [ms]')
title('EI balance')
legend()

figure()
_ = hist(inh_exc_conn.w_plast)

show()
