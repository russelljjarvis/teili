# coding: utf-8
"""
This file contains a class that manages a synapse equation

It automatically adds the line: Iin = Ie0 + Ii0 + Ie1 + Ii1 ...
And it prepares a dictionary of keywords for easy neurongroup creation

It also provides a funtion to add lines to the model

"""
from brian2 import pF, nS, mV, ms, pA, nA, second, volt
# TODO: Take parameters from parameter files


def combineEquations_syn(*args):
    model = ''
    on_pre = ''
    on_post = ''
    varSet = {}
    varSet = set()
    for eq in args:
        if '%' in eq['model']:
            model, tmp = deleteVar(model, eq['model'], '%')
            varSet = set.union(tmp, varSet)
        else:
            model += eq['model']

        if '%' in eq['on_pre']:
            on_pre, tmp = deleteVar(on_pre, eq['on_pre'], '%')
            varSet = set.union(tmp, varSet)
        else:
            on_pre += eq['on_pre']

        if '%' in eq['on_post']:
            on_post, tmp = deleteVar(on_post, eq['on_post'], '%')
            varSet = set.union(tmp, varSet)

        else:
            on_post += eq['on_post']

    return {'model': model, 'on_pre': on_pre, 'on_post': on_post}, varSet


def deleteVar(firstEq, secondEq, var):
    varSet = {}
    varSet = set()
    resultfirstEq = ''
    resultsecondEq = ''
    for line in secondEq.splitlines():
        if var in line:  # for array variables
            var2 = line.split('%', 1)[1].split()[0]
            line = line.replace("%", "")
            if '/' in var2:
                var2 = var2.split('/', 1)[0][1:]
            diffvar2 = 'd' + var2 + '/dt'
            for line2 in firstEq.splitlines():

                # if i found a variable i need to check then if it's the explicit form we want to remove
                if (var2 in line2) or (diffvar2 in line2):

                    if (var2 == line2.replace(':', '=').split('=', 1)[0].split()[0]) or (diffvar2 in line2.replace(':', '=').split('=', 1)[0].split()[0]):
                        varSet.add(var2)
                        pass
                    else:
                        resultfirstEq += line2 + "\n"

                else:
                    resultfirstEq += line2 + "\n"
            if len(line.split()) > 1:
                resultsecondEq += line + "\n"
            firstEq = resultfirstEq
            resultfirstEq = ""
        else:
            resultsecondEq += line + "\n"
    resultEq = firstEq + resultsecondEq
#    print(resultEq)
    return resultEq, varSet


def combineParDictionaries(varSet, *args):
    ParametersDict = {}
    for tmpDict in args:
        # OverrideList = list(ParametersDict.keys() & tmpDict.keys())
        OverrideList = list(
            set(ParametersDict.keys()).intersection(tmpDict.keys()))
        for key in OverrideList:
            ParametersDict.pop(key)
        ParametersDict.update(tmpDict)
    for key in list(varSet):
        if key in ParametersDict:
            ParametersDict.pop(key)
    return ParametersDict


class SynapseEquationBuilder():

    def __init__(self, model=None, baseUnit='current', kernel='exponential',
                 plasticity='nonplastic', inputnumber=1, verbose=False):
        self.verbose = verbose
        if model is not None:
            eqDict = model
            eqDict['model'] = eqDict['model'].format(inputnumber="{inputnumber}", synvar_e='Ie_syn', synvar_i='Ii_syn', unit='amp',
                                                     Ie="Ie" + str(inputnumber - 1), Ii="Ii" + str(inputnumber - 1))

            self.model = eqDict['model']
            self.on_pre = eqDict['on_pre']
            self.on_post = eqDict['on_post']
            self.parameters = eqDict['parameters']

            self.keywords = {'model': self.model, 'on_pre': self.on_pre,
                             'on_post': self.on_post}
        else:
            ERRValue = """
                                    ---Model not present in dictionaries---
                    This class constructor build a model for a synapse using pre-existent blocks.

                    The first entry is the type of model,
                    choice between : 'current' or 'conductance'

                    The second entry is the kernel of the synapse
                    can be one of those : 'exponential', 'alpha', 'resonant' or 'gassian'
                    and 'silicon' for current type of synapse only

                    The third entry is the plasticity of the synapse
                    can be : 'nonplastic', 'fusi' or 'stdp'

                    """

            try:
                modes[baseUnit]
                if baseUnit == 'current':
                    currentkernels[kernel]
                else:
                    conductancekernels[kernel]
                plasticitymodels[plasticity]
            except KeyError as e:
                print(ERRValue)

            if modes[baseUnit] == 'current':
                eqDict, varSet = combineEquations_syn(
                    template, currentkernels[kernel], plasticitymodels[plasticity])
                eqDict['model'] = eqDict['model'].format(inputnumber="{inputnumber}", synvar_e='Ie_syn', synvar_i='Ii_syn', unit='amp')
                eqDict['on_pre'] = eqDict['on_pre'].format(inputnumber="{inputnumber}", synvar_e='Ie_syn', synvar_i='Ii_syn', unit='amp')
                eqDict['on_post'] = eqDict['on_post'].format(inputnumber="{inputnumber}", synvar_e='Ie_syn', synvar_i='Ii_syn', unit='amp')
                if '{synvar_e}' in varSet:
                    varSet.remove('{synvar_e}')
                    varSet.add('Ie_syn')
                if '{synvar_i}' in varSet:
                    varSet.remove('{synvar_i}')
                    varSet.add('Ii_syn')
                eqDict['parameters'] = combineParDictionaries(
                    varSet, current_Parameters[baseUnit], current_Parameters[kernel], current_Parameters[plasticity])

            if modes[baseUnit] == 'conductance':
                eqDict, varSet = combineEquations_syn(
                    template, reversalsyn, conductancekernels[kernel], plasticitymodels[plasticity])
                eqDict['model'] = eqDict['model'].format(inputnumber="{inputnumber}", synvar_e='gIe', synvar_i='gIi', unit='siemens')
                eqDict['on_pre'] = eqDict['on_pre'].format(inputnumber="{inputnumber}", synvar_e='gIe', synvar_i='gIi', unit='siemens')
                eqDict['on_post'] = eqDict['on_post'].format(inputnumber="{inputnumber}", synvar_e='gIe', synvar_i='gIi', unit='siemens')
                if '{synvar_e}' in varSet:
                    varSet.remove('{synvar_e}')
                    varSet.add('gIe')
                if '{synvar_i}' in varSet:
                    varSet.remove('{synvar_i}')
                    varSet.add('gIi')
                eqDict['parameters'] = combineParDictionaries(varSet, conductance_Parameters[baseUnit],
                                                              conductance_Parameters[kernel], conductance_Parameters[plasticity])

            if modes[baseUnit] == 'DPI':
                eqDict, varSet = combineEquations_syn(
                    Dpi, plasticitymodels[plasticity])

                eqDict['model'] = eqDict['model'].format(inputnumber="{inputnumber}", synvar_e='Ie_syn', synvar_i='Ii_syn', unit='amp')
                eqDict['on_pre'] = eqDict['on_pre'].format(inputnumber="{inputnumber}", synvar_e='Ie_syn', synvar_i='Ii_syn', unit='amp')
                eqDict['on_post'] = eqDict['on_post'].format(inputnumber="{inputnumber}", synvar_e='Ie_syn', synvar_i='Ii_syn', unit='amp')

                if '{synvar_e}' in varSet:
                    varSet.remove('{synvar_e}')
                    varSet.add('Ie_syn')
                if '{synvar_i}' in varSet:
                    varSet.remove('{synvar_i}')
                    varSet.add('Ii_syn')
                eqDict['parameters'] = combineParDictionaries(
                    varSet, DPI_Parameters[baseUnit], DPI_Parameters[plasticity])

            self.changeableParameters = ['weight']

            self.standaloneVars = {}  # TODO: this is just a dummy, needs to be written

            #self.model = eqDict['model']
            #self.on_pre = eqDict['on_pre']
            #self.on_post = eqDict['on_post']
            self.parameters = eqDict['parameters']

            self.model = eqDict['model']
            self.on_pre = eqDict['on_pre']
            self.on_post = eqDict['on_post']
    #       self.parameters = eqDict['default']
    #        self.addInputCurrents(inputNumber)

    #        self.keywords = {'modelEq':self.modelEq, 'preEq':self.preEq,
    #                         'postEq':self.postEq, 'parameters' : self.parameters}

            self.keywords = {'model': eqDict['model'], 'on_pre': eqDict['on_pre'],
                             'on_post': eqDict['on_post']}

    def printAll(self):
        printEqDict_syn(self.keywords, self.parameters)

    def set_inputnumber(self, inputnumber):
        self.keywords['model'] = self.keywords['model'].format(inputnumber=str(inputnumber - 1))  # inputnumber-1 ???
        self.keywords['on_pre'] = self.keywords['on_pre'].format(inputnumber=str(inputnumber - 1))
        self.keywords['on_post'] = self.keywords['on_post'].format(inputnumber=str(inputnumber - 1))



############################################################################################
#######_____TEMPLATE MODEL AND PARAMETERS_____##############################################
############################################################################################


# none model is useful when adding exponential kernel and nonplasticity at the synapse as they already present in the template model
none = {'model': ''' ''', 'on_pre': ''' ''', 'on_post': ''' '''}


template = {'model': '''
            d{synvar_e}/dt = (-{synvar_e}) / tausyne + kernel_e: {unit} (clock-driven)
            d{synvar_i}/dt = (-{synvar_i}) / tausyni + kernel_i : {unit} (clock-driven)

            kernel_e : {unit}* second **-1
            kernel_i : {unit}* second **-1

            Ie{inputnumber}_post = Ie_syn : amp  (summed)
            Ii{inputnumber}_post = Ii_syn : amp  (summed)
            weight : 1
            tausyne : second (constant) # synapse time constant
            tausyni : second (constant) # synapse time constant
            wPlast : 1

            baseweight_e : {unit} (constant)     # synaptic gain
            baseweight_i : {unit} (constant)     # synaptic gain
            ''',

            'on_pre': '''
            {synvar_e} += baseweight_e * weight *wPlast*(weight>0)
            {synvar_i} += baseweight_i * weight *wPlast*(weight<0)
            ''',

            'on_post': ''' ''',
            }

# standard parameters for current based models
currentPara = {"tausyne": 5 * ms,
               "tausyni": 5 * ms,
               "wPlast": 1,
               "baseweight_e": 1 * nA,
               "baseweight_i": 1 * nA,
               "kernel_e": 0 * nA * ms**-1,
               "kernel_i": 0 * nA * ms**-1
               }

# Additional equations for conductance based models
reversalsyn = {'model': '''
               Ie_syn = {synvar_e}*(EIe - Vm_post) :amp
               Ii_syn = {synvar_i}*(EIi - Vm_post) :amp
               EIe : volt (shared,constant)             # excitatory reversal potential
               EIi : volt (shared,constant)             # inhibitory reversal potential
               ''',

               'on_pre': ''' ''',

               'on_post': ''' ''',
               }

# standard parameters for conductance based models
reversalPara = {"Ige": 0 * nS,
                "tausyne": 5 * ms,
                # We define tausyn again here since its different from current base, is this a problem?
                "tausyni": 6 * ms,
                "EIe": 60.0 * mV,
                "EIi": -90.0 * mV,
                "wPlast": 1,
                # should we find the way to replace baseweight_e/i, since we already defined it in template?
                "baseweight_e": 7 * nS,
                "baseweight_i": 3 * nS,
                "kernel_e": 0 * nS * ms**-1,
                "kernel_i": 0 * nS * ms**-1
                }

# Dpi type model
Dpi = {'model': '''
        dIe_syn/dt = (-Ie_syn - Ie_gain + 2*Io_syn*(Ie_syn<=Io_syn))/(tausyne*((Ie_gain/Ie_syn)+1)) : amp (clock-driven)
        dIi_syn/dt = (-Ii_syn - Ii_gain + 2*Io_syn*(Ii_syn<=Io_syn))/(tausyni*((Ii_gain/Ii_syn)+1)) : amp (clock-driven)

        Ie{inputnumber}_post = Ie_syn : amp  (summed)
        Ii{inputnumber}_post = -Ii_syn : amp  (summed)

        weight : 1
        wPlast : 1

        Ie_gain = Io_syn*(Ie_syn<=Io_syn) + Ie_th*(Ie_syn>Io_syn) : amp
        Ii_gain = Io_syn*(Ii_syn<=Io_syn) + Ii_th*(Ii_syn>Io_syn) : amp

        Itau_e = Io_syn*(Ie_syn<=Io_syn) + Ie_tau*(Ie_syn>Io_syn) : amp
        Itau_i = Io_syn*(Ii_syn<=Io_syn) + Ii_tau*(Ii_syn>Io_syn) : amp

        baseweight_e : amp (constant)     # synaptic gain
        baseweight_i : amp (constant)     # synaptic gain
        tausyne = Csyn * Ut_syn /(kappa_syn * Itau_e) : second
        tausyni = Csyn * Ut_syn /(kappa_syn * Itau_i) : second
        kappa_syn = (kn_syn + kp_syn) / 2 : 1


        Iw_e = weight*baseweight_e  : amp
        Iw_i = -weight*baseweight_i  : amp

        Ie_tau       : amp (constant)
        Ii_tau       : amp (constant)
        Ie_th        : amp (constant)
        Ii_th        : amp (constant)
        kn_syn       : 1 (constant)
        kp_syn       : 1 (constant)
        Ut_syn       : volt (constant)
        Io_syn       : amp (constant)
        Csyn         : farad (constant)
        ''',
       'on_pre': '''
        Ie_syn += Iw_e*wPlast*Ie_gain*(weight>0)/(Itau_e*((Ie_gain/Ie_syn)+1))
        Ii_syn += Iw_i*wPlast*Ii_gain*(weight<0)/(Itau_i*((Ii_gain/Ii_syn)+1))
        ''',
       'on_post': ''' ''',
       }

# standard parameters for Dpi models
DpiPara = {
    'Io_syn': 0.5 * pA,
    'kn_syn': 0.75,
    'kp_syn': 0.66,
    'Ut_syn': 25. * mV,
    "Igain": 15 * pA,
    'Csyn': 1.5 * pF,
    'Ie_tau': 10. * pA,
    'Ii_tau': 10. * pA,
    'Ie_th': 10 * pA,
    'Ii_th': 10 * pA,
    'Ie_syn': 0.5 * pA,
    'Ii_syn': 0.5 * pA,
    'wPlast': 1,
    'baseweight_e': 50. * pA,
    'baseweight_i': 50. * pA
}


############################################################################################
#######_____ADDITIONAL EQUATIONS BLOCKS AND PARAMETERS_____#################################
############################################################################################
# Every block must specifies additional model, pre and post spike equations, as well as
#  two different sets (dictionaries) of parameters for conductance based models or current models

# If you want to ovverride an equation add '%' before the variable of your block's explicit equation

# example:  Let's say we have the simplest model (current one with template equation),
# and you're implementing a new block with this explicit equation : d{synvar_e}/dt = (-{synvar_e})**2 / synvar_e,
# if you want to override the equation already declared in the template: d{synvar_e}/dt = (-{synvar_e}) / tausyne + kernel_e:
# your equation will be : %d{synvar_e}/dt = (-{synvar_e})**2 / synvar_e


########_____Plasticity Blocks_____#########################################################
# you need to declare two set of parameters for every block : (one for current based models and one for conductance based models)

# Fusi learning rule ##
fusi = {'model': '''
      dCa/dt = (-Ca/tau_ca) : volt (event-driven) #Calcium Potential

      updrift = 1.0*(w>theta_w) : 1
      downdrift = 1.0*(w<=theta_w) : 1

      dw/dt = (alpha*updrift)-(beta*downdrift) : 1 (event-driven) # internal weight variable

      wplus: 1 (shared)
      wminus: 1 (shared)
      theta_upl: volt (shared, constant)
      theta_uph: volt (shared, constant)
      theta_downh: volt (shared, constant)
      theta_downl: volt (shared, constant)
      theta_V: volt (shared, constant)
      alpha: 1/second (shared,constant)
      beta: 1/second (shared, constant)
      tau_ca: second (shared, constant)
      w_min: 1 (shared, constant)
      w_max: 1 (shared, constant)
      theta_w: 1 (shared, constant)
      w_ca: volt (shared, constant)     ''',

        'on_pre': '''
      up = 1. * (Vm_post>theta_V) * (Ca>theta_upl) * (Ca<theta_uph)
      down = 1. * (Vm_post<theta_V) * (Ca>theta_downl) * (Ca<theta_downh)
      w += wplus * up - wminus * down
      w = clip(w,w_min,w_max)
      wPlast = floor(w+0.5)
      ''',

        'on_post': '''Ca += w_ca'''}

fusiPara_current = {"wplus": 0.2,
                    "wminus": 0.2,
                    "theta_upl": 180 * mV,
                    "theta_uph": 1 * volt,
                    "theta_downh": 90 * mV,
                    "theta_downl": 50 * mV,
                    "theta_V": -59 * mV,
                    "alpha": 0.0001 / second,
                    "beta": 0.0001 / second,
                    "tau_ca": 8 * ms,
                    "w_ca": 250 * mV,
                    "w_min": 0,
                    "w_max": 1,
                    "theta_w": 0.5,
                    "w": 0
                    }

fusiPara_conductance = {"wplus": 0.2,
                        "wminus": 0.2,
                        "theta_upl": 180 * mV,
                        "theta_uph": 1 * volt,
                        "theta_downh": 90 * mV,
                        "theta_downl": 50 * mV,
                        "theta_V": -59 * mV,
                        "alpha": 0.0001 / second,
                        "beta": 0.0001 / second,
                        "tau_ca": 8 * ms,
                        "w_ca": 250 * mV,
                        "w_min": 0,
                        "w_max": 1,
                        "theta_w": 0.5,
                        "w": 0
                        }

# STDP learning rule ##
stdp = {'model': '''
      w : 1
      dApre/dt = -Apre / taupre : 1 (event-driven)
      dApost/dt = -Apost / taupost : 1 (event-driven)
      w_max: 1 (shared, constant)
      taupre : second (shared, constant)
      taupost : second (shared, constant)
      dApre : 1 (shared, constant)
      Q_diffAPrePost : 1 (shared, constant)
      ''',

        'on_pre': '''
      wPlast = w
      Apre += dApre*w_max
      w = clip(w + Apost, 0, w_max) ''',

        'on_post': '''
      Apost += -dApre * (taupre / taupost) * Q_diffAPrePost * w_max
      w = clip(w + Apre, 0, w_max) '''}

stdpPara_current = {"baseweight_e": 7 * pA,  # should we find the way to replace since we would define it twice
                    "baseweight_i": 7 * pA,
                    "taupre": 10 * ms,
                    "taupost": 10 * ms,
                    "w_max": 1.,
                    "dApre": 0.1,
                    "Q_diffAPrePost": 1.05,
                    "w": 0,
                    "wPlast": 0}

stdpPara_conductance = {"baseweight_e": 7 * nS,  # should we find the way to replace since we would define it twice
                        "baseweight_i": 3 * nS,
                        "taupre": 20 * ms,
                        "taupost": 20 * ms,
                        "w_max": 0.01,
                        "diffApre": 0.01,
                        "Q_diffAPrePost": 1.05,
                        "w": 0,
                        "wPlast": 0}

########_____Kernels Blocks_____#########################################################
# you need to declare two set of parameters for every block : (one for current based models and one for conductance based models)

# TODO: THESE KERNELS ARE WRONG!

# Alpha kernel ##

alphakernel = {'model': '''
             %kernel_e = baseweight_e*(weight>0)*wPlast*weight*exp(1-t_spike/tausyne_rise)/tausyne : {unit}* second **-1
             %kernel_i = baseweight_i*(weight<0)*wPlast*weight*exp(1-t_spike/tausyni_rise)/tausyni : {unit}* second **-1
             dt_spike/dt = 1 : second (clock-driven)
             tausyne_rise : second
             tausyni_rise : second
             ''',

               'on_pre': '''

             t_spike = 0 * ms
             ''',

               'on_post': ''' '''}

alphaPara_current = {"tausyne": 2 * ms,
                     "tausyni": 2 * ms,
                     "tausyne_rise": 0.5 * ms,
                     "tausyni_rise": 0.5 * ms}

alphaPara_conductance = {"tausyne": 2 * ms,
                         "tausyni": 2 * ms,
                         "tausyne_rise": 1 * ms,
                         "tausyni_rise": 1 * ms}

# Resonant kernel ##
resonantkernel = {'model': '''
                omega: 1/second
                sigma_gaussian : second
                %kernel_e  = baseweight_e*(weight>0)*wPlast*(weight*exp(-t_spike/tausyne_rise)*cos(omega*t_spike))/tausyne : {unit}* second **-1
                %kernel_i  = baseweight_i*(weight<0)*wPlast*(weight*exp(-t_spike/tausyni_rise)*cos(omega*t_spike))/tausyni : {unit}* second **-1
                dt_spike/dt = 1 : second (clock-driven)
                tausyne_rise : second
                tausyni_rise : second
                ''',

                  'on_pre': '''

                t_spike = 0 * ms
                ''',

                  'on_post': ''' '''}

resonantPara_current = {"tausyne": 2 * ms,
                        "tausyni": 2 * ms,
                        "omega": 7 / ms,
                        "tausyne_rise": 0.5 * ms,
                        "tausyni_rise": 0.5 * ms}

resonantPara_conductance = {"tausyne": 2 * ms,
                            "tausyni": 2 * ms,
                            "omega": 1 / ms}


#  Gaussian kernel ##


gaussiankernel = {'model': '''
                  %tausyne = (sigma_gaussian_e**2)/t_spike : second
                  %tausyni = (sigma_gaussian_i**2)/t_spike : second
                  sigma_gaussian_e : second
                  sigma_gaussian_i : second

                  dt_spike/dt = 1 : second (clock-driven)
                  ''',
                  # this time we need to add this pre eq to the template pe eq

                  'on_pre': '''t_spike = 0 * ms''',

                  'on_post': ''' '''}

gaussianPara_current = {"sigma_gaussian_e": 6 * ms,
                        "sigma_gaussian_i": 6 * ms}

gaussianPara_conductance = {"sigma_gaussian_e": 6 * ms,
                            "sigma_gaussian_i": 6 * ms}


nonePara = {}


########_____Dictionary of keywords_____#########################################################
# These dictionaries contains keyword and models and parameters names useful for the __init__ subroutine
# Every new block dictionaries must be added to these definitions

conductancekernels = {'exponential': none, 'alpha': alphakernel,
                      'resonant': resonantkernel, 'gaussian': gaussiankernel}

currentkernels = {'exponential': none, 'alpha': alphakernel,
                  'resonant': resonantkernel, 'gaussian': gaussiankernel}

plasticitymodels = {'nonplastic': none, 'fusi': fusi, 'stdp': stdp}

modes = {'current': 'current', 'conductance': 'conductance', 'DPI': 'DPI'}


current_Parameters = {'current': currentPara, 'nonplastic': nonePara, 'fusi': fusiPara_current,
                      'stdp': stdpPara_current, 'exponential': nonePara, 'alpha': alphaPara_current,
                      'resonant': resonantPara_current, 'gaussian': gaussianPara_current}

conductance_Parameters = {'conductance': reversalPara, 'nonplastic': nonePara, 'fusi': fusiPara_conductance,
                          'stdp': stdpPara_conductance, 'exponential': nonePara, 'alpha': alphaPara_conductance,
                          'resonant': resonantPara_conductance, 'gaussian': gaussianPara_conductance}

DPI_Parameters = {'DPI': DpiPara, 'nonplastic': nonePara, 'fusi': fusiPara_current,
                  'stdp': stdpPara_current}


def printDictionaries(Dict):
    for keys, values in Dict.items():
        print(keys)
        print(repr(values))


def printEqDict_syn(eqDict, param):
    print('Model equation:')
    print(eqDict['model'])
    print('-_-_-_-_-_-_-_-')
    print('Pre spike equation:')
    print(eqDict['on_pre'])
    print('-_-_-_-_-_-_-_-')
    print('Post spike equation:')
    print(eqDict['on_post'])
    print('-_-_-_-_-_-_-_-')
    print('Post default parameters')
    print('')
    printDictionaries(param)
    print('-_-_-_-_-_-_-_-')
