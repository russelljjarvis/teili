******
Models
******
Teili comes equipped with pre-build neuron and synapse models.
Example models can be found in your **teiliApps** folder after successful
installation.
Below we provide a brief overview of the different keywords and properties.
Examples how the pre-build and the dynamic models can be used in your simulations
can be found in ``~/teiliApps/examples/neuron_synapse_tutorial.py`` and
``~/teiliApps/examples/neuron_synapse_builderobj_tutorial.py``


Neurons
=======

As in brian2_ we provide a ``Neuron`` class which inherits from brian2's ``NeuronGroup`` class.
The required keyword arguments are the same as described in brian2's `neuron tutorial`_.
See below a example use case of pre-defined ``neuron_models``.
For static ``neuron_model`` usage please refer to 
``~/teiliApps/examples/neuron_synapse_builderobj_tutorial.py``.

.. code-block:: python

    from teili import Neurons
    from teili.models.neuron_models import DPI as neuron_model

    test_neurons = Neurons(2, equation_builder=neuron_model(num_inputs=2),
                            name="test_neurons")

where **num_inputs** defines how many distinct inputs the ``NeuronGroup`` is expecting.
This allows us to potentially treat each synaptic connection as independent and don't
perform a linear summation before the respective current is injected into the neuron.
For many simulations this is an unnecessary feature as most models expect a linear summation
of all synaptic inputs.
By defining the number of inputs explicitly, however, one can study branch specific inputs
with a distribution of synaptic time constants which are asynchronously integrated.

Each model, whether ``Neuron`` or ``Connection`` is internally generated dynamically
using the NeuronEquationBuilder_ or SynapseEquationBuilder_

An example of the ``neuron_model`` class is shown below:

.. code-block:: python

    class DPI(NeuronEquationBuilder):
        """This class provides you with all equations to simulate a current-based
        exponential, adaptive leaky integrate and fire neuron as implemented on
        the neuromorphic chips by the NCS group. The neuronmodel follows the DPI neuron
        which was published in 2014 (Chicca et al. 2014).
        """

        def __init__(self, num_inputs=1):
            """This initializes the NeuronEquationBuilder with DPI neuron model.

            Args:
                num_inputs (int, optional): Description
            """
            NeuronEquationBuilder.__init__(self, base_unit='current', adaptation='calcium_feedback',
                                          integration_mode='exponential', leak='leaky',
                                          position='spatial', noise='none')
            self.add_input_currents(num_inputs)

The ``NeuronEquationBuilder`` expects the following keyword arguments:
* **base_unit**: Either set to ``current`` or ``voltage`` depinding if you want to simulate current-based hardware neuron models
* **adatation**: Toggles spike-frequency adaptation mechanism in ``neuron_model``
* **integration_mode**: Can be either set to ``linear``, ``quadratic`` or ``exponential``
* **leak**: Toggles leaky integration
* **position**: Adds positional x, y attribute to neuron in order to spatially arrange the neurons
* **noise**: Adds constant noise to ``neuron_model``

The reason behind this is that the ``EquationBuilder`` has access to a set of templates defined in ``teili/models/builder/templates/`` such that the same neuron model can easily be simulated w/ and w/o leak for example. Of course we offer the possibility for work-around so that statically defined models can be simulated. For details please refer to the tutorial_

Let's connect neurons to one another


Connections
===========

As in brian2_ we provide a ``Connections`` class which inherits from brian2's ``Synapses`` class.
The required keyword arguments are the same as described in brian2's `synapse tutorial`_.
See below a example use case of pre-defined ``synapse_models``.
For static ``syapse_model`` usage please refer to 
``~/teiliApps/examples/neuron_synapse_builderobj_tutorial.py``.

.. code-block:: python

  from teili.core.groups import Neurons, Connections
  from teili.models.synapse_models import DPISyn as syn_model

  test_synapse = Connections(test_neurons1, test_neurons2,
                             equation_builder=syn_model(),
                             name="test_synapse")



Each model, whether ``Neuron`` or ``Connection`` is internally generated dynamically
using the NeuronEquationBuilder_ or SynapseEquationBuilder_

An example of the ``synapse_model`` class is shown below:

.. code-block:: python

  class DPISyn(SynapseEquationBuilder):
      """This class provides you with all the equations to simulate a Differential Pair
      Integrator (DPI) synapse as published in Chicca et al. 2014.
      """

      def __init__(self):
          """This class provides you with all the equations to simulate a Differential Pair
          Integrator (DPI) synapse as published in Chicca et al. 2014.
          """
          SynapseEquationBuilder.__init__(self, base_unit='DPI',
                                          plasticity='non_plastic')

The ``SynapseEquationBuilder`` expects the following keyword arguments:
* **base_unit**: Either set to ``current`` or ``conductance`` depending if you want to simulate current-based hardware neuron models. this keyword argument can also be set to ``DPI`` or ``DPIShunting`` for specific hardware model simulation.
* **kernel**: Can be either set to ``exponential``, ``alpha`` or ``resonant`` which ultimately sets the shape of the EPSC and IPSC repectively.
* **plasticity**: This keyword argument lets you easily generate any ``synapse_model`` with an either ``stdp`` or ``fusi`` learning rule. 

The reason behind this is that the ``EquationBuilder`` has access to a set of templates defined in ``teili/models/builder/templates/`` such that the same ``synapse_model`` can easily be simulated w/ and w/o plasticity or different plasticity rules for example.
Of course we offer the possibility for work-around so that statically defined models can be simulated.
For details please refer to the `plasticity tutorial`_

.. note:: TBA Contributing guide for new templates

.. _tutorial: https://teili.readthedocs.io/en/latest/scripts/Tutorials.html#import-equation-from-a-file
.. _plasticity tutorial: https://teili.readthedocs.io/en/latest/scripts/Tutorials.html#stdp-tutorial
.. _neuron tutorial: https://brian2.readthedocs.io/en/stable/resources/tutorials/1-intro-to-brian-neurons.html
.. _syapse tutorial: https://brian2.readthedocs.io/en/stable/resources/tutorials/2-intro-to-brian-synapses.html
.. _brian2: https://brian2.readthedocs.io/en/stable/index.html