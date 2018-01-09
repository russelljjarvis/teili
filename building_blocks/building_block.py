#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summary
"""
# @Author: alpren, mmilde
# @Date:   2017-07-27 10:46:44
# @Last Modified by:   mmilde
# @Last Modified time: 2018-01-09 15:20:42
"""
This class ???
"""

from brian2 import asarray
from collections import OrderedDict

# TODO: There is a problem, when 2 BBs of the same kind are added to another BB, as the names collide.
# We could use a hierarchy of blocks


# TODO: Important all Monitors of Building blocks have to be named and named uniquely!
# Otherwise they will not be found, when a Network is rerun in standalone mode after rebuild without recompile

class BuildingBlock:

    """Summary

    Attributes:
        debug (TYPE): Description
        Groups (dict): Description
        monitor (TYPE): Description
        Monitors (dict): Description
        name (TYPE): Description
        neuron_eq_builder (TYPE): Description
        params (TYPE): Description
        standaloneParams (TYPE): Description
        synapse_eq_builder (TYPE): Description
    """

    def __init__(self, name, neuron_eq_builder, synapse_eq_builder, blockParams, debug, monitor=False):
        """Summary

        Args:
            name (TYPE): Description
            neuron_eq_builder (TYPE): Description
            synapse_eq_builder (TYPE): Description
            blockParams (TYPE): Description
            debug (TYPE): Description
            monitor (bool, optional): Description
        """
        self.name = name
        self.neuron_eq_builder = neuron_eq_builder
        self.synapse_eq_builder = synapse_eq_builder
        self.params = blockParams
        self.debug = debug
        self.Groups = {}
        self.Monitors = {}
        self.monitor = monitor
        self.standaloneParams = OrderedDict()

    def __iter__(self):
        """this allows us to iterate over the BrianObjects and directly add the Block to a Network

        Returns:
            TYPE: Description
        """
        allBrianObjects = self.Groups
        if self.monitor:
            allBrianObjects.update(self.Monitors)
        # return iter([{**self.Groups,**self.Monitors}[key] for key in {**self.Groups,**self.Monitors}]) #not Python 2 compatible
        return iter([allBrianObjects[key] for key in allBrianObjects])

    def get_run_args(self):
        """this collects the arguments to cpp main() for stadalone run

        Returns:
            TYPE: Description
        """
        # asarray is to remove units. It is the way proposed in the tutorial
        run_args = [str(asarray(self.standaloneParams[key]))
                    for key in self.standaloneParams]
        return run_args
