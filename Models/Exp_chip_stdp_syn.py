from NCSBrian2Lib.Parameters.Exp_chip_stdp_syn_param import parameters

Exp_chip_stdp_syn = {'model': """
            dIe_syn/dt = -Ie_syn /(tausyne*((Ie_gain/Ie_syn)+1)) - Ie_gain/(tausyne*((Ie_gain/Ie_syn)+1)) +2*Io_syn/(tausyne*((Ie_gain/Ie_syn)+1)) : amp (clock-driven)
            dIi_syn/dt = -Ii_syn /(tausyni*((Ii_gain/Ii_syn)+1)) - Ii_gain/(tausyni*((Ii_gain/Ii_syn)+1)) +2*Io_syn/(tausyni*((Ii_gain/Ii_syn)+1)) : amp (clock-driven)

            {Ie}_post = Ie_syn : amp  (summed)
            {Ii}_post = -Ii_syn : amp  (summed)

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
            Iw_i = weight*baseweight_i  : amp


            Ie_tau       : amp (constant)
            Ii_tau       : amp (constant)
            Ie_th        : amp (constant)
            Ii_th        : amp (constant)
            kn_syn       : 1 (constant)
            kp_syn       : 1 (constant)
            Ut_syn       : volt (constant)
            Io_syn       : amp (constant)
            Csyn         : farad (constant)
            Vdd_syn      : volt (constant)
            Vth_syn      : volt (constant)


            w : 1
            dApre/dt = -Apre / taupre : 1 (event-driven)
            dApost/dt = -Apost / taupost : 1 (event-driven)
            w_max: 1 (shared, constant)
            taupre : second (shared, constant)
            taupost : second (shared, constant)
            diffApre : 1 (shared, constant)
            Q_diffAPrePost : 1 (shared, constant)

            """,

            'on_pre': """
             Ie_syn += Iw_e*Ie_gain*(weight>0)/(Itau_e*((Ie_gain/Ie_syn)+1))
             Ii_syn += Iw_i*Ii_gain*(weight<0)/(Itau_i*((Ii_gain/Ii_syn)+1))

             wPlast = w
             Apre += diffApre*w_max
             w = clip(w + Apost, 0, w_max)
             """,

            'on_post': """
            Apost += -diffApre * (taupre / taupost) * Q_diffAPrePost * w_max
            w = clip(w + Apre, 0, w_max)
            """,
            'parameters': parameters
                     }
