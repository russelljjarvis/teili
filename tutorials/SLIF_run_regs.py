import numpy as np
from brian2 import implementation, check_units, volt, ms

def add_alt_activity_proxy(groups, buffer_size, decay):
    """This warpper function allows to add an activity proxy 
    run regular function.

    Args:
        group (list): List of neuron groups which are subject to
            weight initialiazion
        buffer_size (int): Size of the buffer which serves to calculate
            the activty
        decay (TYPE): Width of the running window.
    """
    for group in groups:
        add_activity_proxy(group,
                           buffer_size=buffer_size,
                           decay=decay)
        dict_append = {'activity_proxy' : True}
        group._tags.update(dict_append)

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
    group.namespace.update({'get_activity_proxy': get_activity_proxy_iin0})
    group.namespace.update(
        {'normalize_activity_proxy': normalize_activity_proxy_iin0})

    group.add_state_variable('buffer_size', shared=True, constant=True)
    group.add_state_variable('buffer_pointer', shared=True, constant=True)

    group.buffer_size = buffer_size
    group.buffer_pointer = -1
    group.variables.add_array('membrane_buffer', size=(group.N, buffer_size))
    group.variables.add_array('kernel', size=(group.N, buffer_size))
    group.membrane_buffer = np.nan

    mask = np.zeros(np.shape(group.kernel)[1]) * np.nan
    for jj in range(np.shape(group.kernel)[1]):
        mask[jj] = np.exp((jj - (np.shape(group.kernel)[1] - 1)) / decay)
    for ii in range(np.shape(group.kernel)[0]):
        ind = (np.ones(np.shape(group.kernel)[1]) * ii).astype(int)
        group.kernel.set_with_index_array(
            item=ind, value=mask, check_units=False)

    group.run_regularly('''buffer_pointer = (buffer_pointer + 1) % buffer_size;\
    activity_proxy = get_activity_proxy(Iin0, buffer_pointer, membrane_buffer, kernel)''', dt=1 * ms)

    group.run_regularly(
        '''normalized_activity_proxy = normalize_activity_proxy(activity_proxy, 15)''', dt=5 * ms)

@implementation('numpy', discard_units=True)
@check_units(Vm=volt,
             buffer_pointer=1,
             membrane_buffer=1,
             kernel=1,
             result=volt)
def get_activity_proxy_iin0(Vm,
                          buffer_pointer,
                          membrane_buffer,
                          kernel):
    """This function calculates an activity proxy using an integrated,
    exponentially weighted estimate of Imem of the N last time steps and
    stores it in membrane_buffer.

    This is needed for Variance Dependent Plasticity of inhibitory
    synapse.

     Args:
        Vm (float): The membrane potential of the LIF neuron model.
        buffer_pointer (int): Pointer to keep track of the buffer
        membrane_buffer (numpy.ndarray): Ring buffer for membrane potential.
        decay (int): Time constant of exp. weighted decay

    Returns:
        neuron_obj.array: An array which holds the integral of the
            activity_proxy over the N time steps of the
    """
    buffer_pointer = int(buffer_pointer)
    if np.sum(membrane_buffer == np.nan) > 0:
        membrane_buffer[:, buffer_pointer] = Vm
        # kernel = np.zeros(np.shape(membrane_buffer)) * np.nan
    else:
        membrane_buffer[:, :-1] = membrane_buffer[:, 1:]
        membrane_buffer[:, -1] = Vm

    '''Exponential weighing the membrane buffer to reflect more recent
    fluctuations in Imem. The exponential kernel is choosen to weight
    the most recent activity with a weight of 1, so we can normalize using
    the Ispkthr variable.
    '''
    exp_weighted_membrane_buffer = np.array(membrane_buffer, copy=True)
    exp_weighted_membrane_buffer[np.isnan(exp_weighted_membrane_buffer)] = 0
    exp_weighted_membrane_buffer *= kernel[:, :np.shape(exp_weighted_membrane_buffer)[1]]

    activity_proxy = np.sum(exp_weighted_membrane_buffer, axis=1)
    return activity_proxy

@implementation('numpy', discard_units=True)
@check_units(activity_proxy=volt, old_max=1, result=1)
def normalize_activity_proxy_iin0(activity_proxy, old_max):
    """This function normalized the variance of Vm, as calculated
    by get_activity_proxy_vm.

    Args:
        activity_proxy (float): exponentially weighted Imem fluctuations
        old_max (float, volt): Value used to normalize the
            activity proxy variable

    Returns:
        float: Normalized activity proxy
    """
    normalized_activity_proxy = np.zeros(np.shape(activity_proxy))

    return normalized_activity_proxy
