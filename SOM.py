'''
Created 03.2017
@author: Alpha

This is not a building block jet, but it might become one, when it works

This is an attempt to implement a spiking SOM inspired by Rumbell et al. 2014
'''

#===============================================================================
#import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import time
import os
from random import randrange, random
from random import seed as rnseed
from brian2 import ms,mV,pA,nS,nA,pF,us,volt,second,Network,prefs,SpikeGeneratorGroup,NeuronGroup,\
                   Synapses,SpikeMonitor,StateMonitor,figure, plot,show,xlabel,ylabel,\
                   seed,xlim,ylim,subplot,network_operation,set_device,device,TimedArray,\
                   defaultclock,profiling_summary,codegen
from brian2 import *

from NCSBrian2Lib.neuronEquations import ExpAdaptIF as neuronEq
#from NCSBrian2Lib.synapseEquations import fusiSynV as fusiSynapseEq
from NCSBrian2Lib.synapseEquations import StdpSynV as StdpSynapseEq
from NCSBrian2Lib.synapseEquations import reversalSynV as synapseEq
from NCSBrian2Lib.Parameters.neuronParams import gerstnerExpAIFdefaultregular as neuronPar
#from NCSBrian2Lib.Parameters.synapseParams import fusiDefault
from NCSBrian2Lib.Parameters.synapseParams import revSyn_default as synapsePar
from NCSBrian2Lib.Parameters.synapseParams import StdpSyn_default as plasticSynapsePar
from NCSBrian2Lib.tools import setParams, fkernelgauss1d, printStates, fkernel2d, xy2ind
from NCSBrian2Lib.BasicBuildingBlocks.WTA import gen2dWTA,gen1dWTA
from NCSBrian2Lib.Plotting.WTAplot import plotWTA,plotWTATiles

start = time.time()

standalone = True
clean = True
plotInp = False
plotting = True
plotweights = False

if standalone:
    if "somNet" in globals():
        device.reinit()
        device.activate(directory='SOM_standalone', build_on_run=False)
    else:
        set_device('cpp_standalone', directory='SOM_standalone', build_on_run=False)
    prefs.devices.cpp_standalone.openmp_threads = 4
else:
    prefs.codegen.target = "numpy"

seed(42)
rnseed(42)

# network parameters
duration = 3000 * ms #needs to be a multiple of interval # and needs to be much longer for SOM training, but for debugging and looking at input, keep it short 
interval = 20
nWTA1dNeurons = 64
nWTA2dNeurons = 8#16
ninputs = 3 # number of Input groups
# Input inhibition:
nInhNeurons = 4
cutoff = 7

defaultclock.dt = 100 *us

## tuning parameters:
## Important! Some of these parameters might be changed in standalone run (see below) 
# neuron params
neuronPar['taui'] = 6*ms   
neuronPar['a']    = 4*nS
neuronPar['b']    = 0.0805*nA
# input params
sigmGaussInput = 6.0
inputWeight = 2000
# input inh params
synInpInh1e_weight = 0.6
synInpInh1i_weight = -0.2           
synInhInp1i_weight = -1.5
plasticSynapsePar["taupre" ] = 10 *ms
plasticSynapsePar["taupost"] = 10 *ms
plasticSynapsePar["weight"] = 124
plasticWrand=0.2
# wtaSOM params
synWTAInh1e_weight = 0.5
synInhWTA1i_weight = -1.8
synWTAWTA1e_weight = 0.18 # lateral excitation
rpWTA = 2*ms
rpInh = 1*ms
nInhNeurons = 3
# sigm SOM connectivity kernel params 
sigmnbi = 2.6
sigmDecayTau = 2*second

somNet = Network()

#===============================================================================
## create wtaSOM
(gwtaSOMGroup,gwtaSOMInhGroup,gwtaSOMInpGroup,synInpwtaSOM1e,synwtaSOMwtaSOM1e,synwtaSOMInh1e,synInhwtaSOM1i,
            spikemonwtaSOM,spikemonwtaSOMInh,spikemonwtaSOMInp,statemonwtaSOM) = gen2dWTA('wtaSOM',
             neuronParameters = neuronPar, synParameters = synapsePar,
             weInpWTA = 0, weWTAInh = synWTAInh1e_weight, wiInhWTA = synInhWTA1i_weight, weWTAWTA = synWTAWTA1e_weight,
             rpWTA = rpWTA, rpInh = rpInh,sigm = sigmnbi, nNeurons = nWTA2dNeurons,
             nInhNeurons = nInhNeurons, cutoff = cutoff, monitor = plotting, numWtaInputs = 1, debug=False)

sigmnb = sigmnbi 
print("sigm nb: ",sigmnb)
#decay of kernel sigma ???

synwtaSOMwtaSOM1e.run_regularly('''weight = latWeight * fkernel2d(i,j,sigmnb*exp(-t/sigmDecayTau),nWTA2dNeurons)''',dt=200*ms)

#===============================================================================
## generate input array

## color example
red = (1.0,0.0,0.0)
or1 = (1.0,0.3,0.1)
or2 = (1.0,0.7,0.0)
yel = (1.0,0.9,0.0)
gr1 = (0.2,0.8,0.2)
gr2 = (0.2,0.7,0.5)
blu = (0.0,0.0,1.0)
bl2 = (0.0,0.3,1.0)
bl3 = (0.3,0.2,0.9)

collist = [red,or1,or2,yel,gr1,gr2,blu,bl2,bl3]
#collist = [(random(),random(),random()) for ii in range(8)]

nRepet = int((duration/ms) /interval)
randind = [randrange(0,len(collist)) for ii in range(nRepet-2*len(collist))] # we need duration to be at least interval * 2 * len(collist)
col = [collist[ii] for ii in randind]
col += collist * 2 #+ [red] # at the and go through the list twice
#===============================================================================
## create Input groups u

nInpNeurons = nWTA1dNeurons

neuronEqDict= neuronEq(numInputs = 2, debug = False)
gInpGroup = NeuronGroup(ninputs*nInpNeurons, name = 'gInpGroup', **neuronEqDict)
gInpSubgroups = [gInpGroup[(inp*nInpNeurons):((inp+1)*nInpNeurons)] for inp in range(ninputs)]
setParams(gInpGroup, neuronPar, debug = False)
spikemonInp = SpikeMonitor(gInpGroup)
statemonInp = StateMonitor(gInpGroup, ('Vm','Iin','Iconst'), record=range(ninputs*nInpNeurons))

#===============================================================================
## create Input Inhibition Inh_u

gInpInhGroup = NeuronGroup(nInhNeurons, name = 'gInpInhGroup', **neuronEqDict)
setParams(gInpInhGroup, neuronPar, debug = False)
spikemonInpInh = SpikeMonitor(gInpInhGroup)
statemonInpInh = StateMonitor(gInpInhGroup, ('Vm','Iin','Iconst'), record=range(nInhNeurons))

#===============================================================================
## create input inhibition synapses

synDict1 = synapseEq(inputNumber = 1, debug = False)
synDict2 = synapseEq(inputNumber = 2, debug = False)
synInpInh1e = Synapses(gInpGroup, gInpInhGroup, method = "euler", name = 'sInpInh1e', **synDict1)
synInpInh1i = Synapses(gInpGroup, gInpInhGroup, method = "euler", name = 'sInpInh1i', **synDict2)      
synInhInp1i = Synapses(gInpInhGroup, gInpGroup, method = "euler", name = 'sInhInp1i', **synDict1)

synInpInh1e.connect(True)
synInpInh1i.connect(True)
synInhInp1i.connect(True)

synapseParInpInh1i=synapsePar
synapseParInpInh1i["taugIi"] = 5 * ms 
synapseParInpInh1e=synapsePar
synapseParInpInh1e["taugIe"] = 14 * ms

setParams(synInpInh1e, synapseParInpInh1e, debug = False)
setParams(synInpInh1i, synapseParInpInh1i, debug = False)
setParams(synInhInp1i, synapsePar, debug = False)

synInpInh1e.weight = synInpInh1e_weight
synInpInh1i.weight = synInpInh1i_weight          
synInhInp1i.weight = synInhInp1i_weight

#===============================================================================
## create plastic synapses

plasticSynDict = StdpSynapseEq(inputNumber=4,debug=False)
synInpSom1e = Synapses(gInpGroup, gwtaSOMGroup, method = "euler", name = 'sInpSom1e', **plasticSynDict)    

synInpSom1e.connect(True)
setParams(synInpSom1e, plasticSynapsePar, debug = False)
statemonSynInpSom1e = StateMonitor(synInpSom1e,('w'), record=range(ninputs*nInpNeurons*nWTA2dNeurons*nWTA2dNeurons))

#synInpSom1e.weight = '0.1+0.6*rand()' #0.3 # making these random might be a way to get around the binary fusi synapse issue but it might also stop the SOM from working (think about it)  
synInpSom1e.w = 'w_max*rand()'


synInpSom1e.run_regularly('''w = w + plasticWrand*w_max*rand() ''',dt=300*ms)

#===============================================================================
# This is just a first idea of a decay of learning rate
# @network_operation(dt=2*interval*ms)
# def decreaseWplus(ti):
#     synInpSom1e.w_plus = synInpSom1e.w_plus*0.995
#     synInpSom1e.w_minus = synInpSom1e.w_minus*0.995
# 
# somNet.add((decreaseWplus))
#===============================================================================
                                                             
                              
stimTimes = range(0,int(duration/ms),interval)
meangaussind=[TimedArray([int(sigmGaussInput+(nInpNeurons-2*sigmGaussInput)*
                              col[int(np.floor(stimTime/interval))][inp]) for stimTime in stimTimes], dt=interval*ms) for inp in range(ninputs)]

for ii in range(len(meangaussind)):
    exec('meangaussind'+str(ii)+'=meangaussind[ii]') # sorry for that. Please tell me, if you find a better way

for inp in range(ninputs):
    gInpSubgroups[inp].run_regularly('''Iconst = inputWeight * fkernelgauss1d(int(meangaussind{inp}(t)),i,sigmGaussInput)*pA'''.format(inp=inp), dt=interval*ms)

#===============================================================================
## add all groups to network0

somNet.add((gInpGroup,gInpSubgroups))
somNet.add((gwtaSOMGroup,gwtaSOMInhGroup,synwtaSOMwtaSOM1e,synwtaSOMInh1e,synInhwtaSOM1i)) 
somNet.add((synInpSom1e))
somNet.add((gInpInhGroup))
somNet.add((synInpInh1e,synInhInp1i))
             
if plotting:
    somNet.add((spikemonwtaSOM,spikemonwtaSOMInh,statemonwtaSOM)) #,statemonwtaSOM
    
if plotInp:
    somNet.add((spikemonInp,statemonInp))#,statemonInp
    somNet.add((spikemonInpInh,statemonInpInh))

end = time.time()
print ('setting up took ' + str(end - start) + ' sec')
#===============================================================================
## simulation

somNet.run(duration,report_period=200*ms,report='stdout',profile=False)

if plotweights: #this saves memory
    somNet.add((statemonSynInpSom1e))
    somNet.run(interval*ms)
    duration += interval*ms 

if standalone:
    startBuild = time.time()
    
    prefs['codegen.cpp.extra_compile_args_gcc'].append('-std=c++14')
    #prefs['codegen.cpp.extra_compile_args_gcc'].append('-std=c++11')
    device.build(compile=False, run = False, directory='SOM_standalone', clean=clean, debug=False)
    
    end = time.time()
    print ('build took ' + str(end - startBuild) + ' sec')
    startSim = time.time()

    
    #===============================================================================
    # Code that needs to be added to the main.cpp file
    replaceVars = ['sInpSom1e_weight',
                 'sInpSom1e_taupre',
                 'sInpSom1e_taupost',
                 
                 'sInpInh1e_weight',
                 'sInpInh1i_weight',
                 'sInhInp1i_weight',
                 
                 'swtaSOMInh1e_weight',
                 'sInhwtaSOM1i_weight',
                 'swtaSOMwtaSOM1e_latWeight',
                 'gwtaSOM_refP',
                 'gwtaSOM_Inh_refP']
    
    maincppPath = os.path.expanduser('~/Code/SOM_standalone/main.cpp')

    # generate arg code
    cppArgCode = ""
    for ivar, rvar in enumerate(replaceVars):
        cppArgCode += """\n	float {replvar}_p = std::stof(argv[{num}],NULL);
	std::cout << "variable {replvar} is argument {num} with value " << {replvar}_p << std::endl;\n""".format(num=(ivar+1),replvar=rvar)
    
    
    # read main.cpp
    f = open(maincppPath, "r")
    contents = f.readlines()
    f.close()
    
    # insert arg code
    for i_line, line in enumerate(contents):
            if "int main(int argc, char **argv)" in line:
                insertLine = i_line+2
    contents.insert(insertLine, cppArgCode)
    
    # replace var code
    f = open(maincppPath, "w")
    for i_line, line in enumerate(contents):
        replaced = False
        for rvar in replaceVars:
            if rvar+"[i]" in line :
                replaced = True
                keepFirstPart = line.split('=', 1)[0]
                f.write(keepFirstPart + '= ' + rvar + '_p;\n')
                print("replaced " + rvar + " in line " + str(i_line))
        if not replaced:
            f.write(line)
    f.close()

    #===============================================================================

    # compile
    startMake = time.time()  
    #out = check_output(["make","-C","~/Code/SOM_standalone"])
    compiler, args = codegen.cpp_prefs.get_compiler_and_args()
    device.compile_source(directory='SOM_standalone', compiler=compiler, clean=clean, debug=False)
    #print(out)
    end = time.time()
    print ('make took ' + str(end - startMake) + ' sec')
    startSim = time.time()
    
    print('\n\nstandalone SOM was built and compiled, ready to run!')


#%%
startSim = time.time()


# SET PARAMETERS
# please note that those parameters have to be neuron or synapse attributes,
# all other parameters are more complicated to change, as they are replaced by their value in the c++ code (e.g. in run_regularly)
# Parameters can only be changed for a single Neuron or synapse group at once, using this mechanism

## Important: all parameters that are listed here, have to be added to replaceVars above.

paramDict = {
    #InpSOM
    'sInpSom1e_weight'      : 124,
    'sInpSom1e_taupre'      : 10*ms /second,
    'sInpSom1e_taupost'     : 10*ms /second,
    #Inp
    'sInpInh1e_weight'      : 0.6,
    'sInpInh1i_weight'      : -0.2,
    'sInhInp1i_weight'      : -1.5,
    #Som
    'swtaSOMInh1e_weight'   : 0.5,
    'sInhwtaSOM1i_weight'   : -1.8,
    'swtaSOMwtaSOM1e_latWeight': 0.18,
    'gwtaSOM_refP'          : 2 *ms /second,
    'gwtaSOM_Inh_refP'      : 1 *ms /second,
}

print([key for key in paramDict])
print([paramDict[key] for key in paramDict])
#add other parameters ...
#neuronPar['taui'] = 6*ms   
#neuronPar['a']    = 4*nS
#neuronPar['b']    = 0.0805*nA
## input params
#rpInp = 2*ms
#sigmGaussInput = 6.0
#inputWeight = 2000
#plasticWrand=0.2
#rpWTA = 2*ms
#rpInh = 1*ms
#nInhNeurons = 3
## sigm SOM connectivity kernel params 
#sigmnbi = 2.6
#sigmDecayTau = 2*second

run_args=[str(paramDict[key]) for key in paramDict]

#run simulation
device.run(directory='SOM_standalone',with_output=True,run_args=run_args)
end = time.time()
print ('simulation in c++ took ' + str(end - startSim) + ' sec')
print('simulation done!')


plotting = True

if plotting:
    start = time.time()
    dur = 1000 *ms
    startTime = duration - dur
    endTime = duration 
    #plotWTA('wtaSOM',duration,nWTA2dNeurons,True,spikemonwtaSOM,spikemonwtaSOMInh,spikemonwtaSOMInp,False)
    plotWTA('wtaSOM',startTime,endTime,nWTA2dNeurons,True,spikemonwtaSOM,spikemonwtaSOMInh,spikemonwtaSOMInp,statemonwtaSOM)
    ## WTA plot tiles over time
    plotWTATiles('wtaSOM',startTime,endTime,nWTA2dNeurons, spikemonwtaSOM,interval=interval*ms, showfig = False, tilecolors=col[(len(col)-int(dur/(interval*ms))):len(col)] )
    show()
    #plot(statemonwtaSOM.t/ms, statemonwtaSOM.Vm[0]/mV)
    #xlabel('Time [ms]')
    #ylabel('Vm')
    #xlim([0,duration/ms])
    end = time.time()
    print ('plot took ' + str(end - start) + ' sec')
    
#===============================================================================
## plot input

if plotInp:
    fig = figure(figsize=(8,10))
    nPlots=ninputs*100
    for ii in range(ninputs):
        subplot(nPlots+11+ii)
        spikeinds = spikemonInp.i[((nInpNeurons*ii)<spikemonInp.i)&(spikemonInp.i<(nInpNeurons*(ii+1)))]
        spiketimes = spikemonInp.t[((nInpNeurons*ii)<spikemonInp.i)&(spikemonInp.i<(nInpNeurons*(ii+1)))]
        plot(spiketimes/ms, spikeinds, '.k')
        xlabel('Time [ms]')
        ylabel('i_In')
        xlim([0,duration/ms])
        ylim([nInpNeurons*ii,nInpNeurons*(ii+1)])
        
print("done!")


#%%
# fig = figure(figsize=(8,10))
# for ii in range(ninputs*nInpNeurons):
#     plot(statemonInp.t/ms, statemonInp.Vm[ii]/mV, label='v')       
# xlabel('Time [ms]')
# ylabel('V (mV)')
# 
# fig = figure(figsize=(8,10))
# for ii in range(ninputs*nInpNeurons):
#     plot(statemonInp.t/ms, statemonInp.Iin[ii]/pA, label='I')       
# xlabel('Time [ms]')
# ylabel('Iin (pA)')

if plotweights:
    end=np.shape(statemonSynInpSom1e.w)[1]-1
    mat = np.reshape(statemonSynInpSom1e.w[:,end],(-1,nWTA2dNeurons,nWTA2dNeurons))
    imgShape = np.shape(mat) 
    #print(imgShape)
    #nPlots = imgShape[0]
    nPlots = nInpNeurons
    nCol = 8
    nRow = int(np.ceil(nPlots/nCol))
    #for i in range(imgShape[0]):
    for ii in range(ninputs):
        fig, axarr = plt.subplots(nRow,nCol,sharex=True,sharey=True,figsize=(nCol,nPlots//nCol))
        for inp in range(nInpNeurons):
            axarr[inp//nCol,np.mod(inp,nCol)].set_xlim(0,nWTA2dNeurons)
            axarr[inp//nCol,np.mod(inp,nCol)].set_ylim(0,nWTA2dNeurons)
            axarr[inp//nCol,np.mod(inp,nCol)].set_xticks(np.arange(nWTA2dNeurons)+0.5)
            axarr[inp//nCol,np.mod(inp,nCol)].set_yticks(np.arange(nWTA2dNeurons)+0.5)
            axarr[inp//nCol,np.mod(inp,nCol)].set_xticklabels([])
            axarr[inp//nCol,np.mod(inp,nCol)].set_yticklabels([])
            axarr[inp//nCol,np.mod(inp,nCol)].grid(True,linestyle='-')
            axarr[inp//nCol,np.mod(inp,nCol)].autoscale(False)
            img = axarr[inp//nCol,np.mod(inp,nCol)].imshow(mat[inp+nInpNeurons*ii,:,:],cmap=plt.cm.binary, vmin=0, vmax=1)
    
#%%
