'''
This is just an example
can be deleted later on, when more sophisticated examples are available

@author: Alpha
'''
import matplotlib
import matplotlib.pyplot as plt
from brian2 import *
import numpy as np
import time
from NCSBrian2Lib.neuronEquations import *
from NCSBrian2Lib.tools import *
from NCSBrian2Lib.equationParams import *

prefs.codegen.target = "numpy" 


eqsDict = ExpAdaptIF()

testNet = Network()

tsSeq = np.asarray(range(0,600,2)) * ms
indSeq = np.concatenate((np.zeros(50, dtype=np.int), np.ones(50, dtype=np.int),
                        np.zeros(50, dtype=np.int), np.ones(50, dtype=np.int),
                        np.zeros(50, dtype=np.int), 2*np.ones(50, dtype=np.int) ))
gSeqInpGroup = SpikeGeneratorGroup(3, indices = indSeq, times=tsSeq)

gSeqGroup = NeuronGroup(3, **eqsDict, refractory=1*ms, method = "euler")
synInpSeqe = Synapses(gSeqInpGroup, gSeqGroup, on_pre = 'Ie += 2*665*pA')
synInpSeqe.connect('i==j') 

setParams(gSeqGroup , gerstnerExpAIFdefaultregular)

spikemonSeq = SpikeMonitor(gSeqGroup)
spikemonSeqInp = SpikeMonitor(gSeqInpGroup)
statemonSeq = StateMonitor(gSeqGroup,('Vm','Ie'), record=[0,1,2])


testNet.add((gSeqInpGroup,gSeqGroup,spikemonSeq,spikemonSeqInp,statemonSeq,synInpSeqe))

start = time.clock()
duration = 600 * ms
testNet.run(duration)
end = time.clock()
print ('simulation took ' + str(end - start) + ' sec')
print('done!')



fig = figure(figsize=(8,3))
plot(statemonSeq.t/ms, statemonSeq[0].Vm/mV, label='V')
plot(statemonSeq.t/ms, statemonSeq[1].Vm/mV, label='V')
plot(statemonSeq.t/ms, statemonSeq[2].Vm/mV, label='V')
xlabel('Time [ms]')
ylabel('V (mV)')
plt.show()#savefig('fig/figSeqV.png')

fig = figure(figsize=(8,3))
plot(statemonSeq.t/ms, statemonSeq.Ie[0]/pA, label='Ie')
plot(statemonSeq.t/ms, statemonSeq.Ie[1]/pA, label='Ie')
plot(statemonSeq.t/ms, statemonSeq.Ie[2]/pA, label='Ie')
xlabel('Time [ms]')
ylabel('Ie (pA)')
plt.show()#savefig('fig/figSeqIe.png')

