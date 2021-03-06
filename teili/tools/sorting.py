# -*- coding: utf-8 -*-
"""To understand the structure of in the rasterplots but also in the learned weight matrices, we need to sort the weight matrices according to some similarity measure, such as euclidean and jaccard distance.
However, the sorting algorithm is completely agnostic to the similarity measure. It connects each node with maximum two edges and constructs a directed graph.
This is similar to the travelling salesman problem.

Example:
    In order to use this class you need to initialize it
    either without a filename:

    >>> from teili.tools.sorting import SortMatrix
    >>> import numpy as np
    >>> matrix = np.random.randint((49, 49))
    >>> obj = SortMatrix(nrows=49, matrix=matrix)
    >>> print(obj.matrix)
    >>> print(obj.permutation)
    >>> print(ob.sorted_matrix)

    or instead of using a matrix you can also specify a
    path to a stored matrix:

    >>> filename = '/path/to/your/matrix.npy'
    >>> obj = SortMatrix(nrows=49, filename=filename)
"""
# @Author: Moritz Milde
# @Date:   2018-06-05 11:09:20

import numpy as np
import warnings


class SortMatrix():

    """Class which can sort your  matrix based on similarity

    Attributes:
        filename (str, optional): path/to/matrix/name.npy.
        matrix (ndarray, optional): matrix as provided by load_matrix.
        ncols (int, optional): number of columns of the 2d array.
        nrows (int, required): number of rows of the 2d array.
        permutation (list): List of indices which are more similar to
            each other in (euclidean, jaccard) distance.
        similarity_matrix (ndarray, optional): Matrix containing similarities.
        sorted_matrix (TYPE): Sorted matrix according to permutation.
        recurrent_matrix (boolean, optional): Indicates whether it is
            a recurrent matrix or not.
        similarity_metric (str, optional): Indicates metric for calculating
            similarity.
        max_val (float): Maximum value of the provided matrix
    """

    def __init__(self, nrows, ncols=None, filename=None, matrix=None,
                 axis=0, target_indices=None, rec_matrix=False,
                 similarity_metric='euclidean'):
        """Summary

        Args:
            nrows (int, required): number of rows of the 2d array.
            ncols (int, optional): number of columns of the 2d array.
            filename (str, optional): path/to/matrix/name.npy.
            matrix (ndarray, optional): Instead of providing filename
                and location one can also pass the matrix to sort directly
                to the class.
            axis (int, optional): Axis along which similarity should be
                computed.
            target_indices (list of lists, optional): Must be provided only
                when connections between neurons are sparse. Each row
                contains the postsynaptic targets of a neuron whose index
                is represented by the number of the row.
            rec_matrix (boolean, optional): Informs whether it is the matrix
                represents recurrent connections or not. If it is a recurrent
                matrix, both dimensions will be sorted according to
                permutation.
            similarity_metric (str, optional): Metric used to calculate
                similarity between arrays.
        """
        self.nrows = nrows
        self.ncols = ncols
        self.axis = axis
        self.recurrent_matrix = rec_matrix
        self.similarity_metric = similarity_metric

        if self.ncols is None:
            warnings.warn('Unspecified ncols. Matrix is assumed to be squared')
            self.ncols = self.nrows

        self.filename = filename
        # Load reshaped matrix. Dimensions are specified via nrwos, ncols
        if matrix is None:
            self.matrix = self.load_matrix()
        elif matrix is not None:
            if target_indices is None:
                self.matrix = np.reshape(matrix, (self.nrows, self.ncols))
            elif target_indices is not None:
                # Fill un-connected inputs with zero
                filled_matrix = np.zeros((self.nrows, self.ncols))
                for i in range(self.nrows):
                    filled_matrix[i, target_indices[i][:]] = matrix[i][:]
                self.matrix = filled_matrix
        self.max_val = np.max(self.matrix)

        # Compute similarity along specified axis
        self.similarity_matrix = self.get_similarity_matrix(axis=axis)
        # Get permutation along specified axis
        self.permutation = self.get_permutation(axis=axis)
        # Sort matrix
        self.sorted_matrix = self.sort_matrix()

    def load_matrix(self):
        """Load matrix from .npy file

        Returns:
            ndarray: loaded matrix from file.
        """

        # if self.filename is not None:
        try:
            matrix = np.load(self.filename)
        except TypeError:
            raise TypeError('Invalid filename. Please specify a valid path and filename.')

        self.matrix = matrix.reshape((self.nrows, self.ncols))
        return self.matrix

    def compute_distance(self, x, y, similarity_metric, threshold=.8):
        """This function returns the distance
        of any to vectors x and y

        Args:
            x (ndarray, required): 1d vector.
            y (ndarray, required): 1d vector.
            similarity_metric (str, required): Metric used to measure similarity

        Returns:
            ndarray: Element-wise distance of two 1d vectors.
        """
        if similarity_metric == 'euclidean':
            dist = np.linalg.norm(x - y)
        elif similarity_metric == 'jaccard':
            x_elements = np.where(x > self.max_val*threshold)[0]
            y_elements = np.where(y > self.max_val*threshold)[0]
            intersection = len(list(set(x_elements).intersection(y_elements)))
            union = (len(x_elements) + len(y_elements)) - intersection
            dist = (1 - float(intersection) / union)
        else:
            raise ValueError

        return dist

    def get_similarity_matrix(self, axis=0):
        """This function computes a similarity matrix of a given
        matrix.

        Args:
            axis (int, optional): Axis along which similarity should be
                computed.

        Returns:
            ndarray: Matrix containing similarities.
        """

        self.similarity_matrix = np.zeros(
            (np.size(self.matrix, axis), np.size(self.matrix, axis))) * np.nan
        # Loop through both dimensions of the specified matrix
        # and compute the distance between every pairs of vectors

        for index_i in range(np.size(self.matrix, axis)):
            if axis == 0:
                reference_vector = self.matrix[index_i, :]
            else:
                reference_vector = self.matrix[:, index_i]
            for index_j in range(np.size(self.matrix, axis)):
                if index_i != index_j:
                    if axis == 0:
                        comparison_vector = self.matrix[index_j, :]
                    else:
                        comparison_vector = self.matrix[:, index_j]
                    self.similarity_matrix[index_i, index_j] = self.compute_distance(
                        reference_vector, comparison_vector,
                        self.similarity_metric)
                else:
                    self.similarity_matrix[index_i, index_j] = np.inf
        return self.similarity_matrix

    def get_permutation(self, axis=0):
        """To sort a given matrix according to its similarity we need to construct
        permutation indices, which are used to sort the matrix. First we find the most
        similar entry in the similarity matrix. This function allows each node in the similarity
        graph to be only used twice, i.e. each node has maximally two edges connected to it.
        The vector 'degree' keeps track of this. To prevent a loop closure in the similarity graph
        a proxy vector called 'partner' is used to set the distance between the two ends of the
        similarity graph to infinity.

        Args:
            axis (int, optional): Axis along which similarity should be
                computed.

        Returns:
            list: Vector of permuted indices.
        """
        similarity_matrix = np.array(self.similarity_matrix)
        steps = []
        degree = np.zeros((np.size(similarity_matrix, 0)))
        # diagonal was already set to infinity
        partner = np.arange(np.size(similarity_matrix, 0))
        while(len(steps) <= np.size(similarity_matrix, 0) - 1):
            # Get the index (tuple) of the most similar entry in the similarity
            # matrix
            ind_nearest = np.unravel_index(
                np.argmin(similarity_matrix, axis=None),
                similarity_matrix.shape)
            # Define the two to be connected nodes
            vertexA = ind_nearest[0]  # we gonna draw an edge between A and B
            vertexB = ind_nearest[1]
            # Increase the (connectivity) degree of these nodes by one
            degree[vertexA] += 1
            degree[vertexB] += 1
            # Draw an edge between the nodes
            steps.append(ind_nearest)  # the bag of edges

            # don't use anything more than twice
            ind2exclude = np.where(degree >= 2)
            similarity_matrix[ind2exclude, :] = np.inf
            similarity_matrix[:, ind2exclude] = np.inf

            # To prevent loop closure identify the two ends of the graph
            endA = partner[vertexA]
            endB = partner[vertexB]
            # Re-asign the partners of the ends
            partner[endA] = endB
            partner[endB] = endA
            # Set the distance between the new ends of the graph to infinity
            similarity_matrix[endA, endB] = np.inf
            similarity_matrix[endB, endA] = np.inf
            # Break condition that stops the construction of the graph as soon
            # as every node except the two end points are connected twice
            if np.sum(degree) >= np.size(similarity_matrix, 0) * 2 - 2:
                break

        # Now that the graph is defined in steps, we can construct the
        # permutation indices
        self.permutation = []
        # Pick one end of the graph and define as start node
        start_ind = np.where(degree == 1)
        start_node = start_ind[0][0]
        self.permutation.append(start_node)

        while(len(steps) > 0):
            # Find the corresponding node which is the end node for the current
            # edge
            corresponding_tuple = [
                item for item in steps if start_node in item]

            if corresponding_tuple[0][0] == start_node:
                end_node = corresponding_tuple[0][1]
            else:
                end_node = corresponding_tuple[0][0]
            # Remove nodes from steps
            steps = [index_i for index_i in steps if index_i !=
                     corresponding_tuple[0]]
            # Add end node of the edge to the list of permutation
            self.permutation.append(end_node)
            # Set the end_node of the edge to be the start_node of the next
            # edge
            start_node = end_node
        return self.permutation

    def sort_matrix(self):
        """This function returns the sorted matrix given
        the permutation indices.

        Returns:
            ndarray: Sorted matrix according to similarity.
        """
        if len(self.permutation) == 0:
            self.permutation = self.get_permutation(axis=self.axis)
        tmp_matrix = np.array(self.matrix)
        if self.recurrent_matrix:
            # First sort each row
            for row in range(len(self.permutation)):
                tmp_matrix[row] = tmp_matrix[row][self.permutation]
            # Second sort each column
            self.sorted_matrix = tmp_matrix[self.permutation]
        else:
            if self.axis == 0:
                self.sorted_matrix = tmp_matrix[self.permutation, :]

            else:
                self.sorted_matrix = tmp_matrix[:, self.permutation]

        return self.sorted_matrix
