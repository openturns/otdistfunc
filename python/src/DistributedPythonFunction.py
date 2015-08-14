import openturns as ot

class DistributedPythonFunction(object):
    def __init__(self, x):
        self.x_ = x
        
    def square(self, y):
        square = ot.NumericalPoint()
        for i in range(len(y)):
             square.add(y[i]**2)
        return square
  