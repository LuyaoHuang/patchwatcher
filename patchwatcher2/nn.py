#!/usr/bin/env python
import numpy
import math
import time
import scipy.io
import scipy.optimize

def sigmoid(x):
    return (1 / (1 + numpy.exp(-x)))

def dsigmoid(y):
    return y * (1 - y)

class NN:
    def __init__(self, ni, nh, no, lamda=0.0001):
        self.ni = ni
        self.nh = nh
        self.no = no
        self.lamda = lamda

        r = math.sqrt(6) / math.sqrt(ni + nh + 1)

        rand = numpy.random.RandomState(int(time.time()))

        self.limit0 = 0
        self.limit1 = ni * nh
        self.limit2 = ni * nh + nh * no
        self.limit3 = ni * nh + nh * no + nh
        self.limit4 = ni * nh + nh * no + nh + no

        wi = rand.uniform(low = -r, high = r, size = (nh, ni))
        wo = rand.uniform(low = -r, high = r, size = (no, nh))
        bi = numpy.zeros((nh, 1))
        bo = numpy.zeros((no, 1))

        self.theta = numpy.concatenate((wi.flatten(), wo.flatten(),
                                        bi.flatten(), bo.flatten()))

    def FPformin(self, X ,theta):
        wi = theta[self.limit0 : self.limit1].reshape(self.nh, self.ni)
        wo = theta[self.limit1 : self.limit2].reshape(self.no, self.nh)
        bi = theta[self.limit2 : self.limit3].reshape(self.nh, 1)
        bo = theta[self.limit3 : self.limit4].reshape(self.no, 1)

        hidden_layer = sigmoid(numpy.dot(wi, X) + bi)
        output_layer = sigmoid(numpy.dot(wo, hidden_layer) + bo)

        return output_layer

    def BPformin(self, theta, X, Y):
        wi = theta[self.limit0 : self.limit1].reshape(self.nh, self.ni)
        wo = theta[self.limit1 : self.limit2].reshape(self.no, self.nh)
        bi = theta[self.limit2 : self.limit3].reshape(self.nh, 1)
        bo = theta[self.limit3 : self.limit4].reshape(self.no, 1)

        hidden_layer = sigmoid(numpy.dot(wi, X) + bi)
        output_layer = sigmoid(numpy.dot(wo, hidden_layer) + bo)

        error = output_layer - Y

        sum_of_squares_error = 0.5 * numpy.sum(numpy.multiply(error, error)) / X.shape[1]
        weight_decay         = 0.5 * self.lamda * (numpy.sum(numpy.multiply(wi, wi)) + numpy.sum(numpy.multiply(wo, wo)))
        cost = sum_of_squares_error + weight_decay

        del_out = numpy.multiply(error, numpy.multiply(output_layer, 1 - output_layer))
        del_hid = numpy.multiply(numpy.dot(numpy.transpose(wo), del_out), numpy.multiply(hidden_layer, 1 - hidden_layer))

        wi_grad = numpy.dot(del_hid, numpy.transpose(X))
        wo_grad = numpy.dot(del_out, numpy.transpose(hidden_layer))
        bi_grad = numpy.sum(del_hid, axis = 1)
        bo_grad = numpy.sum(del_out, axis = 1)
            
        wi_grad = wi_grad / X.shape[1] + self.lamda * wi
        wo_grad = wo_grad / X.shape[1] + self.lamda * wo
        bi_grad = bi_grad / X.shape[1]
        bo_grad = bo_grad / X.shape[1]

        wi_grad = numpy.array(wi_grad)
        wo_grad = numpy.array(wo_grad)
        bi_grad = numpy.array(bi_grad)
        bo_grad = numpy.array(bo_grad)

        theta_grad = numpy.concatenate((wi_grad.flatten(), wo_grad.flatten(),
                                        bi_grad.flatten(), bo_grad.flatten()))

        return [cost, theta_grad]

def testBP2():
    x = numpy.array([[0,0,1],
                     [0,1,1],
                     [1,0,1],
                     [1,1,1]])
    y = numpy.array([[0, 1],
                     [0, 0],
                     [1, 0],
                     [1, 1]])

    x = x.T
    y = y.T
    max_iterations = 400

    nn = NN(x.shape[0], (x.shape[0] + y.shape[0]) + 2, y.shape[0])
    opt = scipy.optimize.minimize(nn.BPformin, nn.theta, 
                                  args = (x,y), method = 'L-BFGS-B',
                                  jac = True, options = {'maxiter': max_iterations})

    print opt.x
    print opt.message
    print nn.FPformin(x, opt.x)

if __name__ == '__main__':
    testBP2()
