import numpy as np
from teili.tools.sorting import SortMatrix
import random
import copy

import matplotlib.pyplot as plt
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui

# Definitions
n_rows = 50
n_cols = 50
diag_width = 3
max_weight = 15
noise = True
noise_probability = 0.05
conn_probability = 0.6
np.random.seed(26)

test_matrix = np.zeros((n_rows, n_cols))
if max_weight > 1:
    test_matrix = (max_weight*np.random.rand(n_rows, n_cols)).astype(int)
    test_matrix = np.clip(test_matrix, 0, int(max_weight/2))
else:
    test_matrix = (max_weight*np.random.rand(n_rows, n_cols))
    test_matrix = np.clip(test_matrix, 0, max_weight)

# Construct matrix
ids = [x for x in range(n_rows)]
for central_id in ids:
    # Add values on a diagonal with a given width
    add_to_ids = np.arange(central_id-diag_width, central_id+diag_width+1)
    values_to_add = np.array([max_weight for _ in range(2*diag_width+1)])
    # Remove values outside dimensions of matrix
    values_to_add = np.delete(values_to_add, np.append(
        np.where(add_to_ids < 0), np.where(add_to_ids > n_rows-1)))
    add_to_ids = np.delete(add_to_ids, np.append(
        np.where(add_to_ids < 0), np.where(add_to_ids > n_rows-1)))
    try:
        test_matrix[central_id][add_to_ids] = values_to_add
    except IndexError:
        continue

# Add noise
if noise:
    noise_ind = np.where(np.random.rand(n_rows, n_cols) < noise_probability)
    test_matrix[noise_ind] = 0.3

# Test recurrent matrices which need to be shuffled along rows & columns
shuffled_matrix_tmp = np.zeros((n_rows, n_cols))
shuffled_matrix = np.zeros((n_rows, n_cols))
# 32 bits is enough for numbers up to about 4 billion
inds = np.arange(n_cols, dtype='uint32')
np.random.shuffle(inds)
shuffled_matrix_tmp[:, inds] = copy.deepcopy(test_matrix)
shuffled_matrix[inds, :] = shuffled_matrix_tmp

# Add connectivity of recurrent matrix
conn_ind = np.where(np.random.rand(n_rows, n_cols) < conn_probability)
source, target = conn_ind[0], conn_ind[1]
conn_matrix = [[] for x in range(n_cols)]
rec_matrix = [[] for x in range(n_cols)]
for ind, val in enumerate(source):
    conn_matrix[val].append(target[ind])
conn_matrix = np.array(conn_matrix, dtype=object)
for ind_source, ind_target in enumerate(conn_matrix):
    rec_matrix[ind_source] = shuffled_matrix[ind_source, ind_target]
rec_matrix = np.array(rec_matrix, dtype=object)

sorted_matrix1 = SortMatrix(ncols=n_cols, nrows=n_rows, axis=1,
                            matrix=copy.deepcopy(rec_matrix), rec_matrix=True,
                            fill_ids=conn_matrix)
sorted_matrix2 = SortMatrix(ncols=n_cols, nrows=n_rows, axis=1,
                            matrix=copy.deepcopy(shuffled_matrix),
                            rec_matrix=True)

app = QtGui.QApplication.instance()
if app is None:
    app = QtGui.QApplication(sys.argv)
else:
    print('QApplication instance already exists: %s' % str(app))

app = pg.mkQApp()
win = QtGui.QMainWindow()
cw = QtGui.QWidget()
win.setCentralWidget(cw)
layout = QtGui.QGridLayout()
cw.setLayout(layout)

colors = [
    (0, 0, 0),
    (0, 0, 255),
    (0, 255, 0),
    (255, 255, 0)
]
cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 4), color=colors)

image_axis = pg.PlotItem()
image_axis.setLabel(axis='bottom', text='Original matrix')
imv = pg.ImageView(view=image_axis)
imv.setImage(test_matrix)
imv.setColorMap(cmap)
layout.addWidget(imv, 0, 0, 1, 1)

image_axis = pg.PlotItem()
image_axis.setLabel(axis='bottom', text='Shuffled matrix')
imv = pg.ImageView(view=image_axis)
imv.setImage(shuffled_matrix)
imv.setColorMap(cmap)
layout.addWidget(imv, 0, 1, 1, 1)

image_axis = pg.PlotItem()
image_axis.setLabel(axis='bottom', text='Sorted matrix (conn less than 1)')
imv = pg.ImageView(view=image_axis)
imv.setImage(sorted_matrix1.sorted_matrix)
imv.setColorMap(cmap)
layout.addWidget(imv, 1, 0, 1, 1)

image_axis = pg.PlotItem()
image_axis.setLabel(axis='bottom', text='Sorted matrix (conn equals 1)')
imv = pg.ImageView(view=image_axis)
imv.setImage(sorted_matrix2.sorted_matrix)
imv.setColorMap(cmap)
layout.addWidget(imv, 1, 1, 1, 1)

win.show()
app.exec_()
