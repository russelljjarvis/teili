# -*- coding: utf-8 -*-
# @Author: mmilde
# @Date:   2018-01-11 14:48:17
# @Last Modified by:   mmilde
# @Last Modified time: 2018-01-25 16:29:42
import os
import ipdb
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict

import scipy
from scipy.optimize import minimize
from scipy import ndimage

from brian2 import prefs, ms, pA, nA, StateMonitor, device, set_device,\
    second, msecond, defaultclock, TimedArray, psiemens, mV, \
    network_operation
pS = psiemens
from teili.building_blocks.reservoir import Reservoir, plot_reservoir
from teili.core.groups import Neurons, Connections
from teili import teiliNetwork

import runpy

# nc17 = runpy.run_path('nicola_cloapth_2017_params.py')
from scipy.io import loadmat
nc17 ={}
loadmat('config4.mat',nc17) # config2.mat generated by IZFORCECLASSIFICATION_randcontrol.m
# loadmat('config1_testsyn.mat',nc17)
nc17['E'] = nc17['E'].reshape((nc17['N'][0][0]))
nc17['zx'] = nc17['zx'].T
nc17['BPhi'] = nc17['BPhi'].reshape((nc17['N'][0][0]))
BPhi = np.ones((nc17['N'][0][0],1)).reshape((nc17['N'][0][0]))


prefs.codegen.target = 'numpy'

num_neurons = nc17['N']
# num_input_neurons = 1 # nc17['Xin'].shape[1]

Net = teiliNetwork()
duration = nc17['T'] * ms
defaultclock.dt = nc17['dt'] * ms

reservoir_params = {'weInpR': 1.5, # nc17['Ein']
                    'weRInh': 1,
                    'wiInhR': -1,
                    'weRR': 0.5,
                    'sigm': 3,
                    'rpR': 0 * ms,
                    'rpInh': 0 * ms,
                    'taud': nc17['td'] * ms,
                    'taur': nc17['tr'] * ms}
# OMEGA
# randn = np.random.randn
# adjecency_mtr = randn(num_neurons, num_neurons, 2)
# adjecency_mtr[:,:,0] = (adjecency_mtr[:,:,0]<nc17['p'])
# adjecency_mtr[:,:,1] = nc17['G'] * adjecency_mtr[:,:,1] * adjecency_mtr[:,:,0] / (nc17['p'] * np.sqrt(num_neurons)) 
adjecency_mtr = np.zeros((nc17['OMEGA'].shape[0], nc17['OMEGA'].shape[1], 2))
adjecency_mtr[:,:,0] = nc17['OMEGA'].T!=0
adjecency_mtr[:,:,1] = nc17['OMEGA'].T

gtestR = Reservoir(name='testR',
                   num_neurons=num_neurons,
                   fraction_inh_neurons=None,
                   # num_input_neurons=num_input_neurons,
                   Rconn_prob=None,
                   adjecency_mtr=adjecency_mtr,
                   num_inputs=0,
                   num_output_neurons=1,
                   output_weights_init = nc17['BPhi'],
                   block_params=reservoir_params)

# Initialise menbrane potentials
gtestR.Groups['gRGroup'].Vm = nc17['v_init'].reshape((nc17['N'][0][0])) *mV

# Set synaptic baseweight
gtestR.Groups['synRR1e'].baseweight_e = 0.18397145542145726 * pA
gtestR.Groups['synRR1e'].baseweight_i = -0.18397145542145726 * pA

# BIAS & Input
# Input Ein*Xin
Itimed = np.dot(nc17['Ein'],nc17['Xin'].T).T # First dim is time, second is neuron index
It = TimedArray(Itimed * pA, dt=defaultclock.dt)
# print('***********BIAS**************')
I_bias = 1000 * pA #nc17['BIAS'] * pA
# rates = gtestR.Groups['synOutRate1e']
gtestR.Groups['gRGroup'].namespace.update({"It":It, 'I_bias':I_bias}) #, 'E':nc17['E']})
gtestR.Groups['gRGroup'].run_regularly("Iconst = I_bias + It(t,i)",dt=nc17['dt']*ms)
# syn_in_ex = gtestR.Groups['synInpR1e']
# syn_ex_ex = gtestR.Groups['synRR1e']
# syn_ex_ih = gtestR.Groups['synRInh1e']
# syn_ih_ex = gtestR.Groups['synInhR1i']

# Initial code for run_regularly fuction for FORCE: very difficult to implement matrix operations and passing vectors.
# @implementation('cpp', '''
#     float dist1d2dfloat(float i, float j, int nrows_cpp, int ncols_cpp) {
#     int ix = i / ncols_cpp;
#     int iy = i % ncols_cpp;
#     int jx = j / ncols_cpp;
#     int jy = j % ncols_cpp;
#     return sqrt(pow((ix - jx),2) + pow((iy - jy),2));
#     }
#      ''')
# @declare_types(i='float', j='float', nrows='integer', ncols='integer', result='float')
# @check_units(i=mV, j=1, ncols=1, nrows=1, result=1)
# def matrixfunction(i,j,ncols,nrows):
# gtestR.Groups['synOutR1e'].namespace.update({'matrixfunction':matrixfunction})
# gtestR.Groups['synOutR1e'].run_regularly("print_rates = matrixfunction(r,...)",dt=1*ms)


@network_operation(dt=nc17['dt'] * ms, when = 'end')
def debug(t):
    ipdb.set_trace()

# Store Error
error = []

log = False
# Network operation setup for FORCE Learning
@network_operation(dt=nc17['dt']*nc17['step'] * ms, when = 'end')
def FORCE(t):
    if t > nc17['imin']*nc17['dt']*ms and t < nc17['icrit']*nc17['dt']*ms:
        # Store firign rate of individial reservoir neurons
        # r.shape = (num_output_neurons,)
        firing_rate = np.array(gtestR.Groups['synOutRate1e'].r)
        read_out = np.array(gtestR.Groups['gROutGroup'].rate)[0]
        if log: print('firing_rate', firing_rate)
        if log: print('read_out', read_out)
        #  z = BPhi'*r
        z = read_out #np.dot(nc17['BPhi'].T,r)
        if log: print('z',z,)
        zx = nc17['zx'][round(t/nc17['dt'][0][0]/ms)]
        if log: print('zx',zx)
        #  err = z - zx(i)
        err = z - zx # scalar error
        error.append([np.array(t.variable.get_value_with_unit()), err])
        # err = -err
        if log: print('err',err)
        # cd = Pinv*r
        cd = np.dot(nc17['Pinv'], firing_rate).reshape((nc17['N'][0][0],1))
        if log: print('cd',cd)
        #    BPhi = BPhi - (cd*err')
        # nc17['BPhi'] = (nc17['BPhi'] -(cd*err).reshape((20)) )
        if log: print('BPhi',nc17['BPhi'].T)
        gtestR.Groups['synOutR1e'].weight = nc17['BPhi']
        #    Pinv = Pinv -((cd)*(cd'))/( 1 + (r')*(cd))
        if log: print('Pinvz',nc17['Pinv'])
        nc17['Pinv'] = nc17['Pinv'] - (cd * cd.T)/( 1 + np.dot(firing_rate.T,cd))
        # ipdb.set_trace()

# Network operation setup for feddback connections
@network_operation(dt=nc17['dt'] * ms, when = 'start')
def feed_back(t):
    z = np.array(gtestR.Groups['gROutGroup'].rate)[0]
    if log: print('z',z)
    gtestR.Groups['gRGroup'].Iconst = gtestR.Groups['gRGroup'].Iconst + nc17['E'] * z * pA

# statemonRin = StateMonitor(gtestR.Groups['gRGroup'],
#                            ('Ie0', 'Ii0','Ie1', 'Ii1','Ie2', 'Ii2','Iconst','Vm','Iadapt'),
#                            record=True,
#                            name='statemonRin')

statemonRout = StateMonitor(gtestR.Groups['synOutRate1e'],
                            {'r'},
                           record=True,
                           name='statemonRout')


Net.add(gtestR)
for to_add_name,to_add in gtestR.Groups.items():
    Net.add(to_add)
for to_add_name,to_add in gtestR.Monitors.items():
    Net.add(to_add)
Net.add(statemonRout)
# Net.add(FORCE, feed_back)
# Net.add(debug)

#%%
#Net.printParams()
import time
st = time.time()
amplitudes_dict = {}
sigmas_dict={}

# Run it !!!
Net.run(duration)


# Plot activity
# Injected current for Input
plt.figure()
for cinj in gtestR.Monitors['statemonR'].Iconst:
    plt.title('Reservoir input')
    plt.plot(gtestR.Monitors['statemonR'].t/ms,cinj / pA)
    plt.plot(nc17['time'].T,nc17['current_I'],'r')
    plt.xlabel('Time (ms)')
    plt.ylabel('Injected current (pA)')

# to_plot = {'rates':{'var':statemonRout.r.T, # Individual neuron rates
#                      'x_unit':'ms',
#                      'y_unit':'spks/s',
#                      'x_label':'Time',
#                      'y_label':'Firing rate',
#                      'title':'Reservoir rate plot'},
#            'membrane_pot':{'var':gtestR.Monitors['statemonR'].Vm.T, # Individual neuron memb pot
#                            'x_unit':'ms',
#                            'y_unit':'mV',
#                            'x_label':'Time',
#                            'y_label':'Membrane potential',
#                            'title':'Reservoir rate plot'}}
# for tp_n,tp in to_plot.items():
#     plt.figure()
#     plt.plot(gtestR.Monitors['statemonR'].t/ms, tp['var'])
#     plt.title(tp['title'])
#     plt.xlabel('%s (%s)'%(tp['x_label'],tp['x_unit']))
#     plt.ylabel('%s (%s)'%(tp['y_label'],tp['y_unit']))

# Plot individual neuron rates
plt.figure()
plt.title('Individual neuron rates')
plt.plot(gtestR.Monitors['statemonR'].t/ms, statemonRout.r.T)
plt.plot(nc17['time'].T, nc17['current_r']-0.001,'r')
plt.xlabel('Time (ms)')
plt.ylabel('Rate')

# Plot individual neuron memb pot
plt.figure()
plt.title('Individual neuron memb pot')
plt.plot(gtestR.Monitors['statemonR'].t/ms, gtestR.Monitors['statemonR'].Vm.T/mV)
plt.plot(nc17['time'].T, nc17['current_v']-1,'r')
plt.xlabel('Time (ms)')
plt.ylabel('Rate')
# Plot individual neuron memb pot
plt.figure()
plt.title('Individual neuron memb pot')
plt.plot(gtestR.Monitors['statemonR'].t/ms, gtestR.Monitors['statemonR'].Vm.T[:,10]/mV)
plt.plot(nc17['time'].T, nc17['current_v'][:,10],'r')
plt.xlabel('Time (ms)')
plt.ylabel('Rate')

# Plot individual neuron Isyn
plt.figure()
plt.title('Individual neuron memb pot')
plt.plot(gtestR.Monitors['statemonR'].t/ms, gtestR.Monitors['statemonR'].Iin.T[:,10]/pA)
plt.plot(nc17['time'].T, nc17['current_IPSC'][:,10],'r')
plt.xlabel('Time (ms)')
plt.ylabel('Current (pA)')

if gtestR.Monitors['spikemonR'].t.shape is not ():
    plt.figure()
    plt.title('Reservoir raster plot')
    plt.plot(gtestR.Monitors['spikemonR'].t/ms, gtestR.Monitors['spikemonR'].i, '.k')
    plt.xlabel('Time (ms)')
    plt.ylabel('Neuron index')

# # Plot error
# plt.figure()
# plt.title('Readout error')
# error = np.array(error)
# plt.plot(error[:,0]/ms, error[:,1], 'k')
# plt.xlabel('Time (ms)')
# plt.ylabel('Error')

# Plot output
plt.figure()
plt.title('Output and Command')
error = np.array(error)
plt.plot(gtestR.Monitors['statemon_readout_rate'].t/ms, gtestR.Monitors['statemon_readout_rate'].rate.T)
plt.plot(nc17['time'], nc17['zx'].T,'r')
plt.xlabel('Time (ms)')
plt.ylabel('Error')

plt.show(0)


# for par0 in range(0,300,20):
#     for par1 in range(0,500,20):

#         standaloneParams=OrderedDict([('duration', 0.5 * second),
#                          ('stestR_e_latWeight', 400),#280),
#                          ('stestR_e_latSigma', 2),
#                          ('stestR_Inpe_weight', 300),
#                          ('stestR_Inhe_weight', par1),#300),
#                          ('stestR_Inhi_weight', -par0),
#                          ('gtestR_refP', 5. * msecond),
#                          ('gtestR_Inh_refP', 5. * msecond),
#                          ('gtestR_Iconst', 5000 * pA)])

#             Net.run(duration=duration*ms, standaloneParams=standaloneParams, report='text')
#         else:
#             Net.run(duration * ms)

#         num_source_neurons = gtestR.Groups['gRInpGroup'].N
#         num_target_neurons = gtestR.Groups['gRGroup'].N
#         cm = plt.cm.get_cmap('jet')
#         #x = np.arange(0, num_target_neurons, 1)
#         #y = np.arange(0, num_source_neurons, 1)
#         #X, Y = np.meshgrid(x, y)
#         #data = np.zeros((num_target_neurons, num_source_neurons)) * np.nan
#         # Getting sparse weights
#         #wta_plot,_=plotR(name='testR', start_time=0 * ms, end_time=duration * ms,
#         #        RMonitors=gtestR.Monitors, plot_states=False)


#         spikemonR = gtestR.Groups['spikemonR']
#         spiketimes = spikemonR.t
#         dt = defaultclock.dt
#         spikeinds = np.asarray(spiketimes/dt, dtype = 'int')

#         data_sparse = scipy.sparse.coo_matrix((np.ones(len(spikeinds)),(spikeinds,[i for i in spikemonR.i])))
#         data_dense = data_sparse.todense()

#         #data_dense.shape
#         filtersize = 500*ms
#         data_filtered = ndimage.uniform_filter1d(data_dense, size=int(filtersize / dt), axis=0, mode='constant') * second / dt
#         #plt.plot(data) #[400,:])
#         data = data_filtered[400,:]

#         from functools import partial
#         minres = minimize(partial(objective_function,data=data),[10,3,50])#,method='COBYLA')

#         ampl = minres.x[2]
#         mu =  minres.x[0]
#         sig = minres.x[1]

#         gauss_fit =  ampl*gaussian(x, mu, sig)

#         #plt.plot(x,gauss_fit)
#         #plt.plot(x,data)
#         #plt.legend(labels = ['fit','data'])
#         #plt.show()


#         amplitudes_dict[(par0,par1)] = ampl
#         sigmas_dict[(par0,par1)] = sig


# print('took', time.time()-st)


# plt.plot(amplitudes_dict.keys(),amplitudes_dict.values())
# plt.plot(sigmas_dict.keys(),sigmas_dict.values())


# parammap = {par:amplitudes_dict[par] for par in amplitudes_dict if amplitudes_dict[par]<150}
# paramnames = ["excexc", "inh"]
# plot_param_map(parammap=parammap, paramnames=paramnames)


# parammap = {par:sigmas_dict[par] for par in sigmas_dict if sigmas_dict[par]<10 and sigmas_dict[par]>0}
# paramnames = ["excexc", "inh"]
# plot_param_map(parammap=parammap, paramnames=paramnames)

# plt.show()

# if False:
#     plt.plot(syn_ex_ex.weight)#[syn_ex_ex.i==20])
#     plt.plot(syn_ex_ex.weight[20,:])
#     ex_ex_sum = np.sum(syn_ex_ex.weight[20,:] * syn_ex_ex.baseweight_e[20,:])
#     ex_sum = np.sum(syn_ex_ih.weight * syn_ex_ih.baseweight_e)
#     ih_sum = np.sum(syn_ih_ex.weight * syn_ih_ex.baseweight_i)


#     ex_ex_mat = np.zeros((100,100))
#     ex_ex_mat[syn_ex_ex.i,syn_ex_ex.j] =  syn_ex_ex.weight * syn_ex_ex.baseweight_e
#     plt.imshow(ex_ex_mat)

#     from numpy import linalg
#     w,v=linalg.eig(ex_ex_mat)
#     plt.plot(w)
#     plt.imshow(v)

#     statemonR = gtestR.Groups['statemonR']

#     gRGroup = gtestR.Groups["gRGroup"]
#     gRGroup.print_equations()

#     gRGroup.Ie0/pA
#     gRGroup.Ie1/pA
#     gRGroup.Ie2/pA
#     gRGroup.Ie3/pA
#     gRGroup.Ii0/pA
#     gRGroup.Ii1/pA
#     gRGroup.Ii2/pA
#     gRGroup.Ii3/pA

#     Ie = gRGroup.Ie0/pA+gRGroup.Ie1/pA+gRGroup.Ie2/pA+gRGroup.Ie3/pA
#     Ii = gRGroup.Ii0/pA+gRGroup.Ii1/pA+gRGroup.Ii2/pA+gRGroup.Ii3/pA

#     plt.figure()
#     plt.plot(Ie)
#     plt.plot(Ii)
#     plt.plot(Ii/Ie)
#     plt.show()


#     statemonRin.Ie0/pA
#     statemonRin.Ie1/pA
#     statemonRin.Ie2/pA
#     statemonRin.Ie3/pA
#     statemonRin.Ii0/pA
#     statemonRin.Ii1/pA
#     statemonRin.Ii2/pA
#     statemonRin.Ii3/pA

#     Ie = statemonRin.Ie0/pA+statemonRin.Ie1/pA+statemonRin.Ie2/pA+statemonRin.Ie3/pA
#     Ii = statemonRin.Ii0/pA+statemonRin.Ii1/pA+statemonRin.Ii2/pA+statemonRin.Ii3/pA

#     Ie_sum = np.sum(Ie.T,axis=1)
#     Ii_sum = np.sum(Ii.T,axis=1)

#     plt.figure()
#     plt.plot(Ie_sum)
#     plt.plot(Ie_sum)
#     plt.figure()
#     plt.plot(Ii_sum/Ie_sum)
#     plt.show()

#     font = 10
#     fig = plt.figure(figsize=(8,6))
#     ax1 = plt.subplot(211)
#     ax1.plot(statemonR.t / ms, statemonR.Imem[0] / nA)
#     ax1.set_title('Step neurons input: Iconst', fontsize=font)
#     ax1.set_xlabel('Time (ms)', fontsize=font - 2)
#     ax1.set_ylabel('Iconst (nA)', fontsize=font - 2)
#     ax1.tick_params(axis='x', labelsize=font - 4)
#     ax1.tick_params(axis='y', labelsize=font - 4)

# #%%
# standaloneParams=OrderedDict([('duration', 0.5 * second),
#              ('stestR_e_latWeight', 400),#280),
#              ('stestR_e_latSigma', 2),
#              ('stestR_Inpe_weight', 300),
#              ('stestR_Inhe_weight', 200),#300),
#              ('stestR_Inhi_weight', -20),

#              ('gtestR_refP', 5. * msecond),
#              ('gtestR_Inh_refP', 5. * msecond),
#              ('gtestR_Iconst', 5000 * pA)])

# duration=standaloneParams['duration']/ms
# Net.run(duration=duration*ms, standaloneParams=standaloneParams, report='text')

# wta_plot,_=plotR(name='testR', start_time=0 * ms, end_time=duration * ms,
#         RMonitors=gtestR.Monitors, plot_states=False)
# wta_plot.show()


# spikemonR = gtestR.Groups['spikemonR']
# spiketimes = spikemonR.t
# dt = defaultclock.dt
# spikeinds = spiketimes/dt

# data_sparse = scipy.sparse.coo_matrix((np.ones(len(spikeinds)),(spikeinds,[i for i in spikemonR.i])))
# data_dense = data_sparse.todense()

# #data_dense.shape
# filtersize = 500*ms
# data_filtered = ndimage.uniform_filter1d(data_dense, size=int(filtersize / dt), axis=0, mode='constant') * second / dt
# plt.plot(data_filtered[-10]) #[400,:])
