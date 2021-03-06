
***************
Developing Building Blocks
***************

This section explains the generation of new and more complex ``BuildingBlocks``.
An example of such a ``BuildingBlock``  can be found in the `Building Block`_ documentation, as well as in the respective `advanced tutorials`_ such as the ``threeway network`` or the ``OCTA network``.

Every building block inherits from the class ``BuildingBlocks`` which has attributes
such as ``sub_blocks``, ``input_groups``, ``output_groups`` and ``hidden_groups``.

Recommended practices for creating custom ``BuildingBlocks`` are as follow:

- Keep the class initialization as concise as possible.
- Create a generation function which implements the desired connectivity.
- Label correctly ``sub_blocks``, ``input_groups``, ``output_groups`` and ``hidden_groups``.
- Remember to ``_set_tags`` as you expand the network and its functionality; it really helps to keep track of the properties of individual groups.

Important Notes:

- When running the network, add the newly generated ``BuildingBlock`` as well as all the ``sub_blocks`` the network depends on.

.. code-block:: python
   Net.add(
          test_net,
          test_net.sub_blocks['sub_block_1'],
          test_net.sub_blocks['sub_block_2']
        )

- There is a fundamental difference between the attributes ``groups`` and ``_groups``. ``_groups``  is a dictionary containing the objects specific to that ``BuildingBlock``. ``groups`` is a property of the ``BuildingBlock`` class which returns all ``_groups`` included in the ``BuildingBlock`` and its ``sub_blocks``.

- When overwriting an existing population in one of the ``sub_blocks._groups``, remember to re-initialize all the ``Connections`` and ``monitors`` regarding that population. Which will now be specific to the parent class.

Have fun developing your own ``BuildingBlocks`` and advancing neuroscience! :)

.. _Building Block: https://teili.readthedocs.io/en/latest/scripts/Building%20Blocks.html
.. _advanced tutorials: https://teili.readthedocs.io/en/latest/scripts/Advanced%20tutorials.html#
