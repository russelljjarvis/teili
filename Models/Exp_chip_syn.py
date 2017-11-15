from NCSBrian2Lib.Parameters.Exp_chip_syn_param import parameters

Exp_chip_syn = {'model': """
            dIe_syn/dt = (-Ie_syn) /(tausyne*((Igain/Ie_syn)+1)) - (Igain/(tausyne*((Igain/Ie_syn)+1)))*(Ie_syn>=Io_syn): amp (clock-driven)
            dIi_syn/dt = (-Ii_syn) /(tausyni*((-Igain/Ii_syn)+1)) + (Igain/(tausyni*((-Igain/Ii_syn)+1)))*(Ii_syn<=-Io_syn): amp (clock-driven)

            {Ie}_post = Ie_syn : amp  (summed)
            {Ii}_post = Ii_syn : amp  (summed)

            weight : 1
            wPlast : 1

            baseweight_e : amp (constant)     # synaptic gain
            baseweight_i : amp (constant)     # synaptic gain
            tausyne = Csyn * Ut_syn /(kappa_syn * Itau_e) : second
            tausyni = Csyn * Ut_syn /(kappa_syn * Itau_i) : second
            kappa_syn = (kn_syn + kp_syn) / 2 : 1
            Itau_e : amp
            Itau_i : amp

            Iw_e = weight*baseweight_e  : amp
            Iw_i = weight*baseweight_i  : amp

            Igain : amp

            kn_syn       : 1 (constant)
            kp_syn       : 1 (constant)
            Ut_syn       : volt (constant)
            Io_syn       : amp (constant)
            Csyn         : farad (constant)
            """,
            'on_pre': """
            Ie_syn += Iw_e*Igain*wPlast*(weight>0)/(Itau_e*((Igain/Ie_syn)+1))
            Ii_syn -= Iw_i*Igain*wPlast*(weight<0)/(Itau_i*((Igain/Ii_syn)+1))
            """,
            'on_post': """ """,
            'parameters': parameters
                }
