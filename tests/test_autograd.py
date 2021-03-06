import minpy.numpy as mp
import numpy as np
import minpy.dispatch.policy as policy
from minpy.core import wraps, grad_and_loss, minpy_to_numpy as mn, numpy_to_minpy as nm
import time

# mp.set_policy(policy.OnlyNumPyPolicy())

@wraps()
def minpy_rnn_step_forward(x, prev_h, Wx, Wh, b):
    next_h = mp.tanh(x.dot(Wx) + prev_h.dot(Wh) + b)
    return next_h


def rel_error(x, y):
  """ returns relative error """
  return np.max(np.abs(x - y) / (np.maximum(1e-8, np.abs(x) + np.abs(y))))


def rnn_step_forward(x, prev_h, Wx, Wh, b):
    next_h = np.tanh(prev_h.dot(Wh) + x.dot(Wx) + b)
    cache = next_h, prev_h, x, Wx, Wh
    return next_h, cache


def rnn_step_backward(dnext_h, cache):
  dx, dprev_h, dWx, dWh, db = None, None, None, None, None
  # Load values from rnn_step_forward
  next_h, prev_h, x, Wx, Wh = cache
  # Gradients of loss wrt tanh
  dtanh = dnext_h * (1 - next_h * next_h)  # (N, H)
  # Gradients of loss wrt x
  dx = dtanh.dot(Wx.T)
  # Gradients of loss wrt prev_h
  dprev_h = dtanh.dot(Wh.T)
  # Gradients of loss wrt Wx
  dWx = x.T.dot(dtanh)  # (D, H)
  # Gradients of loss wrt Wh
  dWh = prev_h.T.dot(dtanh)
  # Gradients of loss wrt b. Note we broadcast b in practice. Thus result of
  # matrix ops are just sum over columns
  db = dtanh.sum(axis=0)  # == np.ones([N, 1]).T.dot(dtanh)[0, :]
  return dx, dprev_h, dWx, dWh, db


# preparation
N, D, H = 4, 5, 6
x = np.random.randn(N, D)
h = np.random.randn(N, H)
Wx = np.random.randn(D, H)
Wh = np.random.randn(H, H)
b = np.random.randn(H)
out, cache = rnn_step_forward(x, h, Wx, Wh, b)
dnext_h = np.random.randn(*out.shape)

# test MinPy
start = time.time()
rnn_step_forward_loss = lambda x, h, Wx, Wh, b, dnext_h: minpy_rnn_step_forward(x, h, Wx, Wh, b) * nm(dnext_h)
grad_loss_function = wraps('numpy')(grad_and_loss(rnn_step_forward_loss, xrange(5)))
grad_arrays = grad_loss_function(x, h, Wx, Wh, b, dnext_h)[0]
end = time.time()
print "MinPy total time elapsed:", end - start

# test NumPy
start = time.time()
out, cache = rnn_step_forward(x, h, Wx, Wh, b)
dx, dprev_h, dWx, dWh, db = rnn_step_backward(dnext_h, cache)
out *= dnext_h # to agree with MinPy calculation
end = time.time()
print "NumPy total time elapsed:", end - start

print
print "Result Check:"
print 'dx error: ', rel_error(dx, grad_arrays[0])
print 'dprev_h error: ', rel_error(dprev_h, grad_arrays[1])
print 'dWx error: ', rel_error(dWx, grad_arrays[2])
print 'dWh error: ', rel_error(dWh, grad_arrays[3])
print 'db error: ', rel_error(db, grad_arrays[4])
