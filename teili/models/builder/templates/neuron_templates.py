# -*- coding: utf-8 -*-
""" This file contains dictionaries of neuron equations or modules,
combined by the neuron equation builder.
Each template consists of a dictionary containing the relevant
equations and a corresponding parameter dictionary.

For usage example plaese refer to `teili/models/neuron_models.py`

Contributing guide:
*  Dictionary describing the neuron model
    *  Describing the model dynamics, including all used variables
       and their units.
    *  Required keys in the dictionary: 'model', 'threshold', 'reset'.
    *  name: modelname_template
*  Corresponding dictionary containing default/init parameters.
    *  name: modelname_template_params
TBA: How to add dictionaries to Model dictionaries (see bottom)
"""

from teili import constants
from brian2 import pF, nS, mV, ms, mA, pA, nA, psiemens, ohm
pS = psiemens

# voltage based equation building blocks
v_model_template = {
    'model': """
        dVm/dt  = (Ileak + Iexp + Iin + Iconst + Inoise - Iadapt)/Cm  : volt (unless refractory)
        Ileak   : amp                            # leak current

        Iexp    : amp                            # exponential current
        Iadapt  : amp                            # adaptation current
        Inoise  : amp                            # noise current
        Iconst  : amp                            # additional input current
        Cm      : farad     (constant)           # membrane capacitance
        refP    : second    (constant)           # refractory period
        Vthr    : volt
        Vres    : volt      (constant)           # reset potential
        gL      : siemens   (constant)           # leak conductance
        """,
    'threshold': "Vm > Vthr",
    'reset': """
        Vm = Vres;
        """
}

v_model_template_params = {
    "Cm": 281 * pF,
    "refP": 2 * ms,
    "Ileak": 0 * pA,
    "Iexp": 0 * pA,
    "Iadapt": 0 * pA,
    "Inoise": 0 * pA,
    "Iconst": 0 * pA,
    "Vthr": -50.4 * mV,
    "Vres": -70.6 * mV
    }

# exponential current (see exponential I&F Model)
# exponential
v_exp_current = {
    'model': """
        %Iexp = gL*DeltaT*exp((Vm - VT)/DeltaT) : amp
        %Vthr = (VT + 5 * DeltaT) : volt

        VT      : volt (constant)
        DeltaT  : volt (constant) # slope factor
        """,
    'threshold': "",
    'reset': """ """
    }

v_exp_current_params = {
    "gL": 4.3 * nS,
    "DeltaT": 2 * mV,
    "VT": -50.4 * mV
    }

# quadratic current (see Izhikevich Model)
v_quad_current = {
    'model': """
        %Iexp = k*(Vm - VR)*(Vm - VT) : amp
        %tauIadapt = 1.0/a            : second  # adaptation time constant
        %gAdapt = b                   : siemens # adaptation decay parameter
        %wIadapt = d                  : amp     # adaptation weight
        %EL = VR                      : volt

        VT      : volt                (constant)        # V integration threshold
        Vpeak   : volt                (constant)        # V spike threshold
        VR      : volt                (constant)        # V rest
        k       : siemens * volt **-1 (constant)        # slope factor
        a       : second **-1         (constant)        # recovery time constant
        b       : siemens             (constant)        # 1/Rin
        c       : volt                (constant)        # potential reset value
        d       : amp                 (constant)        # outward minus inward currents
                                                        # activated during the spike
                                                        # and affecting the after-spike
                                                        # behavior
        %Vthr = Vpeak : volt
        %Vres = VR : volt
        """,
    'threshold': "",
    'reset': """
        %Vm = c;
        Iadapt += wIadapt;
        """
    }

""" Paramters for the quadratic model taken from
Nicola & Clopath 2017. Please refer to this paper for more information.
The parameter k represents k = 1/Rin in the original study.
"""
v_quad_params = {
    "Cm": 250.0 * pF,
    "Vpeak": 30.0 * mV,
    "VR": -60.0 * mV,
    "VT": -20.0 * mV,
    "a": 0.01 / ms,
    "b": 0.0 * pS,
    "c": -65 * mV,
    "d": 200 * pA,
    "k":  2.5 * nS / mV,
    "EL": -55 * mV,
}

# leak
v_leak = {
    'model': """
        %Ileak = -gL*(Vm - EL) : amp

        EL : volt (constant) # leak reversal potential
        """,
    'threshold': "",
    'reset': """
    """
    }

v_leak_params = {
    "gL": 4.3 * nS,
    "EL": -55 * mV
    }

# adaptation
v_adapt = {
    'model': """
        %dIadapt/dt = -(gAdapt*(EL - Vm) + Iadapt)/tauIadapt : amp

        tauIadapt : second  (constant) # adaptation time constant
        gAdapt    : siemens (constant) # adaptation decay parameter
        wIadapt   : amp     (constant) # adaptation weight
        EL        : volt    (constant) # reversal potential
        """,
    'threshold': "",
    'reset': """
        Iadapt += wIadapt;
        """
    }

v_adapt_params = {
    "gAdapt": 4 * nS,
    "wIadapt": 0.0805 * nA,
    "tauIadapt": 144 * ms,
    "EL": -70.6 * mV
    }

thr_adapt = {
    'model': """
        %dVthr/dt = -(Vthr-thr_min)/tau_thr : volt

        tau_thr : second (constant) # Threshold decay time constant
        thr_inc     : volt (constant)   # Increment of threshold
        thr_min   : volt (constant)   # Threshold minimum value
        thr_max   : volt (constant)   # Threshold maximum value
        """,
    'threshold': "",
    'reset': """
        Vthr = clip(Vthr+thr_inc, thr_min, thr_max)
        """
    }

quantized_thresh_adapt = {
    'model': """
        %dVthr/dt = Vthr*decay_thresh/second + (thr_min*dt*decay_thresh/tau_thr)/second: volt
        decay_thresh = tau_thr/(tau_thr + dt) : 1

        tau_thr : second (constant)
        thr_inc     : volt (constant)   # Increment of threshold
        thr_min   : volt (constant)   # Threshold minimum value
        thr_max   : volt (constant)   # Threshold maximum value
        """,
    'threshold': "",
    'reset': """
        Vthr = clip(Vthr+thr_inc, thr_min, thr_max)
        """
    }

thr_adapt_params = {
    "tau_thr": 60000*ms,
    "thr_min": 4*mV,
    "thr_max": 16*mV,
    "thr_inc": 0.01*mV
    }

# noise
v_noise = {
    'model': """
        %Inoise = xi*Anoise*(second**0.5) : amp

        Anoise : amp (constant)
        """,
    'threshold': "",
    'reset': """ """
    }

""" Adds spatial location to neuron locate at the soma.
This additional information is **not** set by default.
"""
spatial = {
    'model': """
        x : 1 (constant) # x location on 2d grid
        y : 1 (constant) # y location on 2d grid
        """,
    'threshold': "",
    'reset': """ """
    }

# activity
activity = {
    'model': """
        dActivity/dt = -Activity/tauAct : 1

        tauAct : second (constant)
        """,
    'threshold': "",
    'reset': """
        Activity += 1;
        """
    }



# Silicon Neuron as in Chicca et al. 2014
# Author: Moritz Milde
# Code partially adapted from Daniele Conti and Llewyn Salt
# Email: mmilde@ini.uzh.ch
i_model_template = {'model': '''
            dImem/dt = (((Ith_clip / Itau_clip) * (Iin_clip  + Ia_clip - Ishunt_clip - Iahp_clip)) - Ith_clip - ((1 + ((Ishunt_clip + Iahp_clip - Ia_clip) / Itau_clip)) * Imem)) / (tau * ((Ith_clip/(Imem + Io)) + 1)) : amp (unless refractory)

            Iahp      : amp
            Ia        : amp
            Iahp_clip : amp

            Itau_clip = Itau*(Imem>Io) + Io*(Imem<=Io)  : amp
            Ith_clip = Ith*(Imem>Io) + Io*(Imem<=Io)    : amp
            Iin_clip = clip(Iin+Iconst,Io, 1*amp) : amp
            Ia_clip = Ia*(Imem>Io) + 2*Io*(Imem<=Io)    : amp
            Ithahp_clip = Ithahp*(Iahp>Io) + Io*(Iahp<=Io) : amp
            Ishunt_clip = clip(Ishunt, Io, Imem) : amp

            tau = (Cmem * Ut) / (kappa * Itau_clip) : second        # Membrane time constant
            kappa = (kn + kp) / 2 : 1

            Inoise  : amp                                    # Noise due to mismatch

            kn      : 1 (constant)                   # subthreshold slope factor for nFETs
            kp      : 1 (constant)                   # subthreshold slope factor for pFETs
            Ut      : volt (constant)                # Thermal voltage
            Io      : amp (constant)                 # Dark current
            Cmem    : farad (constant)               # Membrane capacitance
            Ispkthr : amp (constant)                         # Spiking threshold
            Ireset  : amp (constant)                 # Reset current
            refP    : second    (constant)           # refractory period (It is still possible to set it to False)
            Ith     : amp (constant)                         # DPI threshold (low pass filter).
            Itau    : amp (constant)                         # Leakage current
            Iconst  : amp (constant)                         # Additional input current similar to constant current injection
            Ishunt  : amp (constant)                         # Shunting inhibitory current (directly affects soma)
            Ica     : amp (constant)

         ''',
                    'threshold': "Imem > Ispkthr",
                    'reset': "Imem = Ireset;"}

i_model_template_params = {
    "Inoise": constants.I0,
    "Iconst": constants.I0,
    "kn": constants.KAPPA_N,
    "kp": constants.KAPPA_P,
    "Ut": constants.UT,
    "Io": constants.I0,
    "Cmem": 1.5 * pF,
    # ---------------------------------------------------------
    # Positive feedback parameters
    # ---------------------------------------------------------
    "Ia": constants.I0,                                # Feedback current
    # rest set in exponenctial integratin
    # ---------------------------------------------------------
    # Adaptative and Calcium parameters
    # ---------------------------------------------------------
    "Ica": constants.I0,
    "Iahp": constants.I0,                                # Adaptation current
    # ---------------------------------------------------------
    # Shunting inhibition
    # ---------------------------------------------------------
    "Ishunt": constants.I0,
    "Ispkthr": 1. * nA,
    "Ireset": 0.6 * pA,
    "Ith": 0.9 * pA,
    "Itau": 8 * pA,
    "refP": 1 * ms,
}

# noise
i_noise = {
    'model': """
         %Inoise = b * (sigma * randn() + mu) : amp (constant over dt)
         b = sign(2 * rand() -1)              : 1   (constant over dt)

         mu    : amp
         sigma : amp
         """,
    'threshold': "",
    'reset': """
         """
}

i_noise_params = {
    "mu": 0.25 * pA,
    "sigma": 0.1 * pA
}

# Positive feedback current
i_a = {
    'model': """
         %Ia = Iagain / (1 + exp(-(Imem - Iath) / Ianorm)) : amp
         %Ia_clip = Ia*(Imem>Io) + 2*Io*(Imem<=Io)         : amp

         Iagain : amp (constant)
         Iath   : amp (constant)
         Ianorm : amp (constant)
         """,
    'threshold': "",
    'reset': """
         """
}

i_a_params = {
    "Iath": 0.5 * nA,
    "Iagain": 50. * pA,
    "Ianorm": 10. * pA
}

# adaptation
i_ahp = {'model': """
          %dIahp/dt = (- Ithahp_clip - Iahp + 2*Io*(Iahp<=Io)) / (tauahp * (Ithahp_clip / Iahp + 1)) : amp # adaptation current
          %Iahp_clip = Iahp*(Imem>Io) + Io*(Imem<=Io)  : amp
          tauahp = (Cahp * Ut) / (kappa * Itauahp) : second # time constant of adaptation
          Iahpmax = (Ica / Itauahp) * Ithahp_clip : amp     # Ratio of currents through diffpair and adaptation block
          Ithahp : amp (constant)
          Itauahp : amp (constant)
          Cahp : farad (constant)
         """,
         'threshold': '',
         'reset': '''
             Iahp += Iahpmax;
                  '''}
# gain modulation
i_gm = {'model': """
          dIpred/dt = (1 - Ipred)/tau_pred  : 1
          tau_pred : second (constant)
          """,
        'threshold': '',
        'reset': ''
        }


i_gm_params = {'Ipred': 1.0,
               'tau_pred': 1.5 * ms
               }

# Keep track of the Imem activity. Usefull with run regular functions.
i_act = {'model': """
          normalized_activity_proxy : 1
          activity_proxy : amp
          """,
         'threshold': '',
         'reset': """
       """
         }

i_ahp_params = {
    "Itauahp": 1 * pA,
    "Ithahp": 1 * pA,
    "Ica": 2 * pA,
    "Cahp": 1 * pF
}

i_exponential_params = {
    "Ith": 0.9 * pA,
    "Iath": 0.5 * nA,
    "Iagain": 50 * pA,
    "Ianorm": 10 * pA,
    "Itau": 8 * pA
}

i_non_leaky_params = {
    "Itau": constants.I0
}

none_model = {
    'model': """
         """,
    'threshold': "",
    'reset': """
         """
    }

none_params = {}

"""LIF neuron model with stochastic decay taken from Wang et al. (2018).
Please refer to this paper for more information. Note that this model was
conceptualized in discrete time with backward euler scheme and an integer
operation. An state updader with x_new = f(x,t) and
defaultclock.dt = 1*ms in the code using this model.
"""
q_model_template = {
    'model': '''
        dVm/dt = (int(not refrac)*int(normal_decay) + int(refrac)*int(refractory_decay))*mV/second : volt
        normal_decay = clip(dec_term1 - dec_term2 - dec_term3 + Vrest/mV + g_psc*I/mV + Vm_noise/mV, Vrest/mV, Vm_max) : 1
        refractory_decay = clip(refrac_dec_term1 - refrac_dec_term2 + Vrest/mV, 0, Vrest/mV) : 1

        dec_term1 = clip(stochastic_decay(Vm/mV, decay_numerator, rand_num_bits), Vrest/mV, Vm_max) : 1 (constant over dt)
        dec_term2 = stochastic_decay(Vrest/mV, decay_numerator, rand_num_bits) : 1 (constant over dt)
        dec_term3 = stochastic_decay(g_psc*I/mV, decay_numerator, rand_num_bits) : 1 (constant over dt)
        refrac_dec_term1 = stochastic_decay(Vm/mV, refrac_decay_numerator, rand_num_bits) : 1 (constant over dt)
        refrac_dec_term2 = stochastic_decay(Vrest/mV, refrac_decay_numerator, rand_num_bits) : 1 (constant over dt)

        I = clip(I_syn + Iconst, I_min, I_max) : amp
        dI_syn/dt = int(syn_dec_term1)*mA/second : amp
        syn_dec_term1 = stochastic_decay(I_clip/mA, syn_decay_numerator, rand_num_bits) : 1 (constant over dt)
        I_clip = clip(I_syn, I_min, I_max) : amp

        refrac = Vm<Vrest                                    : boolean

        g_psc                : ohm    (constant) # Gain of post synaptic current
        Iconst  : amp                         # constant input current
        Iin0 : amp
        Vm_noise          : volt
        tau               : second (constant)
        tausyn               : second (constant)
        refrac_tau        : second (constant)
        refP              : second
        rand_num_bits     : 1     (constant, shared)
        Vthr              : volt   (constant)
        Vm_max            : 1      (constant)
        I_min            : amp      (constant)
        I_max            : amp      (constant)
        Vrest             : volt   (constant)
        Vreset            : volt   (constant)
        decay_numerator : 1 (constant) # L in L/256 describing decay
        refrac_decay_numerator : 1 (constant) # L in L/256 describing decay
        syn_decay_numerator : 1 (constant) # L in L/256 describing decay


    ''',
    'threshold': '''Vm>=Vthr''',
    'reset': '''
        Vm=Vreset;
        Vm_noise = 0*mV''',
}

q_model_template_params = {
    'rand_num_bits': 4,
    'Vthr': 15*mV,
    'Vm_max': 15,
    'I_min': -15*mA,
    'I_max': 15*mA,
    'Vrest': 3*mV,
    'Vreset': 0*mV,
    'Iconst': 0*pA,
    'g_psc' : 1*ohm,
    'tau': 19*ms,
    'decay_numerator': 243,
    'refrac_tau': 2*ms,
    'refrac_decay_numerator': 154,
    'refP': 0.*ms,
    'Vm_noise': 0*mV,
    'tausyn': 3*ms,
    'syn_decay_numerator': 192,
    }

# Use lfsr to generate random numbers. Function must be added to namespace
lfsr = {
    'model': """
        %decay_probability = lfsr_timedarray( ((seed+t) % lfsr_max_value) + lfsr_init ) / (2**lfsr_num_bits) : 1

        lfsr_max_value : second
        seed : second
        lfsr_init : second
        lfsr_num_bits : 1 # Number of bits in the LFSR used
         """,
    'threshold': "",
    'reset': """
         """
    }
lfsr_params = {
    'lfsr_num_bits': 6
    }

modes = {
    'current': i_model_template,
    'voltage': v_model_template,
    'quantized': q_model_template
    }

current_equation_sets = {
    'calcium_feedback': i_ahp,
    'exponential': i_a,
    'leaky': none_model,
    'non_leaky': none_model,
    'quadratic': none_model,
    'spatial': spatial,
    'gaussian': i_noise,
    'none': none_model,
    'linear': none_model,
    'gain_modulation': i_gm,
    'activity': i_act}

voltage_equation_sets = {
    'calcium_feedback': v_adapt,
    'exponential': v_exp_current,
    'quadratic': v_quad_current,
    'leaky': v_leak,
    'non_leaky': none_model,
    'spatial': spatial,
    'gaussian': v_noise,
    'none': none_model,
    'linear': none_model,
    'threshold_adaptation': thr_adapt
    }

quantized_equation_sets = {
    'none': none_model,
    'spatial': spatial,
    'lfsr': lfsr,
    'threshold_adaptation': quantized_thresh_adapt
    }

current_parameters = {
    'current': i_model_template_params,
    'calcium_feedback': i_ahp_params,
    'quadratic': none_params,
    'exponential': i_exponential_params,
    'leaky': none_params,
    'non_leaky': i_non_leaky_params,
    'spatial': none_params,
    'gaussian': i_noise_params,
    'none': none_params,
    'linear': none_params,
    'gain_modulation': i_gm_params,
    'activity': none_params
    }

voltage_parameters = {
    'voltage': v_model_template_params,
    'calcium_feedback': v_adapt_params,
    'exponential': v_exp_current_params,
    'quadratic': v_quad_params,
    'leaky': v_leak_params,
    'non_leaky': none_params,
    'spatial': none_params,
    'gaussian': none_params,
    'none': none_params,
    'linear': none_params,
    'threshold_adaptation': thr_adapt_params
    }

quantized_parameters = {
    'quantized': q_model_template_params,
    'none': none_params,
    'spatial': none_params,
    'lfsr': lfsr_params,
    'threshold_adaptation': thr_adapt_params
    }
