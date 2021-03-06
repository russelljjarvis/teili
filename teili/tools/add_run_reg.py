# -*- coding: utf-8 -*-
"""This set of functions allows the user to easily add the property of
certain run_regularly functions, specified in run_reg_functions.py to
neuron/synapse groups. These function should take a certain neuron/synapse
group and add all necessary state_variables and function calls.
"""
# @Author: mmilde
# @Date:   2018-07-30 14:19:44

from teili.core.groups import Neurons, Connections
import numpy as np
from brian2 import ms, pA, amp, second
from teili.tools.run_reg_functions import re_init_params,\
    get_activity_proxy_vm, get_activity_proxy_imem,\
    max_value_update_vm, max_value_update_imem,\
    normalize_activity_proxy_vm, normalize_activity_proxy_imem,\
    get_re_init_indices, reset_re_init_variable, lfsr




def add_re_init_params(group, 
                       variable, 
                       re_init_variable, 
                       re_init_indices, 
                       re_init_threshold, 
                       re_init_dt,
                       dist_param, 
                       scale, 
                       distribution,
                       reference,
                       unit,
                       clip_min=None,
                       clip_max=None,
                       const_value=None,
                       params_type=None):
    """Adds a re-initialization run_regularly to a synapse group

    Args:
        group (teiligroup, required): Connections or Neurons group
        variable (str, required): Name of the variable to be re-initialised
        re_init_variable (str, optional): Name of the variable to be used to
            calculate re_init_indices.
        re_init_indices (ndarray, optional): Array to indicate which parameters
            need to be re-initialised.
        re_init_threshold (float, required): Threshold value below which
            index is added to re_init_indices.
        re_init_dt (second): Dt of run_regularly.
        dist_param (float, required): Mean of distribution in case.
            of 'gaussian' or shape parameter k for 'gamma' distribution.
        scale (float, required): Scale parameter sigma for
            distribution.
        distribution (str): Parameter to determine the strategy to be used
            to initialise the weights. Random distributions available are
            'gaussian' or 'gamma', but a 'deterministic' reinitialization
            with constant values can also be done.
        reference (str, required): Specifies which reference metric is used
            to get indices of parameters to be re-initialised. 'mean', 
            'spike_time', 'synapse_counter' or 'neuron_threshold'.
        unit (str, optional): Unit of variable according to brian2.units.
        clip_min (float, optional): Value to clip distribution at lower bound.
        clip_max (float, optional): Value to clip distribution at upper bound.
        const_value (int or float, optional): Constant used as reinitialization
            value when argument distribution is "deterministic".
        params_type (str, optional): Data type of variable. Can be 'int' or
            'float'.
    """
    if type(group) == Connections:
        size=len(group)
        if reference == 'spike_time':
            raise TypeError(f'Reference \'{reference}\' incompatible with '
                            f'{type(group)}.')
    elif type(group) == Neurons:
        if reference != 'spike_time':
            raise TypeError(f'Reference \'{reference}\' incompatible with '
                            f'{type(group)}.')
        size=group.N 
    
    if any((variable in key) for key in group.namespace.keys()):
        raise AssertionError(f'{type(group)} already has {variable} in '
                              'namespace.')

    # Assignments and mappings between keywords to avoid passing strings
    if reference == 'mean':
        reference = 0
    elif reference == 'spike_time':
        reference = 1
    elif reference == 'synapse_counter':
        reference = 2
    else:
        raise AssertionError(f'Unexpected reference {reference}.')

    if distribution == 'normal':
        dist = 0
        const_value = 0
    elif distribution == 'gamma':
        dist = 1
        const_value = 0
    elif distribution == 'deterministic':
        dist = 2
        dist_param = 0
        scale = 0
        clip_min, clip_max = 0, 0
        if not isinstance(const_value, (int, float)):
            raise TypeError(f'Constant value {const_value} incompatible '
                             'with parameter \'{distribution}\'')

    if unit is None:
        unit = 1

    if params_type == 'int':
        params_type = 1
    else:
        params_type = 0

    # Ensures that multiple state variables can use the same re_init_variable
    if f'{re_init_variable}_flag' not in group.namespace.keys():
        group.namespace[f'{re_init_variable}_flag'] = 1
        # re_init_indices is only added once per group re_init_variable, so it
        # can be used to check if one re_init_variable is used
        if 're_init_indices' in group.variables.keys():
            raise AssertionError(f'{type(group)} must be associated with '
                                  'single re_init_variable.')

        if reference == 2:
            # Assign NaN to disconnected synapses
            temp_var = np.array(group.__getattr__(re_init_variable))
            temp_var[np.where(group.weight==0)[0]] = np.nan
            group.__setattr__(re_init_variable, temp_var)

        if re_init_indices is None:
            group.add_state_variable('re_init_indices')
        else:
            group.variables.add_array('re_init_indices', size=np.int(size))

        group.namespace.update({'get_re_init_indices': get_re_init_indices})
        group.run_regularly(f'''re_init_indices = get_re_init_indices(\
                                   {re_init_variable},\
                                   {reference},\
                                   {re_init_threshold},\
                                   lastspike,\
                                   t)''',
                            order=0,
                            dt=re_init_dt)
        group.namespace.update({'reset_re_init_variable': reset_re_init_variable})
        group.run_regularly(f'''{re_init_variable} = reset_re_init_variable(\
                                   {re_init_variable},\
                                   {reference},\
                                   re_init_indices)''',
                            when='end',
                            dt=re_init_dt)

    # TODO This needs double checking. I believe the name in namespace needs
    # to match the function name itself. So we might need to remove the format.
    group.namespace.update({f're_init_{variable}': re_init_params})
    group.run_regularly(f'''{variable} = re_init_{variable}({variable}/{unit},\
                                                        {clip_min},\
                                                        {clip_max},\
                                                        {const_value},\
                                                        re_init_indices,\
                                                        {re_init_threshold},\
                                                        {dist_param},\
                                                        {scale},\
                                                        {dist},\
                                                        {params_type})*{unit}''',
                        order=1,
                        dt=re_init_dt)


def add_activity_proxy(group, buffer_size, decay):
    """Adds all needed functionality to track normalised Vm/Imem activity proxy 
    for Activity Dependent Plasticity.

    Args:
        group (Neuron group): Neuron group
        buffer_size (int, optional): Parameter to set the size of the buffer
            for activity dependent plasticity rule. Meaning how many
            samples are considered to calculate the activity proxy of post
            synaptic neurons
         decay (int, optional): Time constant for decay of exponentioally
            weighted activity proxy
    """
    if 'Imem' in group.equations.names:
        group.namespace.update({'get_activity_proxy': get_activity_proxy_imem})
        group.namespace.update({'max_value_update': max_value_update_imem})
        group.namespace.update(
            {'normalize_activity_proxy': normalize_activity_proxy_imem})
    else:
        group.namespace.update({'get_activity_proxy': get_activity_proxy_vm})
        group.namespace.update({'max_value_update': max_value_update_vm})
        group.namespace.update(
            {'normalize_activity_proxy': normalize_activity_proxy_vm})

    group.add_state_variable('buffer_size', shared=True, constant=True)
    group.add_state_variable('buffer_pointer', shared=True, constant=True)

    group.buffer_size = buffer_size
    group.buffer_pointer = -1
    group.variables.add_array('membrane_buffer', size=(group.N, buffer_size))
    group.variables.add_array('kernel_adp', size=(group.N, buffer_size))
    group.variables.add_array('old_max', size=1)
    group.membrane_buffer = np.nan

    mask = np.zeros(np.shape(group.kernel_adp)[1]) * np.nan
    for jj in range(np.shape(group.kernel_adp)[1]):
        mask[jj] = np.exp((jj - (np.shape(group.kernel_adp)[1] - 1)) / decay)
    for ii in range(np.shape(group.kernel_adp)[0]):
        ind = (np.ones(np.shape(group.kernel_adp)[1]) * ii).astype(int)
        group.kernel_adp.set_with_index_array(
            item=ind, value=mask, check_units=False)

    if 'Imem' in group.equations.names:
        group.run_regularly('''buffer_pointer = (buffer_pointer + 1) % buffer_size;\
        activity_proxy = get_activity_proxy(Imem, buffer_pointer, membrane_buffer, kernel_adp)''', dt=1 * ms)
    else:
        group.run_regularly('''buffer_pointer = (buffer_pointer + 1) % buffer_size;\
        activity_proxy = get_activity_proxy(Vm, buffer_pointer, membrane_buffer, kernel_adp)''', dt=1 * ms)

    group.run_regularly(
        '''old_max = max_value_update(activity_proxy, old_max)''', dt=5 * ms)
    group.run_regularly(
        '''normalized_activity_proxy = normalize_activity_proxy(activity_proxy, old_max)''', dt=5 * ms)


def add_weight_decay(group, decay_rate, dt):
    """Summary

    Args:
        group (Connection group): Synapse group which weight should
            be decayed.
        decay_rate (float, required): Value smaller 1 which is multiplied
            with w_plast every dt.
        dt (float, second, required): Time interval for the weight decay to
            be executed.
    """
    group.add_state_variable('decay')
    group.decay = decay_rate
    if 'w_plast' in group.equations.names:
        group.run_regularly('''w_plast *= decay''', dt=dt)
    elif 'Ipred_plast' in group.equations.names:
        group.run_regularly('''Ipred_plast *= decay''', dt=dt)

def add_lfsr(group, lfsr_seed, dt):
    """
    Initializes numbers that will be used for each element on the LFSR
    function by iterating on the LFSR num_elements times. This is a
    Galois or many-to-one implementation.

    The value of the mask is hard-coded according to the number of
    bits used. The MSB and LSB bits of the mask should be 1 to
    perform the equivalent of a circular shift. Moreover, bits relative
    to taps+1 (because it was shifted first) should also be 1 to XOR
    the correct bits.

    Parameters
    ----------
    group : Connection group
        Group that the random numbers will be distributed to
    lfsr_seed : int
        The seed of the LFSR
    dt : float
        Time step to run_regularly
    """
    if isinstance(group, Neurons):
        num_bits = int(group.lfsr_num_bits[0])
        num_elements = len(group.lfsr_num_bits)
    else:
        num_bits = int(group.lfsr_num_bits_syn[0])
        num_elements_syn = len(group.lfsr_num_bits_syn)
        if hasattr(group, 'decay_probability_stdp'):
            num_elements_stdp = len(group.lfsr_num_bits_syn)
        else:
            num_elements_stdp = 0
        num_elements = num_elements_syn + num_elements_stdp
    lfsr_out = [0 for _ in range(num_elements)]
    taps = {3: 0b1011, 5: 0b100101, 6:0b1000011, 9: 0b1000010001}
    mask = taps[num_bits]

    for i in range(num_elements):
        lfsr_seed = lfsr_seed << 1
        overflow = lfsr_seed >> num_bits
        if overflow:
            lfsr_seed ^= mask
        lfsr_out[i] = lfsr_seed

    group.add_state_variable('mask', shared=True, constant=True)
    group.mask = mask
    if isinstance(group, Neurons):
        group.decay_probability = np.asarray(lfsr_out)/2**num_bits
        group.namespace.update({'lfsr': lfsr})
        group.run_regularly('''decay_probability = lfsr(decay_probability,\
                                                         N,\
                                                         lfsr_num_bits,\
                                                         mask)
                             ''',
                             dt=dt)
    else:
        group.decay_probability_syn = np.asarray(lfsr_out)[0:num_elements_syn]/2**num_bits
        group.namespace.update({'lfsr': lfsr})
        group.run_regularly('''decay_probability_syn = lfsr(decay_probability_syn,\
                                                         N,\
                                                         lfsr_num_bits_syn,\
                                                         mask)
                             ''',
                             dt=dt)
        if hasattr(group, 'decay_probability_stdp'):
            group.decay_probability_stdp = np.asarray(lfsr_out)[num_elements_syn:]/2**num_bits
            group.run_regularly('''decay_probability_stdp = lfsr(decay_probability_stdp,\
                                                             N,\
                                                             lfsr_num_bits_syn,\
                                                             mask)
                                 ''',
                                 dt=dt)
